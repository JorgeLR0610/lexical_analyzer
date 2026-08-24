from fastapi import APIRouter, HTTPException
from api.schemas import CodeRequest, LexerResponse, ParseResponse, SemanticResponse
from core.lexer import analyze_code
from core.parser import analyze_syntax
from core.semantic import analyze_semantics

router = APIRouter()

@router.post("/tokenize", response_model=LexerResponse)
def tokenize_endpoint(request: CodeRequest):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="El bloque de código no puede estar vacío.")
    return analyze_code(request.code)

@router.post("/parse", response_model=ParseResponse)
def parse_endpoint(request: CodeRequest):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="El bloque de código no puede estar vacío.")
    return analyze_syntax(request.code)

@router.post("/semantic", response_model=SemanticResponse)
def semantic_endpoint(request: CodeRequest):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="El bloque de código no puede estar vacío.")
    return analyze_semantics(request.code)