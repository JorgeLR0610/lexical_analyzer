from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from api.schemas import (
    CodeRequest,
    LexerResponse,
    ParseResponse,
    SemanticResponse,
    IRResponse,
    OptimizationResponse,
    InterferenceGraphRequest,
    InterferenceGraphResponse,
    ObjectCodeResponse
)
from core.lexer import analyze_code
from core.parser import analyze_syntax
from core.semantic import analyze_semantics
from core.ir_generator import generate_ir
from core.optimizer import optimize_code
from core.interference_graph import analyze_interference_graph
from core.object_code import generate_object_code
import csv
import io

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

@router.post("/interference-graph", response_model=InterferenceGraphResponse)
def interference_graph_endpoint(request: InterferenceGraphRequest):
    if not request.adjacency_list.strip():
        raise HTTPException(status_code=400, detail="La lista de adyacencia no puede estar vacía.")
    return analyze_interference_graph(request.adjacency_list)

@router.post("/object-code", response_model=ObjectCodeResponse)
def object_code_endpoint(request: CodeRequest):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="El bloque de código no puede estar vacío.")
    return generate_object_code(request.code)

@router.post("/object-code/export")
def export_object_code_endpoint(request: CodeRequest):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="El bloque de código no puede estar vacío.")
    res = generate_object_code(request.code)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=" | ".join(res.get("errors") or ["Error al generar código objeto."]))
    return Response(
        content=res["assembly"],
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=programa.asm"}
    )

@router.post("/object-code/export-registers")
def export_registers_endpoint(request: CodeRequest):
    if not request.code.strip():
        raise HTTPException(status_code=400, detail="El bloque de código no puede estar vacío.")
    res = generate_object_code(request.code)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=" | ".join(res.get("errors") or ["Error al generar tabla de registros."]))
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['symbol', 'function', 'scope', 'data_type', 'location'], extrasaction='ignore')
    writer.writeheader()
    writer.writerows(res.get("register_assignments", []))
    return Response(
        content=output.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=registros.csv"}
    )

