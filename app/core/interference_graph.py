#type: ignore
import re
from typing import Optional
from api.schemas import (
    RegisterColorClass,
    NodeAssignment,
    InterferenceGraphResponse
)

# Paleta de colores
PALETTE = [
    {"name": "Cian", "hex": "#06b6d4", "text": "#082f49", "border": "#22d3ee"},
    {"name": "Rojo", "hex": "#f43f5e", "text": "#ffffff", "border": "#fb7185"},
    {"name": "Verde", "hex": "#10b981", "text": "#022c22", "border": "#34d399"},
    {"name": "Ámbar", "hex": "#f59e0b", "text": "#451a03", "border": "#fbbf24"},
    {"name": "Violeta", "hex": "#a855f7", "text": "#ffffff", "border": "#c084fc"},
    {"name": "Rosa", "hex": "#ec4899", "text": "#ffffff", "border": "#f472b6"},
    {"name": "Azul", "hex": "#3b82f6", "text": "#ffffff", "border": "#60a5fa"},
    {"name": "Lima", "hex": "#84cc16", "text": "#1a2e05", "border": "#a3e635"},
    {"name": "Naranja", "hex": "#f97316", "text": "#431407", "border": "#fb923c"},
    {"name": "Esmeralda", "hex": "#14b8a6", "text": "#042f2e", "border": "#2dd4bf"},
    {"name": "Índigo", "hex": "#6366f1", "text": "#ffffff", "border": "#818cf8"},
    {"name": "Fucsia", "hex": "#d946ef", "text": "#ffffff", "border": "#e879f9"},
]

def get_palette_color(color_idx: int) -> dict:
    """Devuelve el esquema de color para un índice de color (1-based)."""
    if 1 <= color_idx <= len(PALETTE):
        return PALETTE[color_idx - 1]
    # Generador dinámico HSL si se requieren más de 12 colores
    hue = ((color_idx - 1) * 137.5) % 360
    return {
        "name": f"Color {color_idx}",
        "hex": f"hsl({hue:.0f}, 80%, 55%)",
        "text": "#ffffff",
        "border": f"hsl({hue:.0f}, 90%, 65%)"
    }


def parse_adjacency_list(text: str) -> tuple[list[str], list[tuple[str, str]], list[str]]:
    """
    Parsea una lista de adyacencia textual en formatos flexibles:
    - Formato estándar:
        A: B, F
        B: C
        C: D
    - Formato con espacios:
        A: B F
    - Formato de aristas directas:
        A - B  o  A-B
    - Nodos aislados:
        G:  o  G
    - Soporta comentarios con '#' o '//'.
    
    Retorna: (nodes, edges, errors)
    donde edges son tuplas normalizadas (u, v) con u < v, sin lazos ni duplicados
    """
    raw_nodes_order = []
    seen_nodes = set()
    adj_set: set[tuple[str, str]] = set()
    errors = []

    lines = text.strip().splitlines()
    for line_idx, line in enumerate(lines, 1):
        # Eliminar comentarios
        clean_line = re.sub(r'(#|//).*$', '', line).strip()
        if not clean_line:
            continue

        # Formato de arista 'A - B' o 'A -- B'
        if '-' in clean_line and ':' not in clean_line:
            parts = re.split(r'-+', clean_line)
            if len(parts) == 2:
                u, v = parts[0].strip(), parts[1].strip()
                if u and v:
                    for n in (u, v):
                        if n not in seen_nodes:
                            seen_nodes.add(n)
                            raw_nodes_order.append(n)
                    if u != v:
                        edge = (min(u, v), max(u, v))
                        adj_set.add(edge)
                    continue
                else:
                    errors.append(f"Línea {line_idx}: arista inválida '{clean_line}'")
                    continue

        # formato estandar como 'U: V1, V2...' o 'U: V1 V2...'
        if ':' in clean_line:
            parts = clean_line.split(':', 1)
            u = parts[0].strip()
            rest = parts[1].strip()

            if not u:
                errors.append(f"Línea {line_idx}: falta identificador de nodo antes de ':'")
                continue

            if u not in seen_nodes:
                seen_nodes.add(u)
                raw_nodes_order.append(u)

            if rest:
                # Separar vecinos por coma o por espacios
                neighbors = [tok.strip() for tok in re.split(r'[,;\s]+', rest) if tok.strip()]
                for v in neighbors:
                    if v not in seen_nodes:
                        seen_nodes.add(v)
                        raw_nodes_order.append(v)
                    if u != v:
                        edge = (min(u, v), max(u, v))
                        adj_set.add(edge)
            continue

        # Declaración simple de nodo aislado (algo como solo 'G')
        tokens = [tok.strip() for tok in re.split(r'[,;\s]+', clean_line) if tok.strip()]
        for tok in tokens:
            if tok not in seen_nodes:
                seen_nodes.add(tok)
                raw_nodes_order.append(tok)

    edges_list = sorted(list(adj_set))
    return raw_nodes_order, edges_list, errors


class InterferenceGraph:
    def __init__(self, nodes: list[str], edges: list[tuple[str, str]]):
        self.nodes = nodes
        self.edges = edges
        self.neighbors: dict[str, set[str]] = {n: set() for n in self.nodes}
        for u, v in self.edges:
            if u in self.neighbors and v in self.neighbors:
                self.neighbors[u].add(v)
                self.neighbors[v].add(u)

    @property
    def total_nodes(self) -> int:
        return len(self.nodes)

    @property
    def total_edges(self) -> int:
        return len(self.edges)

    def degrees(self) -> dict[str, int]:
        return {n: len(self.neighbors[n]) for n in self.nodes}

    def max_degree(self) -> int:
        deg = self.degrees()
        return max(deg.values()) if deg else 0

    def dsatur_coloring(self) -> dict[str, int]:
        """
        Heurística DSATUR (Brelaz, 1979).
        Ordena la coloración priorizando nodos con mayor grado de saturación
        (número de colores distintos usados por sus vecinos).
        Retorna: {node: color_id (1-based)}
        """
        if not self.nodes:
            return {}

        colors: dict[str, Optional[int]] = {n: None for n in self.nodes}
        saturation: dict[str, set[int]] = {n: set() for n in self.nodes}
        degrees = self.degrees()

        for _ in range(len(self.nodes)):
            # Seleccionar nodo no coloreado con máxima saturación; desempatar con grado
            uncolored = [n for n in self.nodes if colors[n] is None]
            best_node = max(
                uncolored,
                key=lambda n: (len(saturation[n]), degrees[n])
            )

            # Asignar el menor color disponible que no usen sus vecinos
            neighbor_colors = {colors[nbr] for nbr in self.neighbors[best_node] if colors[nbr] is not None}
            c = 1
            while c in neighbor_colors:
                c += 1

            colors[best_node] = c
            # Actualizar saturación de los nodos vecinos
            for nbr in self.neighbors[best_node]:
                saturation[nbr].add(c)

        return {n: int(colors[n]) for n in self.nodes}

    def optimal_chromatic_coloring(self) -> tuple[int, dict[str, int]]:
        """
        Determina el número cromático exacto χ(G) y la asignación óptima
        mediante DSATUR + Branch & Bound.
        """
        if not self.nodes:
            return 0, {}

        # obtener cota superior inicial con DSATUR
        heuristic_colors = self.dsatur_coloring()
        k_upper = max(heuristic_colors.values()) if heuristic_colors else 1
        best_coloring = heuristic_colors

        # Si k_upper <= 2 o grafo vacío/árbol bipartito, es inmediato
        if k_upper <= 2:
            return k_upper, best_coloring

        # cota inferior: tamaño del clan máximo clique estimado (mínimo 1, 2 si hay aristas, 3 si hay triángulos)
        k_lower = 1 if self.total_edges == 0 else 2
        # buscar triángulos (K3)
        for u in self.nodes:
            if k_lower >= 3:
                break
            for v in self.neighbors[u]:
                common = self.neighbors[u].intersection(self.neighbors[v])
                if common:
                    k_lower = 3
                    break

        if k_upper == k_lower:
            return k_upper, best_coloring

        # Branch & Bound para buscar si es coloreable con k < k_upper
        nodes_sorted = sorted(self.nodes, key=lambda n: len(self.neighbors[n]), reverse=True)

        def can_color(k_target: int) -> Optional[dict[str, int]]:
            assignment = {}

            def backtrack(idx: int) -> bool:
                if idx == len(nodes_sorted):
                    return True
                curr = nodes_sorted[idx]
                used_by_nbrs = {assignment[nbr] for nbr in self.neighbors[curr] if nbr in assignment}
                for color_cand in range(1, k_target + 1):
                    if color_cand not in used_by_nbrs:
                        assignment[curr] = color_cand
                        if backtrack(idx + 1):
                            return True
                        del assignment[curr]
                return False

            if backtrack(0):
                return assignment
            return None

        for k in range(k_lower, k_upper):
            coloring = can_color(k)
            if coloring is not None:
                return k, coloring

        return k_upper, best_coloring

    def verify_coloring(self, coloring: dict[str, int]) -> bool:
        """Verifica que ningún par de nodos conectados comparta el mismo color"""
        for u, v in self.edges:
            if coloring.get(u) == coloring.get(v):
                return False
        return True

    def to_mermaid(self, coloring: dict[str, int]) -> str:
        """Genera diagrama Mermaid con nodos coloreados según registro"""
        lines = ["graph TD"]
        # Definir estilos de clase para cada color
        unique_colors = sorted(list(set(coloring.values())))
        for cid in unique_colors:
            info = get_palette_color(cid)
            lines.append(f"    classDef reg{cid} fill:{info['hex']},stroke:{info['border']},stroke-width:2px,color:{info['text']};")

        # Nodos
        for n in self.nodes:
            cid = coloring.get(n, 1)
            reg_name = f"R{cid}"
            lines.append(f'    {n}["<b>{n}</b><br/>{reg_name}"]')
            lines.append(f"    class {n} reg{cid};")

        # Aristas
        for u, v in self.edges:
            lines.append(f"    {u} --- {v}")

        return "\n".join(lines)


def analyze_interference_graph(text: str) -> InterferenceGraphResponse:
    """Función para procesar la lista de adyacencia y generar la coloración óptima"""
    nodes, edges, errors = parse_adjacency_list(text)
    if not nodes:
        return InterferenceGraphResponse(
            success=False,
            errors=errors or ["No se encontraron variables ni aristas válidas en la entrada"],
            nodes=[],
            edges=[],
            chromatic_number=0,
            total_nodes=0,
            num_nodes=0,
            total_edges=0,
            num_edges=0,
            max_degree=0,
            color_distribution=[],
            color_classes=[],
            node_assignments=[],
            mermaid_diagram=""
        )

    graph = InterferenceGraph(nodes, edges)
    chromatic_number, coloring = graph.optimal_chromatic_coloring()
    is_valid = graph.verify_coloring(coloring)

    if not is_valid:
        errors.append("Error interno: la coloración generada presenta conflictos en variables adyacentes")

    # Agrupar por clases de color (registros)
    color_to_nodes: dict[int, list[str]] = {}
    for n in nodes:
        cid = coloring.get(n, 1)
        color_to_nodes.setdefault(cid, []).append(n)

    color_distribution = []
    for cid in sorted(color_to_nodes.keys()):
        c_info = get_palette_color(cid)
        color_distribution.append(
            RegisterColorClass(
                color_id=cid,
                register_name=f"R{cid}",
                color_name=c_info["name"],
                color_hex=c_info["hex"],
                hex_color=c_info["hex"],
                nodes=color_to_nodes[cid],
                count=len(color_to_nodes[cid])
            )
        )

    node_assignments = []
    degrees = graph.degrees()
    for n in nodes:
        cid = coloring.get(n, 1)
        c_info = get_palette_color(cid)
        node_assignments.append(
            NodeAssignment(
                node=n,
                degree=degrees.get(n, 0),
                register_name=f"R{cid}",
                color_name=c_info["name"],
                color_hex=c_info["hex"],
                hex_color=c_info["hex"]
            )
        )

    mermaid_diagram = graph.to_mermaid(coloring)

    return InterferenceGraphResponse(
        success=len(errors) == 0 or is_valid,
        errors=errors,
        nodes=nodes,
        edges=[[u, v] for u, v in edges],
        chromatic_number=chromatic_number,
        total_nodes=graph.total_nodes,
        num_nodes=graph.total_nodes,
        total_edges=graph.total_edges,
        num_edges=graph.total_edges,
        max_degree=graph.max_degree(),
        color_distribution=color_distribution,
        color_classes=color_distribution,
        node_assignments=node_assignments,
        mermaid_diagram=mermaid_diagram
    )
