"""Native execution checks: assert observable behavior, not assembly spelling."""
import os
import sys
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from core.object_code import generate_object_code
from fastapi.testclient import TestClient
from main import app


class TestObjectCode(unittest.TestCase):
    def execute(self, body, declarations='', expected='', exitcode=0):
        code = 'package main\nimport "fmt"\n' + declarations + '\nfunc main() {\n' + body + '\n}'
        result = generate_object_code(code)
        self.assertTrue(result['success'], result['errors'])
        if not shutil.which('gcc') or os.uname().machine != 'x86_64':
            self.skipTest('La ejecución nativa requiere GCC y Linux x86-64')
        with tempfile.TemporaryDirectory() as directory:
            asm = Path(directory) / 'programa.asm'
            obj = asm.with_suffix('.o')
            exe = Path(directory) / 'programa'
            asm.write_text(result['assembly'])
            subprocess.run(['gcc', '-x', 'assembler', '-c', str(asm), '-o', str(obj)], check=True, capture_output=True)
            subprocess.run(['gcc', str(obj), '-o', str(exe)], check=True, capture_output=True)
            run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=3)
            self.assertEqual(run.returncode, exitcode, run.stderr)
            self.assertEqual(run.stdout, expected)
        return result

    def test_arithmetic_and_negative_division(self):
        self.execute('a := -7\nb := 3\nfmt.Println(a / b, a % b, 4 * 3 + 2)', expected='-2 -1 14\n')

    def test_loop_functions_and_boolean(self):
        self.execute('s := 0\nfor i := 0; i < 5; i++ { s += doble(i) }\nfmt.Println(s, s == 20)',
                     'func doble(n int) int { return n * 2 }', expected='20 true\n')

    def test_recursion(self):
        self.execute('fmt.Println(fact(6))', 'func fact(n int) int { if n <= 1 { return 1 }\nreturn n * fact(n - 1) }', expected='720\n')

    def test_stack_arguments_and_spills(self):
        params = ', '.join(f'{c} int' for c in 'abcdefgh')
        declaration = f'func sum({params}) int {{ return a+b+c+d+e+f+g+h }}'
        result = self.execute('fmt.Println(sum(1,2,3,4,5,6,7,8))', declaration, expected='36\n')
        self.assertTrue(any('[rbp-' in r['location'] for r in result['register_assignments']))
        self.assertTrue(any(r['storage'] == 'register' for r in result['register_assignments']))

    def test_scopes_and_initialization(self):
        self.execute('var z int\nx := 9\nif true { x := 2\nfmt.Println(x) }\nfmt.Println(x,z)', expected='2\n9 0\n')

    def test_short_circuit(self):
        self.execute('zero := 0\nfmt.Println(false && 1/zero > 0, true || 1/zero > 0)', expected='false true\n')

    def test_globals_and_argument_order(self):
        self.execute('fmt.Println(g, change(), g)\nfmt.Println(add(g, change()))',
                     'var g int = 3\nfunc change() int { g += 1\nreturn g }\nfunc add(a int,b int) int { return a+b }', expected='3 4 4\n9\n')

    def test_binary_left_operand_survives_call(self):
        self.execute('fmt.Println(g + change())',
                     'var g int = 3\nfunc change() int { g = 9\nreturn g }', expected='12\n')

    def test_integer_wrap_and_minimum_division(self):
        self.execute('x := -9223372036854775808\ny := -1\nfmt.Println(x/y, x%y, 9223372036854775807+1)',
                     expected='-9223372036854775808 0 -9223372036854775808\n')

    def test_runtime_zero_divisor(self):
        self.execute('z := 0\nfmt.Println(3/z)', expected='Error: division por cero\n', exitcode=1)

    def test_if_else_and_while(self):
        self.execute('x := 0\nfor x < 3 { if x == 1 { fmt.Println(true) } else { fmt.Println(false) }\nx++ }', expected='false\ntrue\nfalse\n')

    def test_diagnostics(self):
        for code in ('package main\nfunc main() { var x int = true }',
                     'package main\nfunc main() { x := 1.5 }', 'var x int = 1'):
            r = generate_object_code(code)
            self.assertFalse(r['success'])
            self.assertFalse(r['assembly'])

    def test_api_exports(self):
        client = TestClient(app)
        payload = {'code': 'package main\nfunc main() { x := 1+2 }'}
        result = client.post('/object-code', json=payload)
        self.assertTrue(result.json()['success'])
        asm = client.post('/object-code/export', json=payload)
        self.assertEqual(asm.text, result.json()['assembly'])
        self.assertIn('programa.asm', asm.headers['content-disposition'])
        csv_res = client.post('/object-code/export-registers', json=payload)
        self.assertEqual(csv_res.status_code, 200)
        self.assertIn('location', csv_res.text)
        self.assertEqual(client.post('/object-code/export', json={'code': 'x = true'}).status_code, 400)
        self.assertEqual(client.post('/object-code', json={'code': ''}).status_code, 400)

    def test_ui_exposes_download(self):
        page = TestClient(app).get('/').text
        self.assertIn('Código objeto', page)
        self.assertIn('Descargar programa.asm', page)
        self.assertIn("fetch('/object-code'", page)
