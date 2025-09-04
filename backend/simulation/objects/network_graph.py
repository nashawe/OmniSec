import json
import networkx as nx
from typing import List, Tuple, Dict, Any
from .node import Node
from .edge import Edge

class NetworkGraph:
    """
    Holds the network topology using NetworkX for powerful graph operations.
    This class acts as a manager and wrapper around a NetworkX graph object,
    storing our custom Node and Edge objects as node/edge attributes.
    """

    def __init__(self):
        # Use a DiGraph for directed connections, which is more realistic.
        # An edge from A to B doesn't automatically mean B can talk to A.
        self.graph = nx.DiGraph()

    def add_node(self, node: Node):
        """Adds a Node object to the graph."""
        if self.graph.has_node(node.id):
            raise ValueError(f"Node with id {node.id} already exists.")
        # The node's ID is the graph node. The entire Node object is stored
        # in the 'data' attribute of the graph node.
        self.graph.add_node(node.id, data=node)

    def add_edge(self, edge: Edge):
        """Adds an Edge object to the graph."""
        if not self.graph.has_node(edge.source_node_id):
            raise ValueError(f"Source node {edge.source_node_id} not in graph.")
        if not self.graph.has_node(edge.target_node_id):
            raise ValueError(f"Target node {edge.target_node_id} not in graph.")
        
        # The entire Edge object is stored in the 'data' attribute of the graph edge.
        self.graph.add_edge(edge.source_node_id, edge.target_node_id, data=edge)
        if edge.bidirectional:
            self.graph.add_edge(edge.target_node_id, edge.source_node_id, data=edge)

    def get_node_by_id(self, node_id: str) -> Node | None:
        """Retrieves the full Node object by its ID."""
        if self.graph.has_node(node_id):
            return self.graph.nodes[node_id]['data']
        return None

    def get_all_nodes(self) -> List[Node]:
        """Returns a list of all Node objects in the graph."""
        return [data['data'] for _, data in self.graph.nodes(data=True)]

    def get_neighbors(self, node_id: str) -> List[Node]:
        """Gets all directly connected neighbor Node objects."""
        if not self.graph.has_node(node_id):
            return []
        # In a DiGraph, successors are nodes that can be reached from node_id.
        # We also check predecessors for a complete neighbor list.
        neighbor_ids = set(self.graph.successors(node_id)) | set(self.graph.predecessors(node_id))
        return [self.get_node_by_id(nid) for nid in neighbor_ids if nid]

    def get_path(self, source_id: str, target_id: str) -> List[Node] | None:
        """Finds the shortest path between two nodes."""
        try:
            path_ids = nx.shortest_path(self.graph, source=source_id, target=target_id)
            return [self.get_node_by_id(pid) for pid in path_ids if pid]
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    @staticmethod
    def load_from_json(file_path: str) -> 'NetworkGraph':
        """Static method to load a scenario from a JSON file."""
        graph_manager = NetworkGraph()
        with open(file_path, 'r') as f:
            data = json.load(f)

        for node_data in data.get('nodes', []):
            # We can perform validation or transformation here if needed
            graph_manager.add_node(Node(**node_data))
        
        for edge_data in data.get('edges', []):
            graph_manager.add_edge(Edge(**edge_data))
            
        print(f"DEBUG: Loaded NetworkGraph from {file_path} with {graph_manager.graph.number_of_nodes()} nodes and {graph_manager.graph.number_of_edges()} edges.")
        return graph_manager

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the graph state to a dictionary for API transmission."""
        return {
            "nodes": [node.to_dict() for node in self.get_all_nodes()],
            "edges": [
                {**edge_data['data'].to_dict(), 'source': u, 'target': v} 
                for u, v, edge_data in self.graph.edges(data=True)
            ]
        }
    
    def reset(self):
        """Clears the graph."""
        self.graph.clear()