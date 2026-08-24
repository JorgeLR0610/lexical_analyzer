import unittest
import sys
from pathlib import Path

app_dir = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(app_dir))

from core.semantic import analyze_semantics, SemanticAnalyzer
from core.lexer import MyLexer
from core.parser import MyParser


class TestGoSemanticAnalyzer(unittest.TestCase):
    def setUp(self):
        self.lexer = MyLexer()
        self.parser = MyParser()
        self.analyzer = SemanticAnalyzer()

    def test_valid_program_and_symbol_table(self):
        code = """package main

import "fmt"

func sumar(a int, b int) int {
    return a + b
}

func main() {
    x := 10
    var total int = sumar(x, 5)
    for i := 0; i < x; i++ {
        total += i
    }
    fmt.Println(total)
}"""
        res = analyze_semantics(code)
        self.assertTrue(res.success)
        self.assertEqual(len(res.errors), 0)
        self.assertGreater(len(res.symbols), 0)

        # Validar columnas de símbolos (name, data_type, scope, line)
        for s in res.symbols:
            self.assertIsNotNone(s.name)
            self.assertIsNotNone(s.data_type)
            self.assertIsNotNone(s.scope)
            self.assertIsNotNone(s.line)

        # Validar símbolos específicos
        x_sym = next(s for s in res.symbols if s.name == "x")
        self.assertEqual(x_sym.data_type, "int")
        self.assertEqual(x_sym.scope, "local:main")
        self.assertEqual(x_sym.line, 10)

        i_sym = next(s for s in res.symbols if s.name == "i")
        self.assertEqual(i_sym.data_type, "int")
        self.assertEqual(i_sym.scope, "local:main:for")
        self.assertEqual(i_sym.line, 12)

        sumar_sym = next(s for s in res.symbols if s.name == "sumar")
        self.assertEqual(sumar_sym.data_type, "func(int,int)->int")
        self.assertEqual(sumar_sym.scope, "global")
        self.assertEqual(sumar_sym.line, 5)

    def test_type_mismatch_assignment(self):
        code = """package main
func main() {
    var x int = 10
    x = true
}"""
        res = analyze_semantics(code)
        self.assertFalse(res.success)
        self.assertTrue(any("Error semántico en línea 4: no se puede asignar 'bool' a 'int'" in err for err in res.errors))

    def test_type_mismatch_var_init(self):
        code = """package main
func main() {
    var x int = "hola"
}"""
        res = analyze_semantics(code)
        self.assertFalse(res.success)
        self.assertTrue(any("Error semántico en línea 3: no se puede asignar 'string' a 'int'" in err for err in res.errors))

    def test_type_mismatch_arithmetic(self):
        code = """package main
func main() {
    var a string = "hola"
    var b int = 5
    var c string = a + b
}"""
        res = analyze_semantics(code)
        self.assertFalse(res.success)
        self.assertTrue(any("Error semántico en línea 5: tipos incompatibles para '+': 'string' y 'int'" in err for err in res.errors))

    def test_type_mismatch_relational(self):
        code = """package main
func main() {
    var x int = 10
    var y string = "diez"
    if x == y {
        x = 0
    }
}"""
        res = analyze_semantics(code)
        self.assertFalse(res.success)
        self.assertTrue(any("Error semántico en línea 5: tipos incomparables para '==': 'int' y 'string'" in err for err in res.errors))

    def test_if_condition_non_bool(self):
        code = """package main
func main() {
    var x int = 10
    if x {
        x = 0
    }
}"""
        res = analyze_semantics(code)
        self.assertFalse(res.success)
        self.assertTrue(any("Error semántico en línea 4: la condición del 'if' debe ser de tipo bool, se obtuvo 'int'" in err for err in res.errors))

    def test_for_condition_non_bool(self):
        code = """package main
func main() {
    var x int = 10
    for x {
        x = 0
    }
}"""
        res = analyze_semantics(code)
        self.assertFalse(res.success)
        self.assertTrue(any("Error semántico en línea 4: la condición del 'for' debe ser de tipo bool, se obtuvo 'int'" in err for err in res.errors))

    def test_function_return_mismatch(self):
        code = """package main
func sumar(a int, b int) int {
    return "no es int"
}"""
        res = analyze_semantics(code)
        self.assertFalse(res.success)
        self.assertTrue(any("Error semántico en línea 3: valor de retorno incompatible: se esperaba 'int', se obtuvo 'string'" in err for err in res.errors))

    def test_missing_return_in_function(self):
        code = """package main
func sumar(a int, b int) int {
    x := a + b
}"""
        res = analyze_semantics(code)
        self.assertFalse(res.success)
        self.assertTrue(any("falta sentencia 'return' en la función 'sumar' que declara retorno de tipo 'int'" in err for err in res.errors))

    def test_valid_return_in_if_else(self):
        code = """package main
func maximo(a int, b int) int {
    if a > b {
        return a
    } else {
        return b
    }
}"""
        res = analyze_semantics(code)
        self.assertTrue(res.success)
        self.assertEqual(len(res.errors), 0)

    def test_function_call_arg_mismatch(self):
        code = """package main
func duplicar(n int) int {
    return n * 2
}
func main() {
    res := duplicar("texto")
}"""
        res = analyze_semantics(code)
        self.assertFalse(res.success)
        self.assertTrue(any("Error semántico en línea 6: argumento 1 de 'duplicar' incompatible: se esperaba 'int', se obtuvo 'string'" in err for err in res.errors))

    def test_undeclared_variable(self):
        code = """package main
func main() {
    total = a + 5
}"""
        res = analyze_semantics(code)
        self.assertFalse(res.success)
        self.assertTrue(any("Error semántico en línea 3: variable 'total' no declarada" in err for err in res.errors))
        self.assertTrue(any("Error semántico en línea 3: variable 'a' no declarada" in err for err in res.errors))

    def test_redeclaration_same_scope(self):
        code = """package main
func main() {
    x := 10
    var x string = "duplicado"
}"""
        res = analyze_semantics(code)
        self.assertFalse(res.success)
        self.assertTrue(any("Error semántico en línea 4: identificador 'x' ya ha sido declarado en el ámbito 'local:main'" in err for err in res.errors))

    def test_valid_variable_shadowing(self):
        code = """package main
var x int = 100
func main() {
    x := 10
    if x > 0 {
        x := "sombra valida"
    }
}"""
        res = analyze_semantics(code)
        self.assertTrue(res.success)
        self.assertEqual(len(res.errors), 0)


if __name__ == "__main__":
    unittest.main()
