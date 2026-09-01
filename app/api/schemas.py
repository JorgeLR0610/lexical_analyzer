from pydantic import BaseModel
from typing import Optional, Any

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
    ast_mermaid: Optional[str] = None
    ast_json: Optional[dict[str, Any]] = None

class SymbolResponse(BaseModel):
    name: str
    data_type: str
    scope: str
    line: Optional[int] = None

class SemanticResponse(BaseModel):
    success: bool
    errors: list[str]
    symbols: list[SymbolResponse]

class QuadrupleResponse(BaseModel):
    index: int
    op: str
    arg1: str
    arg2: str
    result: str
    formatted: str

class PostfixItemResponse(BaseModel):
    infix: str
    postfix: str

class IRResponse(BaseModel):
    success: bool
    errors: list[str]
    tac_code: Optional[str] = None
    triples: list[str] = []
    quadruples: list[QuadrupleResponse] = []
    postfix_expressions: list[PostfixItemResponse] = []