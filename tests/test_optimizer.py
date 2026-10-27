import unittest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

app_dir = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(app_dir))

from core.lexer import MyLexer
from core.parser import MyParser
from core.ir_generator import generate_ir
from core.optimizer import (
    Quad,
    BasicBlock,
    ControlFlowGraph,
    IROptimizer,
    optimize_code
)
from main import app


class TestGoOptimizerU3(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_basic_block_partitioning(self):
        # Secuencia con saltos y etiquetas
        quads = [
            Quad('=', '5', '', 'a'),
            Quad('=', '10', '', 'b'),
            Quad('ifFalse', 't1', '', 'L1'),
            Quad('=', '1', '', 'x'),
            Quad('goto', '', '', 'L2'),
            Quad('label', '', '', 'L1'),
            Quad('=', '0', '', 'x'),
            Quad('label', '', '', 'L2'),
            Quad('return', 'x', '', '')
        ]
        cfg = ControlFlowGraph.from_quads(quads)
        self.assertGreaterEqual(len(cfg.blocks), 4)
        # B1 debe tener a=5, b=10, ifFalse
        self.assertEqual(cfg.blocks[0].id, "B1")
        self.assertIn("B2", cfg.blocks[0].successors)

    def test_cfg_successors_and_cyclomatic_complexity(self):
        code = """package main
func test() int {
    var x int = 10
    if x > 5 {
        x = 1
    } else {
        x = 0
    }
    return x
}"""
        res = optimize_code(code)
        self.assertTrue(res.success)
        self.assertGreaterEqual(res.metrics.cyclomatic_complexity_before, 2)
        self.assertGreater(len(res.blocks_before), 1)

    def test_constant_folding(self):
        quads = [
            Quad('+', '20', '30', 't1'),
            Quad('*', '4', '5', 't2'),
            Quad('>', '15', '10', 't3'),
            Quad('return', 't1', '', '')
        ]
        optimizer = IROptimizer()
        opt_quads, trans = optimizer.optimize(quads)

        # Buscar transformaciones de folding
        folding_trans = [t for t in trans if "Constant Folding" in t.technique or "Plegado de constantes" in t.technique]
        self.assertGreaterEqual(len(folding_trans), 3)
        self.assertTrue(any("t1 = 50" in t.optimized_code for t in folding_trans))
        self.assertTrue(any("t2 = 20" in t.optimized_code for t in folding_trans))
        self.assertTrue(any("t3 = true" in t.optimized_code for t in folding_trans))

        # En el código final, el return debe tener el valor constante plegado 50
        ret_q = next(q for q in opt_quads if q.op == 'return')
        self.assertEqual(ret_q.arg1, '50')

    def test_constant_propagation(self):
        quads = [
            Quad('=', '5', '', 'a'),
            Quad('=', '10', '', 'b'),
            Quad('+', 'a', 'b', 't1'),
            Quad('return', 't1', '', '')
        ]
        optimizer = IROptimizer()
        opt_quads, trans = optimizer.optimize(quads)

        # La suma a + b debe haberse transformado en constante plegada
        ret_q = next(q for q in opt_quads if q.op == 'return')
        self.assertEqual(ret_q.arg1, '15')

        prop_trans = [t for t in trans if "Propagación de constantes" in t.technique]
        self.assertGreater(len(prop_trans), 0)

    def test_common_subexpression_elimination_cse(self):
        quads = [
            Quad('+', 'a', 'b', 't1'),
            Quad('+', 'a', 'b', 't2'),
            Quad('return', 't2', '', '')
        ]
        optimizer = IROptimizer()
        opt_quads, trans = optimizer.optimize(quads)

        cse_trans = [t for t in trans if "CSE" in t.technique or "subexpresiones comunes" in t.technique]
        self.assertGreater(len(cse_trans), 0)

    def test_unreachable_code_elimination(self):
        quads = [
            Quad('=', '1', '', 'x'),
            Quad('return', 'x', '', ''),
            Quad('=', '200', '', 'w')  # Inalcanzable tras return
        ]
        optimizer = IROptimizer()
        opt_quads, trans = optimizer.optimize(quads)

        # w = 200 no debe estar presente
        self.assertFalse(any(q.arg1 == '200' for q in opt_quads))
        unreach_trans = [t for t in trans if "inalcanzable" in t.technique.lower()]
        self.assertGreater(len(unreach_trans), 0)

    def test_dead_code_elimination(self):
        quads = [
            Quad('=', '100', '', 'unused_var'),
            Quad('=', '1', '', 'used_var'),
            Quad('return', 'used_var', '', '')
        ]
        optimizer = IROptimizer()
        opt_quads, trans = optimizer.optimize(quads)

        # unused_var no debe estar presente
        self.assertFalse(any(q.result == 'unused_var' for q in opt_quads))
        dead_trans = [t for t in trans if "muerto" in t.technique.lower()]
        self.assertGreater(len(dead_trans), 0)

    def test_ejemplo_pdf_full_pipeline(self):
        code_go = """package main

func ejecutar() int {
    a := 5
    b := 10
    t1 := a + b
    t2 := a + b
    var x int = 0
    if t1 > 10 {
        x = 1
    } else {
        x = 0
    }
    y := x
    z := 20 + 30
    w := 100
    return y
    w = 200
}

func main() {
    ejecutar()
}"""
        res = optimize_code(code_go)
        self.assertTrue(res.success)
        self.assertEqual(len(res.errors), 0)
        self.assertGreater(len(res.transformations), 0)
        self.assertGreater(res.metrics.reduction_percent, 0.0)
        # Debe haber simplificado la complejidad ciclomática
        self.assertEqual(res.metrics.cyclomatic_complexity_before, 2)
        self.assertEqual(res.metrics.cyclomatic_complexity_after, 1)

    def test_fastapi_optimization_endpoints(self):
        code_go = """package main
func main() {
    x := 20 + 30
}"""
        # 1. POST /optimize
        r = self.client.post("/optimize", json={"code": code_go})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["success"])
        self.assertIn("original_ir", data)
        self.assertIn("optimized_ir", data)
        self.assertIn("transformations", data)
        self.assertIn("metrics", data)

        # 2. POST /optimize/export-before
        r_before = self.client.post("/optimize/export-before", json={"code": code_go})
        self.assertEqual(r_before.status_code, 200)
        self.assertIn("attachment; filename=antes.ir", r_before.headers.get("content-disposition", ""))

        # 3. POST /optimize/export-after
        r_after = self.client.post("/optimize/export-after", json={"code": code_go})
        self.assertEqual(r_after.status_code, 200)
        self.assertIn("attachment; filename=despues.ir", r_after.headers.get("content-disposition", ""))

    def test_standalone_variable_declaration_and_tac_comparison(self):
        # Caso específico: var x int = 3 + 4 * 2
        code = "var x int = 3 + 4 * 2"
        res = optimize_code(code)
        self.assertTrue(res.success)
        self.assertEqual(res.metrics.total_instructions_after, 1)
        self.assertEqual(len(res.blocks_after), 1)
        self.assertIn("x = 11", res.optimized_tac)
        self.assertIn("(=, 11, , x)", res.optimized_ir)
        self.assertIn("t1 = 4 * 2", res.original_tac)
        # Verificar que todos los bloques en transformaciones sean identificadores reales (B1, etc.)
        self.assertTrue(all(t.block_id.startswith("B") for t in res.transformations))
        self.assertFalse(any(t.block_id in ("Local", "Control") for t in res.transformations))

    def test_optimization_analysis_generation_and_api(self):
        # Validar generación del informe de análisis y conclusiones (Rúbrica U3 numeral 7)
        code_go = """package main
func ejecutar() int {
    a := 5
    b := 10
    t1 := a + b
    t2 := a + b
    var x int = 0
    if t1 > 10 {
        x = 1
    } else {
        x = 0
    }
    y := x
    z := 20 + 30
    w := 100
    return y
    w = 200
}
func main() {
    ejecutar()
}"""
        res = optimize_code(code_go)
        self.assertTrue(res.success)
        self.assertIsNotNone(res.analysis)
        self.assertGreater(len(res.analysis.optimizations_applied), 0)
        self.assertGreater(len(res.analysis.benefits), 0)
        self.assertTrue(bool(res.analysis.instructions_analysis))
        self.assertTrue(bool(res.analysis.cfg_contribution))
        self.assertTrue(bool(res.analysis.conclusions))
        self.assertIn("GFG", res.analysis.cfg_contribution)
        self.assertIn("Complejidad Ciclomática", res.analysis.cfg_contribution)

        # Validar serialización en endpoint FastAPI
        r = self.client.post("/optimize", json={"code": code_go})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("analysis", data)
        self.assertIsNotNone(data["analysis"])
        self.assertIn("summary", data["analysis"])
        self.assertIn("optimizations_applied", data["analysis"])
        self.assertIn("benefits", data["analysis"])
        self.assertIn("instructions_analysis", data["analysis"])
        self.assertIn("cfg_contribution", data["analysis"])
        self.assertIn("conclusions", data["analysis"])


if __name__ == "__main__":
    unittest.main()
