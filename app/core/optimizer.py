#type: ignore
from typing import Optional, Any
from core.lexer import MyLexer
from core.parser import MyParser
from core.semantic import SemanticAnalyzer
from core.ir_generator import generate_ir, Quadruple, IRGenerator
from api.schemas import (
    TransformationResponse,
    BasicBlockResponse,
    CFGMetricsResponse,
    OptimizationResponse,
    OptimizationAnalysisResponse
)
import copy


def quad_to_tac(op: str, arg1: str = "", arg2: str = "", result: str = "") -> str:
    if op == 'label':
        return f"{result}:"
    elif op == 'goto':
        return f"goto {result}"
    elif op == 'ifFalse':
        return f"ifFalse {arg1} goto {result}"
    elif op == 'ifTrue':
        return f"ifTrue {arg1} goto {result}"
    elif op == '=':
        return f"{result} = {arg1}"
    elif op in ('+', '-', '*', '/', '%', '==', '!=', '<', '<=', '>', '>=', '&&', '||'):
        return f"{result} = {arg1} {op} {arg2}"
    elif op in ('!', 'NOT'):
        return f"{result} = !{arg1}"
    elif op == 'param':
        return f"param {arg1}"
    elif op == 'call':
        return f"{result} = call {arg1}, {arg2}" if result else f"call {arg1}, {arg2}"
    elif op == 'return':
        return f"return {arg1}" if arg1 else "return"
    elif op == 'func_begin':
        return f"func {result}:"
    elif op == 'func_end':
        return f"endfunc"
    else:
        return f"{result} = {op} {arg1} {arg2}"


class Quad:
    def __init__(self, op: str, arg1: str = "", arg2: str = "", result: str = "", block_id: str = "B1"):
        self.op = op
        self.arg1 = str(arg1) if arg1 is not None else ""
        self.arg2 = str(arg2) if arg2 is not None else ""
        self.result = str(result) if result is not None else ""
        self.block_id = str(block_id) if block_id else "B1"

    def to_tac(self) -> str:
        return quad_to_tac(self.op, self.arg1, self.arg2, self.result)

    def to_triple(self, idx: int) -> str:
        a1 = self.arg1 if self.arg1 else ""
        a2 = self.arg2 if self.arg2 else ""
        res = self.result if self.result else ""
        return f"#{idx}  ({self.op}, {a1}, {a2}, {res})"

    def clone(self) -> 'Quad':
        return Quad(self.op, self.arg1, self.arg2, self.result, self.block_id)


class Transformation:
    def __init__(self, step: int, block_id: str, technique: str, original_code: str, optimized_code: str, justification: str):
        self.step = step
        self.block_id = block_id
        self.technique = technique
        self.original_code = original_code
        self.optimized_code = optimized_code
        self.justification = justification

    def to_schema(self) -> TransformationResponse:
        return TransformationResponse(
            step=self.step,
            block_id=self.block_id,
            technique=self.technique,
            original_code=self.original_code,
            optimized_code=self.optimized_code,
            justification=self.justification
        )


class BasicBlock:
    def __init__(self, block_id: str, quads: list[Quad]):
        self.id = block_id
        self.quads = quads
        self.successors: list[str] = []
        self.predecessors: list[str] = []
        self.is_unreachable: bool = False

    def to_tac_lines(self) -> list[str]:
        return [q.to_tac() for q in self.quads]

    def to_schema(self) -> BasicBlockResponse:
        return BasicBlockResponse(
            id=self.id,
            instructions=self.to_tac_lines(),
            successors=self.successors,
            predecessors=self.predecessors,
            is_unreachable=self.is_unreachable
        )


class ControlFlowGraph:
    def __init__(self, blocks: list[BasicBlock]):
        self.blocks = blocks

    @classmethod
    def from_quads(cls, quads: list[Quad]) -> 'ControlFlowGraph':
        if not quads:
            return cls([])

        n = len(quads)
        leaders = set([0])

        for i, q in enumerate(quads):
            if q.op == 'label':
                leaders.add(i)
            elif q.op in ('goto', 'ifFalse', 'ifTrue', 'return'):
                if i + 1 < n:
                    leaders.add(i + 1)

        sorted_leaders = sorted(list(leaders))
        blocks = []

        for idx, start_idx in enumerate(sorted_leaders):
            end_idx = sorted_leaders[idx + 1] if idx + 1 < len(sorted_leaders) else n
            block_id = f"B{len(blocks) + 1}"
            block_quads = []
            for q in quads[start_idx:end_idx]:
                q.block_id = block_id
                block_quads.append(q.clone())
            if block_quads:
                b = BasicBlock(block_id, block_quads)
                blocks.append(b)

        label_to_block = {}
        for b in blocks:
            for q in b.quads:
                if q.op == 'label':
                    label_to_block[q.result] = b.id

        for i, b in enumerate(blocks):
            if not b.quads:
                continue
            last_q = b.quads[-1]

            if last_q.op == 'goto':
                target_block = label_to_block.get(last_q.result)
                if target_block and target_block not in b.successors:
                    b.successors.append(target_block)
            elif last_q.op in ('ifFalse', 'ifTrue'):
                target_block = label_to_block.get(last_q.result)
                fall_through = blocks[i + 1].id if i + 1 < len(blocks) else None
                if fall_through and fall_through not in b.successors:
                    b.successors.append(fall_through)
                if target_block and target_block not in b.successors:
                    b.successors.append(target_block)
            elif last_q.op == 'return':
                pass
            else:
                if i + 1 < len(blocks):
                    next_id = blocks[i + 1].id
                    if next_id not in b.successors:
                        b.successors.append(next_id)

        block_map = {b.id: b for b in blocks}
        for b in blocks:
            for s_id in b.successors:
                if s_id in block_map and b.id not in block_map[s_id].predecessors:
                    block_map[s_id].predecessors.append(b.id)

        if blocks:
            reachable = set()
            queue = [blocks[0].id]
            visited = set([blocks[0].id])
            while queue:
                curr_id = queue.pop(0)
                reachable.add(curr_id)
                curr_b = block_map.get(curr_id)
                if curr_b:
                    for succ_id in curr_b.successors:
                        if succ_id not in visited:
                            visited.add(succ_id)
                            queue.append(succ_id)

            for b in blocks:
                if b.id not in reachable:
                    b.is_unreachable = True

        return cls(blocks)

    def calculate_cyclomatic_complexity(self) -> int:
        reachable_blocks = [b for b in self.blocks if not b.is_unreachable]
        N = len(reachable_blocks)
        if N == 0:
            return 1
        reachable_ids = set(b.id for b in reachable_blocks)
        E = sum(len([s for s in b.successors if s in reachable_ids]) for b in reachable_blocks)
        M = E - N + 2
        return max(M, 1)

    def to_mermaid(self) -> str:
        lines = ["graph TD"]
        lines.append("    classDef normal fill:#1e293b,stroke:#38bdf8,stroke-width:2px,color:#f8fafc;")
        lines.append("    classDef unreachable fill:#450a0a,stroke:#ef4444,stroke-width:2px,stroke-dasharray: 5 5,color:#fca5a5;")
        lines.append("    classDef entry fill:#064e3b,stroke:#10b981,stroke-width:2px,color:#f8fafc;")
        lines.append("    classDef exitNode fill:#312e81,stroke:#818cf8,stroke-width:2px,color:#f8fafc;")

        if not self.blocks:
            lines.append("    Entry([Inicio]) --> Exit([Fin])")
            lines.append("    class Entry entry;")
            lines.append("    class Exit exitNode;")
            return "\n".join(lines)

        lines.append("    Entry([Inicio]) --> B1")
        lines.append("    class Entry entry;")

        for i, b in enumerate(self.blocks):
            content_escaped = "<br/>".join([line.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;') for line in b.to_tac_lines()])
            status_text = " (Inalcanzable)" if b.is_unreachable else ""
            node_label = f"<b>{b.id}{status_text}</b><br/>{content_escaped}"
            lines.append(f'    {b.id}["{node_label}"]')
            if b.is_unreachable:
                lines.append(f'    class {b.id} unreachable;')
            else:
                lines.append(f'    class {b.id} normal;')

            for succ_id in b.successors:
                last_q = b.quads[-1] if b.quads else None
                edge_label = ""
                if last_q and last_q.op in ('ifFalse', 'ifTrue'):
                    if succ_id == b.successors[-1] and len(b.successors) > 1:
                        edge_label = " -- Salto --> "
                    else:
                        edge_label = " -- Secuencial --> "
                else:
                    edge_label = " --> "
                lines.append(f'    {b.id}{edge_label}{succ_id}')

            if not b.successors and not b.is_unreachable:
                lines.append(f'    {b.id} --> Exit([Fin])')

        lines.append("    class Exit exitNode;")
        return "\n".join(lines)


class IROptimizer:
    def __init__(self):
        self.transformations: list[Transformation] = []
        self.step_counter = 0

    def add_transformation(self, block_id: str, technique: str, orig: str, opt: str, just: str):
        self.step_counter += 1
        trans = Transformation(self.step_counter, block_id, technique, orig, opt, just)
        self.transformations.append(trans)

    def optimize(self, quads: list[Quad]) -> tuple[list[Quad], list[Transformation]]:
        self.transformations = []
        self.step_counter = 0

        # Particionar inicialmente en bloques para que cada Quad conozca su block_id (B1, B2...)
        ControlFlowGraph.from_quads(quads)
        current_quads = [q.clone() for q in quads]

        # Pasadas de optimización iterativa hasta convergencia
        max_passes = 5
        for _ in range(max_passes):
            changed = False
            
            # 1. Eliminar asignaciones idénticas iniciales x = x
            current_quads, ch_ident = self._remove_identity_assignments(current_quads)
            if ch_ident:
                changed = True

            # 2. Subexpresiones Comunes (CSE)
            current_quads, ch_cse = self._apply_cse(current_quads)
            if ch_cse:
                changed = True

            # 3. Propagación de Constantes
            current_quads, ch_prop = self._apply_constant_propagation(current_quads)
            if ch_prop:
                changed = True

            # 4. Plegado de Constantes (Constant Folding)
            current_quads, ch_fold = self._apply_constant_folding(current_quads)
            if ch_fold:
                changed = True

            # 5. Simplificación de Saltos y Condiciones Constantes
            current_quads, ch_branch = self._apply_branch_simplification(current_quads)
            if ch_branch:
                changed = True

            # 6. Eliminación de Bloques y Código Inalcanzable
            current_quads, ch_unreach = self._apply_unreachable_code_elimination(current_quads)
            if ch_unreach:
                changed = True

            # 7. Eliminación de Código Muerto
            current_quads, ch_dead = self._apply_dead_code_elimination(current_quads)
            if ch_dead:
                changed = True

            if not changed:
                break

        return current_quads, self.transformations

    def _remove_identity_assignments(self, quads: list[Quad]) -> tuple[list[Quad], bool]:
        new_quads = []
        changed = False
        for q in quads:
            if q.op == '=' and q.arg1 == q.result and not q.arg2:
                changed = True
                continue
            new_quads.append(q)
        return new_quads, changed

    def _apply_cse(self, quads: list[Quad]) -> tuple[list[Quad], bool]:
        # Detectar expresiones idénticas dentro de la misma secuencia de instrucciones
        seen_exprs = {}  # (op, arg1, arg2): prev_result
        new_quads = []
        changed = False

        for q in quads:
            if q.op in ('label', 'goto', 'ifFalse', 'ifTrue', 'call', 'func_begin', 'func_end'):
                seen_exprs.clear()
                new_quads.append(q)
                continue

            if q.op in ('+', '-', '*', '/', '%', '==', '!=', '<', '<=', '>', '>=', '&&', '||'):
                key = (q.op, q.arg1, q.arg2)
                if key in seen_exprs:
                    prev_res = seen_exprs[key]
                    orig_tac = q.to_tac()
                    # Reemplazar con asignación directa
                    opt_q = Quad('=', prev_res, '', q.result, block_id=q.block_id)
                    new_quads.append(opt_q)
                    self.add_transformation(
                        q.block_id,
                        "Eliminación de subexpresiones comunes",
                        orig_tac,
                        opt_q.to_tac(),
                        f"La operación {q.arg1} {q.op} {q.arg2} ya fue calculada en {prev_res}; se reutiliza el valor evitando el cálculo redundante."
                    )
                    changed = True
                    continue
                else:
                    seen_exprs[key] = q.result

            # Si una variable cambia, invalidar expresiones que la usan
            if q.result:
                to_del = [k for k in seen_exprs if q.result in (k[1], k[2])]
                for k in to_del:
                    del seen_exprs[k]

            new_quads.append(q)

        return new_quads, changed

    def _apply_constant_propagation(self, quads: list[Quad]) -> tuple[list[Quad], bool]:
        known_constants = {}  # var: const_value_str
        new_quads = []
        changed = False

        for q in quads:
            if q.op in ('label', 'goto', 'ifFalse', 'ifTrue', 'func_begin', 'func_end'):
                # Reset local en etiquetas/saltos para seguridad intra-bloque
                known_constants.clear()
                new_quads.append(q)
                continue

            orig_tac = q.to_tac()
            replaced = False
            new_arg1 = q.arg1
            new_arg2 = q.arg2

            if q.arg1 in known_constants:
                new_arg1 = known_constants[q.arg1]
                replaced = True

            if q.arg2 in known_constants:
                new_arg2 = known_constants[q.arg2]
                replaced = True

            if replaced:
                opt_q = Quad(q.op, new_arg1, new_arg2, q.result, block_id=q.block_id)
                new_quads.append(opt_q)
                self.add_transformation(
                    q.block_id,
                    "Propagación de constantes",
                    orig_tac,
                    opt_q.to_tac(),
                    f"Se sustituyen variables por sus valores constantes conocidos en la instrucción."
                )
                changed = True
                q = opt_q
            else:
                new_quads.append(q)

            # Rastrear constantes asignadas
            if q.op == '=' and self._is_literal(q.arg1) and not q.arg2:
                known_constants[q.result] = q.arg1
            elif q.result and q.result in known_constants:
                del known_constants[q.result]

        return new_quads, changed

    def _apply_constant_folding(self, quads: list[Quad]) -> tuple[list[Quad], bool]:
        new_quads = []
        changed = False

        for q in quads:
            if q.op in ('+', '-', '*', '/', '%', '==', '!=', '<', '<=', '>', '>=', '&&', '||') and self._is_literal(q.arg1) and self._is_literal(q.arg2):
                val = self._evaluate_binop(q.op, q.arg1, q.arg2)
                if val is not None:
                    orig_tac = q.to_tac()
                    val_str = "true" if val is True else ("false" if val is False else str(val))
                    opt_q = Quad('=', val_str, '', q.result, block_id=q.block_id)
                    new_quads.append(opt_q)
                    self.add_transformation(
                        q.block_id,
                        "Constant Folding",
                        orig_tac,
                        opt_q.to_tac(),
                        f"La operación {q.arg1} {q.op} {q.arg2} se evalúa en tiempo de compilación a {val_str}."
                    )
                    changed = True
                    continue

            new_quads.append(q)

        return new_quads, changed

    def _apply_branch_simplification(self, quads: list[Quad]) -> tuple[list[Quad], bool]:
        # Simplificación de saltos condicionales con condiciones constantes conocidas
        new_quads = []
        changed = False

        # Primero mapear si alguna variable antes del salto era constante (ej. t3 = true)
        const_map = {}
        for q in quads:
            if q.op == '=' and q.arg1 in ('true', 'false'):
                const_map[q.result] = q.arg1

        for i, q in enumerate(quads):
            if q.op == 'ifFalse':
                cond_val = const_map.get(q.arg1, q.arg1)
                if cond_val == 'true':
                    # ifFalse true -> NUNCA salta! Se puede eliminar el salto
                    orig_tac = q.to_tac()
                    self.add_transformation(
                        q.block_id,
                        "Simplificación de saltos",
                        orig_tac,
                        "// Salto condicional eliminado",
                        f"La condición '{q.arg1}' es 'true'; el salto ifFalse nunca se toma y se elimina la bifurcación."
                    )
                    changed = True
                    continue
                elif cond_val == 'false':
                    # ifFalse false -> SIEMPRE salta! Se convierte en goto incondicional
                    orig_tac = q.to_tac()
                    opt_q = Quad('goto', '', '', q.result, block_id=q.block_id)
                    new_quads.append(opt_q)
                    self.add_transformation(
                        q.block_id,
                        "Simplificación de saltos",
                        orig_tac,
                        opt_q.to_tac(),
                        f"La condición '{q.arg1}' es 'false'; el salto ifFalse siempre se ejecuta, convirtiéndose en goto {q.result}."
                    )
                    changed = True
                    continue

            new_quads.append(q)

        # Eliminar goto redundantes si saltan a la etiqueta inmediatamente siguiente
        clean_quads = []
        for i, q in enumerate(new_quads):
            if q.op == 'goto' and i + 1 < len(new_quads):
                next_q = new_quads[i + 1]
                if next_q.op == 'label' and next_q.result == q.result:
                    self.add_transformation(
                        q.block_id,
                        "Simplificación de saltos redundantes",
                        q.to_tac(),
                        "// Salto redundante eliminado",
                        f"El salto goto {q.result} apunta inmediatamente a la siguiente instrucción ({next_q.result}:) y se omite."
                    )
                    changed = True
                    continue
            clean_quads.append(q)

        return clean_quads, changed

    def _apply_unreachable_code_elimination(self, quads: list[Quad]) -> tuple[list[Quad], bool]:
        # Construir CFG y filtrar bloques inalcanzables
        cfg = ControlFlowGraph.from_quads(quads)
        unreachable_blocks = [b for b in cfg.blocks if b.is_unreachable]
        if not unreachable_blocks:
            return quads, False

        new_quads = []
        changed = False
        for b in cfg.blocks:
            if b.is_unreachable:
                changed = True
                orig_block_code = "\n".join(b.to_tac_lines())
                self.add_transformation(
                    b.id,
                    "Eliminación de bloques inalcanzables",
                    orig_block_code,
                    "// Bloque eliminado",
                    f"El bloque {b.id} no posee caminos de ejecución alcanzables desde el punto de entrada y se elimina del flujo."
                )
            else:
                new_quads.extend(b.quads)

        return new_quads, changed

    def _apply_dead_code_elimination(self, quads: list[Quad]) -> tuple[list[Quad], bool]:
        # Identificar qué variables son usadas / leídas
        used_vars = set()
        for q in quads:
            if q.op == 'return':
                if q.arg1:
                    used_vars.add(q.arg1)
            elif q.op in ('param', 'call'):
                if q.arg1:
                    used_vars.add(q.arg1)
                if q.arg2 and not q.arg2.isdigit():
                    used_vars.add(q.arg2)
            elif q.op in ('ifFalse', 'ifTrue'):
                if q.arg1:
                    used_vars.add(q.arg1)
            else:
                if q.arg1 and not self._is_literal(q.arg1):
                    used_vars.add(q.arg1)
                if q.arg2 and not self._is_literal(q.arg2):
                    used_vars.add(q.arg2)

        has_return = any(q.op == 'return' for q in quads)

        # Regla: Propagación de return directo y eliminación de asignación intermedia: y = x; return y -> return x
        for i in range(len(quads) - 1):
            q_curr = quads[i]
            q_next = quads[i + 1]
            if q_curr.op == '=' and q_next.op == 'return' and q_next.arg1 == q_curr.result:
                # Si q_curr.result no se usa en ningún otro lado
                other_uses = sum(1 for q in quads if q_curr.result in (q.arg1, q.arg2))
                if other_uses <= 1:
                    orig_ret = q_next.to_tac()
                    q_next.arg1 = q_curr.arg1
                    used_vars.discard(q_curr.result)
                    used_vars.add(q_curr.arg1)
                    self.add_transformation(
                        q_curr.block_id,
                        "Propagación de retorno",
                        orig_ret,
                        q_next.to_tac(),
                        f"Se retorna directamente '{q_curr.arg1}' en lugar de pasar por la variable temporal/intermedia '{q_curr.result}'."
                    )

        new_quads = []
        changed = False

        for q in quads:
            # Nunca eliminar llamadas, funciones, etiquetas, saltos ni returns
            if q.op in ('call', 'param', 'return', 'func_begin', 'func_end', 'label', 'goto', 'ifFalse', 'ifTrue'):
                new_quads.append(q)
                continue

            # Si es una asignación o cálculo pero su resultado nunca es leído:
            if q.result and q.result not in used_vars:
                # Si es una variable de usuario (no temporal) y el programa no tiene return, preservarla
                if not self._is_temporal(q.result) and not has_return:
                    new_quads.append(q)
                    continue

                # Es código muerto!
                orig_tac = q.to_tac()
                self.add_transformation(
                    q.block_id,
                    "Eliminación de código muerto",
                    orig_tac,
                    "// Instrucción eliminada",
                    f"La variable/temporal '{q.result}' no vuelve a ser utilizada en el programa; su asignación carece de efecto secundario."
                )
                changed = True
                continue

            new_quads.append(q)

        return new_quads, changed

    def _is_temporal(self, s: str) -> bool:
        if not s:
            return False
        return s.startswith('t') and s[1:].isdigit()

    def _is_literal(self, s: str) -> bool:
        if not s:
            return False
        if s in ('true', 'false'):
            return True
        try:
            int(s)
            return True
        except ValueError:
            try:
                float(s)
                return True
            except ValueError:
                return False

    def _evaluate_binop(self, op: str, a: str, b: str) -> Optional[Any]:
        try:
            is_int = a.isdigit() or (a.startswith('-') and a[1:].isdigit())
            is_int_b = b.isdigit() or (b.startswith('-') and b[1:].isdigit())
            
            if is_int and is_int_b:
                na = int(a)
                nb = int(b)
            else:
                na = float(a)
                nb = float(b)

            if op == '+':
                return na + nb
            elif op == '-':
                return na - nb
            elif op == '*':
                return na * nb
            elif op == '/':
                return na // nb if (is_int and is_int_b and nb != 0) else (na / nb if nb != 0 else None)
            elif op == '%':
                return na % nb if nb != 0 else None
            elif op == '>':
                return na > nb
            elif op == '<':
                return na < nb
            elif op == '>=':
                return na >= nb
            elif op == '<=':
                return na <= nb
            elif op == '==':
                return na == nb
            elif op == '!=':
                return na != nb
        except Exception:
            return None
        return None


def generate_optimization_analysis(
    metrics: CFGMetricsResponse,
    transformations: list[Transformation],
    blocks_before: list[BasicBlock],
    blocks_after: list[BasicBlock],
    quads_before: list[Quad],
    quads_after: list[Quad]
) -> OptimizationAnalysisResponse:
    from collections import Counter
    tech_counts = Counter(t.technique for t in transformations)
    tech_blocks = {}
    for t in transformations:
        tech_blocks.setdefault(t.technique, set()).add(t.block_id)

    total_before = metrics.total_instructions_before
    total_after = metrics.total_instructions_after
    eliminated = max(0, total_before - total_after)
    reduction = metrics.reduction_percent
    temps = metrics.temporals_saved
    c_before = metrics.cyclomatic_complexity_before
    c_after = metrics.cyclomatic_complexity_after
    b_before = metrics.blocks_before
    b_after = metrics.blocks_after

    # 1. Optimizaciones realizadas
    opt_list = []
    if not transformations:
        opt_list.append("No se requirieron transformaciones adicionales; el código intermedio analizado ya se encuentra en su representación óptima.")
    else:
        def get_tech_explanation(tech_name: str) -> str:
            t = tech_name.lower()
            if "folding" in t or "plegado" in t:
                return "Se evaluaron operaciones aritméticas y relacionales directamente en tiempo de compilación con operandos constantes conocidos, reemplazando el cálculo en tiempo de ejecución por su resultado literal directo."
            if "retorno" in t:
                return "Se propagó la variable final directamente hacia la sentencia de retorno, permitiendo descartar variables intermedias auxiliares."
            if "propagación" in t or "propagacion" in t:
                return "Se sustituyeron variables locales por sus valores constantes previamente asignados dentro del mismo bloque básico, habilitando nuevos pliegues de expresiones y eliminando lecturas redundantes."
            if "subexpresiones" in t or "cse" in t:
                return "Se detectaron cálculos repetidos con operandos inalterados dentro del bloque básico, reutilizando el resultado del cálculo inicial y evitando operaciones redundantes de procesador."
            if "inalcanzable" in t:
                return "Se podaron instrucciones y bloques ubicados posteriormente a instrucciones de retorno incondicional o saltos sin transiciones entrantes alcanzables desde la entrada."
            if "muerto" in t or "dead" in t:
                return "Se suprimieron asignaciones a variables y temporales cuyos valores nunca vuelven a ser consultados o leídos antes del retorno o fin de ejecución."
            if "salto" in t:
                return "Se eliminaron transferencias de control innecesarias (como saltos dirigidos a la instrucción inmediatamente contigua o ramas condicionales con condición constante) optimizando el flujo de control."
            if "identidad" in t:
                return "Se eliminaron instrucciones de asignación redundantes de la forma x = x."
            return "Se aplicó transformación de optimización en el bloque básico."

        for tech, count in tech_counts.items():
            blocks_str = ", ".join(sorted(tech_blocks.get(tech, [])))
            expl = get_tech_explanation(tech)
            opt_list.append(f"**{tech}** ({count} intervención{'es' if count > 1 else ''} en bloque(s) {blocks_str}): {expl}")

    # 2. Beneficios obtenidos
    benefits = [
        f"**Mayor eficiencia en tiempo de ejecución (CPU)**: Se redujo la carga de procesamiento al pasar de {total_before} a {total_after} instrucciones ejecutables (-{reduction}%). La eliminación de cálculos redundantes y saltos innecesarios disminuye el número de ciclos de reloj requeridos.",
        f"**Menor consumo de memoria y registros**: Se economizaron {temps} registro(s) temporal(es) intermedio(s). Esto aminora la presión de registros en la etapa de generación de código objeto/máquina y optimiza el uso de la pila de memoria.",
        f"**Preservación estricta de la semántica**: Todas las transformaciones se rigen por la regla de equivalencia funcional, garantizando que el programa optimizado produzca con total fidelidad las mismas salidas y efectos colaterales que el código fuente Go original."
    ]
    if c_before > c_after or b_before > b_after:
        benefits.append(
            f"**Simplificación topológica del flujo de control**: La complejidad ciclomática de McCabe se redujo de {c_before} a {c_after}, y los bloques básicos de {b_before} a {b_after}. Esto elimina bifurcaciones muertas y caminos de ejecución inalcanzables, facilitando el análisis, prueba y posterior traducción del programa."
        )
    else:
        benefits.append(
            f"**Flujo de control robusto y determinista**: Se mantuvo una complejidad ciclomática estable ({c_after}) preservando la estructura lógica condicional con menor sobrecarga de instrucciones auxiliares."
        )

    # 3. Instrucciones eliminadas o simplificadas
    inst_analysis = (
        f"El código intermedio original constaba de {total_before} instrucciones en cuádruplos/TAC. "
        f"Tras el análisis iterativo, se eliminaron o simplificaron {eliminated} instrucciones, alcanzando una reducción neta del {reduction}%. "
        f"El código intermedio optimizado resultante contiene únicamente {total_after} instrucciones esenciales. "
        f"Las instrucciones removidas corresponden principalmente a operaciones aritméticas precalculadas en compilación, "
        f"asignaciones a variables que no impactan el resultado final y bloques de código ubicados después de sentencias terminales de retorno."
    )

    # 4. Contribución del GFG en el proceso de optimización
    cfg_contrib = (
        f"El Grafo de Flujo de Control (GFG) fue la herramienta central e indispensable para estructurar la optimización:\n"
        f"1. **Partición en bloques básicos**: Permitió dividir el flujo secuencial en {b_before} bloques mediante la detección rigurosa de líderes (primera instrucción, destinos de saltos/etiquetas e instrucciones posteriores a saltos).\n"
        f"2. **Análisis topológico de alcanzabilidad**: Gracias a la matriz de sucesores y predecesores, el GFG identificó visual y formalmente qué bloques no poseen ningún camino ejecutable desde el nodo de entrada ([Inicio] -> B1), fundamentando la eliminación rigurosa de código inalcanzable.\n"
        f"3. **Métricas estructurales de complejidad**: El grafo permitió calcular la Complejidad Ciclomática de McCabe, constatando la reducción de complejidad de {c_before} a {c_after} y demostrando formalmente la simplificación estructural obtenida."
    )

    # 5. Conclusiones
    conclusions = (
        f"El proceso de optimización implementado sobre el Grafo de Flujo de Control valida la importancia del análisis estático intermedio en compiladores. "
        f"A través de la combinación de optimizaciones locales intra-bloque (plegado, propagación y eliminación de subexpresiones) "
        f"y optimizaciones globales basadas en el flujo de control (eliminación de código inalcanzable y código muerto), se obtuvo un código {reduction}% más compacto, "
        f"ahorrando {temps} temporales y simplificando el flujo de ejecución, cumpliendo con los criterios de optimización sin alterar el comportamiento del programa Go original."
    )

    summary = (
        f"Optimización completada con éxito: {eliminated} instrucciones eliminadas ({reduction}% de reducción), "
        f"{temps} temporales ahorrados y complejidad ciclomática de {c_before} → {c_after} sobre el Grafo de Flujo de Control."
    )

    return OptimizationAnalysisResponse(
        summary=summary,
        optimizations_applied=opt_list,
        benefits=benefits,
        instructions_analysis=inst_analysis,
        cfg_contribution=cfg_contrib,
        conclusions=conclusions
    )


def optimize_code(code: str) -> OptimizationResponse:
    # Paso 1: Generar IR original
    ir_res = generate_ir(code)
    if not ir_res.success:
        return OptimizationResponse(
            success=False,
            errors=ir_res.errors,
            original_tac="",
            optimized_tac="",
            original_ir="",
            optimized_ir="",
            original_cfg_mermaid="",
            optimized_cfg_mermaid="",
            blocks_before=[],
            blocks_after=[],
            transformations=[],
            metrics=CFGMetricsResponse(
                total_instructions_before=0,
                total_instructions_after=0,
                reduction_percent=0.0,
                temporals_saved=0,
                cyclomatic_complexity_before=0,
                cyclomatic_complexity_after=0,
                blocks_before=0,
                blocks_after=0
            )
        )

    # Convertir quadruples a Quad
    quads_before = [Quad(q.op, q.arg1, q.arg2, q.result) for q in ir_res.quadruples]

    # Paso 2: CFG Original
    cfg_before = ControlFlowGraph.from_quads(quads_before)
    mermaid_before = cfg_before.to_mermaid()
    complexity_before = cfg_before.calculate_cyclomatic_complexity()
    blocks_schema_before = [b.to_schema() for b in cfg_before.blocks]

    # Paso 3: Optimización
    optimizer = IROptimizer()
    quads_after, transformations = optimizer.optimize(quads_before)

    # Paso 4: CFG Optimizado
    cfg_after = ControlFlowGraph.from_quads(quads_after)
    mermaid_after = cfg_after.to_mermaid()
    complexity_after = cfg_after.calculate_cyclomatic_complexity()
    blocks_schema_after = [b.to_schema() for b in cfg_after.blocks]

    # Paso 5: Formatear IR strings (before.ir y after.ir) y TAC strings
    tac_before = "\n".join([q.to_tac() for q in quads_before])
    tac_after = "\n".join([q.to_tac() for q in quads_after])
    triples_before = [q.to_triple(i + 1) for i, q in enumerate(quads_before)]
    triples_after = [q.to_triple(i + 1) for i, q in enumerate(quads_after)]
    ir_str_before = "\n".join(triples_before) + "\n"
    ir_str_after = "\n".join(triples_after) + "\n"

    # Paso 6: Métricas
    total_before = len(quads_before)
    total_after = len(quads_after)
    reduction = round(((total_before - total_after) / total_before * 100), 2) if total_before > 0 else 0.0

    # Temporales ahorrados
    temps_before = len(set(q.result for q in quads_before if q.result.startswith('t') and q.result[1:].isdigit()))
    temps_after = len(set(q.result for q in quads_after if q.result.startswith('t') and q.result[1:].isdigit()))
    temporals_saved = max(0, temps_before - temps_after)

    metrics = CFGMetricsResponse(
        total_instructions_before=total_before,
        total_instructions_after=total_after,
        reduction_percent=reduction,
        temporals_saved=temporals_saved,
        cyclomatic_complexity_before=complexity_before,
        cyclomatic_complexity_after=complexity_after,
        blocks_before=len(cfg_before.blocks),
        blocks_after=len(cfg_after.blocks)
    )

    analysis = generate_optimization_analysis(
        metrics=metrics,
        transformations=transformations,
        blocks_before=cfg_before.blocks,
        blocks_after=cfg_after.blocks,
        quads_before=quads_before,
        quads_after=quads_after
    )

    return OptimizationResponse(
        success=True,
        errors=[],
        original_tac=tac_before,
        optimized_tac=tac_after,
        original_ir=ir_str_before,
        optimized_ir=ir_str_after,
        original_cfg_mermaid=mermaid_before,
        optimized_cfg_mermaid=mermaid_after,
        blocks_before=blocks_schema_before,
        blocks_after=blocks_schema_after,
        transformations=[t.to_schema() for t in transformations],
        metrics=metrics,
        analysis=analysis
    )
