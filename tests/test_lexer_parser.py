import unittest
import sys
from pathlib import Path

# Agregar directorio app al path para importar módulos
app_dir = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(app_dir))

from core.lexer import MyLexer, analyze_code
from core.parser import MyParser, analyze_syntax


class TestGoLexer(unittest.TestCase):
    def setUp(self):
        self.lexer = MyLexer()

    def test_keywords_recognition(self):
        code = "package import func var const type struct if else for return true false nil"
        res = analyze_code(code)
        self.assertEqual(len(res.errors), 0)
        expected_types = [
            "package", "import", "func", "var", "const", "type", "struct",
            "if", "else", "for", "return", "true", "false", "nil"
        ]
        actual_types = [t.token_name for t in res.tokens]
        self.assertEqual(actual_types, expected_types)

    def test_assignment_operator_asign(self):
        code = "var x = 10"
        res = analyze_code(code)
        self.assertEqual(len(res.errors), 0)
        assign_tok = next(t for t in res.tokens if t.lexeme == "=")
        self.assertEqual(assign_tok.token_name, "asign")
        self.assertEqual(assign_tok.attribute_value, "=")

    def test_short_assignment_operator_asign_corta(self):
        code = "x := 20"
        res = analyze_code(code)
        self.assertEqual(len(res.errors), 0)
        short_assign_tok = next(t for t in res.tokens if t.lexeme == ":=")
        self.assertEqual(short_assign_tok.token_name, "asign_corta")
        self.assertEqual(short_assign_tok.attribute_value, ":=")

    def test_semicolon_delimitador(self):
        code = "var x = 10;"
        res = analyze_code(code)
        self.assertEqual(len(res.errors), 0)
        semi_tok = next(t for t in res.tokens if t.lexeme == ";")
        self.assertEqual(semi_tok.token_name, "delimitador")
        self.assertEqual(semi_tok.attribute_value, ";")

    def test_arithmetic_operators_opar(self):
        code = "+ - * / %"
        res = analyze_code(code)
        self.assertEqual(len(res.errors), 0)
        for t in res.tokens:
            self.assertEqual(t.token_name, "OPAR")
            self.assertEqual(t.attribute_value, t.lexeme)

    def test_relational_operators_oprel(self):
        code = "== != <= >= < >"
        res = analyze_code(code)
        self.assertEqual(len(res.errors), 0)
        expected = [
            ("==", "OPREL", "EQ"),
            ("!=", "OPREL", "NE"),
            ("<=", "OPREL", "LE"),
            (">=", "OPREL", "GE"),
            ("<", "OPREL", "LT"),
            (">", "OPREL", "GT"),
        ]
        actual = [(t.lexeme, t.token_name, t.attribute_value) for t in res.tokens]
        self.assertEqual(actual, expected)

    def test_primitive_types(self):
        code = "int string bool float64 float32 byte rune uint error any"
        res = analyze_code(code)
        self.assertEqual(len(res.errors), 0)
        for t in res.tokens:
            self.assertEqual(t.token_name, "TYPE")
            self.assertEqual(t.attribute_value, t.lexeme.upper())

    def test_deduplication(self):
        code = """
        func suma(a int, b int) int {
            return a + b + a
        }
        """
        res = analyze_code(code)
        self.assertEqual(len(res.errors), 0)
        lexemes = [t.lexeme for t in res.tokens]
        # Ningún elemento debe estar repetido
        self.assertEqual(len(lexemes), len(set(lexemes)))
        # 'int' y 'a' y '+' solo deben aparecer 1 vez
        self.assertEqual(lexemes.count("int"), 1)
        self.assertEqual(lexemes.count("a"), 1)
        self.assertEqual(lexemes.count("+"), 1)

    def test_literals(self):
        code = '42 3.14159 "hola mundo" `cadena raw`'
        res = analyze_code(code)
        self.assertEqual(len(res.errors), 0)
        self.assertEqual(res.tokens[0].token_name, "int_lit")
        self.assertEqual(res.tokens[0].lexeme, "42")
        self.assertEqual(res.tokens[1].token_name, "float_lit")
        self.assertEqual(res.tokens[1].lexeme, "3.14159")
        self.assertEqual(res.tokens[2].token_name, "string_lit")
        self.assertEqual(res.tokens[3].token_name, "string_lit")

    def test_comments_and_newlines(self):
        code = """// Comentario de una línea
        /* Comentario
           de bloque multilínea */
        var x int = 10
        """
        res = analyze_code(code)
        self.assertEqual(len(res.errors), 0)
        lexemes = [t.lexeme for t in res.tokens]
        self.assertEqual(lexemes, ["var", "x", "int", "=", "10"])

    def test_lexical_error_detection(self):
        code = "var x = 10 @ $ ~"
        res = analyze_code(code)
        self.assertGreater(len(res.errors), 0)
        self.assertTrue(any("@" in err for err in res.errors))
        self.assertTrue(any("$" in err for err in res.errors))


class TestGoParser(unittest.TestCase):
    def test_full_program(self):
        code = """
        package main

        import "fmt"

        func sumar(a int, b int) int {
            return a + b
        }

        func main() {
            x := 10
            total := 0
            for i := 0; i < x; i++ {
                if i % 2 == 0 {
                    total = sumar(total, i)
                } else if i <= 5 {
                    total += 10
                } else {
                    total -= 1
                }
            }
            fmt.Println("Total:", total)
        }
        """
        res = analyze_syntax(code)
        self.assertTrue(res.success)
        self.assertIsNone(res.error_message)

    def test_invalid_fun_keyword(self):
        # En Go las funciones deben usar 'func', no 'fun'
        code = """
        fun main() {
            var a string = "a"
        }
        """
        res = analyze_syntax(code)
        self.assertFalse(res.success)
        self.assertIsNotNone(res.error_message)

    def test_valid_func_main(self):
        code = """
        func main() {
            var a string = "a"
        }
        """
        res = analyze_syntax(code)
        self.assertTrue(res.success)
        self.assertIsNone(res.error_message)

    def test_invalid_bare_identifiers(self):
        code = "foo bar baz"
        res = analyze_syntax(code)
        self.assertFalse(res.success)

    def test_control_structures(self):
        # if-else if-else
        code_if = """
        if x > 100 {
            res = 1
        } else if x == 100 {
            res = 0
        } else {
            res = -1
        }
        """
        res = analyze_syntax(code_if)
        self.assertTrue(res.success)

        # for condition
        code_for_cond = "for total < 1000 { total += 10 }"
        self.assertTrue(analyze_syntax(code_for_cond).success)

        # for infinite
        code_for_inf = "for { breakLoop() }"
        self.assertTrue(analyze_syntax(code_for_inf).success)

    def test_struct_and_type_declarations(self):
        code = """
        type Persona struct {
            nombre string
            edad int
            activo bool
        }

        type ID int
        """
        res = analyze_syntax(code)
        self.assertTrue(res.success)

    def test_variable_declarations(self):
        code = """
        var a int = 10;
        var b string;
        var c = 20;
        const PI float64 = 3.1416;
        const MAX = 100;
        y := a + 50;
        """
        res = analyze_syntax(code)
        self.assertTrue(res.success)

    def test_complex_expressions(self):
        code = "val := (a + b) * (c - d) / 2 > 0 && !flag || isReady"
        res = analyze_syntax(code)
        self.assertTrue(res.success)

    def test_syntax_error_missing_braces(self):
        code = """
        if x > 10
            return 20
        """
        res = analyze_syntax(code)
        self.assertFalse(res.success)
        self.assertIsNotNone(res.error_message)
        self.assertIn("Error de sintaxis", res.error_message)

    def test_syntax_error_unclosed_brace(self):
        code = """
        func test() {
            x := 1
        """
        res = analyze_syntax(code)
        self.assertFalse(res.success)
        self.assertIsNotNone(res.error_message)


if __name__ == "__main__":
    unittest.main()
