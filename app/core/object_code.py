"""Native GNU assembler backend. Compilation never executes submitted code."""
from core.lexer import MyLexer
from core.parser import MyParser
from core.semantic import SemanticAnalyzer
from core.native_ir import NativeIR
from core.optimizer import Quad
from core.register_allocator import allocate, REGISTERS


def literal(s):
    return s in ('true', 'false') or (bool(s) and s.lstrip('-').isdigit())


def integer(s):
    return {'true': 1, 'false': 0}.get(s, int(s) if s.lstrip('-').isdigit() else 0)


def fold(op, a, b):
    x, y = integer(a), integer(b)
    if op in ('/', '%'):
        if not y:
            return None
        quotient = abs(x) // abs(y) * (-1 if (x < 0) != (y < 0) else 1)
        value = quotient if op == '/' else x - quotient * y
    elif op in ('+', '-', '*'):
        value = {'+': lambda: x + y, '-': lambda: x - y, '*': lambda: x * y}[op]()
    elif op in ('==', '!=', '<', '>', '<=', '>='):
        return str({'==': x == y, '!=': x != y, '<': x < y, '>': x > y, '<=': x <= y, '>=': x >= y}[op]).lower()
    else:
        return None
    return str((value + (1 << 63)) % (1 << 64) - (1 << 63))


def optimize(quads, globals_):
    """Conservative block-local propagation/folding; calls invalidate facts."""
    constants = {}
    result = []
    changes = []
    for i, original in enumerate(quads):
        q = original.clone()
        if q.op in ('label', 'call'):
            constants.clear()
        if q.op not in ('label', 'goto', 'call', 'newline'):
            q.arg1 = constants.get(q.arg1, q.arg1)
            if q.op != 'print':
                q.arg2 = constants.get(q.arg2, q.arg2)
        value = fold(q.op, q.arg1, q.arg2) if literal(q.arg1) and literal(q.arg2) else None
        if value is not None:
            q = Quad('=', value, result=q.result)
        if q.result and q.op not in ('label', 'goto', 'ifFalse', 'ifTrue', 'print'):
            constants.pop(q.result, None)
            if q.op == '=' and literal(q.arg1) and q.result not in globals_:
                constants[q.result] = q.arg1
        if q.to_tac() != original.to_tac():
            changes.append(dict(
                step=len(changes) + 1,
                block_id='',
                technique='Propagación / plegado de constantes',
                original_code=original.to_tac(),
                optimized_code=q.to_tac(),
                justification='Evaluación int64 y sustitución segura dentro del bloque.'
            ))
        result.append(q)
        if q.op in ('goto', 'ifFalse', 'ifTrue', 'return'):
            constants.clear()
    return result, changes


def normalize_calls(node):
    """Resolve call attachment in the permissive teaching grammar for U4."""
    if isinstance(node, list):
        return [normalize_calls(x) for x in node]
    if not isinstance(node, tuple):
        return node
    node = tuple(normalize_calls(x) for x in node)
    if node[0] == 'call' and node[1][0] in ('binop', 'relop', 'logop'):
        callee = node[1]
        return (callee[0], callee[1], callee[2], normalize_calls(('call', callee[3], node[2])))
    if node[0] == 'call' and node[1][0] == 'unary':
        callee = node[1]
        return ('unary', callee[1], normalize_calls(('call', callee[2], node[2])))
    return node


def generate_object_code(code: str) -> dict:
    try:
        lexer = MyLexer()
        tokens = list(lexer.tokenize(code))
        if lexer.errores_lexicos:
            raise ValueError(' | '.join(lexer.errores_lexicos))
        parser = MyParser()
        ast = normalize_calls(parser.parse(iter(tokens)))
        if parser.error_msg:
            raise ValueError(parser.error_msg)
        ok, errors, _ = SemanticAnalyzer().analyze(ast, parser._line_positions)
        if not ok:
            raise ValueError(' | '.join(errors))
        funcs = [n for n in ast[1] if n and n[0] == 'func']
        if any(n[1] == '__init' for n in funcs):
            raise ValueError('Nombre reservado por el backend: __init')
        main = next((n for n in funcs if n[1] == 'main'), None)
        if not main or main[2] or main[3] or ('package', 'main') not in ast[1]:
            raise ValueError('U4 requiere package main y func main() sin parámetros ni retorno.')
        if any(n[3] not in (None, 'int', 'bool') for n in funcs):
            raise ValueError('Retorno no soportado')
        gen = NativeIR({n[1]: n[3] for n in funcs})
        functions = gen.program(ast)
        return emit_program(gen, functions)
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        return dict(
            success=False,
            errors=[str(exc)],
            assembly='',
            register_assignments=[],
            optimized_quadruples=[],
            transformations=[]
        )


def emit_program(gen, functions):
    globals_ = {n for n, s in gen.symbols.items() if s['function'] == '__init' and n.startswith('v')}
    text = [
        '.intel_syntax noprefix',
        '.section .rodata',
        '.Lfmt: .asciz "%ld"',
        '.Lstr: .asciz "%s"',
        '.Ltrue: .asciz "true"',
        '.Lfalse: .asciz "false"',
        '.Ldivision: .asciz "Error: division por cero"',
        '.bss'
    ]
    for n in sorted(globals_):
        text += ['.align 8', f'.G{n}: .zero 8']
    text += ['.text', '.globl main']
    assignments = []
    before = []
    after = []
    transformations = []
    mapping = []
    edges = []
    for name, params, original in functions:
        quads, changes = optimize(original, globals_)
        transformations.extend(dict(t, function=name) for t in changes)
        symbols = {n: s for n, s in gen.symbols.items() if n not in globals_}
        locations, spills, interference = allocate(quads, params, symbols, name)
        edges.extend(dict(function=name, nodes=list(e)) for e in interference)
        used_regs = [r for r in REGISTERS if r in locations.values()]
        # Fixed save area reserves 40 bytes; frame remains aligned at calls.
        frame = ((40 + 8 * spills + 15) // 16) * 16
        label = 'main' if name == 'main' else 'go_' + name
        end = '.Lend_' + name
        text += [f'{label}:', 'push rbp', 'mov rbp, rsp', f'sub rsp, {frame}']
        for i, r in enumerate(REGISTERS):
            if r in used_regs:
                text.append(f'mov QWORD PTR [rbp-{8 * (i + 1)}], {r}')

        def operand(x):
            if literal(x):
                return str(integer(x))
            if x in globals_:
                return f'QWORD PTR [rip+.G{x}]'
            return locations[x]

        def load(reg, x):
            text.append(f'mov {reg}, {operand(x)}')

        def store(x, reg='rax'):
            text.append(f'mov {operand(x)}, {reg}')

        argregs = ('rdi', 'rsi', 'rdx', 'rcx', 'r8', 'r9')
        for i, p in enumerate(params):
            source = argregs[i] if i < 6 else f'QWORD PTR [rbp+{16 + 8 * (i - 6)}]'
            text.append(f'mov rax, {source}')
            store(p)
        if name == 'main':
            text.append('call go___init')
        pending = []
        for index, q in enumerate(quads):
            start = len(text) + 1
            text.append('# ' + q.to_tac())
            op = q.op
            if op == 'label':
                text.append(f'.L{name}_{q.result}:')
            elif op == 'goto':
                text.append(f'jmp .L{name}_{q.result}')
            elif op in ('ifTrue', 'ifFalse'):
                load('rax', q.arg1)
                text += ['test rax, rax', f'{"jz" if op == "ifFalse" else "jnz"} .L{name}_{q.result}']
            elif op == 'return':
                if q.arg1:
                    load('rax', q.arg1)
                text.append(f'jmp {end}')
            elif op == 'param':
                pending.append(q.arg1)
            elif op == 'call':
                count = int(q.arg2)
                args = pending[-count:] if count else []
                if count:
                    del pending[-count:]
                padding = 8 if max(0, count - 6) % 2 else 0
                if padding:
                    text.append('sub rsp, 8')
                for a in reversed(args[6:]):
                    load('rax', a)
                    text.append('push rax')
                for r, a in zip(argregs, args):
                    load(r, a)
                text.append('call go_' + q.arg1)
                cleanup = padding + 8 * max(0, count - 6)
                if cleanup:
                    text.append(f'add rsp, {cleanup}')
                store(q.result)
            elif op == 'print':
                if q.result:
                    text += ['mov edi, 32', 'call putchar@PLT']
                load('rsi', q.arg1)
                if q.arg2 == 'bool':
                    text += ['test rsi, rsi', 'lea rsi, [rip+.Lfalse]', 'lea rax, [rip+.Ltrue]', 'cmovne rsi, rax', 'lea rdi, [rip+.Lstr]']
                else:
                    text.append('lea rdi, [rip+.Lfmt]')
                text += ['xor eax, eax', 'call printf@PLT']
            elif op == 'newline':
                text += ['mov edi, 10', 'call putchar@PLT']
            else:
                load('rax', q.arg1)
                if q.arg2:
                    load('rcx', q.arg2)
                    if op in ('+', '-', '*'):
                        text.append({'+': 'add', '-': 'sub', '*': 'imul'}[op] + ' rax, rcx')
                    elif op in ('/', '%'):
                        special = f'.Ldiv_{name}_{index}'
                        done = special + '_done'
                        text += ['test rcx, rcx', 'jz .Lzero', 'mov rdx, -9223372036854775808', 'cmp rax, rdx', f'jne {special}', 'cmp rcx, -1', f'jne {special}']
                        if op == '%':
                            text.append('xor eax, eax')
                        text += [f'jmp {done}', special + ':', 'cqo', 'idiv rcx']
                        if op == '%':
                            text.append('mov rax, rdx')
                        text.append(done + ':')
                    else:
                        cc = {'<': 'l', '>': 'g', '<=': 'le', '>=': 'ge', '==': 'e', '!=': 'ne'}[op]
                        text += ['cmp rax, rcx', f'set{cc} al', 'movzx rax, al']
                elif op == '-':
                    text.append('neg rax')
                elif op == '!':
                    text += ['test rax, rax', 'sete al', 'movzx rax, al']
                elif op not in ('=', '+'):
                    raise ValueError(f'Operación no soportada: {op}')
                store(q.result)
            mapping.append(dict(function=name, quadruple=index + 1, asm_line=start))
        text += ['xor eax, eax', end + ':']
        for i, r in enumerate(REGISTERS):
            if r in used_regs:
                text.append(f'mov {r}, QWORD PTR [rbp-{8 * (i + 1)}]')
        text += ['leave', 'ret']
        for key, s in gen.symbols.items():
            if s['function'] == name:
                loc = operand(key) if key in locations or key in globals_ else 'Eliminado'
                assignments.append(dict(s, location=loc, register_name=loc if loc in REGISTERS else '', storage='register' if loc in REGISTERS else 'memory'))
        for target, qs in ((before, original), (after, quads)):
            target.extend(dict(function=name, index=i + 1, op=q.op, arg1=q.arg1, arg2=q.arg2, result=q.result, formatted=q.to_triple(i + 1)) for i, q in enumerate(qs))
    text += ['.Lzero:', 'lea rdi, [rip+.Ldivision]', 'call puts@PLT', 'mov edi, 1', 'call exit@PLT', 'ud2', '.section .note.GNU-stack,"",@progbits']
    return dict(
        success=True,
        errors=[],
        assembly='\n'.join(text) + '\n',
        target='x86-64 Linux / GNU assembler (Intel)',
        original_quadruples=before,
        optimized_quadruples=after,
        register_assignments=assignments,
        transformations=transformations,
        instruction_mapping=mapping,
        interference_edges=edges
    )
