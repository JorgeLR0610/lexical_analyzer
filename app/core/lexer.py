from sly import Lexer
from api.schemas import TokenResponse, LexerResponse

class MyLexer(Lexer):
    tokens = { ID, NUMERO, IF, ELSE, ELIF, WHILE, FOR, IN, DEF, RETURN, AND, OR, NOT, TRUE, FALSE, OPREL } # type: ignore
    
    literals = { '(', ')', '{', '}', '[', ']', '+', '-', '*', '/', '=', ':', ',', '.' }
        
    ignore = ' \t' 

    @_(r'\n+')
    def ignore_newline(self, t):
        self.lineno += t.value.count('\n')

    @_(r'==')
    def EQ(self, t):
        t.type = "OPREL"
        t.value = "EQ"
        return t

    @_(r'!=|<>')
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
    
    NUMERO = r'\d+'
    
    ID = r'[a-zA-Z_][a-zA-Z0-9_]*'
    
    ID['if'] = IF
    ID['else'] = ELSE
    ID['elif'] = ELIF
    ID['while'] = WHILE
    ID['for'] = FOR
    ID['in'] = IN
    ID['def'] = DEF
    ID['return'] = RETURN
    ID['and'] = AND
    ID['or'] = OR
    ID['not'] = NOT
    ID['True'] = TRUE
    ID['False'] = FALSE

    ignore_comment = r'\#.*'

    def __init__(self):
        self.errores_lexicos = []

    def error(self, t):
        self.errores_lexicos.append(
            f"Carácter no válido '{t.value[0]}' en la línea {self.lineno}, posición {t.index}"
        )
        self.index += 1
        
OPREL_MAP = { 
    "LE": "<=",
    "LT": "<",
    "EQ": "==",
    "NE": "!=",
    "GE": ">=",
    "GT": ">"
}
        
def analyze_code(code: str) -> LexerResponse:
    lexer = MyLexer()
    tokens_list = list()
    
    for token in lexer.tokenize(code):
        if token.type == "OPREL":
            original_lexeme = OPREL_MAP[token.value]
        else:
            original_lexeme = str(token.value)
        
        # Establecer el valor del atributo        
        if token.type in ["ID", "NUMERO", "OPREL"]: 
            attribute_value = str(token.value)
        elif token.type in lexer.literals:
            attribute_value = str(token.value)
        else:
            attribute_value = "-"

        tokens_obj = TokenResponse(
            lexeme=original_lexeme,
            token_name=token.type.lower() if hasattr(token, 'type') else str(token.type),
            attribute_value=attribute_value
        )
        tokens_list.append(tokens_obj)
        
    return LexerResponse(
        tokens=tokens_list,
        errors=lexer.errores_lexicos
    )
