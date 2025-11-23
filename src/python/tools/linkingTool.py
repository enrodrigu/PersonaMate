"""
Tool for linking different elements such as persons and likings to each others with named attributes like "likes" or "knows".
"""

import sys
import os

# Add the project root to the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from src.python.utils.neo4j_graph import Neo4jGraph
from langchain_core.tools import tool


@tool
def link_elements(element1: str, type1: str, element2: str, type2: str, linktype: str) -> str:
    """
    Link two elements in the graph with a given link type

    Args:
        element1 (str): Name of the first element
        type1 (str): Type of the first element
        element2 (str): Name of the second element
        type2 (str): Type of the second element
        linktype (str): Type of the link between the elements

    Returns:
        str: Success message
    """
    graph = Neo4jGraph.load()
    graph.add_edge(type1, element1, type2, element2, linktype)
    try:
        graph.close()
    except Exception:
        pass
    return f"{element1} and {element2} linked with type {linktype}"
