"""
Tool for linking different elements such as persons and likings to each others with named attributes like "likes" or "knows".
"""

import sys
import os

# Add the project root to the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from src.python.utils.MultiPurposeGraph import MultiPurposeGraph as mpg
from src.python.utils.MultiPurposeGraph import Node as mpgNode
from langchain_core.tools import tool

FILEPATH = "data/links.pkl"

def load_graph(filepath:str) -> mpg:
    """
    Load a MultiPurposeGraph object from a file and create the file if it doesn't exist

    Args:
        filepath (str): Path to the file to load the graph from

    Returns:
        mpg: The loaded graph
    """
    return mpg.load(FILEPATH)
    
def save_graph(graph:mpg, filepath:str) -> None:
    """
    Save a MultiPurposeGraph object to a file

    Args:
        graph (mpg): The graph to save
        filepath (str): Path to the file to save the graph to
    """
    mpg.save(graph, FILEPATH)

@tool
def link_elements(element1:str, type1:str, element2:str, type2:str, linktype:str) -> str:
    """
    Link two elements in the graph with a given link type

    Args:
        graph (mpg): The graph to link the elements in
        element1 (str): Name of the first element
        type1 (str): Type of the first element
        element2 (str): Name of the second element
        type2 (str): Type of the second element
        linktype (str): Type of the link between the elements

    Returns:
        str: Success message
    """
    graph = load_graph(FILEPATH)
    node1 = graph.get_node(element1, type1)
    node2 = graph.get_node(element2, type2)
    if not node1:
        node1 = mpgNode(type1, element1)
        graph.add_node(node1)
    if not node2:
        node2 = mpgNode(type2, element2)
        graph.add_node(node2)
    graph.add_edge(node1, node2, linktype)
    save_graph(graph, FILEPATH)
    return f"{element1} and {element2} linked with type {linktype}"
