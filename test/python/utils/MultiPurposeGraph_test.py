import unittest
import sys
import os

# Add the project root to the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from src.python.utils.MultiPurposeGraph import MultiPurposeGraph, Node

class TestMultiPurposeGraph(unittest.TestCase):

    #def test_load_emptyfile(self):
    #    graph = MultiPurposeGraph.load("data/empty.pkl")
    #    self.assertEqual(graph.nodes, [])
    #    self.assertEqual(graph.typeOrganizedNodes, dict())

    def test_load_and_use_emptyfile(self):
        graph = MultiPurposeGraph.load("data/empty.pkl")
        graph.get_node("Alice", "Person")
        graph.save("data/empty.pkl")

    def test_add_node(self):
        graph = MultiPurposeGraph()
        node = Node(type="Person", name="Alice")
        graph.add_node(node)
        
        self.assertIn(node, graph.nodes)
        self.assertIn("Person", graph.typeOrganizedNodes)
        self.assertIn("Alice", graph.typeOrganizedNodes["Person"])
        self.assertEqual(graph.typeOrganizedNodes["Person"]["Alice"], node)

    def test_add_edge(self):
        graph = MultiPurposeGraph()
        node1 = Node(type="Person", name="Alice")
        node2 = Node(type="Person", name="Bob")
        graph.add_node(node1)
        graph.add_node(node2)
        
        graph.add_edge(node1, node2, "knows")
        
        self.assertIn("knows", node1.links)
        self.assertIn(node2, node1.links["knows"])

    def test_node_str(self):
        node = Node(type="Person", name="Alice")
        expected_str = "Person: Alice, {}"
        self.assertEqual(str(node), expected_str)

    def test_add_link(self):
        node1 = Node(type="Person", name="Alice")
        node2 = Node(type="Person", name="Bob")
        node1.add_link(node2, "knows")
        
        self.assertIn("knows", node1.links)
        self.assertIn(node2, node1.links["knows"])

if __name__ == '__main__':
    unittest.main()
    TestMultiPurposeGraph.test_load_and_use_emptyfile()