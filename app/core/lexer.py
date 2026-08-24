#type: ignore
from sly import Lexer
from api.schemas import TokenResponse, LexerResponse

class MyLexer(Lexer):
    tokens = {
        PACKAGE, IMPORT, FUNC, VAR, CONST, TYPE_KW, STRUCT,
        IF, ELSE, FOR, RETURN,
        TRUE, FALSE, NIL,
        ID, INT_LIT, FLOAT_LIT, STRING_LIT,
        ASSIGN_DEF, ASSIGN, OPREL, AND, OR, INC, DEC,
        ADD_ASSIGN, SUB_ASSIGN, MUL_ASSIGN, DIV_ASSIGN,
        TYPE
    }

    literals = {
        '(', ')', '{', '}', '[', ']',
        '+', '-', '*', '/', '%',
        '!',
        ',', ';', ':', '.'
    }

    ignore = ' \t\r'

    @_(r'\n+')
    def ignore_newline(self, t):
        # Incrementar line number
        self.lineno += t.value.count('\n')

    # Comentarios de bloque multilínea: /* ... */
    @_(r'/\*[\s\S]*?\*/')
    def ignore_block_comment(self, t):
        self.lineno += t.value.count('\n')

    # Comentario de una sola línea: // ...
    ignore_comment = r'//.*'

    # Operadores compuestos (el orden de definición importa)
    ASSIGN_DEF = r':='
    AND = r'&&'
    OR = r'\|\|'
    INC = r'\+\+'
    DEC = r'--'
    ADD_ASSIGN = r'\+='
    SUB_ASSIGN = r'-='
    MUL_ASSIGN = r'\*='
    DIV_ASSIGN = r'/='

    # Operadores relacionales -> OPREL
    @_(r'==')
    def EQ(self, t):
        t.type = "OPREL"
        t.value = "EQ"
        return t

    @_(r'!=')
    def NE(self, t):
        t.type = "OPREL"
        t.value = "NE"
        return t

    @_(r'<=')
    def LE(self, t):
        t.type = "OPREL"
        t.value = "LE"
        return t

    @_(r'>=')
    def GE(self, t):
        t.type = "OPREL"
        t.value = "GE"
        return t

    @_(r'<')
    def LT(self, t):
        t.type = "OPREL"
        t.value = "LT"
        return t

    @_(r'>')
    def GT(self, t):
        t.type = "OPREL"
        t.value = "GT"
        return t

    # Operador de asignación simple '='
    ASSIGN = r'='

    # Literales flotantes
    FLOAT_LIT = r'\d+\.\d+'

    # Literales enteros
    INT_LIT = r'\d+'

    # Literales de cadena (comillas dobles o comillas invertidas)
    @_(r'\"([^\\\n]|(\\.))*\"|`[^`]*`')
    def STRING_LIT(self, t):
        self.lineno += t.value.count('\n')
        return t

    # Catch all para todos los identificadores y palabras clave
    ID = r'[a-zA-Z_][a-zA-Z0-9_]*'

    # Separar ids de las palabras reservadas
    ID['package'] = PACKAGE
    ID['import'] = IMPORT
    ID['func'] = FUNC
    ID['var'] = VAR
    ID['const'] = CONST
    ID['type'] = TYPE_KW
    ID['struct'] = STRUCT
    ID['if'] = IF
    ID['else'] = ELSE
    ID['for'] = FOR
    ID['return'] = RETURN
    ID['true'] = TRUE
    ID['false'] = FALSE
    ID['nil'] = NIL

    # Separar tipos de datos primitivos -> TYPE
    ID['int'] = TYPE
    ID['string'] = TYPE
    ID['bool'] = TYPE
    ID['float64'] = TYPE
    ID['float32'] = TYPE
    ID['byte'] = TYPE
    ID['rune'] = TYPE
    ID['uint'] = TYPE
    ID['int64'] = TYPE
    ID['int32'] = TYPE
    ID['uint64'] = TYPE
    ID['uint32'] = TYPE
    ID['any'] = TYPE
    ID['error'] = TYPE

    def __init__(self):
        self.errores_lexicos = []

    def error(self, t):
        self.errores_lexicos.append(
            f"Carácter no válido '{t.value[0]}' en la línea {self.lineno}, posición {t.index}"
        )
        self.index += 1


KEYWORDS_SET = {
    'PACKAGE', 'IMPORT', 'FUNC', 'VAR', 'CONST', 'STRUCT',
    'IF', 'ELSE', 'FOR', 'RETURN', 'TRUE', 'FALSE', 'NIL'
}

OPREL_MAP = {
    'EQ': '==',
    'NE': '!=',
    'LE': '<=',
    'GE': '>=',
    'LT': '<',
    'GT': '>'
}

ARITHMETIC_OPS = {'+', '-', '*', '/', '%'}

OTHER_OPERATORS_MAP = {
    'AND': '&&',
    'OR': '||',
    'INC': '++',
    'DEC': '--',
    'ADD_ASSIGN': '+=',
    'SUB_ASSIGN': '-=',
    'MUL_ASSIGN': '*=',
    'DIV_ASSIGN': '/=',
}


def analyze_code(code: str) -> LexerResponse:
    lexer = MyLexer()
    tokens_list = list()
    seen = set()

    for token in lexer.tokenize(code):
        token_type = str(token.type)
        
        if token_type == 'OPREL':
            original_lexeme = OPREL_MAP.get(token.value, str(token.value))
            token_name = "OPREL"
            attribute_value = str(token.value)
        elif token_type == 'ASSIGN':
            original_lexeme = "="
            token_name = "asign"
            attribute_value = "="
        elif token_type == 'ASSIGN_DEF':
            original_lexeme = ":="
            token_name = "asign_corta"
            attribute_value = ":="
        elif token.value == ';':
            original_lexeme = ";"
            token_name = "delimitador"
            attribute_value = ";"
        elif token_type in ARITHMETIC_OPS or token.value in ARITHMETIC_OPS:
            original_lexeme = str(token.value)
            token_name = "OPAR"
            attribute_value = str(token.value)
        elif token_type == 'TYPE':
            original_lexeme = str(token.value)
            token_name = "TYPE"
            attribute_value = str(token.value).upper()
        elif token_type == 'TYPE_KW':
            original_lexeme = str(token.value)
            token_name = "type"
            attribute_value = "-"
        elif token_type in KEYWORDS_SET:
            original_lexeme = str(token.value)
            token_name = token_type.lower()
            attribute_value = "-"
        elif token_type in ["ID", "INT_LIT", "FLOAT_LIT", "STRING_LIT"]:
            original_lexeme = str(token.value)
            token_name = token_type.lower()
            attribute_value = str(token.value)
        elif token_type in OTHER_OPERATORS_MAP:
            original_lexeme = OTHER_OPERATORS_MAP[token_type]
            token_name = token_type.lower()
            attribute_value = OTHER_OPERATORS_MAP[token_type]
        elif token_type in lexer.literals:
            original_lexeme = str(token.value)
            token_name = str(token.value)
            attribute_value = str(token.value)
        else:
            original_lexeme = str(token.value)
            token_name = token_type.lower()
            attribute_value = str(token.value)

        # Solo agregar a la tabla si no ha sido visto previamente
        token_key = (original_lexeme, token_name, attribute_value)
        if token_key not in seen:
            seen.add(token_key)
            tokens_obj = TokenResponse(
                lexeme=original_lexeme,
                token_name=token_name,
                attribute_value=attribute_value
            )
            tokens_list.append(tokens_obj)

    return LexerResponse(
        tokens=tokens_list,
        errors=lexer.errores_lexicos
    )
