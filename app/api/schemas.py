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

class TransformationResponse(BaseModel):
    step: int
    block_id: str
    technique: str
    original_code: str
    optimized_code: str
    justification: str

class BasicBlockResponse(BaseModel):
    id: str
    instructions: list[str]
    successors: list[str] = []
    predecessors: list[str] = []
    is_unreachable: bool = False

class CFGMetricsResponse(BaseModel):
    total_instructions_before: int
    total_instructions_after: int
    reduction_percent: float
    temporals_saved: int
    cyclomatic_complexity_before: int
    cyclomatic_complexity_after: int
    blocks_before: int
    blocks_after: int

class OptimizationResponse(BaseModel):
    success: bool
    errors: list[str] = []
    original_tac: str = ""
    optimized_tac: str = ""
    original_ir: str = ""
    optimized_ir: str = ""
    original_cfg_mermaid: str = ""
    optimized_cfg_mermaid: str = ""
    blocks_before: list[BasicBlockResponse] = []
    blocks_after: list[BasicBlockResponse] = []
    transformations: list[TransformationResponse] = []
    metrics: CFGMetricsResponse