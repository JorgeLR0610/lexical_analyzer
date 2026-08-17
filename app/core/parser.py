import logging
from sly import Parser
from core.lexer import MyLexer
from api.schemas import ParseResponse

# Suprimir warnings de SLY sobre conflictos reducir/desplazar inevitables por falta de llaves/indentación explícita
log = logging.getLogger('sly')
log.setLevel(logging.ERROR)

class MyParser(Parser):
    tokens = MyLexer.tokens
    
    precedence = (
        ('left', 'OR'),
        ('left', 'AND'),
        ('right', 'NOT'),
        ('left', 'OPREL'),
        ('left', '+', '-'),
        ('left', '*', '/'),
    )
    
    def __init__(self):
        self.error_msg = None
        self.error_line = None
        self.error_index = None

    @_('statements')
    def program(self, p):
        return p.statements

    @_('statement statements')
    def statements(self, p):
        return [p.statement] + p.statements

    @_('statement')
    def statements(self, p):
        return [p.statement]
        
    @_('assignment', 'expr', 'if_statement', 'while_statement', 'for_statement', 'function_def', 'return_statement')
    def statement(self, p):
        return p[0]
        
    @_('ID "=" expr')
    def assignment(self, p):
        return ('assign', p.ID, p.expr)

    @_('expr "+" expr',
       'expr "-" expr',
       'expr "*" expr',
       'expr "/" expr')
    def expr(self, p):
        return ('binop', p[1], p.expr0, p.expr1)
        
    @_('expr OPREL expr')
    def expr(self, p):
        return ('oprel', p.OPREL, p.expr0, p.expr1)

    @_('expr AND expr',
       'expr OR expr')
    def expr(self, p):
        return ('boolop', p[1], p.expr0, p.expr1)

    @_('NOT expr')
    def expr(self, p):
        return ('not', p.expr)

    @_('"(" expr ")"')
    def expr(self, p):
        return p.expr

    @_('ID', 'NUMERO', 'TRUE', 'FALSE')
    def expr(self, p):
        return p[0]
        
    @_('ID "(" args ")"')
    def expr(self, p):
        return ('call', p.ID, p.args)
        
    @_('expr "," args')
    def args(self, p):
        return [p.expr] + p.args
        
    @_('expr')
    def args(self, p):
        return [p.expr]
        
    @_('empty')
    def args(self, p):
        return []
        
    @_('')
    def empty(self, p):
        pass

    @_('IF expr ":" statements elif_list ELSE ":" statements')
    def if_statement(self, p):
        return ('if_elif_else', p.expr, p.statements0, p.elif_list, p.statements1)

    @_('IF expr ":" statements elif_list')
    def if_statement(self, p):
        return ('if_elif', p.expr, p.statements, p.elif_list)
        
    @_('ELIF expr ":" statements elif_list')
    def elif_list(self, p):
        return [('elif', p.expr, p.statements)] + p.elif_list
        
    @_('empty')
    def elif_list(self, p):
        return []

    @_('WHILE expr ":" statements')
    def while_statement(self, p):
        return ('while', p.expr, p.statements)

    @_('FOR ID IN expr ":" statements')
    def for_statement(self, p):
        return ('for', p.ID, p.expr, p.statements)

    @_('DEF ID "(" args_def ")" ":" statements')
    def function_def(self, p):
        return ('def', p.ID, p.args_def, p.statements)
        
    @_('ID "," args_def')
    def args_def(self, p):
        return [p.ID] + p.args_def

    @_('ID')
    def args_def(self, p):
        return [p.ID]
        
    @_('empty')
    def args_def(self, p):
        return []
        
    @_('RETURN expr')
    def return_statement(self, p):
        return ('return', p.expr)

    def error(self, p):
        if p:
            self.error_msg = f"Error de sintaxis cerca de '{p.value}'"
            self.error_line = p.lineno
            self.error_index = p.index
        else:
            self.error_msg = "Error de sintaxis: Fin de archivo inesperado"
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
            parser.error_msg = f"Estructura no válida o no soportada por el analizador."
            
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
