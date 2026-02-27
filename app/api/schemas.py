from pydantic import BaseModel

class CodeRequest(BaseModel):
    code: str

class TokenResponse(BaseModel):
    lexeme: str
    token_name: str
    attribute_value: str

class LexerResponse(BaseModel):
    tokens: list[TokenResponse]
    errors: list[str]