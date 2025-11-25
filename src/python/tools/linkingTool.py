"""
Tool for linking different elements such as persons and likings to each others with named attributes like "likes" or "knows".
"""

from langchain_core.tools import tool
from utils.neo4j_graph import Neo4jGraph


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


@tool
def fetch_entity_context(name: str, type: str = "Person", depth: int = 1) -> str:
    """Fetch structured context for an entity from Neo4j and return a summary string.

    The function performs a breadth-first traversal up to `depth` steps and returns
    a JSON-like string containing nodes and edges plus a short human-readable summary
    that can be passed to an LLM as additional context.
    """
    graph = Neo4jGraph.load()

    # BFS
    queue = [(name, type, 0)]
    visited = set()
    nodes = {}
    edges = []

    while queue:
        cur_name, cur_type, cur_depth = queue.pop(0)
        key = (cur_name, cur_type)
        if key in visited:
            continue
        visited.add(key)
        nodes[key] = {"name": cur_name, "type": cur_type}

        # fetch neighbors
        try:
            neigh = graph.get_neighbors(cur_name, cur_type)
        except Exception:
            neigh = []

        for n in neigh:
            n_name = n.get("name")
            n_labels = n.get("labels") or []
            n_type = n_labels[0] if n_labels else "Unknown"
            if n.get("direction") == "out":
                edges.append({"from": {"name": cur_name, "type": cur_type},
                              "to": {"name": n_name, "type": n_type},
                              "rel": n.get("rel")})
                neighbor_key = (n_name, n_type)
            else:
                edges.append({"from": {"name": n_name, "type": n_type},
                              "to": {"name": cur_name, "type": cur_type},
                              "rel": n.get("rel")})
                neighbor_key = (n_name, n_type)

            if neighbor_key not in visited and cur_depth + 1 <= depth:
                queue.append((neighbor_key[0], neighbor_key[1], cur_depth + 1))
                nodes[neighbor_key] = {"name": neighbor_key[0], "type": neighbor_key[1]}

    # Build human-readable summary
    lines = []
    for e in edges:
        lines.append(f"{e['from']['name']} ({e['from']['type']}) -[{e['rel']}]-> {e['to']['name']} ({e['to']['type']})")

    summary = "; ".join(lines) if lines else "No relations found"

    # Close driver
    try:
        graph.close()
    except Exception:
        pass

    # Return a compact payload suitable for LLM context injection
    payload = {
        "entity": {"name": name, "type": type},
        "nodes": list(nodes.values()),
        "edges": edges,
        "summary": summary,
    }

    import json

    return json.dumps(payload)
