# cybersec_project/backend/entities/network_elements.py

import networkx as nx
import uuid
from typing import List, Dict, Any, Optional, Set

class Node:
    """
    Represents a single node (e.g., server, workstation, firewall) in the network graph.
    """
    def __init__(self,
                 node_id: str,
                 node_type: str,
                 ip_address: str,
                 status: str = "operational",
                 vulnerabilities: Optional[List[str]] = None,
                 compromised_by: Optional[str] = None, # Actor ID (e.g., "RedTeam")
                 c2_active: bool = False,
                 data_value: int = 0, # Arbitrary value of data on this node
                 security_posture: int = 5, # Arbitrary scale, 1-10 (10 is best)
                 services: Optional[List[str]] = None, # e.g., ["HTTP:80", "SSH:22"]
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Initializes a Node object.

        Args:
            node_id (str): A unique identifier for the node.
            node_type (str): The type of the node (e.g., "web_server", "db_server").
            ip_address (str): The IP address of the node.
            status (str, optional): Current operational status (e.g., "operational", "compromised", "down").
                                     Defaults to "operational".
            vulnerabilities (Optional[List[str]], optional): List of vulnerability IDs present on this node.
                                                              Defaults to None (becomes empty list).
            compromised_by (Optional[str], optional): ID of the actor that compromised this node.
                                                      Defaults to None.
            c2_active (bool, optional): True if a Command & Control implant is active. Defaults to False.
            data_value (int, optional): An arbitrary measure of the value of data on this node. Defaults to 0.
            security_posture (int, optional): An arbitrary measure of the node's inherent security. Defaults to 5.
            services (Optional[List[str]], optional): List of services running on the node. Defaults to None.
            metadata (Optional[Dict[str, Any]], optional): Any additional custom data for the node.
                                                            Defaults to None (becomes empty dict).
        """
        self.node_id: str = node_id
        self.node_type: str = node_type
        self.ip_address: str = ip_address
        self.status: str = status
        self.vulnerabilities: List[str] = vulnerabilities if vulnerabilities is not None else []
        self.compromised_by: Optional[str] = compromised_by
        self.c2_active: bool = c2_active
        self.data_value: int = data_value
        self.security_posture: int = security_posture
        self.services: List[str] = services if services is not None else []
        self.metadata: Dict[str, Any] = metadata if metadata is not None else {}
        self.known_to_actors: Set[str] = set() # Set of actor IDs that are aware of this node

    def __repr__(self) -> str:
        return f"Node(id='{self.node_id}', type='{self.node_type}', ip='{self.ip_address}')"

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the Node object to a dictionary."""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "ip_address": self.ip_address,
            "status": self.status,
            "vulnerabilities": self.vulnerabilities,
            "compromised_by": self.compromised_by,
            "c2_active": self.c2_active,
            "data_value": self.data_value,
            "security_posture": self.security_posture,
            "services": self.services,
            "metadata": self.metadata,
            "known_to_actors": list(self.known_to_actors)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Node':
        """Creates a Node object from a dictionary."""
        node = cls(
            node_id=data["node_id"],
            node_type=data["node_type"],
            ip_address=data["ip_address"],
            status=data.get("status", "operational"),
            vulnerabilities=data.get("vulnerabilities"),
            compromised_by=data.get("compromised_by"),
            c2_active=data.get("c2_active", False),
            data_value=data.get("data_value", 0),
            security_posture=data.get("security_posture", 5),
            services=data.get("services"),
            metadata=data.get("metadata")
        )
        node.known_to_actors = set(data.get("known_to_actors", []))
        return node

class Edge:
    """
    Represents a connection (edge) between two nodes in the network graph.
    """
    def __init__(self,
                 source_node_id: str,
                 target_node_id: str,
                 edge_id: Optional[str] = None,
                 protocol: Optional[str] = None, # e.g., "HTTP", "SSH", "MySQL"
                 port: Optional[int] = None,
                 is_traversable_by_red: bool = True,
                 is_traversable_by_blue: bool = True, # For monitoring/management paths
                 detection_difficulty: int = 5, # How hard to detect traffic on this edge
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Initializes an Edge object.

        Args:
            source_node_id (str): The ID of the source node.
            target_node_id (str): The ID of the target node.
            edge_id (Optional[str], optional): A unique identifier for the edge.
                                               Defaults to a new UUID if None.
            protocol (Optional[str], optional): The communication protocol over this edge. Defaults to None.
            port (Optional[int], optional): The port number associated with the protocol. Defaults to None.
            is_traversable_by_red (bool, optional): Can the Red team traverse this edge (e.g., for lateral movement).
                                                    Defaults to True.
            is_traversable_by_blue (bool, optional): Can the Blue team traverse this edge (e.g., for monitoring).
                                                     Defaults to True.
            detection_difficulty (int, optional): An arbitrary measure of how hard it is to detect malicious traffic.
                                                  Defaults to 5.
            metadata (Optional[Dict[str, Any]], optional): Any additional custom data for the edge.
                                                            Defaults to None (becomes empty dict).
        """
        self.edge_id: str = edge_id if edge_id is not None else str(uuid.uuid4())
        self.source_node_id: str = source_node_id
        self.target_node_id: str = target_node_id
        self.protocol: Optional[str] = protocol
        self.port: Optional[int] = port
        self.is_traversable_by_red: bool = is_traversable_by_red
        self.is_traversable_by_blue: bool = is_traversable_by_blue
        self.detection_difficulty: int = detection_difficulty
        self.metadata: Dict[str, Any] = metadata if metadata is not None else {}

    def __repr__(self) -> str:
        return f"Edge(id='{self.edge_id}', from='{self.source_node_id}', to='{self.target_node_id}')"

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the Edge object to a dictionary."""
        return {
            "edge_id": self.edge_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "protocol": self.protocol,
            "port": self.port,
            "is_traversable_by_red": self.is_traversable_by_red,
            "is_traversable_by_blue": self.is_traversable_by_blue,
            "detection_difficulty": self.detection_difficulty,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Edge':
        """Creates an Edge object from a dictionary."""
        return cls(
            source_node_id=data["source_node_id"],
            target_node_id=data["target_node_id"],
            edge_id=data.get("edge_id"),
            protocol=data.get("protocol"),
            port=data.get("port"),
            is_traversable_by_red=data.get("is_traversable_by_red", True),
            is_traversable_by_blue=data.get("is_traversable_by_blue", True),
            detection_difficulty=data.get("detection_difficulty", 5),
            metadata=data.get("metadata")
        )

class NetworkGraph:
    """
    Manages the network topology using NetworkX, storing custom Node and Edge objects
    as node/edge attributes.
    """
    def __init__(self):
        self.graph: nx.Graph = nx.Graph() # Using an undirected graph for simplicity, can be DiGraph if needed

    def add_node_object(self, node: Node):
        """Adds a Node object to the graph."""
        self.graph.add_node(node.node_id, **node.to_dict())

    def get_node_object(self, node_id: str) -> Optional[Node]:
        """Retrieves a Node object from the graph by its ID."""
        if node_id in self.graph:
            node_data = self.graph.nodes[node_id]
            return Node.from_dict(node_data) # Re-hydrate the object
        return None

    def update_node_attribute(self, node_id: str, attribute: str, value: Any):
        """Updates a specific attribute of a node in the graph."""
        if node_id in self.graph:
            self.graph.nodes[node_id][attribute] = value
        else:
            # Consider logging a warning or raising an error
            print(f"Warning: Node {node_id} not found for attribute update.")

    def add_edge_object(self, edge: Edge):
        """Adds an Edge object to the graph."""
        # Storing edge objects with a unique key, or as data on the edge itself.
        # For simplicity, using NetworkX edge attributes directly.
        self.graph.add_edge(edge.source_node_id, edge.target_node_id, **edge.to_dict())

    def get_edge_object(self, source_node_id: str, target_node_id: str) -> Optional[Edge]:
        """Retrieves an Edge object from the graph by its source and target node IDs."""
        if self.graph.has_edge(source_node_id, target_node_id):
            edge_data = self.graph.edges[source_node_id, target_node_id]
            # Ensure edge_data includes source and target if not already present
            edge_data.setdefault("source_node_id", source_node_id)
            edge_data.setdefault("target_node_id", target_node_id)
            return Edge.from_dict(edge_data)
        return None

    def get_all_nodes(self) -> List[Node]:
        """Returns a list of all Node objects in the graph."""
        return [Node.from_dict(self.graph.nodes[node_id]) for node_id in self.graph.nodes()]

    def get_all_edges(self) -> List[Edge]:
        """Returns a list of all Edge objects in the graph."""
        edges = []
        for u, v, data in self.graph.edges(data=True):
            # Ensure edge_data includes source and target if not already present
            data.setdefault("source_node_id", u)
            data.setdefault("target_node_id", v)
            edges.append(Edge.from_dict(data))
        return edges

    def get_neighbors(self, node_id: str) -> List[Node]:
        """Returns a list of neighbor Node objects for a given node_id."""
        if node_id not in self.graph:
            return []
        neighbor_ids = list(self.graph.neighbors(node_id))
        return [self.get_node_object(nid) for nid in neighbor_ids if self.get_node_object(nid) is not None]

    def to_serializable_dict(self) -> Dict[str, Any]:
        """Converts the graph to a JSON-serializable dictionary representation."""
        nodes_serializable = [node_data for node_id, node_data in self.graph.nodes(data=True)]
        # For edges, NetworkX format is (u, v, data). We need to make sure it's easily serializable.
        edges_serializable = []
        for u, v, data in self.graph.edges(data=True):
            edge_repr = data.copy() # Start with existing attributes
            edge_repr["source"] = u
            edge_repr["target"] = v
            edges_serializable.append(edge_repr)

        return {
            "nodes": nodes_serializable,
            "edges": edges_serializable
        }

    @classmethod
    def from_serializable_dict(cls, data: Dict[str, Any]) -> 'NetworkGraph':
        """Creates a NetworkGraph object from a serializable dictionary."""
        network_graph = cls()
        for node_data in data.get("nodes", []):
            # Node.from_dict creates the Node object, then we add its dict form to graph
            node_obj = Node.from_dict(node_data)
            network_graph.graph.add_node(node_obj.node_id, **node_obj.to_dict())

        for edge_data in data.get("edges", []):
            # Edge.from_dict creates the Edge object, then we add its dict form to graph
            # The dict representation for edges needs 'source' and 'target' keys.
            u = edge_data.get("source") # Or source_node_id if that's the key in your dict
            v = edge_data.get("target") # Or target_node_id
            if u and v:
                # Create edge data by removing source/target, as NetworkX handles them.
                attributes = {k: val for k, val in edge_data.items() if k not in ["source", "target"]}
                network_graph.graph.add_edge(u, v, **attributes)
            else:
                print(f"Warning: Edge data missing source or target: {edge_data}")
        return network_graph

if __name__ == '__main__':
    # Example Usage (for quick testing within this file)
    print("--- Testing Network Elements ---")

    # Create Node objects
    web_server = Node(node_id="web_srv_01", node_type="web_server", ip_address="192.168.1.10", vulnerabilities=["SQLi_WebApp_CVE-2023-1234"], services=["HTTP:80", "HTTPS:443"])
    db_server = Node(node_id="db_srv_01", node_type="db_server", ip_address="10.0.0.5", data_value=100, services=["MySQL:3306"])
    attacker_node = Node(node_id="attacker_pc", node_type="external_attacker", ip_address="5.6.7.8")

    print(web_server)
    print(web_server.to_dict())

    # Create Edge objects
    edge1 = Edge(source_node_id="attacker_pc", target_node_id="web_srv_01", protocol="HTTP", port=80)
    edge2 = Edge(source_node_id="web_srv_01", target_node_id="db_srv_01", protocol="MySQL", port=3306)

    print(edge1)
    print(edge1.to_dict())

    # Create NetworkGraph
    sim_network = NetworkGraph()
    sim_network.add_node_object(web_server)
    sim_network.add_node_object(db_server)
    sim_network.add_node_object(attacker_node)
    sim_network.add_edge_object(edge1)
    sim_network.add_edge_object(edge2)

    print("\n--- Graph Nodes ---")
    for node_obj in sim_network.get_all_nodes():
        print(node_obj.to_dict())

    print("\n--- Graph Edges ---")
    for edge_obj in sim_network.get_all_edges():
        print(edge_obj.to_dict())

    print("\n--- Neighbors of web_srv_01 ---")
    for neighbor in sim_network.get_neighbors("web_srv_01"):
        print(neighbor.to_dict())

    print("\n--- Serializable Graph ---")
    serializable_graph = sim_network.to_serializable_dict()
    import json
    print(json.dumps(serializable_graph, indent=2))

    print("\n--- Graph from Serializable ---")
    rehydrated_network = NetworkGraph.from_serializable_dict(serializable_graph)
    print("Rehydrated nodes count:", len(rehydrated_network.get_all_nodes()))
    print("Rehydrated edges count:", len(rehydrated_network.get_all_edges()))
    assert len(sim_network.get_all_nodes()) == len(rehydrated_network.get_all_nodes())
    assert len(sim_network.get_all_edges()) == len(rehydrated_network.get_all_edges())

    print("\n--- Testing Node Attribute Update ---")
    sim_network.update_node_attribute("web_srv_01", "status", "compromised")
    sim_network.update_node_attribute("web_srv_01", "compromised_by", "RedTeam_Alpha")
    updated_web_server_obj = sim_network.get_node_object("web_srv_01")
    if updated_web_server_obj:
        print(updated_web_server_obj.to_dict())

    print("--- Network Elements Test Complete ---")