#type: ignore
from typing import Optional, Any
from core.lexer import MyLexer
from core.parser import MyParser
from core.semantic import SemanticAnalyzer
from api.schemas import QuadrupleResponse, PostfixItemResponse, IRResponse


class Quadruple:
    def __init__(self, index: int, op: str, arg1: str = "", arg2: str = "", result: str = ""):
        self.index = index
        self.op = op
        self.arg1 = str(arg1) if arg1 is not None else ""
        self.arg2 = str(arg2) if arg2 is not None else ""
        self.result = str(result) if result is not None else ""

    def to_triple_str(self) -> str:
        # Formato .ir del curso (página 15 de IR.pdf): #1  (*, 4, 2, t1)
        a1 = self.arg1 if self.arg1 else ""
        a2 = self.arg2 if self.arg2 else ""
        res = self.result if self.result else ""
        return f"#{self.index}  ({self.op}, {a1}, {a2}, {res})"

    def to_tac_str(self) -> str:
        # Formato Three-Address Code (TAC)
        if self.op == 'label':
            return f"{self.result}:"
        elif self.op == 'goto':
            return f"goto {self.result}"
        elif self.op == 'ifFalse':
            return f"ifFalse {self.arg1} goto {self.result}"
        elif self.op == 'ifTrue':
            return f"ifTrue {self.arg1} goto {self.result}"
        elif self.op == '=':
            return f"{self.result} = {self.arg1}"
        elif self.op in ('+', '-', '*', '/', '%', '==', '!=', '<', '<=', '>', '>=', '&&', '||'):
            return f"{self.result} = {self.arg1} {self.op} {self.arg2}"
        elif self.op in ('!', 'NOT'):
            return f"{self.result} = !{self.arg1}"
        elif self.op == 'param':
            return f"param {self.arg1}"
        elif self.op == 'call':
            return f"{self.result} = call {self.arg1}, {self.arg2}" if self.result else f"call {self.arg1}, {self.arg2}"
        elif self.op == 'return':
            return f"return {self.arg1}" if self.arg1 else "return"
        elif self.op == 'func_begin':
            return f"func {self.result}:"
        elif self.op == 'func_end':
            return f"endfunc"
        else:
            return f"{self.result} = {self.op} {self.arg1} {self.arg2}"

    def to_schema(self) -> QuadrupleResponse:
        return QuadrupleResponse(
            index=self.index,
            op=self.op,
            arg1=self.arg1,
            arg2=self.arg2,
            result=self.result,
            formatted=self.to_triple_str()
        )


class IRGenerator:
    OP_MAP = {
        'EQ': '==', 'NEQ': '!=', 'LT': '<', 'LE': '<=', 'GT': '>', 'GE': '>=',
        'AND': '&&', 'OR': '||', 'NOT': '!'
    }

    def __init__(self):
        self.temp_count = 0
        self.label_count = 0
        self.quadruples: list[Quadruple] = []
        self.postfix_list: list[dict[str, str]] = []

    def new_temp(self) -> str:
        self.temp_count += 1
        return f"t{self.temp_count}"

    def new_label(self) -> str:
        self.label_count += 1
        return f"L{self.label_count}"

    def emit(self, op: str, arg1: str = "", arg2: str = "", result: str = "") -> Quadruple:
        idx = len(self.quadruples) + 1
        quad = Quadruple(idx, op, arg1, arg2, result)
        self.quadruples.append(quad)
        return quad

    def generate(self, ast) -> tuple[list[Quadruple], list[dict[str, str]]]:
        self.temp_count = 0
        self.label_count = 0
        self.quadruples = []
        self.postfix_list = []

        if not ast or not isinstance(ast, tuple) or ast[0] != 'program':
            return [], []

        top_levels = ast[1]
        for item in top_levels:
            if not isinstance(item, tuple):
                continue
            tag = item[0]
            if tag == 'func':
                self._gen_func(item)
            elif tag in ('var_init', 'var_typed', 'var_inferred', 'const_typed', 'const_inferred', 'short_var', 'assign', 'if', 'for_clause', 'call_stmt'):
                self._gen_statement(item)

        return self.quadruples, self.postfix_list

    def _gen_func(self, node):
        name = node[1]
        block = node[4]
        if name != 'main':
            self.emit('func_begin', result=name)
        if block:
            self._gen_block(block)
        if name != 'main':
            self.emit('func_end')

    def _gen_block(self, block_node):
        if not block_node or not isinstance(block_node, tuple) or block_node[0] != 'block':
            return
        statements = block_node[1]
        for stmt in statements:
            self._gen_statement(stmt)

    def _gen_statement(self, stmt):
        if not stmt or not isinstance(stmt, tuple):
            return

        tag = stmt[0]

        if tag in ('var_init', 'const_typed'):
            var_name = stmt[1]
            expr = stmt[3]
            res_temp = self._gen_expr(expr)
            self._record_postfix(expr)
            self.emit('=', res_temp, "", var_name)

        elif tag in ('var_inferred', 'const_inferred', 'short_var'):
            var_name = stmt[1]
            expr = stmt[2]
            res_temp = self._gen_expr(expr)
            self._record_postfix(expr)
            self.emit('=', res_temp, "", var_name)

        elif tag == 'var_typed':
            pass

        elif tag == 'assign':
            op = stmt[1]
            lhs = stmt[2]
            rhs = stmt[3]
            rhs_res = self._gen_expr(rhs)
            self._record_postfix(rhs)
            lhs_name = lhs[1] if isinstance(lhs, tuple) and lhs[0] == 'lit' else str(lhs)

            if op == '=':
                self.emit('=', rhs_res, "", lhs_name)
            elif op == '+=':
                t = self.new_temp()
                self.emit('+', lhs_name, rhs_res, t)
                self.emit('=', t, "", lhs_name)
            elif op == '-=':
                t = self.new_temp()
                self.emit('-', lhs_name, rhs_res, t)
                self.emit('=', t, "", lhs_name)
            elif op == '*=':
                t = self.new_temp()
                self.emit('*', lhs_name, rhs_res, t)
                self.emit('=', t, "", lhs_name)
            elif op == '/=':
                t = self.new_temp()
                self.emit('/', lhs_name, rhs_res, t)
                self.emit('=', t, "", lhs_name)

        elif tag == 'inc':
            lhs = stmt[1]
            lhs_name = lhs[1] if isinstance(lhs, tuple) and lhs[0] == 'lit' else str(lhs)
            t = self.new_temp()
            self.emit('+', lhs_name, "1", t)
            self.emit('=', t, "", lhs_name)

        elif tag == 'dec':
            lhs = stmt[1]
            lhs_name = lhs[1] if isinstance(lhs, tuple) and lhs[0] == 'lit' else str(lhs)
            t = self.new_temp()
            self.emit('-', lhs_name, "1", t)
            self.emit('=', t, "", lhs_name)

        elif tag == 'call_stmt':
            self._gen_expr(stmt[1])

        elif tag in ('if', 'if_else', 'if_else_if'):
            cond = stmt[1]
            then_block = stmt[2]
            else_branch = stmt[3] if len(stmt) > 3 else None

            cond_res = self._gen_expr(cond)
            self._record_postfix(cond)

            label_else = self.new_label()
            label_end = self.new_label() if else_branch else label_else

            self.emit('ifFalse', cond_res, "", label_else)
            self._gen_block(then_block)

            if else_branch:
                self.emit('goto', result=label_end)
                self.emit('label', result=label_else)
                if isinstance(else_branch, tuple) and else_branch[0] == 'block':
                    self._gen_block(else_branch)
                else:
                    self._gen_statement(else_branch)
                self.emit('label', result=label_end)
            else:
                self.emit('label', result=label_else)

        elif tag.startswith('if_with_init'):
            self._gen_statement(stmt[1])
            cond_res = self._gen_expr(stmt[2])
            self._record_postfix(stmt[2])

            else_branch = stmt[4] if len(stmt) > 4 else None
            label_else = self.new_label()
            label_end = self.new_label() if else_branch else label_else

            self.emit('ifFalse', cond_res, "", label_else)
            self._gen_block(stmt[3])

            if else_branch:
                self.emit('goto', result=label_end)
                self.emit('label', result=label_else)
                if isinstance(else_branch, tuple) and else_branch[0] == 'block':
                    self._gen_block(else_branch)
                else:
                    self._gen_statement(else_branch)
                self.emit('label', result=label_end)
            else:
                self.emit('label', result=label_else)

        elif tag == 'for_clause':
            init_stmt = stmt[1]
            cond_expr = stmt[2]
            post_stmt = stmt[3]
            block = stmt[4]

            if init_stmt:
                self._gen_statement(init_stmt)

            label_start = self.new_label()
            label_end = self.new_label()

            self.emit('label', result=label_start)

            if cond_expr:
                cond_res = self._gen_expr(cond_expr)
                self._record_postfix(cond_expr)
                self.emit('ifFalse', cond_res, "", label_end)

            self._gen_block(block)

            if post_stmt:
                self._gen_statement(post_stmt)

            self.emit('goto', result=label_start)
            self.emit('label', result=label_end)

        elif tag == 'for_cond':
            cond_expr = stmt[1]
            block = stmt[2]
            label_start = self.new_label()
            label_end = self.new_label()

            self.emit('label', result=label_start)
            cond_res = self._gen_expr(cond_expr)
            self._record_postfix(cond_expr)
            self.emit('ifFalse', cond_res, "", label_end)

            self._gen_block(block)
            self.emit('goto', result=label_start)
            self.emit('label', result=label_end)

        elif tag == 'for_inf':
            block = stmt[1]
            label_start = self.new_label()
            self.emit('label', result=label_start)
            self._gen_block(block)
            self.emit('goto', result=label_start)

        elif tag == 'return':
            ret_expr = stmt[1]
            if ret_expr:
                res = self._gen_expr(ret_expr)
                self._record_postfix(ret_expr)
                self.emit('return', arg1=res)
            else:
                self.emit('return')

        elif tag == 'block':
            self._gen_block(stmt)

    def _gen_expr(self, expr) -> str:
        if not expr or not isinstance(expr, tuple):
            return str(expr) if expr is not None else ""

        tag = expr[0]

        if tag == 'lit':
            return str(expr[1])

        elif tag in ('binop', 'relop', 'logop'):
            raw_op = expr[1]
            op = self.OP_MAP.get(raw_op, raw_op)
            arg1 = self._gen_expr(expr[2])
            arg2 = self._gen_expr(expr[3])
            t = self.new_temp()
            self.emit(op, arg1, arg2, t)
            return t

        elif tag == 'unary':
            raw_op = expr[1]
            op = self.OP_MAP.get(raw_op, raw_op)
            arg = self._gen_expr(expr[2])
            t = self.new_temp()
            self.emit(op, arg, "", t)
            return t

        elif tag == 'call':
            callee = expr[1]
            args = expr[2] or []
            callee_name = callee[1] if isinstance(callee, tuple) and callee[0] == 'lit' else (f"{callee[1][1]}.{callee[2]}" if isinstance(callee, tuple) and callee[0] == 'selector' else str(callee))

            arg_temps = [self._gen_expr(a) for a in args]
            for a in arg_temps:
                self.emit('param', arg1=a)

            t = self.new_temp()
            self.emit('call', callee_name, str(len(arg_temps)), t)
            return t

        elif tag == 'selector':
            return f"{expr[1][1]}.{expr[2]}"

        elif tag == 'index':
            base = self._gen_expr(expr[1])
            idx = self._gen_expr(expr[2])
            t = self.new_temp()
            self.emit('index', base, idx, t)
            return t

        return ""

    def _to_postfix(self, expr) -> list[str]:
        if not expr or not isinstance(expr, tuple):
            return [str(expr)] if expr is not None else []
        tag = expr[0]
        if tag == 'lit':
            return [str(expr[1])]
        elif tag in ('binop', 'relop', 'logop'):
            raw_op = expr[1]
            op = self.OP_MAP.get(raw_op, raw_op)
            left_post = self._to_postfix(expr[2])
            right_post = self._to_postfix(expr[3])
            return left_post + right_post + [op]
        elif tag == 'unary':
            raw_op = expr[1]
            op = self.OP_MAP.get(raw_op, raw_op)
            inner_post = self._to_postfix(expr[2])
            return inner_post + [op]
        elif tag == 'call':
            callee_name = expr[1][1] if isinstance(expr[1], tuple) and expr[1][0] == 'lit' else str(expr[1])
            args_post = []
            for a in (expr[2] or []):
                args_post.extend(self._to_postfix(a))
            return args_post + [f"{callee_name}()"]
        return []

    def _expr_to_infix_str(self, expr) -> str:
        if not expr or not isinstance(expr, tuple):
            return str(expr)
        tag = expr[0]
        if tag == 'lit':
            return str(expr[1])
        elif tag in ('binop', 'relop', 'logop'):
            raw_op = expr[1]
            op = self.OP_MAP.get(raw_op, raw_op)
            return f"({self._expr_to_infix_str(expr[2])} {op} {self._expr_to_infix_str(expr[3])})"
        elif tag == 'unary':
            return f"({expr[1]}{self._expr_to_infix_str(expr[2])})"
        return str(expr)

    def _record_postfix(self, expr):
        if not expr or not isinstance(expr, tuple):
            return
        if expr[0] in ('binop', 'relop', 'logop', 'unary'):
            infix = self._expr_to_infix_str(expr)
            postfix_tokens = self._to_postfix(expr)
            self.postfix_list.append({
                "infix": infix,
                "postfix": " ".join(postfix_tokens)
            })


def generate_ir(code: str) -> IRResponse:
    lexer = MyLexer()
    parser = MyParser()

    tokens = list(lexer.tokenize(code))
    if lexer.errores_lexicos:
        return IRResponse(
            success=False,
            errors=["Errores léxicos detectados: " + " | ".join(lexer.errores_lexicos)],
            tac_code=None,
            triples=[],
            quadruples=[],
            postfix_expressions=[]
        )

    ast = None
    try:
        ast = parser.parse(lexer.tokenize(code))
    except Exception as e:
        return IRResponse(
            success=False,
            errors=[f"Error sintáctico al procesar el código: {e}"],
            tac_code=None,
            triples=[],
            quadruples=[],
            postfix_expressions=[]
        )

    if parser.error_msg:
        return IRResponse(
            success=False,
            errors=[parser.error_msg],
            tac_code=None,
            triples=[],
            quadruples=[],
            postfix_expressions=[]
        )

    # Validar semántica antes de generar IR
    semantic_analyzer = SemanticAnalyzer()
    sem_ok, sem_errors, _ = semantic_analyzer.analyze(ast, parser._line_positions)
    if not sem_ok:
        return IRResponse(
            success=False,
            errors=sem_errors,
            tac_code=None,
            triples=[],
            quadruples=[],
            postfix_expressions=[]
        )

    # Generar IR
    generator = IRGenerator()
    quads, postfix = generator.generate(ast)

    tac_lines = [q.to_tac_str() for q in quads]
    triples_lines = [q.to_triple_str() for q in quads]
    quads_schema = [q.to_schema() for q in quads]
    postfix_schema = [PostfixItemResponse(infix=p["infix"], postfix=p["postfix"]) for p in postfix]

    return IRResponse(
        success=True,
        errors=[],
        tac_code="\n".join(tac_lines),
        triples=triples_lines,
        quadruples=quads_schema,
        postfix_expressions=postfix_schema
    )
