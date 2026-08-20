#type: ignore
import logging
from sly import Parser
from core.lexer import MyLexer
from api.schemas import ParseResponse

# Configurar logging de SLY
log = logging.getLogger('sly')
log.setLevel(logging.ERROR)


class MyParser(Parser):
    tokens = MyLexer.tokens

    precedence = (
        ('left', 'OR'),
        ('left', 'AND'),
        ('left', 'OPREL'),
        ('left', '+', '-'),
        ('left', '*', '/', '%'),
        ('right', 'UNARY'),
    )

    def __init__(self):
        self.error_msg = None
        self.error_line = None
        self.error_index = None

    # ==========================================
    # Estructura Principal / Programa
    # ==========================================
    @_('top_level_list')
    def program(self, p):
        return ('program', p.top_level_list)

    @_('empty')
    def program(self, p):
        return ('program', [])

    @_('top_level top_level_list')
    def top_level_list(self, p):
        return [p.top_level] + p.top_level_list

    @_('top_level')
    def top_level_list(self, p):
        return [p.top_level]

    # Declaraciones válidas a nivel superior
    @_('package_decl', 'import_decl', 'func_decl', 'type_decl', 'var_decl', 'const_decl',
       'short_var_decl', 'assignment_stmt', 'inc_dec_stmt', 'if_stmt', 'for_stmt', 'call_stmt', 'semi_stmt')
    def top_level(self, p):
        return p[0]

    # Declaración de Paquete: package main
    @_('PACKAGE ID')
    def package_decl(self, p):
        return ('package', p.ID)

    # Declaración de Importaciones: import "fmt" o import ( "fmt" "os" )
    @_('IMPORT STRING_LIT')
    def import_decl(self, p):
        return ('import_single', p.STRING_LIT)

    @_('IMPORT "(" import_spec_list ")"')
    def import_decl(self, p):
        return ('import_multi', p.import_spec_list)

    @_('import_spec import_spec_list')
    def import_spec_list(self, p):
        return [p.import_spec] + p.import_spec_list

    @_('import_spec')
    def import_spec_list(self, p):
        return [p.import_spec]

    @_('STRING_LIT')
    def import_spec(self, p):
        return p.STRING_LIT

    @_('ID STRING_LIT')
    def import_spec(self, p):
        return (p.ID, p.STRING_LIT)

    # Declaración de Funciones: func sumar(a int, b int) int { ... }
    @_('FUNC ID "(" param_list ")" type_spec block')
    def func_decl(self, p):
        return ('func', p.ID, p.param_list, p.type_spec, p.block)

    @_('FUNC ID "(" param_list ")" block')
    def func_decl(self, p):
        return ('func', p.ID, p.param_list, None, p.block)

    @_('FUNC ID "(" ")" type_spec block')
    def func_decl(self, p):
        return ('func', p.ID, [], p.type_spec, p.block)

    @_('FUNC ID "(" ")" block')
    def func_decl(self, p):
        return ('func', p.ID, [], None, p.block)

    # Lista de parámetros
    @_('param "," param_list')
    def param_list(self, p):
        return [p.param] + p.param_list

    @_('param')
    def param_list(self, p):
        return [p.param]

    @_('ID type_spec')
    def param(self, p):
        return (p.ID, p.type_spec)

    # Especificación de Tipos (primitivos TYPE o personalizados ID, []type, *type)
    @_('TYPE', 'ID')
    def type_spec(self, p):
        return p[0]

    @_('"[" "]" type_spec')
    def type_spec(self, p):
        return ('slice_type', p.type_spec)

    @_('"*" type_spec')
    def type_spec(self, p):
        return ('ptr_type', p.type_spec)

    # Declaración de Tipos y Structs: type Persona struct { ... }
    @_('TYPE_KW ID STRUCT "{" struct_field_list "}"')
    def type_decl(self, p):
        return ('type_struct', p.ID, p.struct_field_list)

    @_('TYPE_KW ID STRUCT "{" "}"')
    def type_decl(self, p):
        return ('type_struct', p.ID, [])

    @_('TYPE_KW ID type_spec')
    def type_decl(self, p):
        return ('type_alias', p.ID, p.type_spec)

    @_('struct_field struct_field_list')
    def struct_field_list(self, p):
        return [p.struct_field] + p.struct_field_list

    @_('struct_field')
    def struct_field_list(self, p):
        return [p.struct_field]

    @_('ID type_spec')
    def struct_field(self, p):
        return ('field', p.ID, p.type_spec)

    # ==========================================
    # Bloques y Sentencias
    # ==========================================
    @_('"{" statement_list "}"')
    def block(self, p):
        return ('block', p.statement_list)

    @_('"{" "}"')
    def block(self, p):
        return ('block', [])

    @_('statement statement_list')
    def statement_list(self, p):
        return [p.statement] + p.statement_list

    @_('statement')
    def statement_list(self, p):
        return [p.statement]

    # Sentencias válidas dentro de bloques
    @_('type_decl', 'var_decl', 'const_decl', 'short_var_decl',
       'assignment_stmt', 'inc_dec_stmt', 'if_stmt', 'for_stmt',
       'return_stmt', 'call_stmt', 'block', 'semi_stmt')
    def statement(self, p):
        return p[0]

    @_('";"')
    def semi_stmt(self, p):
        return ('empty_stmt',)

    # Declaraciones de Variables (con ASSIGN)
    @_('VAR ID type_spec ASSIGN expr')
    def var_decl(self, p):
        return ('var_init', p.ID, p.type_spec, p.expr)

    @_('VAR ID type_spec')
    def var_decl(self, p):
        return ('var_typed', p.ID, p.type_spec)

    @_('VAR ID ASSIGN expr')
    def var_decl(self, p):
        return ('var_inferred', p.ID, p.expr)

    # Declaraciones de Constantes (con ASSIGN)
    @_('CONST ID type_spec ASSIGN expr')
    def const_decl(self, p):
        return ('const_typed', p.ID, p.type_spec, p.expr)

    @_('CONST ID ASSIGN expr')
    def const_decl(self, p):
        return ('const_inferred', p.ID, p.expr)

    # Declaración Corta de Variables: x := 10
    @_('ID ASSIGN_DEF expr')
    def short_var_decl(self, p):
        return ('short_var', p.ID, p.expr)

    # Asignaciones: x = 10, x += 5
    @_('expr ASSIGN expr')
    def assignment_stmt(self, p):
        return ('assign', '=', p.expr0, p.expr1)

    @_('expr ADD_ASSIGN expr',
       'expr SUB_ASSIGN expr',
       'expr MUL_ASSIGN expr',
       'expr DIV_ASSIGN expr')
    def assignment_stmt(self, p):
        return ('assign', p[1], p.expr0, p.expr1)

    # Incremento y Decremento: x++, x--
    @_('expr INC')
    def inc_dec_stmt(self, p):
        return ('inc', p.expr)

    @_('expr DEC')
    def inc_dec_stmt(self, p):
        return ('dec', p.expr)

    # Sentencia de llamada a función / método (única sentencia de expresión válida en Go)
    @_('call_expr')
    def call_stmt(self, p):
        return ('call_stmt', p.call_expr)

    # Sentencias Simples (utilizadas en encabezados de if / for)
    @_('short_var_decl', 'assignment_stmt', 'inc_dec_stmt', 'call_expr')
    def simple_stmt(self, p):
        return p[0]

    # Condicionales IF / ELSE IF / ELSE
    @_('IF expr block')
    def if_stmt(self, p):
        return ('if', p.expr, p.block, None)

    @_('IF expr block ELSE block')
    def if_stmt(self, p):
        return ('if_else', p.expr, p.block0, p.block1)

    @_('IF expr block ELSE if_stmt')
    def if_stmt(self, p):
        return ('if_else_if', p.expr, p.block, p.if_stmt)

    @_('IF simple_stmt ";" expr block')
    def if_stmt(self, p):
        return ('if_with_init', p.simple_stmt, p.expr, p.block, None)

    @_('IF simple_stmt ";" expr block ELSE block')
    def if_stmt(self, p):
        return ('if_with_init_else', p.simple_stmt, p.expr, p.block0, p.block1)

    @_('IF simple_stmt ";" expr block ELSE if_stmt')
    def if_stmt(self, p):
        return ('if_with_init_else_if', p.simple_stmt, p.expr, p.block, p.if_stmt)

    # Bucles FOR (Infinito, Condicional tipo While, y de 3 componentes)
    @_('FOR block')
    def for_stmt(self, p):
        return ('for_inf', p.block)

    @_('FOR expr block')
    def for_stmt(self, p):
        return ('for_cond', p.expr, p.block)

    @_('FOR simple_stmt ";" expr ";" simple_stmt block')
    def for_stmt(self, p):
        return ('for_clause', p.simple_stmt0, p.expr, p.simple_stmt1, p.block)

    # Sentencia de Retorno
    @_('RETURN expr')
    def return_stmt(self, p):
        return ('return', p.expr)

    @_('RETURN')
    def return_stmt(self, p):
        return ('return', None)

    # ==========================================
    # Expresiones y Operadores
    # ==========================================
    @_('expr "+" expr',
       'expr "-" expr',
       'expr "*" expr',
       'expr "/" expr',
       'expr "%" expr')
    def expr(self, p):
        return ('binop', p[1], p.expr0, p.expr1)

    @_('expr OPREL expr')
    def expr(self, p):
        return ('relop', p.OPREL, p.expr0, p.expr1)

    @_('expr AND expr',
       'expr OR expr')
    def expr(self, p):
        return ('logop', p[1], p.expr0, p.expr1)

    @_('"!" expr %prec UNARY',
       '"-" expr %prec UNARY',
       '"+" expr %prec UNARY')
    def expr(self, p):
        return ('unary', p[0], p.expr)

    @_('"(" expr ")"')
    def expr(self, p):
        return p.expr

    @_('ID', 'INT_LIT', 'FLOAT_LIT', 'STRING_LIT', 'TRUE', 'FALSE', 'NIL')
    def expr(self, p):
        return ('lit', p[0])

    @_('expr "." ID')
    def expr(self, p):
        return ('selector', p.expr, p.ID)

    @_('expr "[" expr "]"')
    def expr(self, p):
        return ('index', p.expr0, p.expr1)

    @_('expr "(" arg_list ")"')
    def call_expr(self, p):
        return ('call', p.expr, p.arg_list)

    @_('expr "(" ")"')
    def call_expr(self, p):
        return ('call', p.expr, [])

    @_('call_expr')
    def expr(self, p):
        return p.call_expr

    @_('expr "," arg_list')
    def arg_list(self, p):
        return [p.expr] + p.arg_list

    @_('expr')
    def arg_list(self, p):
        return [p.expr]

    @_('')
    def empty(self, p):
        pass

    # ==========================================
    # Manejo de Errores Sintácticos
    # ==========================================
    def error(self, p):
        if p:
            self.error_msg = f"Error de sintaxis cerca de '{p.value}' en la línea {p.lineno}"
            self.error_line = p.lineno
            self.error_index = p.index
        else:
            self.error_msg = "Error de sintaxis: Fin de archivo inesperado (posibles llaves '{' o paréntesis sin cerrar)"
            self.error_line = None
            self.error_index = None


# ==========================================
# Visualizador del Árbol Sintáctico (AST)
# ==========================================
class ASTVisualizer:
    def __init__(self):
        self.node_counter = 0

    def generate_mermaid(self, ast_root) -> str:
        self.node_counter = 0
        lines = ["graph TD"]
        lines.append("    classDef rootNode fill:#0284c7,stroke:#38bdf8,stroke-width:2px,color:#ffffff,font-weight:bold;")
        lines.append("    classDef funcNode fill:#4f46e5,stroke:#818cf8,stroke-width:2px,color:#ffffff,font-weight:bold;")
        lines.append("    classDef stmtNode fill:#1e293b,stroke:#64748b,stroke-width:1.5px,color:#f8fafc;")
        lines.append("    classDef exprNode fill:#065f46,stroke:#34d399,stroke-width:1.5px,color:#f8fafc;")
        lines.append("    classDef litNode fill:#831843,stroke:#f472b6,stroke-width:1px,color:#fdf2f8;")
        lines.append("    classDef typeNode fill:#134e4a,stroke:#2dd4bf,stroke-width:1.5px,color:#f0fdfa;")

        root_id = self._build_mermaid(ast_root, lines)
        if root_id:
            lines.append(f"    class {root_id} rootNode;")
        return "\n".join(lines)

    def _sanitize(self, text: str) -> str:
        text = str(text).replace('"', "'").replace("\n", " ")
        if len(text) > 40:
            text = text[:37] + "..."
        return text

    def _new_node(self, label: str, node_class: str = None) -> tuple[str, str]:
        self.node_counter += 1
        node_id = f"node_{self.node_counter}"
        sanitized = self._sanitize(label)
        def_str = f'    {node_id}["{sanitized}"]'
        if node_class:
            def_str += f"\n    class {node_id} {node_class};"
        return node_id, def_str

    def _build_mermaid(self, node, lines: list) -> str:
        if node is None:
            return None

        if isinstance(node, (str, int, float, bool)):
            node_id, def_str = self._new_node(str(node), "litNode")
            lines.append(def_str)
            return node_id

        if isinstance(node, list):
            if not node:
                return None
            node_id, def_str = self._new_node("Secuencia", "stmtNode")
            lines.append(def_str)
            for item in node:
                child_id = self._build_mermaid(item, lines)
                if child_id:
                    lines.append(f"    {node_id} --> {child_id}")
            return node_id

        if not isinstance(node, tuple):
            node_id, def_str = self._new_node(str(node), "litNode")
            lines.append(def_str)
            return node_id

        tag = node[0]

        if tag == 'program':
            node_id, def_str = self._new_node("Programa (Go)", "rootNode")
            lines.append(def_str)
            for item in node[1]:
                child_id = self._build_mermaid(item, lines)
                if child_id:
                    lines.append(f"    {node_id} --> {child_id}")
            return node_id

        elif tag == 'package':
            node_id, def_str = self._new_node(f"Package: {node[1]}", "typeNode")
            lines.append(def_str)
            return node_id

        elif tag == 'import_single':
            node_id, def_str = self._new_node(f"Import: {node[1]}", "typeNode")
            lines.append(def_str)
            return node_id

        elif tag == 'import_multi':
            node_id, def_str = self._new_node("Imports", "typeNode")
            lines.append(def_str)
            for imp in node[1]:
                child_id = self._build_mermaid(imp, lines)
                if child_id:
                    lines.append(f"    {node_id} --> {child_id}")
            return node_id

        elif tag == 'func':
            name = node[1]
            ret_type = node[3] if node[3] else "void"
            node_id, def_str = self._new_node(f"Func: {name}() -> {ret_type}", "funcNode")
            lines.append(def_str)
            
            if node[2]:
                params_id, p_def = self._new_node("Parámetros", "typeNode")
                lines.append(p_def)
                lines.append(f"    {node_id} --> {params_id}")
                for p in node[2]:
                    p_id, p_item_def = self._new_node(f"{p[0]}: {p[1]}", "typeNode")
                    lines.append(p_item_def)
                    lines.append(f"    {params_id} --> {p_id}")

            block_id = self._build_mermaid(node[4], lines)
            if block_id:
                lines.append(f"    {node_id} --> {block_id}")
            return node_id

        elif tag == 'block':
            node_id, def_str = self._new_node("Bloque { ... }", "stmtNode")
            lines.append(def_str)
            for stmt in node[1]:
                child_id = self._build_mermaid(stmt, lines)
                if child_id:
                    lines.append(f"    {node_id} --> {child_id}")
            return node_id

        elif tag == 'var_init':
            node_id, def_str = self._new_node(f"VarDecl: {node[1]} ({node[2]})", "stmtNode")
            lines.append(def_str)
            expr_id = self._build_mermaid(node[3], lines)
            if expr_id:
                lines.append(f"    {node_id} -- \"=\" --> {expr_id}")
            return node_id

        elif tag == 'var_typed':
            node_id, def_str = self._new_node(f"VarDecl: {node[1]} ({node[2]})", "stmtNode")
            lines.append(def_str)
            return node_id

        elif tag == 'var_inferred':
            node_id, def_str = self._new_node(f"VarDecl: {node[1]}", "stmtNode")
            lines.append(def_str)
            expr_id = self._build_mermaid(node[2], lines)
            if expr_id:
                lines.append(f"    {node_id} -- \"=\" --> {expr_id}")
            return node_id

        elif tag == 'const_typed':
            node_id, def_str = self._new_node(f"ConstDecl: {node[1]} ({node[2]})", "stmtNode")
            lines.append(def_str)
            expr_id = self._build_mermaid(node[3], lines)
            if expr_id:
                lines.append(f"    {node_id} -- \"=\" --> {expr_id}")
            return node_id

        elif tag == 'const_inferred':
            node_id, def_str = self._new_node(f"ConstDecl: {node[1]}", "stmtNode")
            lines.append(def_str)
            expr_id = self._build_mermaid(node[2], lines)
            if expr_id:
                lines.append(f"    {node_id} -- \"=\" --> {expr_id}")
            return node_id

        elif tag == 'short_var':
            node_id, def_str = self._new_node(f"Asignación Corta (:=): {node[1]}", "stmtNode")
            lines.append(def_str)
            expr_id = self._build_mermaid(node[2], lines)
            if expr_id:
                lines.append(f"    {node_id} --> {expr_id}")
            return node_id

        elif tag == 'assign':
            op = node[1]
            node_id, def_str = self._new_node(f"Asignación ({op})", "stmtNode")
            lines.append(def_str)
            lhs_id = self._build_mermaid(node[2], lines)
            rhs_id = self._build_mermaid(node[3], lines)
            if lhs_id:
                lines.append(f"    {node_id} -- \"Destino\" --> {lhs_id}")
            if rhs_id:
                lines.append(f"    {node_id} -- \"Valor\" --> {rhs_id}")
            return node_id

        elif tag in ('inc', 'dec'):
            op_sym = "++" if tag == 'inc' else "--"
            node_id, def_str = self._new_node(f"Op Unario ({op_sym})", "stmtNode")
            lines.append(def_str)
            child_id = self._build_mermaid(node[1], lines)
            if child_id:
                lines.append(f"    {node_id} --> {child_id}")
            return node_id

        elif tag in ('if', 'if_else', 'if_else_if'):
            node_id, def_str = self._new_node("Sentencia IF", "stmtNode")
            lines.append(def_str)
            cond_id = self._build_mermaid(node[1], lines)
            then_id = self._build_mermaid(node[2], lines)
            if cond_id:
                lines.append(f"    {node_id} -- \"Condición\" --> {cond_id}")
            if then_id:
                lines.append(f"    {node_id} -- \"Then\" --> {then_id}")
            if len(node) > 3 and node[3]:
                else_id = self._build_mermaid(node[3], lines)
                if else_id:
                    lines.append(f"    {node_id} -- \"Else\" --> {else_id}")
            return node_id

        elif tag.startswith('if_with_init'):
            node_id, def_str = self._new_node("IF (con Inicialización)", "stmtNode")
            lines.append(def_str)
            init_id = self._build_mermaid(node[1], lines)
            cond_id = self._build_mermaid(node[2], lines)
            then_id = self._build_mermaid(node[3], lines)
            if init_id:
                lines.append(f"    {node_id} -- \"Init\" --> {init_id}")
            if cond_id:
                lines.append(f"    {node_id} -- \"Cond\" --> {cond_id}")
            if then_id:
                lines.append(f"    {node_id} -- \"Then\" --> {then_id}")
            if len(node) > 4 and node[4]:
                else_id = self._build_mermaid(node[4], lines)
                if else_id:
                    lines.append(f"    {node_id} -- \"Else\" --> {else_id}")
            return node_id

        elif tag == 'for_inf':
            node_id, def_str = self._new_node("Bucle FOR (Infinito)", "stmtNode")
            lines.append(def_str)
            block_id = self._build_mermaid(node[1], lines)
            if block_id:
                lines.append(f"    {node_id} --> {block_id}")
            return node_id

        elif tag == 'for_cond':
            node_id, def_str = self._new_node("Bucle FOR (Condicional)", "stmtNode")
            lines.append(def_str)
            cond_id = self._build_mermaid(node[1], lines)
            block_id = self._build_mermaid(node[2], lines)
            if cond_id:
                lines.append(f"    {node_id} -- \"Condición\" --> {cond_id}")
            if block_id:
                lines.append(f"    {node_id} -- \"Cuerpo\" --> {block_id}")
            return node_id

        elif tag == 'for_clause':
            node_id, def_str = self._new_node("Bucle FOR (3 Cláusulas)", "stmtNode")
            lines.append(def_str)
            init_id = self._build_mermaid(node[1], lines)
            cond_id = self._build_mermaid(node[2], lines)
            post_id = self._build_mermaid(node[3], lines)
            body_id = self._build_mermaid(node[4], lines)
            if init_id:
                lines.append(f"    {node_id} -- \"Init\" --> {init_id}")
            if cond_id:
                lines.append(f"    {node_id} -- \"Cond\" --> {cond_id}")
            if post_id:
                lines.append(f"    {node_id} -- \"Post\" --> {post_id}")
            if body_id:
                lines.append(f"    {node_id} -- \"Cuerpo\" --> {body_id}")
            return node_id

        elif tag == 'return':
            node_id, def_str = self._new_node("Sentencia Return", "stmtNode")
            lines.append(def_str)
            if node[1]:
                expr_id = self._build_mermaid(node[1], lines)
                if expr_id:
                    lines.append(f"    {node_id} --> {expr_id}")
            return node_id

        elif tag == 'call_stmt':
            return self._build_mermaid(node[1], lines)

        elif tag in ('binop', 'relop', 'logop'):
            op = node[1]
            node_id, def_str = self._new_node(f"Op: {op}", "exprNode")
            lines.append(def_str)
            left_id = self._build_mermaid(node[2], lines)
            right_id = self._build_mermaid(node[3], lines)
            if left_id:
                lines.append(f"    {node_id} -- \"Izq\" --> {left_id}")
            if right_id:
                lines.append(f"    {node_id} -- \"Der\" --> {right_id}")
            return node_id

        elif tag == 'unary':
            op = node[1]
            node_id, def_str = self._new_node(f"Unario: {op}", "exprNode")
            lines.append(def_str)
            expr_id = self._build_mermaid(node[2], lines)
            if expr_id:
                lines.append(f"    {node_id} --> {expr_id}")
            return node_id

        elif tag == 'lit':
            node_id, def_str = self._new_node(f"{node[1]}", "litNode")
            lines.append(def_str)
            return node_id

        elif tag == 'selector':
            node_id, def_str = self._new_node(f"Acceso (. {node[2]})", "exprNode")
            lines.append(def_str)
            obj_id = self._build_mermaid(node[1], lines)
            if obj_id:
                lines.append(f"    {node_id} --> {obj_id}")
            return node_id

        elif tag == 'index':
            node_id, def_str = self._new_node("Indexación [ ]", "exprNode")
            lines.append(def_str)
            arr_id = self._build_mermaid(node[1], lines)
            idx_id = self._build_mermaid(node[2], lines)
            if arr_id:
                lines.append(f"    {node_id} -- \"Array\" --> {arr_id}")
            if idx_id:
                lines.append(f"    {node_id} -- \"Índice\" --> {idx_id}")
            return node_id

        elif tag == 'call':
            node_id, def_str = self._new_node("Llamada a Función ( )", "exprNode")
            lines.append(def_str)
            callee_id = self._build_mermaid(node[1], lines)
            if callee_id:
                lines.append(f"    {node_id} -- \"Función\" --> {callee_id}")
            if node[2]:
                args_id, a_def = self._new_node("Argumentos", "exprNode")
                lines.append(a_def)
                lines.append(f"    {node_id} --> {args_id}")
                for arg in node[2]:
                    arg_id = self._build_mermaid(arg, lines)
                    if arg_id:
                        lines.append(f"    {args_id} --> {arg_id}")
            return node_id

        elif tag == 'type_struct':
            node_id, def_str = self._new_node(f"Struct: {node[1]}", "typeNode")
            lines.append(def_str)
            for f in node[2]:
                f_id, f_def = self._new_node(f"{f[1]}: {f[2]}", "typeNode")
                lines.append(f_def)
                lines.append(f"    {node_id} --> {f_id}")
            return node_id

        elif tag == 'type_alias':
            node_id, def_str = self._new_node(f"Alias Tipo: {node[1]} = {node[2]}", "typeNode")
            lines.append(def_str)
            return node_id

        elif tag == 'empty_stmt':
            return None

        # Fallback para cualquier otra tupla
        node_id, def_str = self._new_node(f"Nodo: {tag}", "stmtNode")
        lines.append(def_str)
        for i in range(1, len(node)):
            child_id = self._build_mermaid(node[i], lines)
            if child_id:
                lines.append(f"    {node_id} --> {child_id}")
        return node_id

    def generate_json_tree(self, node) -> dict:
        if node is None:
            return None
        if isinstance(node, (str, int, float, bool)):
            return {"name": str(node), "type": "literal"}
        if isinstance(node, list):
            return {
                "name": "Secuencia",
                "type": "sequence",
                "children": [self.generate_json_tree(item) for item in node if item is not None]
            }
        if not isinstance(node, tuple):
            return {"name": str(node), "type": "value"}
        
        tag = node[0]
        if tag == 'program':
            return {
                "name": "Programa (Go)",
                "type": "program",
                "children": [self.generate_json_tree(item) for item in node[1] if item is not None]
            }
        elif tag == 'package':
            return {"name": f"package {node[1]}", "type": "package"}
        elif tag == 'import_single':
            return {"name": f"import {node[1]}", "type": "import"}
        elif tag == 'import_multi':
            return {
                "name": "import ( ... )",
                "type": "import",
                "children": [self.generate_json_tree(item) for item in node[1]]
            }
        elif tag == 'func':
            children = []
            if node[2]:
                children.append({
                    "name": "Parámetros",
                    "type": "params",
                    "children": [{"name": f"{p[0]}: {p[1]}", "type": "param"} for p in node[2]]
                })
            if node[4]:
                children.append(self.generate_json_tree(node[4]))
            return {
                "name": f"func {node[1]}() {node[3] or ''}",
                "type": "function",
                "children": children
            }
        elif tag == 'block':
            return {
                "name": "{ Bloque }",
                "type": "block",
                "children": [self.generate_json_tree(stmt) for stmt in node[1] if stmt is not None]
            }
        elif tag == 'var_init':
            return {
                "name": f"var {node[1]} {node[2]} =",
                "type": "var_decl",
                "children": [self.generate_json_tree(node[3])]
            }
        elif tag == 'short_var':
            return {
                "name": f"{node[1]} :=",
                "type": "short_var",
                "children": [self.generate_json_tree(node[2])]
            }
        elif tag == 'assign':
            return {
                "name": f"Asignación ({node[1]})",
                "type": "assignment",
                "children": [self.generate_json_tree(node[2]), self.generate_json_tree(node[3])]
            }
        elif tag in ('binop', 'relop', 'logop'):
            return {
                "name": f"Operación ({node[1]})",
                "type": "binary_op",
                "children": [self.generate_json_tree(node[2]), self.generate_json_tree(node[3])]
            }
        elif tag == 'unary':
            return {
                "name": f"Unario ({node[1]})",
                "type": "unary_op",
                "children": [self.generate_json_tree(node[2])]
            }
        elif tag == 'lit':
            return {"name": str(node[1]), "type": "literal"}
        elif tag == 'call':
            children = [self.generate_json_tree(node[1])]
            if node[2]:
                children.append({
                    "name": "Argumentos",
                    "type": "args",
                    "children": [self.generate_json_tree(arg) for arg in node[2]]
                })
            return {"name": "Llamada", "type": "call", "children": children}
        elif tag == 'call_stmt':
            return self.generate_json_tree(node[1])
        elif tag == 'return':
            children = [self.generate_json_tree(node[1])] if node[1] else []
            return {"name": "return", "type": "return", "children": children}
        elif tag in ('if', 'if_else', 'if_else_if'):
            children = [self.generate_json_tree(node[1]), self.generate_json_tree(node[2])]
            if len(node) > 3 and node[3]:
                children.append(self.generate_json_tree(node[3]))
            return {"name": "if", "type": "if", "children": children}
        elif tag == 'for_clause':
            children = [
                self.generate_json_tree(node[1]),
                self.generate_json_tree(node[2]),
                self.generate_json_tree(node[3]),
                self.generate_json_tree(node[4])
            ]
            return {"name": "for (3 cláusulas)", "type": "for", "children": children}
        elif tag == 'for_cond':
            return {
                "name": "for (condición)",
                "type": "for",
                "children": [self.generate_json_tree(node[1]), self.generate_json_tree(node[2])]
            }
        elif tag == 'for_inf':
            return {
                "name": "for { }",
                "type": "for",
                "children": [self.generate_json_tree(node[1])]
            }
        else:
            children = [self.generate_json_tree(node[i]) for i in range(1, len(node))]
            return {"name": str(tag), "type": "node", "children": children}


def analyze_syntax(code: str) -> ParseResponse:
    lexer = MyLexer()
    parser = MyParser()

    tokens = list(lexer.tokenize(code))

    if lexer.errores_lexicos:
        return ParseResponse(
            success=False,
            error_message="Errores léxicos detectados: " + " | ".join(lexer.errores_lexicos),
            error_line=None,
            error_index=None
        )

    ast = None
    try:
        ast = parser.parse(lexer.tokenize(code))
    except Exception as e:
        if not parser.error_msg:
            parser.error_msg = f"Estructura sintáctica no válida o no soportada por el analizador: {e}"

    if parser.error_msg:
        return ParseResponse(
            success=False,
            error_message=parser.error_msg,
            error_line=parser.error_line,
            error_index=parser.error_index
        )

    # Generar diagramas del árbol sintáctico
    ast_mermaid = None
    ast_json = None
    if ast is not None:
        visualizer = ASTVisualizer()
        ast_mermaid = visualizer.generate_mermaid(ast)
        ast_json = visualizer.generate_json_tree(ast)

    return ParseResponse(
        success=True,
        error_message=None,
        error_line=None,
        error_index=None,
        ast_mermaid=ast_mermaid,
        ast_json=ast_json
    )
