import pickle as pkl
#for saving and loading the graph

class Node:
    def __init__(self, type:str, name:str) -> None:
        self.links = dict()
        self.type = type
        self.name = name

    def add_link(self, node, edgetype:str):
        if edgetype not in self.links:
            self.links[edgetype] = []
        self.links[edgetype].append(node)

    def __str__(self):
        return f"{self.type}: {self.name}, {self.links}"
    
class MultiPurposeGraph:
    def __init__(self):
        self.nodes = []
        self.typeOrganizedNodes = dict()

    def add_node(self, node:Node):
        self.nodes.append(node)
        if node.type not in self.typeOrganizedNodes:
            self.typeOrganizedNodes[node.type] = dict()
        self.typeOrganizedNodes[node.type][node.name] = node

    def add_edge(self, node1:Node, node2:Node, edgetype:str):
        if node1 not in self.nodes:
            self.add_node(node1)
        if node2 not in self.nodes:
            self.add_node(node2)
        node1.add_link(node2, edgetype)

    def get_node(self, name:str, type:str=None):
        if type is None:
            for node in self.nodes:
                if node.name == name:
                    return node
        else:
            if type in self.typeOrganizedNodes:
                return self.typeOrganizedNodes[type].get(name)
        return None
    
    def get_graph(self, xray:bool=False):
        graph = "graph TD\n"
        for node in self.nodes:
            graph += f"    {node.name}({node.type}: {node.name})\n"
            for linktype, linkednodes in node.links.items():
                graph += f"    {node.name} -->|{linktype}|"
                for linkednode in linkednodes:
                    graph += f" {linkednode.name}"
                graph += "\n"
        return graph
    
    def __str__(self):
        return str([str(node) for node in self.nodes])
    
    def save(self, filename:str):
        with open(filename, 'wb') as file:
            pkl.dump(self, file)

    @staticmethod
    def load(filename:str):
        with open(filename, 'rb') as file:
            return pkl.load(file)