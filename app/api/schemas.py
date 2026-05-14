from pydantic import BaseModel
from typing import Optional

class CodeRequest(BaseModel):
    code: str

class TokenResponse(BaseModel):
    lexeme: str
    token_name: str
    attribute_value: str

class LexerResponse(BaseModel):
    tokens: list[TokenResponse]
    errors: list[str]

class ParseResponse(BaseModel):
    success: bool
    error_message: Optional[str] = None
    error_line: Optional[int] = None
    error_index: Optional[int] = None