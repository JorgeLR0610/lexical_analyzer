#type: ignore
import logging
from sly import Parser
from core.lexer import MyLexer
from api.schemas import ParseResponse

# Configurar logging de SLY
log = logging.getLogger('sly')
log.setLevel(logging.ERROR)

# Parser LALR ascendente generado a partir de las reglas anotadas con @_('...'), similar a yacc/bison


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

    # Declaración de paquete, como: package main
    @_('PACKAGE ID')
    def package_decl(self, p):
        return ('package', p.ID)

    # Declaración de importaciones: import "fmt" o import ( "fmt" "os" )
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

    # Declaración de funciones: func sumar(a int, b int) int { ... }
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

    # Especificación de tipos (primitivos TYPE o personalizados ID, []type, *type)
    @_('TYPE', 'ID')
    def type_spec(self, p):
        return p[0]

    @_('"[" "]" type_spec')
    def type_spec(self, p):
        return ('slice_type', p.type_spec)

    @_('"*" type_spec')
    def type_spec(self, p):
        return ('ptr_type', p.type_spec)

    # Declaración de Tipos y Structs: type Persona struct {...}
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
    # Bloques y sentencias
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

    # Bucles FOR (infinito, condicional tipo While, y de 3 componentes)
    @_('FOR block')
    def for_stmt(self, p):
        return ('for_inf', p.block)

    @_('FOR expr block')
    def for_stmt(self, p):
        return ('for_cond', p.expr, p.block)

    @_('FOR simple_stmt ";" expr ";" simple_stmt block')
    def for_stmt(self, p):
        return ('for_clause', p.simple_stmt0, p.expr, p.simple_stmt1, p.block)

    # Return
    @_('RETURN expr')
    def return_stmt(self, p):
        return ('return', p.expr)

    @_('RETURN')
    def return_stmt(self, p):
        return ('return', None)

    # ==========================================
    # Expresiones y operadores
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
    def error(self, p):
        if p:
            self.error_msg = f"Error de sintaxis cerca de '{p.value}' en la línea {p.lineno}"
            self.error_line = p.lineno
            self.error_index = p.index
        else:
            self.error_msg = "Error de sintaxis: Fin de archivo inesperado (posibles llaves '{' o paréntesis sin cerrar)"
            self.error_line = None
            self.error_index = None


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

    try:
        parser.parse(lexer.tokenize(code))
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

    return ParseResponse(
        success=True,
        error_message=None,
        error_line=None,
        error_index=None
    )
