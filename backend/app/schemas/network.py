# cybersec_project/backend/app/schemas/network.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Set

# These schemas are primarily for API data transfer (requests/responses).
# They might mirror some attributes from the entity classes in backend.entities,
# but are designed for what the API exposes or consumes.

class NodeSchema(BaseModel):
    """
    Pydantic schema for representing a Node in API responses.
    """
    node_id: str = Field(..., description="Unique identifier for the node.")
    node_type: str = Field(..., description="Type of the node (e.g., 'web_server', 'db_server').")
    ip_address: str = Field(..., description="IP address of the node.")
    status: str = Field(default="operational", description="Current operational status of the node.")
    vulnerabilities: List[str] = Field(default_factory=list, description="List of vulnerability IDs present on this node.")
    compromised_by: Optional[str] = Field(default=None, description="ID of the actor that compromised this node, if any.")
    c2_active: bool = Field(default=False, description="True if a Command & Control implant is active on this node.")
    data_value: int = Field(default=0, description="An arbitrary measure of the value of data on this node.")
    security_posture: int = Field(default=5, description="An arbitrary measure of the node's inherent security (1-10).")
    services: List[str] = Field(default_factory=list, description="List of services running on the node (e.g., 'HTTP:80').")
    known_to_actors: List[str] = Field(default_factory=list, description="List of actor IDs that are aware of this node.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Any additional custom data for the node.")

    class Config:
        # Pydantic V2:
        # from_attributes = True
        # Pydantic V1:
        orm_mode = True # Allows easy conversion from ORM objects (or objects with similar attributes)

class EdgeSchema(BaseModel):
    """
    Pydantic schema for representing an Edge in API responses.
    NetworkX edge data often uses 'source' and 'target' for the node IDs.
    """
    # edge_id: str = Field(..., description="Unique identifier for the edge.") # Provided by NetworkX iteration
    source: str = Field(..., description="The ID of the source node of the edge.") # 'source' from NetworkX
    target: str = Field(..., description="The ID of the target node of the edge.") # 'target' from NetworkX
    protocol: Optional[str] = Field(default=None, description="Communication protocol over this edge.")
    port: Optional[int] = Field(default=None, description="Port number associated with the protocol.")
    is_traversable_by_red: bool = Field(default=True, description="Can Red team traverse this edge.")
    is_traversable_by_blue: bool = Field(default=True, description="Can Blue team traverse this edge (e.g., for monitoring).")
    detection_difficulty: int = Field(default=5, description="Difficulty to detect malicious traffic on this edge (1-10).")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Any additional custom data for the edge.")
    # We might also include the original source_node_id and target_node_id from our Edge entity
    # if they differ from NetworkX's u, v iteration (especially for directed graphs)
    edge_id: Optional[str] = Field(default=None, description="Original unique ID of the edge if available.")
    source_node_id: Optional[str] = Field(default=None, description="Original source node ID from Edge entity.")
    target_node_id: Optional[str] = Field(default=None, description="Original target node ID from Edge entity.")


    class Config:
        # Pydantic V2:
        # from_attributes = True
        # Pydantic V1:
        orm_mode = True

class NetworkGraphStateSchema(BaseModel):
    """
    Pydantic schema for representing the entire network graph state.
    This is what would typically be sent to the frontend for visualization.
    """
    nodes: List[NodeSchema] = Field(..., description="List of all nodes in the network.")
    edges: List[EdgeSchema] = Field(..., description="List of all edges connecting the nodes.")
    current_time: int = Field(..., description="Current simulation time step.")
    blocked_ips: List[str] = Field(default_factory=list, description="List of currently blocked IP addresses.")
    global_flags: Dict[str, Any] = Field(default_factory=dict, description="Global flags or states for the simulation scenario.")

    class Config:
        # Pydantic V2:
        # from_attributes = True
        # Pydantic V1:
        orm_mode = True # Helpful if constructing from an object with similar attributes


# --- Example Usage (for ensuring correctness, not for runtime) ---
if __name__ == '__main__':
    print("--- Testing Network Schemas ---")

    # Example Node Data (as if coming from an entity or database)
    node_data_example = {
        "node_id": "web_srv_01",
        "node_type": "web_server",
        "ip_address": "192.168.1.10",
        "status": "compromised",
        "vulnerabilities": ["SQLi_WebApp_Login_001"],
        "compromised_by": "RedTeam_Alpha",
        "c2_active": True,
        "services": ["HTTP:80"],
        "known_to_actors": ["RedTeam_Alpha", "BlueTeam_Delta"],
        "metadata": {"os_version": "Ubuntu 22.04"}
    }
    node_schema_instance = NodeSchema(**node_data_example)
    print("\nNode Schema Instance:")
    print(node_schema_instance.model_dump_json(indent=2) if hasattr(node_schema_instance, 'model_dump_json') else node_schema_instance.json(indent=2)) # V2 vs V1
    assert node_schema_instance.node_id == "web_srv_01"
    assert node_schema_instance.c2_active is True

    # Example Edge Data (as if coming from NetworkX graph.edges(data=True))
    # Note: NetworkX provides (u, v, data_dict)
    # 'source' and 'target' will be u and v
    edge_data_example = {
        "source": "web_srv_01", # This would be 'u' from (u,v,data)
        "target": "db_srv_01",  # This would be 'v' from (u,v,data)
        "edge_id": "edge_uuid_123", # This comes from our Edge entity's data
        "source_node_id": "web_srv_01", # From original Edge entity
        "target_node_id": "db_srv_01", # From original Edge entity
        "protocol": "MySQL",
        "port": 3306,
        "detection_difficulty": 8
    }
    edge_schema_instance = EdgeSchema(**edge_data_example)
    print("\nEdge Schema Instance:")
    print(edge_schema_instance.model_dump_json(indent=2) if hasattr(edge_schema_instance, 'model_dump_json') else edge_schema_instance.json(indent=2))
    assert edge_schema_instance.source == "web_srv_01"
    assert edge_schema_instance.port == 3306

    # Example NetworkGraphState Data
    graph_state_data_example = {
        "nodes": [node_data_example], # List of node data dicts
        "edges": [edge_data_example], # List of edge data dicts
        "current_time": 150,
        "blocked_ips": ["1.2.3.4", "5.6.7.8"]
    }
    # To create NetworkGraphStateSchema, we need to pass lists of NodeSchema/EdgeSchema instances
    # or lists of dicts that Pydantic can coerce.
    graph_state_schema_instance = NetworkGraphStateSchema(
        nodes=[NodeSchema(**node_data_example)],
        edges=[EdgeSchema(**edge_data_example)],
        current_time=150,
        blocked_ips=["1.2.3.4", "5.6.7.8"],
        global_flags={"scenario_difficulty": "Hard"}
    )
    print("\nNetworkGraphState Schema Instance:")
    print(graph_state_schema_instance.model_dump_json(indent=2) if hasattr(graph_state_schema_instance, 'model_dump_json') else graph_state_schema_instance.json(indent=2))
    assert graph_state_schema_instance.current_time == 150
    assert len(graph_state_schema_instance.nodes) == 1
    assert graph_state_schema_instance.nodes[0].status == "compromised"
    assert "1.2.3.4" in graph_state_schema_instance.blocked_ips

    print("\n--- Network Schemas Test Complete ---")