from sly import Lexer
from api.schemas import TokenResponse, LexerResponse

class MyLexer(Lexer):
    tokens = { ID, NUMERO, IF, THEN, ELSE, OPREL }  # type: ignore
        
    ignore = ' \t\n' 

    @_(r'<=')
    def LE(self, t):
        t.type = "OPREL"
        t.value = "LE"
        return t

    @_(r'<>')
    def NE(self, t):
        t.type = "OPREL"
        t.value = "NE"
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

    @_(r'=')
    def EQ(self, t):
        t.type = "OPREL"
        t.value = "EQ"
        return t

    @_(r'>')
    def GT(self, t):
        t.type = "OPREL"
        t.value = "GT"
        return t
    
    NUMERO = r'\d+'
    
    ID = r'[a-zA-Z_][a-zA-Z0-9_]*'
    
    # Las palabras reservadas serian excepciones en los identificadores
    ID['if'] = IF
    ID['then'] = THEN
    ID['else'] = ELSE

    ignore_comment = r'\#.*'

    def __init__(self):
        self.errores_lexicos = []

    def error(self, t):
        self.errores_lexicos.append(
            f"Carácter no válido '{t.value[0]}' en la posición {t.index}"
        )
        self.index += 1
        
OPREL_MAP = { 
"LE": "<=",
"LT": "<",
"EQ": "=",
"NE": "<>",
"GE": ">=",
"GT": ">"
}
        
def analyze_code(code: str) -> LexerResponse:
    lexer = MyLexer()
    tokens_list = list()
    
    for token in lexer.tokenize(code):
        
        # Obtener lexema original para oprel y establecer los de los otros
        if token.type == "OPREL":
            original_lexeme = OPREL_MAP[token.value]
        else:
            original_lexeme = str(token.value)
        
        # Establecer el valor del atributo        
        if token.type in ["ID", "NUMERO", "OPREL"]: 
            attribute_value = str(token.value)
        else:
            attribute_value = "-"

        # Hacer la lista acorde al schema
        
        tokens_obj = TokenResponse(
            lexeme=original_lexeme,
            token_name=token.type.lower(),
            attribute_value=attribute_value
        )
        tokens_list.append(tokens_obj)
        
    return LexerResponse(
        tokens=tokens_list,
        errors=lexer.errores_lexicos
    )
