# cybersec_project/backend/scenarios/mvp_scenario.py

from typing import List, Dict, Any

from backend.entities.network_elements import Node, Edge, NetworkGraph
from backend.entities.vulnerabilities import VULN_REGISTRY, Vulnerability # Access to global registry

# For type hinting, not direct import at load time
if False: # TYPE_CHECKING
    from backend.core.state_manager import StateManager # type: ignore

# --- MVP Scenario Definition ---
# This data could also be loaded from JSON/YAML files for more complex scenarios.

MVP_NODES_DATA: List[Dict[str, Any]] = [
    {
        "node_id": "Internet",
        "node_type": "external_source", # A distinct type for the origin of external threats
        "ip_address": "0.0.0.0/0", # Represents the wider internet
        "status": "operational",
        "metadata": {"description": "Represents the public internet, source of external actors."}
    },
    {
        "node_id": "Web_Server_01",
        "node_type": "web_server",
        "ip_address": "172.16.0.10", # Example internal/DMZ IP
        "status": "operational",
        "vulnerabilities": [ # List of vuln_ids present on this node
            "SQLi_WebApp_Login_001", # Assumes this ID is registered in VULN_REGISTRY
            "InfoLeak_WebServer_DirectoryListing_004"
        ],
        "services": ["HTTP:80", "HTTPS:443"],
        "security_posture": 4, # Slightly below average
        "data_value": 10, # Contains some valuable data (e.g., web content, user session info)
        "metadata": {"os": "Linux Ubuntu 20.04", "web_framework": "CustomLegacyPHP"}
    },
    {
        "node_id": "DB_Server_01",
        "node_type": "database_server",
        "ip_address": "10.10.1.5", # Example internal network IP
        "status": "operational",
        "vulnerabilities": [], # Initially, no known vulns or fewer obvious ones
        "services": ["MySQL:3306"],
        "security_posture": 6,
        "data_value": 80, # High value data
        "metadata": {"os": "Linux CentOS 8", "db_version": "MySQL 8.0"}
    },
    {
        "node_id": "BlueTeam_Workstation_01",
        "node_type": "analyst_workstation",
        "ip_address": "192.168.1.100", # Example Blue Team internal segment
        "status": "operational",
        "services": ["SSH:22", "RDP:3389"], # For management access
        "security_posture": 7,
        "metadata": {"os": "Windows 10 Pro", "tools": ["SIEM_Agent", "EDR_Client"]}
    }
    # Future: Add RedTeam_C2_Server, other internal servers, workstations, firewalls, etc.
]

MVP_EDGES_DATA: List[Dict[str, Any]] = [
    {
        "source_node_id": "Internet",
        "target_node_id": "Web_Server_01",
        "protocol": "HTTP/HTTPS",
        "port": None, # Port implied by services on Web_Server_01
        "metadata": {"description": "Public access to web server"}
    },
    {
        "source_node_id": "Web_Server_01",
        "target_node_id": "DB_Server_01",
        "protocol": "MySQL",
        "port": 3306,
        "detection_difficulty": 7, # Harder to spot malicious internal traffic
        "metadata": {"description": "Web server connection to database"}
    },
    {
        "source_node_id": "BlueTeam_Workstation_01",
        "target_node_id": "Web_Server_01",
        "protocol": "SSH/Management", # Abstracted monitoring/management protocol
        "is_traversable_by_red": False, # Red Team shouldn't easily use Blue's management paths
        "metadata": {"description": "Blue Team monitoring/management of Web Server"}
    },
    {
        "source_node_id": "BlueTeam_Workstation_01",
        "target_node_id": "DB_Server_01",
        "protocol": "SSH/Management",
        "is_traversable_by_red": False,
        "metadata": {"description": "Blue Team monitoring/management of DB Server"}
    },
    # Example: Blue Team needs internet for updates/threat intel
    {
        "source_node_id": "BlueTeam_Workstation_01",
        "target_node_id": "Internet", # Assumes some form of outbound internet access
        "protocol": "HTTPS",
        "metadata": {"description": "Blue Team outbound internet access"}
    }
]

MVP_ACTOR_DATA: List[Dict[str, Any]] = [
    {
        "actor_id": "RedTeam_Alpha",
        "team": "Red",
        "description": "Automated Red Team agent focusing on initial access and data exfiltration.",
        "initial_knowledge": ["Internet"], # Knows about the "Internet" node
        "objectives": ["compromise_DB_Server_01", "exfiltrate_data_DB_Server_01"],
        "action_points_per_turn": 10, # Example resource
        "skill_level": 6 # Arbitrary skill
    },
    {
        "actor_id": "BlueTeam_Delta",
        "team": "Blue",
        "description": "Automated Blue Team agent focusing on detection and response.",
        "initial_knowledge": ["Web_Server_01", "DB_Server_01", "BlueTeam_Workstation_01"],
        "objectives": ["prevent_compromise_DB_Server_01", "detect_red_team_activity"],
        "action_points_per_turn": 10,
        "skill_level": 7
    }
]


def load_mvp_scenario(state_manager: 'StateManager') -> None:
    """
    Loads the MVP scenario (nodes, edges, actors) into the provided StateManager.
    It populates the network graph and actor information.

    Args:
        state_manager (StateManager): The simulation state manager to populate.
    """
    print("Loading MVP Scenario...")

    # 1. Clear any existing state (optional, depends on StateManager design)
    # state_manager.reset_state() # Assuming such a method exists

    # 2. Load Nodes
    for node_data in MVP_NODES_DATA:
        node = Node.from_dict(node_data)
        state_manager.network_graph.add_node_object(node)
        # print(f"  Added Node: {node.node_id}")

    # 3. Load Edges
    for edge_data in MVP_EDGES_DATA:
        edge = Edge.from_dict(edge_data)
        state_manager.network_graph.add_edge_object(edge)
        # print(f"  Added Edge: {edge.source_node_id} -> {edge.target_node_id}")

    # 4. Load Actors (StateManager will need a method to add/manage actors)
    for actor_data in MVP_ACTOR_DATA:
        # Assuming StateManager has a method like add_actor or similar
        # For now, we might just store this info in a simple list/dict in StateManager
        # Or, if Actor class exists, instantiate and add:
        # from backend.entities.actor import Actor # Assuming Actor class
        # actor = Actor.from_dict(actor_data)
        # state_manager.add_actor(actor)
        state_manager.register_actor_details(actor_data) # Placeholder for actual actor management
        # print(f"  Registered Actor: {actor_data['actor_id']}")


    # 5. Initialize actor knowledge (which nodes they are aware of initially)
    for actor_data in MVP_ACTOR_DATA:
        actor_id = actor_data["actor_id"]
        for node_id in actor_data.get("initial_knowledge", []):
            state_manager.add_actor_knowledge(node_id, actor_id)

    # 6. Set global simulation parameters if any for this scenario
    # state_manager.set_global_parameter("scenario_name", "MVP_Basic_Attack")

    print(f"MVP Scenario loaded: {len(MVP_NODES_DATA)} nodes, {len(MVP_EDGES_DATA)} edges, {len(MVP_ACTOR_DATA)} actors.")


if __name__ == '__main__':
    # This test requires a mock or simple StateManager and the NetworkGraph from network_elements.
    # It demonstrates how the scenario loading function would be used.
    print("--- MVP Scenario Test ---")

    # Mock StateManager for testing purposes
    class MockStateManager:
        def __init__(self):
            self.network_graph = NetworkGraph()
            self.actors_details: List[Dict[str, Any]] = [] # Simplified actor storage for mock
            self.actor_node_knowledge: Dict[str, set[str]] = {} # actor_id -> set of node_ids
            # Mock the IP blocking mechanism needed by blue_actions BlockIPAddress test
            self.blocked_ips_set: set[str] = set()
            # Mock the random number generator
            import random
            self.rng = random.Random()
            self.rng.seed(42) # for reproducibility

        def register_actor_details(self, actor_data: Dict[str, Any]):
            self.actors_details.append(actor_data)

        def add_actor_knowledge(self, node_id: str, actor_id: str):
            if actor_id not in self.actor_node_knowledge:
                self.actor_node_knowledge[actor_id] = set()
            self.actor_node_knowledge[actor_id].add(node_id)

        def is_ip_blocked(self, ip_address: str) -> bool: # Needed by BlockIPAddress
            return ip_address in self.blocked_ips_set

        def add_blocked_ip(self, ip_address: str): # Needed by BlockIPAddress
            self.blocked_ips_set.add(ip_address)

        def update_node_attribute(self, node_id: str, attribute: str, value: Any): # Needed by Exploit Action
            self.network_graph.update_node_attribute(node_id, attribute, value)


    test_state_manager = MockStateManager()
    load_mvp_scenario(test_state_manager)

    print("\n--- Loaded Network Graph (from MockStateManager) ---")
    if test_state_manager.network_graph:
        print(f"Nodes ({len(test_state_manager.network_graph.get_all_nodes())}):")
        for node in test_state_manager.network_graph.get_all_nodes():
            print(f"  - {node.node_id} ({node.node_type}), Vulns: {node.vulnerabilities}")

        print(f"\nEdges ({len(test_state_manager.network_graph.get_all_edges())}):")
        for edge in test_state_manager.network_graph.get_all_edges():
            print(f"  - {edge.source_node_id} -> {edge.target_node_id} ({edge.protocol})")

    print("\n--- Registered Actors (from MockStateManager) ---")
    if test_state_manager.actors_details:
        for actor in test_state_manager.actors_details:
            print(f"  - ID: {actor['actor_id']}, Team: {actor['team']}, Objectives: {actor.get('objectives', [])}")
            print(f"    Initial Knowledge: {test_state_manager.actor_node_knowledge.get(actor['actor_id'], set())}")


    print("\n--- Verifying Vulnerability Registration ---")
    web_server_node = test_state_manager.network_graph.get_node_object("Web_Server_01")
    if web_server_node:
        print(f"Web Server Vulnerabilities (IDs): {web_server_node.vulnerabilities}")
        for vuln_id in web_server_node.vulnerabilities:
            vuln_detail = VULN_REGISTRY.get_vulnerability(vuln_id)
            if vuln_detail:
                print(f"  -> {vuln_detail.vuln_id}: {vuln_detail.name} ({vuln_detail.severity.value})")
            else:
                print(f"  -> Error: Vulnerability ID '{vuln_id}' not found in registry!")
        assert "SQLi_WebApp_Login_001" in web_server_node.vulnerabilities

    print("\n--- MVP Scenario Test Complete ---")