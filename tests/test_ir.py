import unittest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

app_dir = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(app_dir))

from core.ir_generator import generate_ir, IRGenerator
from core.lexer import MyLexer
from core.parser import MyParser
from main import app


class TestGoIRGenerator(unittest.TestCase):
    def setUp(self):
        self.lexer = MyLexer()
        self.parser = MyParser()
        self.generator = IRGenerator()
        self.client = TestClient(app)

    def test_arithmetic_precedence_and_temporals(self):
        # x = 3 + 4 * 2 (Páginas 7 y 10 de IR.pdf)
        code = """package main
func main() {
    x := 3 + 4 * 2
}"""
        res = generate_ir(code)
        self.assertTrue(res.success)
        self.assertEqual(len(res.errors), 0)
        self.assertIsNotNone(res.tac_code)
        self.assertGreater(len(res.triples), 0)
        self.assertGreater(len(res.quadruples), 0)
        self.assertGreater(len(res.postfix_expressions), 0)

        # Verificar cuádruplos de multiplicación y suma
        ops = [q.op for q in res.quadruples]
        self.assertIn("*", ops)
        self.assertIn("+", ops)
        self.assertIn("=", ops)

        # Multiplicación antes que suma
        mul_idx = ops.index("*")
        add_idx = ops.index("+")
        self.assertLess(mul_idx, add_idx)

        # Notación postfija correspondiente
        postfix_strs = [p.postfix for p in res.postfix_expressions]
        self.assertTrue(any("3 4 2 * +" in p for p in postfix_strs))

        # TAC contiene temporales
        self.assertIn("t1 = 4 * 2", res.tac_code)
        self.assertIn("t2 = 3 + t1", res.tac_code)
        self.assertIn("x = t2", res.tac_code)

    def test_if_else_control_flow(self):
        # if (x > 5) { x = x - 1; } else { x = 0; } (Página 11 de IR.pdf)
        code = """package main
func main() {
    var x int = 10
    if x > 5 {
        x = x - 1
    } else {
        x = 0
    }
}"""
        res = generate_ir(code)
        self.assertTrue(res.success)
        self.assertEqual(len(res.errors), 0)

        # Verificar saltos y etiquetas
        ops = [q.op for q in res.quadruples]
        self.assertIn("ifFalse", ops)
        self.assertIn("goto", ops)
        self.assertIn("label", ops)

        # TAC contiene control de flujo con ifFalse y goto
        self.assertIn("ifFalse", res.tac_code)
        self.assertIn("goto", res.tac_code)
        self.assertIn("L1:", res.tac_code)
        self.assertIn("L2:", res.tac_code)

    def test_for_loop_control_flow(self):
        code = """package main
func main() {
    var total int = 0
    for i := 0; i < 10; i++ {
        total += i
    }
}"""
        res = generate_ir(code)
        self.assertTrue(res.success)
        self.assertEqual(len(res.errors), 0)

        # Verificar bucle con labels y saltos
        self.assertIn("L1:", res.tac_code)
        self.assertIn("ifFalse", res.tac_code)
        self.assertIn("goto L1", res.tac_code)

    def test_function_call_and_return(self):
        code = """package main

func duplicar(n int) int {
    return n * 2
}

func main() {
    res := duplicar(5)
}"""
        res = generate_ir(code)
        self.assertTrue(res.success)
        self.assertEqual(len(res.errors), 0)

        ops = [q.op for q in res.quadruples]
        self.assertIn("param", ops)
        self.assertIn("call", ops)
        self.assertIn("return", ops)

    def test_syntax_or_semantic_error_blocks_ir(self):
        # Código con error de tipos (int = bool)
        code = """package main
func main() {
    var x int = 10
    x = true
}"""
        res = generate_ir(code)
        self.assertFalse(res.success)
        self.assertGreater(len(res.errors), 0)
        self.assertIsNone(res.tac_code)

    def test_fastapi_ir_endpoint(self):
        code = """package main
func main() {
    x := 3 + 4 * 2
}"""
        r = self.client.post("/ir", json={"code": code})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["success"])
        self.assertIn("t1 = 4 * 2", data["tac_code"])
        self.assertGreater(len(data["triples"]), 0)
        self.assertGreater(len(data["quadruples"]), 0)


if __name__ == "__main__":
    unittest.main()
