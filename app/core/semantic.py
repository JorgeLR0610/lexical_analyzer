#type: ignore
from typing import Optional, Any
from core.lexer import MyLexer
from core.parser import MyParser
from api.schemas import SemanticResponse, SymbolResponse


class SymbolRecord:
    def __init__(self, name: str, data_type: str, scope: str, line: Optional[int] = None):
        self.name = name
        self.data_type = data_type
        self.scope = scope
        self.line = line

    def to_schema(self) -> SymbolResponse:
        return SymbolResponse(
            name=self.name,
            data_type=self.data_type,
            scope=self.scope,
            line=self.line
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "data_type": self.data_type,
            "scope": self.scope,
            "line": self.line
        }

    def __repr__(self):
        return f"Symbol({self.name}, tipo={self.data_type}, scope={self.scope}, linea={self.line})"


class Scope:
    def __init__(self, name: str, parent: Optional['Scope'] = None):
        self.name = name
        self.parent = parent
        self.symbols: dict[str, SymbolRecord] = {}

    def define(self, name: str, data_type: str, line: Optional[int] = None) -> tuple[bool, Optional[str]]:
        if name in self.symbols:
            line_str = f" en línea {line}" if line else ""
            return False, f"Error semántico{line_str}: identificador '{name}' ya ha sido declarado en el ámbito '{self.name}'"
        sym = SymbolRecord(name, data_type, self.name, line)
        self.symbols[name] = sym
        return True, None

    def lookup(self, name: str) -> Optional[SymbolRecord]:
        if name in self.symbols:
            return self.symbols[name]
        if self.parent:
            return self.parent.lookup(name)
        return None

    def lookup_current(self, name: str) -> Optional[SymbolRecord]:
        return self.symbols.get(name)


class SemanticAnalyzer:
    NUMERIC_INT_TYPES = {"int", "int8", "int16", "int32", "int64", "uint", "uint8", "uint16", "uint32", "uint64", "byte", "rune"}
    NUMERIC_FLOAT_TYPES = {"float32", "float64"}
    NUMERIC_TYPES = NUMERIC_INT_TYPES | NUMERIC_FLOAT_TYPES

    OP_DISPLAY = {
        'EQ': '==', 'NEQ': '!=', 'LT': '<', 'LE': '<=', 'GT': '>', 'GE': '>=',
        'AND': '&&', 'OR': '||', 'NOT': '!'
    }

    def __init__(self):
        self.errors: list[str] = []
        self.all_symbols: list[SymbolRecord] = []
        self.line_positions: dict[int, int] = {}
        self.global_scope = Scope("global")
        self.current_function_return: Optional[str] = None
        self.current_function_name: Optional[str] = None
        self._init_builtins()

    def _init_builtins(self):
        # Tipos primitivos
        for t in ["int", "string", "bool", "float64", "float32", "byte", "rune", "uint", "error", "any"]:
            self.global_scope.define(t, "type", 1)
        # Constantes predefinidas
        self.global_scope.define("true", "bool", 1)
        self.global_scope.define("false", "bool", 1)
        self.global_scope.define("nil", "nil", 1)
        # Funciones predefinidas comunes
        for fn in ["println", "print", "len", "cap", "make", "append", "panic", "recover"]:
            self.global_scope.define(fn, "builtin_func", 1)

    def _get_line(self, node) -> int:
        if not node:
            return 1
        if isinstance(node, tuple):
            if id(node) in self.line_positions:
                return self.line_positions[id(node)]
            for child in node[1:]:
                if isinstance(child, tuple) and id(child) in self.line_positions:
                    return self.line_positions[id(child)]
        return 1

    def _record_symbol(self, scope: Scope, name: str, data_type: str, line: int) -> bool:
        ok, err = scope.define(name, data_type, line)
        if not ok:
            self.errors.append(err)
            return False
        self.all_symbols.append(scope.symbols[name])
        return True

    def analyze(self, ast, line_positions: dict[int, int]) -> tuple[bool, list[str], list[SymbolResponse]]:
        self.errors = []
        self.all_symbols = []
        self.line_positions = line_positions
        self.global_scope = Scope("global")
        self.current_function_name = None
        self.current_function_return = None
        self._init_builtins()

        if not ast or not isinstance(ast, tuple) or ast[0] != 'program':
            return False, ["AST no válido para análisis semántico"], []

        top_levels = ast[1]

        # Paso 1: Declaraciones a nivel global (paquete, imports, structs y firmas de funciones)
        for item in top_levels:
            if not isinstance(item, tuple):
                continue
            tag = item[0]
            line = self._get_line(item)

            if tag == 'package':
                sym = SymbolRecord(item[1], "package", "global", line)
                self.all_symbols.append(sym)
            elif tag == 'import_single':
                pkg_name = item[1].strip('"').strip('`')
                self._record_symbol(self.global_scope, pkg_name, "package", line)
            elif tag == 'import_multi':
                for imp in item[1]:
                    if isinstance(imp, tuple):
                        self._record_symbol(self.global_scope, imp[0], "package", line)
                    else:
                        pkg_name = str(imp).strip('"').strip('`')
                        self._record_symbol(self.global_scope, pkg_name, "package", line)
            elif tag == 'type_struct':
                self._record_symbol(self.global_scope, item[1], "struct", line)
            elif tag == 'type_alias':
                self._record_symbol(self.global_scope, item[1], str(item[2]), line)
            elif tag == 'func':
                ret = item[3] or "void"
                param_types = [str(p[1]) for p in item[2]] if item[2] else []
                func_type = f"func({','.join(param_types)})->{ret}"
                self._record_symbol(self.global_scope, item[1], func_type, line)

        # Paso 2: Análisis de cuerpos de funciones, variables globales y verificación de tipos
        for item in top_levels:
            if not isinstance(item, tuple):
                continue
            tag = item[0]
            line = self._get_line(item)

            if tag == 'func':
                func_name = item[1]
                params = item[2]
                ret_type = item[3] or "void"
                block = item[4]

                self.current_function_name = func_name
                self.current_function_return = ret_type

                func_scope = Scope(f"local:{func_name}", self.global_scope)

                if params:
                    for p in params:
                        p_name = p[0]
                        p_type = str(p[1])
                        p_line = self._get_line(p) or line
                        self._record_symbol(func_scope, p_name, p_type, p_line)

                if block:
                    self._analyze_block(block, func_scope)

                # Si la función declara un tipo de retorno (no void) y no contiene sentencia return
                if ret_type != "void":
                    if not self._has_return_statement(block):
                        self.errors.append(f"Error semántico en línea {line}: falta sentencia 'return' en la función '{func_name}' que declara retorno de tipo '{ret_type}'")

                self.current_function_name = None
                self.current_function_return = None
            elif tag in ('var_init', 'var_typed', 'var_inferred', 'const_typed', 'const_inferred', 'short_var', 'assign', 'if', 'for_clause', 'call_stmt'):
                self._analyze_statement(item, self.global_scope)

        # Filtrar tipos nativos y funciones internas para la tabla del usuario
        user_symbols = [
            s.to_schema() for s in self.all_symbols
            if s.data_type not in ("builtin_func", "type") or s.scope != "global" or s.data_type == "struct"
        ]

        return len(self.errors) == 0, self.errors, user_symbols

    def _has_return_statement(self, node) -> bool:
        if not node or not isinstance(node, tuple):
            return False
        tag = node[0]
        if tag == 'return':
            return True
        if tag == 'block':
            for stmt in node[1]:
                if self._has_return_statement(stmt):
                    return True
            return False
        if tag in ('if', 'if_else', 'if_else_if'):
            if self._has_return_statement(node[2]):
                return True
            if len(node) > 3 and node[3] and self._has_return_statement(node[3]):
                return True
        if tag.startswith('if_with_init'):
            if self._has_return_statement(node[3]):
                return True
            if len(node) > 4 and node[4] and self._has_return_statement(node[4]):
                return True
        if tag.startswith('for_'):
            if self._has_return_statement(node[-1]):
                return True
        return False

    def _analyze_block(self, block_node, scope: Scope):
        if not block_node or not isinstance(block_node, tuple) or block_node[0] != 'block':
            return
        statements = block_node[1]
        for stmt in statements:
            self._analyze_statement(stmt, scope)

    def _analyze_statement(self, stmt, scope: Scope):
        if not stmt or not isinstance(stmt, tuple):
            return

        tag = stmt[0]
        line = self._get_line(stmt)

        if tag == 'var_init':
            var_name = stmt[1]
            type_spec = str(stmt[2])
            expr = stmt[3]
            expr_type = self._eval_expr_type(expr, scope)
            if expr_type != "unknown" and not self._are_types_compatible(type_spec, expr_type):
                self.errors.append(f"Error semántico en línea {line}: no se puede asignar '{expr_type}' a '{type_spec}'")
            self._record_symbol(scope, var_name, type_spec, line)

        elif tag == 'var_typed':
            var_name = stmt[1]
            type_spec = str(stmt[2])
            self._record_symbol(scope, var_name, type_spec, line)

        elif tag == 'var_inferred':
            var_name = stmt[1]
            expr = stmt[2]
            expr_type = self._eval_expr_type(expr, scope)
            inferred = expr_type if expr_type != "unknown" else "inferred"
            self._record_symbol(scope, var_name, inferred, line)

        elif tag == 'const_typed':
            const_name = stmt[1]
            type_spec = str(stmt[2])
            expr = stmt[3]
            expr_type = self._eval_expr_type(expr, scope)
            if expr_type != "unknown" and not self._are_types_compatible(type_spec, expr_type):
                self.errors.append(f"Error semántico en línea {line}: no se puede asignar '{expr_type}' a constante de tipo '{type_spec}'")
            self._record_symbol(scope, const_name, type_spec, line)

        elif tag == 'const_inferred':
            const_name = stmt[1]
            expr = stmt[2]
            expr_type = self._eval_expr_type(expr, scope)
            inferred = expr_type if expr_type != "unknown" else "inferred"
            self._record_symbol(scope, const_name, inferred, line)

        elif tag == 'short_var':
            var_name = stmt[1]
            expr = stmt[2]
            expr_type = self._eval_expr_type(expr, scope)
            inferred = expr_type if expr_type != "unknown" else "inferred"
            self._record_symbol(scope, var_name, inferred, line)

        elif tag == 'assign':
            op = stmt[1]
            lhs_expr = stmt[2]
            rhs_expr = stmt[3]
            lhs_type = self._eval_expr_type(lhs_expr, scope)
            rhs_type = self._eval_expr_type(rhs_expr, scope)

            if lhs_type != "unknown" and rhs_type != "unknown":
                if op == '=':
                    if not self._are_types_compatible(lhs_type, rhs_type):
                        self.errors.append(f"Error semántico en línea {line}: no se puede asignar '{rhs_type}' a '{lhs_type}'")
                elif op == '+=':
                    if not ((lhs_type in self.NUMERIC_TYPES and rhs_type in self.NUMERIC_TYPES and lhs_type == rhs_type) or (lhs_type == 'string' and rhs_type == 'string')):
                        self.errors.append(f"Error semántico en línea {line}: tipos incompatibles para '+=': '{lhs_type}' y '{rhs_type}'")
                elif op in ('-=', '*=', '/='):
                    if not (lhs_type in self.NUMERIC_TYPES and rhs_type in self.NUMERIC_TYPES and lhs_type == rhs_type):
                        self.errors.append(f"Error semántico en línea {line}: tipos incompatibles para '{op}': '{lhs_type}' y '{rhs_type}'")

        elif tag in ('inc', 'dec'):
            expr = stmt[1]
            expr_type = self._eval_expr_type(expr, scope)
            if expr_type != "unknown" and expr_type not in self.NUMERIC_TYPES:
                op_name = "++" if tag == 'inc' else "--"
                self.errors.append(f"Error semántico en línea {line}: operador '{op_name}' solo es aplicable a tipos numéricos, se obtuvo '{expr_type}'")

        elif tag == 'call_stmt':
            self._eval_expr_type(stmt[1], scope)

        elif tag in ('if', 'if_else', 'if_else_if'):
            cond = stmt[1]
            then_block = stmt[2]
            cond_type = self._eval_expr_type(cond, scope)
            if cond_type != "unknown" and cond_type != "bool":
                self.errors.append(f"Error semántico en línea {line}: la condición del 'if' debe ser de tipo bool, se obtuvo '{cond_type}'")

            if_scope = Scope(f"{scope.name}:if", scope)
            self._analyze_block(then_block, if_scope)

            if len(stmt) > 3 and stmt[3]:
                else_branch = stmt[3]
                else_scope = Scope(f"{scope.name}:else", scope)
                if isinstance(else_branch, tuple) and else_branch[0] == 'block':
                    self._analyze_block(else_branch, else_scope)
                else:
                    self._analyze_statement(else_branch, else_scope)

        elif tag.startswith('if_with_init'):
            if_scope = Scope(f"{scope.name}:if", scope)
            self._analyze_statement(stmt[1], if_scope)
            cond_type = self._eval_expr_type(stmt[2], if_scope)
            if cond_type != "unknown" and cond_type != "bool":
                self.errors.append(f"Error semántico en línea {line}: la condición del 'if' debe ser de tipo bool, se obtuvo '{cond_type}'")
            self._analyze_block(stmt[3], if_scope)

            if len(stmt) > 4 and stmt[4]:
                else_scope = Scope(f"{scope.name}:else", scope)
                if isinstance(stmt[4], tuple) and stmt[4][0] == 'block':
                    self._analyze_block(stmt[4], else_scope)
                else:
                    self._analyze_statement(stmt[4], else_scope)

        elif tag == 'for_clause':
            for_scope = Scope(f"{scope.name}:for", scope)
            self._analyze_statement(stmt[1], for_scope)
            if stmt[2]:
                cond_type = self._eval_expr_type(stmt[2], for_scope)
                if cond_type != "unknown" and cond_type != "bool":
                    self.errors.append(f"Error semántico en línea {line}: la condición del 'for' debe ser de tipo bool, se obtuvo '{cond_type}'")
            if stmt[3]:
                self._analyze_statement(stmt[3], for_scope)
            self._analyze_block(stmt[4], for_scope)

        elif tag == 'for_cond':
            for_scope = Scope(f"{scope.name}:for", scope)
            cond_type = self._eval_expr_type(stmt[1], for_scope)
            if cond_type != "unknown" and cond_type != "bool":
                self.errors.append(f"Error semántico en línea {line}: la condición del 'for' debe ser de tipo bool, se obtuvo '{cond_type}'")
            self._analyze_block(stmt[2], for_scope)

        elif tag == 'for_inf':
            for_scope = Scope(f"{scope.name}:for", scope)
            self._analyze_block(stmt[1], for_scope)

        elif tag == 'return':
            ret_expr = stmt[1]
            if ret_expr:
                expr_type = self._eval_expr_type(ret_expr, scope)
                if self.current_function_return == "void" or not self.current_function_return:
                    self.errors.append(f"Error semántico en línea {line}: la función '{self.current_function_name}' no retorna ningún valor")
                elif expr_type != "unknown" and not self._are_types_compatible(self.current_function_return, expr_type):
                    self.errors.append(f"Error semántico en línea {line}: valor de retorno incompatible: se esperaba '{self.current_function_return}', se obtuvo '{expr_type}'")
            else:
                if self.current_function_return and self.current_function_return != "void":
                    self.errors.append(f"Error semántico en línea {line}: se esperaba un valor de retorno de tipo '{self.current_function_return}'")

        elif tag == 'block':
            child_scope = Scope(f"{scope.name}:block", scope)
            self._analyze_block(stmt, child_scope)

    def _eval_expr_type(self, expr, scope: Scope) -> str:
        if not expr or not isinstance(expr, tuple):
            return "unknown"

        tag = expr[0]
        line = self._get_line(expr)

        if tag == 'lit':
            val = str(expr[1])
            # Entero literal
            if val.isdigit() or (val.startswith('-') and val[1:].isdigit()):
                return "int"
            # Flotante literal
            if '.' in val:
                try:
                    float(val)
                    return "float64"
                except ValueError:
                    pass
            # String literal
            if val.startswith('"') or val.startswith('`'):
                return "string"
            # Booleano literal
            if val in ('true', 'false'):
                return "bool"
            # Nil
            if val == 'nil':
                return "nil"

            # Identificador
            sym = scope.lookup(val)
            if not sym:
                self.errors.append(f"Error semántico en línea {line}: variable '{val}' no declarada")
                return "unknown"
            return sym.data_type

        elif tag == 'binop':
            op = expr[1]
            t_left = self._eval_expr_type(expr[2], scope)
            t_right = self._eval_expr_type(expr[3], scope)

            if t_left == "unknown" or t_right == "unknown":
                return "unknown"

            if op == '+':
                if t_left in self.NUMERIC_TYPES and t_right in self.NUMERIC_TYPES and t_left == t_right:
                    return t_left
                if t_left == 'string' and t_right == 'string':
                    return 'string'
                self.errors.append(f"Error semántico en línea {line}: tipos incompatibles para '+': '{t_left}' y '{t_right}'")
                return "unknown"

            elif op in ('-', '*', '/'):
                if t_left in self.NUMERIC_TYPES and t_right in self.NUMERIC_TYPES and t_left == t_right:
                    return t_left
                self.errors.append(f"Error semántico en línea {line}: tipos incompatibles para '{op}': '{t_left}' y '{t_right}'")
                return "unknown"

            elif op == '%':
                if t_left in self.NUMERIC_INT_TYPES and t_right in self.NUMERIC_INT_TYPES and t_left == t_right:
                    return t_left
                self.errors.append(f"Error semántico en línea {line}: operador '%' solo es válido para enteros, se obtuvo '{t_left}' y '{t_right}'")
                return "unknown"

            return "unknown"

        elif tag == 'relop':
            raw_op = expr[1]
            op = self.OP_DISPLAY.get(raw_op, raw_op)
            t_left = self._eval_expr_type(expr[2], scope)
            t_right = self._eval_expr_type(expr[3], scope)

            if t_left == "unknown" or t_right == "unknown":
                return "bool"

            if op in ('==', '!='):
                if not self._are_types_compatible(t_left, t_right):
                    self.errors.append(f"Error semántico en línea {line}: tipos incomparables para '{op}': '{t_left}' y '{t_right}'")
                return "bool"
            elif op in ('<', '<=', '>', '>='):
                if not ((t_left in self.NUMERIC_TYPES and t_right in self.NUMERIC_TYPES and t_left == t_right) or (t_left == 'string' and t_right == 'string')):
                    self.errors.append(f"Error semántico en línea {line}: tipos incompatibles para comparación '{op}': '{t_left}' y '{t_right}'")
                return "bool"

            return "bool"

        elif tag == 'logop':
            raw_op = expr[1]
            op = self.OP_DISPLAY.get(raw_op, raw_op)
            t_left = self._eval_expr_type(expr[2], scope)
            t_right = self._eval_expr_type(expr[3], scope)

            if t_left != "unknown" and t_left != "bool":
                self.errors.append(f"Error semántico en línea {line}: operador '{op}' requiere operandos de tipo bool, se obtuvo '{t_left}'")
            if t_right != "unknown" and t_right != "bool":
                self.errors.append(f"Error semántico en línea {line}: operador '{op}' requiere operandos de tipo bool, se obtuvo '{t_right}'")
            return "bool"

        elif tag == 'unary':
            raw_op = expr[1]
            op = self.OP_DISPLAY.get(raw_op, raw_op)
            t_inner = self._eval_expr_type(expr[2], scope)

            if t_inner == "unknown":
                return "unknown"

            if op in ('+', '-'):
                if t_inner not in self.NUMERIC_TYPES:
                    self.errors.append(f"Error semántico en línea {line}: operador unario '{op}' requiere tipo numérico, se obtuvo '{t_inner}'")
                    return "unknown"
                return t_inner
            elif op == '!':
                if t_inner != "bool":
                    self.errors.append(f"Error semántico en línea {line}: operador '!' requiere tipo bool, se obtuvo '{t_inner}'")
                    return "unknown"
                return "bool"

        elif tag == 'call':
            callee = expr[1]
            args = expr[2] or []

            callee_name = None
            if isinstance(callee, tuple) and callee[0] == 'lit':
                callee_name = str(callee[1])
            elif isinstance(callee, tuple) and callee[0] == 'selector':
                callee_name = f"{callee[1][1]}.{callee[2]}"

            arg_types = [self._eval_expr_type(a, scope) for a in args]

            if callee_name:
                if callee_name.startswith("fmt.") or callee_name in ("println", "print", "len", "cap", "append", "make", "panic", "recover"):
                    return "void"

                sym = scope.lookup(callee_name)
                if not sym:
                    self.errors.append(f"Error semántico en línea {line}: función '{callee_name}' no declarada")
                    return "unknown"

                if "func(" in sym.data_type:
                    sig = sym.data_type
                    params_part = sig[sig.find("func(") + 5:sig.find(")->")]
                    ret_part = sig[sig.find(")->") + 3:]
                    expected_params = [p.strip() for p in params_part.split(",") if p.strip()]

                    if len(expected_params) != len(arg_types):
                        self.errors.append(f"Error semántico en línea {line}: la función '{callee_name}' espera {len(expected_params)} argumentos, se recibieron {len(arg_types)}")
                    else:
                        for idx, (exp_p, act_p) in enumerate(zip(expected_params, arg_types)):
                            if act_p != "unknown" and not self._are_types_compatible(exp_p, act_p):
                                self.errors.append(f"Error semántico en línea {line}: argumento {idx+1} de '{callee_name}' incompatible: se esperaba '{exp_p}', se obtuvo '{act_p}'")
                    return ret_part

            return "unknown"

        elif tag == 'selector':
            pkg_or_struct = expr[1]
            if isinstance(pkg_or_struct, tuple) and pkg_or_struct[0] == 'lit':
                sym_name = str(pkg_or_struct[1])
                sym = scope.lookup(sym_name)
                if not sym:
                    self.errors.append(f"Error semántico en línea {line}: identificador '{sym_name}' no declarado")
                    return "unknown"
                if sym.data_type == "package":
                    return "builtin_func"
            return "unknown"

        elif tag == 'index':
            t_base = self._eval_expr_type(expr[1], scope)
            t_idx = self._eval_expr_type(expr[2], scope)
            if t_idx != "unknown" and t_idx not in self.NUMERIC_INT_TYPES:
                self.errors.append(f"Error semántico en línea {line}: el índice debe ser de tipo entero, se obtuvo '{t_idx}'")
            return "inferred"

        return "unknown"

    def _are_types_compatible(self, t1: str, t2: str) -> bool:
        if t1 == t2:
            return True
        if t1 == "unknown" or t2 == "unknown":
            return True
        if t1 == "any" or t2 == "any":
            return True
        if t2 == "nil" and (t1 in ("pointer", "interface", "slice", "map", "func") or t1.startswith("func") or t1 == "struct"):
            return True
        return False


def analyze_semantics(code: str) -> SemanticResponse:
    lexer = MyLexer()
    parser = MyParser()

    tokens = list(lexer.tokenize(code))
    if lexer.errores_lexicos:
        return SemanticResponse(
            success=False,
            errors=["Errores léxicos detectados: " + " | ".join(lexer.errores_lexicos)],
            symbols=[]
        )

    ast = None
    try:
        ast = parser.parse(lexer.tokenize(code))
    except Exception as e:
        return SemanticResponse(
            success=False,
            errors=[f"Error sintáctico al procesar el código: {e}"],
            symbols=[]
        )

    if parser.error_msg:
        return SemanticResponse(
            success=False,
            errors=[parser.error_msg],
            symbols=[]
        )

    analyzer = SemanticAnalyzer()
    success, errors, symbols = analyzer.analyze(ast, parser._line_positions)

    return SemanticResponse(
        success=success,
        errors=errors,
        symbols=symbols
    )
