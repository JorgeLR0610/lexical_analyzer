"""Reproduce U4 evidence. Run with .venv/bin/python ejemplos/u4/verificar.py."""
import csv
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'app'))
from core.object_code import generate_object_code


def main():
    directory = Path(__file__).resolve().parent
    if not shutil.which('gcc'):
        raise SystemExit('Instala GCC y binutils para ejecutar esta evidencia.')
    result = generate_object_code((directory / 'integrador.go').read_text())
    if not result['success']:
        raise SystemExit('\n'.join(result['errors']))
    asm = directory / 'programa.asm'
    asm.write_text(result['assembly'])
    for key, filename in [('original_quadruples', 'antes.ir'), ('optimized_quadruples', 'optimizado.ir')]:
        (directory / filename).write_text('\n'.join(f"{q['function']}: {q['formatted']}" for q in result[key]) + '\n')
    with (directory / 'registros.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['symbol', 'function', 'scope', 'data_type', 'location'], extrasaction='ignore')
        writer.writeheader()
        writer.writerows(result['register_assignments'])
    with tempfile.TemporaryDirectory(prefix='lya-u4-') as temporary:
        obj = Path(temporary) / 'programa.o'
        executable = Path(temporary) / 'programa'
        subprocess.run(['gcc', '-x', 'assembler', '-c', str(asm), '-o', str(obj)], check=True)
        subprocess.run(['gcc', str(obj), '-o', str(executable)], check=True)
        run = subprocess.run([str(executable)], capture_output=True, text=True, timeout=5, check=True)
    expected = (directory / 'esperado.txt').read_text()
    if run.stdout != expected:
        raise SystemExit(f'Salida incorrecta: {run.stdout!r}; esperada: {expected!r}')
    evidence = 'GCC: ensamblado y enlace correctos\nSalida de ejecución:\n' + run.stdout + 'Código de salida: 0\nResultado: coincide con esperado.txt\n'
    (directory / 'ejecucion.txt').write_text(evidence)
    print(evidence)


if __name__ == '__main__':
    main()
