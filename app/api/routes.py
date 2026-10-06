from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from api.schemas import (
    CodeRequest,
    LexerResponse,
    ParseResponse,
    SemanticResponse,
    IRResponse,
    OptimizationResponse
)
from core.lexer import analyze_code
from core.parser import analyze_syntax
from core.semantic import analyze_semantics
from core.ir_generator import generate_ir
from core.optimizer import optimize_code

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

@router.post("/optimize", response_model=OptimizationResponse)
def optimize_endpoint(request: CodeRequest):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="El bloque de código no puede estar vacío.")
    return optimize_code(request.code)

@router.post("/optimize/export-before")
def export_before_endpoint(request: CodeRequest):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="El bloque de código no puede estar vacío.")
    res = optimize_code(request.code)
    if not res.success:
        raise HTTPException(status_code=400, detail=" | ".join(res.errors))
    return Response(
        content=res.original_ir,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=antes.ir"}
    )

@router.post("/optimize/export-after")
def export_after_endpoint(request: CodeRequest):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="El bloque de código no puede estar vacío.")
    res = optimize_code(request.code)
    if not res.success:
        raise HTTPException(status_code=400, detail=" | ".join(res.errors))
    return Response(
        content=res.optimized_ir,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=despues.ir"}
    )