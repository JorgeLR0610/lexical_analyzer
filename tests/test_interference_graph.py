import unittest
import sys
import os

# Asegurar path de app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'app')))

from core.interference_graph import (
    parse_adjacency_list,
    InterferenceGraph,
    analyze_interference_graph
)
from fastapi.testclient import TestClient
from main import app


class TestInterferenceGraph(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_parse_adjacency_user_example(self):
        text = """
A: B, F
B: C
C: D
D: E, F
E: F
"""
        nodes, edges, errors = parse_adjacency_list(text)
        self.assertEqual(len(errors), 0)
        self.assertEqual(nodes, ['A', 'B', 'F', 'C', 'D', 'E'])
        self.assertEqual(len(edges), 7)
        expected_edges = [
            ('A', 'B'), ('A', 'F'),
            ('B', 'C'),
            ('C', 'D'),
            ('D', 'E'), ('D', 'F'),
            ('E', 'F')
        ]
        self.assertEqual(sorted(edges), sorted(expected_edges))

    def test_user_example_coloring_optimal_chromatic_3(self):
        text = """
A: B, F
B: C
C: D
D: E, F
E: F
"""
        res = analyze_interference_graph(text)
        self.assertTrue(res.success)
        self.assertEqual(res.chromatic_number, 3)
        self.assertEqual(res.total_nodes, 6)
        self.assertEqual(res.total_edges, 7)
        self.assertEqual(res.max_degree, 3)  # D y F tienen grado 3
        self.assertEqual(len(res.color_distribution), 3)

        # Verificar que ningún par adyacente comparta registro
        node_to_reg = {a.node: a.register_name for a in res.node_assignments}
        for u, v in res.edges:
            self.assertNotEqual(node_to_reg[u], node_to_reg[v], f"Conflicto entre {u} y {v}")

    def test_cycle_graphs_bipartite_and_odd(self):
        # Ciclo Par C6: debe ser 2-cromático (chi = 2)
        c6_text = """
1: 2, 6
2: 3
3: 4
4: 5
5: 6
"""
        res_c6 = analyze_interference_graph(c6_text)
        self.assertTrue(res_c6.success)
        self.assertEqual(res_c6.chromatic_number, 2)

        # Ciclo Impar C5: debe ser 3-cromático (chi = 3)
        c5_text = """
1: 2, 5
2: 3
3: 4
4: 5
"""
        res_c5 = analyze_interference_graph(c5_text)
        self.assertTrue(res_c5.success)
        self.assertEqual(res_c5.chromatic_number, 3)

    def test_complete_graph_k4(self):
        # Grafo Completo K4: debe ser 4-cromático
        k4_text = """
A: B, C, D
B: C, D
C: D
"""
        res_k4 = analyze_interference_graph(k4_text)
        self.assertTrue(res_k4.success)
        self.assertEqual(res_k4.chromatic_number, 4)
        self.assertEqual(res_k4.total_edges, 6)

    def test_graph_with_isolated_nodes(self):
        # Nodos aislados sin interferencias: chi = 1
        text = """
X
Y
Z
"""
        res = analyze_interference_graph(text)
        self.assertTrue(res.success)
        self.assertEqual(res.chromatic_number, 1)
        self.assertEqual(res.total_edges, 0)
        self.assertEqual(len(res.color_distribution), 1)

    def test_mixed_input_formats(self):
        # Formato mixto con guiones, espacios, comas y comentarios
        text = """
# Interferencia entre variables temporales
t1 - t2
t2: t3 t4
// t4 interfiere con t5
t4 - t5
t6:
"""
        nodes, edges, errors = parse_adjacency_list(text)
        self.assertEqual(len(errors), 0)
        self.assertIn('t1', nodes)
        self.assertIn('t6', nodes)
        self.assertIn(('t1', 't2'), edges)
        self.assertIn(('t2', 't3'), edges)
        self.assertIn(('t2', 't4'), edges)
        self.assertIn(('t4', 't5'), edges)

        res = analyze_interference_graph(text)
        self.assertTrue(res.success)

    def test_fastapi_interference_graph_endpoint(self):
        payload = {
            "adjacency_list": "A: B, F\nB: C\nC: D\nD: E, F\nE: F"
        }
        r = self.client.post("/interference-graph", json=payload)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["chromatic_number"], 3)
        self.assertEqual(data["total_nodes"], 6)
        self.assertEqual(data["total_edges"], 7)
        self.assertIn("mermaid_diagram", data)
        self.assertIn("classDef", data["mermaid_diagram"])

    def test_empty_input_error(self):
        payload = {"adjacency_list": "   "}
        r = self.client.post("/interference-graph", json=payload)
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
