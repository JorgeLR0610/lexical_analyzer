from core.ir_generator import IRGenerator
from core.optimizer import Quad


class NativeIR(IRGenerator):
    def __init__(self, signatures):
        super().__init__()
        self.scopes = [{}]
        self.symbols = {}
        self.signatures = signatures
        self.function = '__init'
        self.functions = []

    def bind(self, name, typ):
        key = f'v{len(self.symbols)}'
        self.scopes[-1][name] = key
        self.symbols[key] = dict(symbol=name, identity=key, data_type=typ,
                                 function=self.function, scope=len(self.scopes)-1)
        return key

    def lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        raise ValueError(f'Identificador no resuelto: {name}')

    def new_temp(self):
        self.temp_count += 1
        key = f't{self.temp_count}'
        self.symbols[key] = dict(symbol=key, identity=key, data_type='int', function=self.function, scope=len(self.scopes)-1)
        return key

    def _gen_block(self, node):
        self.scopes.append({})
        try:
            super()._gen_block(node)
        finally:
            self.scopes.pop()

    def _gen_statement(self, node):
        if not node:
            return
        tag = node[0]
        if tag in ('var_init', 'var_typed', 'var_inferred', 'short_var', 'const_typed', 'const_inferred'):
            typed = tag in ('var_init', 'var_typed', 'const_typed')
            expr = None if tag == 'var_typed' else node[3 if typed else 2]
            typ = str(node[2]) if typed else self.expr_type(expr)
            if typ not in ('int', 'bool'):
                raise ValueError(f'Tipo no soportado en U4: {typ}')
            value = self._gen_expr(expr) if expr else '0'
            key = self.bind(node[1], typ)
            self.emit('=', value, result=key)
            return
        if tag.startswith('if_with_init') or tag.startswith('for_'):
            self.scopes.append({})
            try:
                super()._gen_statement(node)
            finally:
                self.scopes.pop()
            return
        if tag in ('assign', 'inc', 'dec'):
            at = 2 if tag == 'assign' else 1
            lhs = node[at]
            if lhs[0] != 'lit':
                raise ValueError('Asignación no escalar no soportada')
            values = list(node)
            values[at] = ('lit', self.lookup(lhs[1]))
            super()._gen_statement(tuple(values))
            return
        if tag not in ('call_stmt', 'if', 'if_else', 'if_else_if', 'return', 'block'):
            raise ValueError(f'Construcción no soportada: {tag}')
        super()._gen_statement(node)

    def snapshot(self, expr):
        value = self._gen_expr(expr)
        temp = self.new_temp()
        self.symbols[temp]['data_type'] = self.expr_type(expr)
        self.emit('=', value, result=temp)
        return temp

    def expr_type(self, expr):
        if expr[0] in ('relop', 'logop') or (expr[0] == 'unary' and expr[1] in ('NOT', '!')):
            return 'bool'
        if expr[0] == 'lit':
            val = str(expr[1])
            if val in ('true', 'false'):
                return 'bool'
            if val.lstrip('-').isdigit():
                return 'int'
            if val.startswith(('"', '`')) or val == 'nil' or '.' in val:
                return 'unsupported'
            return self.symbols[self.lookup(val)]['data_type']
        if expr[0] == 'call':
            callee = expr[1]
            return self.signatures.get(callee[1], 'int') if callee[0] == 'lit' else 'int'
        return self.expr_type(expr[2])

    def _gen_expr(self, expr):
        tag = expr[0]
        if tag == 'unary' and expr[1] == '-' and expr[2] == ('lit', str(1 << 63)):
            return str(-(1 << 63))
        if tag == 'lit':
            val = str(expr[1])
            if val in ('true', 'false') or val.lstrip('-').isdigit():
                if val.lstrip('-').isdigit() and not -(1 << 63) <= int(val) < (1 << 63):
                    raise ValueError('Literal fuera del rango int64')
                return val
            return self.lookup(val)
        if tag == 'call':
            callee = expr[1]
            name = callee[1] if callee[0] == 'lit' else f'{callee[1][1]}.{callee[2]}'
            if name == 'fmt.Println':
                args = expr[2] or []
                vals = [(self.snapshot(a), self.expr_type(a)) for a in args]
                for i, (val, typ) in enumerate(vals):
                    if typ not in ('int', 'bool'):
                        raise ValueError('Println admite int y bool')
                    self.emit('print', val, typ, 'space' if i else '')
                self.emit('newline')
                return '0'
            if name not in self.signatures:
                raise ValueError(f'Llamada no soportada: {name}')
            vals = [self.snapshot(a) for a in (expr[2] or [])]
            for val in vals:
                self.emit('param', val)
            t = self.new_temp()
            self.symbols[t]['data_type'] = self.signatures[name] or 'int'
            self.emit('call', name, str(len(vals)), t)
            return t
        if tag == 'logop':
            op = self.OP_MAP.get(expr[1], expr[1])
            t = self.new_temp()
            end = self.new_label()
            self.symbols[t]['data_type'] = 'bool'
            self.emit('=', self._gen_expr(expr[2]), result=t)
            self.emit('ifFalse' if op == '&&' else 'ifTrue', t, result=end)
            self.emit('=', self._gen_expr(expr[3]), result=t)
            self.emit('label', result=end)
            return t
        if tag not in ('binop', 'relop', 'unary'):
            raise ValueError(f'Expresión no soportada: {tag}')
        typ = self.expr_type(expr)
        if typ not in ('int', 'bool'):
            raise ValueError(f'Tipo no soportado: {typ}')
        if tag in ('binop', 'relop'):
            left = self.snapshot(expr[2])
            right = self._gen_expr(expr[3])
            t = self.new_temp()
            self.emit(self.OP_MAP.get(expr[1], expr[1]), left, right, t)
        else:
            t = super()._gen_expr(expr)
        self.symbols[t]['data_type'] = typ
        return t

    def program(self, ast):
        items = ast[1]
        for item in items:
            if item is None:
                continue
            if item[0] not in ('func', 'package', 'import_single', 'import_multi'):
                self._gen_statement(item)
        self.functions.append(('__init', [], self.take()))
        for item in items:
            if item[0] != 'func':
                continue
            self.function = item[1]
            self.scopes.append({})
            params = []
            for name, typ in (item[2] or []):
                if str(typ) not in ('int', 'bool'):
                    raise ValueError('Parámetro no soportado')
                params.append(self.bind(name, str(typ)))
            self._gen_block(item[4])
            self.scopes.pop()
            self.functions.append((item[1], params, self.take()))
        return self.functions

    def take(self):
        quads = [Quad(q.op, q.arg1, q.arg2, q.result) for q in self.quadruples]
        self.quadruples = []
        return quads
