from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from api.schemas import CodeRequest, LexerResponse, ParseResponse, SemanticResponse, IRResponse
from core.lexer import analyze_code
from core.parser import analyze_syntax
from core.semantic import analyze_semantics
from core.ir_generator import generate_ir

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

@router.post("/ir", response_model=IRResponse)
def ir_endpoint(request: CodeRequest):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="El bloque de código no puede estar vacío.")
    return generate_ir(request.code)

@router.post("/export-ir")
def export_ir_endpoint(request: CodeRequest):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="El bloque de código no puede estar vacío.")
    res = generate_ir(request.code)
    if not res.success:
        raise HTTPException(status_code=400, detail=" | ".join(res.errors))
    content = "\n".join(res.triples) + "\n"
    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=programa.ir"}
    )