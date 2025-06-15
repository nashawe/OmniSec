# cybersec_project/backend/core/state_manager.py

from typing import List, Dict, Any, Optional, Set
import random # For the rng attribute

from backend.entities.network_elements import NetworkGraph, Node, Edge
from backend.core.random_seed import get_rng, initialize_rng # For simulation's RNG

class StateManager:
    """
    Manages the overall state of the simulation.
    This includes the network topology, node/edge attributes, actor states,
    global parameters (like blocked IPs), and the random number generator.
    It provides an interface for actions and the simulation engine to query
    and modify the current state.
    """
    def __init__(self, seed: Optional[int] = None):
        """
        Initializes the StateManager.

        Args:
            seed (Optional[int], optional): Seed for the random number generator
                                            to ensure deterministic simulation runs.
                                            If None, a default seed will be used.
        """
        # Initialize the global RNG for the simulation session
        initialize_rng(seed)
        self.rng: random.Random = get_rng() # Get the seeded RNG instance

        self.network_graph: NetworkGraph = NetworkGraph()
        
        # Actor-specific information
        self.actors_data: Dict[str, Dict[str, Any]] = {} # actor_id -> actor_properties_dict
        self.actor_node_knowledge: Dict[str, Set[str]] = {} # actor_id -> set of known node_ids
        self.actor_action_points: Dict[str, int] = {} # actor_id -> current action points

        # Global simulation parameters
        self.current_time: int = 0
        self.blocked_ips: Set[str] = set()
        self.global_flags: Dict[str, Any] = {} # For scenario-specific global states
        
        self.simulation_log: List[str] = [] # A simple log of major events or messages

        print(f"StateManager initialized with RNG seed: {seed if seed is not None else 'default'}")

    def reset_state(self, seed: Optional[int] = None) -> None:
        """
        Resets the entire simulation state to its initial conditions,
        optionally re-seeding the RNG.

        Args:
            seed (Optional[int], optional): New seed for the RNG. If None,
                                            the RNG is re-initialized with its
                                            previous seed or default.
        """
        if seed is not None:
            initialize_rng(seed)
        else:
            # Re-initialize with the current seed if it exists, or default
            current_rng_seed = self.rng.getstate()[1][0] if hasattr(self.rng, 'getstate') else None # A bit hacky to get seed
            initialize_rng(current_rng_seed) # Re-seed or use default

        self.rng = get_rng() # Get the potentially re-seeded RNG instance

        self.network_graph = NetworkGraph()
        self.actors_data.clear()
        self.actor_node_knowledge.clear()
        self.actor_action_points.clear()
        self.current_time = 0
        self.blocked_ips.clear()
        self.global_flags.clear()
        self.simulation_log.clear()
        print(f"StateManager reset. RNG re-initialized with seed: {seed if seed is not None else 'previous/default'}")

    # --- Network Graph Methods (delegates or wraps NetworkGraph) ---
    def get_node(self, node_id: str) -> Optional[Node]:
        """Retrieves a Node object by its ID."""
        return self.network_graph.get_node_object(node_id)

    def update_node_attribute(self, node_id: str, attribute: str, value: Any) -> None:
        """Updates a specific attribute of a node."""
        # This also logs the change.
        # old_value = self.network_graph.nodes[node_id].get(attribute) if node_id in self.network_graph.graph else None
        self.network_graph.update_node_attribute(node_id, attribute, value)
        # self.log_state_change("node_attribute_update", {"node_id": node_id, "attribute": attribute, "old_value": old_value, "new_value": value})


    # --- Actor Management Methods ---
    def register_actor_details(self, actor_data: Dict[str, Any]) -> None:
        """
        Registers initial details for an actor.

        Args:
            actor_data (Dict[str, Any]): Dictionary containing actor properties
                                         (e.g., actor_id, team, objectives).
        """
        actor_id = actor_data.get("actor_id")
        if actor_id:
            self.actors_data[actor_id] = actor_data
            # Initialize action points if specified, otherwise default
            self.actor_action_points[actor_id] = actor_data.get("action_points_per_turn", 10)
            self.simulation_log.append(f"Time {self.current_time}: Actor '{actor_id}' registered.")
        else:
            self.simulation_log.append(f"Time {self.current_time}: Warning - Attempted to register actor without ID.")


    def get_actor_details(self, actor_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the registered details for an actor."""
        return self.actors_data.get(actor_id)

    def add_actor_knowledge(self, node_id: str, actor_id: str) -> None:
        """Adds a node to an actor's set of known nodes."""
        if actor_id not in self.actor_node_knowledge:
            self.actor_node_knowledge[actor_id] = set()
        
        if node_id not in self.actor_node_knowledge[actor_id]:
            self.actor_node_knowledge[actor_id].add(node_id)
            # self.log_state_change("actor_knowledge_add", {"actor_id": actor_id, "node_id": node_id})


    def actor_knows_node(self, actor_id: str, node_id: str) -> bool:
        """Checks if an actor knows about a specific node."""
        return node_id in self.actor_node_knowledge.get(actor_id, set())

    def get_actor_action_points(self, actor_id: str) -> int:
        """Gets the current action points for an actor."""
        return self.actor_action_points.get(actor_id, 0)

    def spend_actor_action_points(self, actor_id: str, points: int) -> bool:
        """
        Deducts action points from an actor. Returns True if successful,
        False if insufficient points.
        """
        if self.actor_action_points.get(actor_id, 0) >= points:
            self.actor_action_points[actor_id] -= points
            # self.log_state_change("actor_ap_spend", {"actor_id": actor_id, "points_spent": points, "remaining_ap": self.actor_action_points[actor_id]})
            return True
        return False

    def reset_actor_action_points(self, actor_id: str, default_points: Optional[int] = None) -> None:
        """Resets an actor's action points, e.g., at the start of a new 'turn' or time period."""
        if default_points is not None:
            self.actor_action_points[actor_id] = default_points
        else:
            # Reset to their initial/default if stored in actors_data
            actor_data = self.actors_data.get(actor_id)
            if actor_data:
                self.actor_action_points[actor_id] = actor_data.get("action_points_per_turn", 10)
            else: # Fallback if actor data somehow missing
                self.actor_action_points[actor_id] = 10
        # self.log_state_change("actor_ap_reset", {"actor_id": actor_id, "new_ap_total": self.actor_action_points[actor_id]})


    # --- Global Parameter Methods ---
    def add_blocked_ip(self, ip_address: str) -> None:
        """Adds an IP address to the global blocklist."""
        if ip_address not in self.blocked_ips:
            self.blocked_ips.add(ip_address)
            # self.log_state_change("ip_block_add", {"ip_address": ip_address})

    def remove_blocked_ip(self, ip_address: str) -> None:
        """Removes an IP address from the global blocklist."""
        if ip_address in self.blocked_ips:
            self.blocked_ips.discard(ip_address)
            # self.log_state_change("ip_block_remove", {"ip_address": ip_address})

    def is_ip_blocked(self, ip_address: str) -> bool:
        """Checks if an IP address is currently blocked."""
        return ip_address in self.blocked_ips

    def set_global_flag(self, flag_name: str, value: Any) -> None:
        """Sets a global simulation flag."""
        self.global_flags[flag_name] = value
        # self.log_state_change("global_flag_set", {"flag_name": flag_name, "value": value})

    def get_global_flag(self, flag_name: str, default: Optional[Any] = None) -> Any:
        """Gets a global simulation flag."""
        return self.global_flags.get(flag_name, default)

    # --- Logging and State Change Tracking ---
    def log_message(self, message: str):
        """Adds a message to the simulation log."""
        self.simulation_log.append(f"Time {self.current_time}: {message}")

    # def log_state_change(self, change_type: str, change_data: Dict[str, Any]):
    #     """
    #     A more structured way to log state changes.
    #     This can be used by HistoryManager later.
    #     """
    #     # For now, just add to simple log, can be expanded for HistoryManager
    #     self.simulation_log.append(f"Time {self.current_time}: StateChange - {change_type}: {change_data}")


# --- Example Usage and Testing ---
if __name__ == '__main__':
    from backend.scenarios.mvp_scenario import load_mvp_scenario # For testing scenario loading

    print("--- Testing State Manager ---")

    # Test 1: Initialization and RNG
    state_mgr = StateManager(seed=12345)
    print(f"Initialized with seed: {state_mgr.rng.getstate()[1][0] if hasattr(state_mgr.rng, 'getstate') else 'N/A'}") # Check seed
    initial_random_num = state_mgr.rng.random()
    print(f"First random number: {initial_random_num}")

    state_mgr_default_seed = StateManager() # Uses default seed from random_seed.py
    print(f"Initialized with default seed: {state_mgr_default_seed.rng.getstate()[1][0] if hasattr(state_mgr_default_seed.rng, 'getstate') else 'N/A'}")


    # Test 2: Loading a scenario
    print("\nLoading MVP scenario into StateManager...")
    load_mvp_scenario(state_mgr) # This populates network_graph and actors_data

    web_server = state_mgr.get_node("Web_Server_01")
    if web_server:
        print(f"Web Server found: {web_server.node_id}, IP: {web_server.ip_address}")
        assert web_server.ip_address == "172.16.0.10"
    else:
        print("Error: Web_Server_01 not found after loading scenario.")

    red_team_details = state_mgr.get_actor_details("RedTeam_Alpha")
    if red_team_details:
        print(f"Red Team actor found: {red_team_details['actor_id']}, Team: {red_team_details['team']}")
        assert red_team_details['team'] == "Red"
    else:
        print("Error: RedTeam_Alpha actor not found.")

    # Test 3: Node attribute update
    print("\nUpdating Web_Server_01 status...")
    state_mgr.update_node_attribute("Web_Server_01", "status", "compromised")
    state_mgr.update_node_attribute("Web_Server_01", "compromised_by", "RedTeam_Alpha")
    updated_web_server = state_mgr.get_node("Web_Server_01")
    if updated_web_server:
        print(f"Web Server new status: {updated_web_server.status}, Compromised by: {updated_web_server.compromised_by}")
        assert updated_web_server.status == "compromised"
        assert updated_web_server.compromised_by == "RedTeam_Alpha"

    # Test 4: Actor knowledge
    print("\nTesting actor knowledge...")
    state_mgr.add_actor_knowledge("Web_Server_01", "RedTeam_Alpha")
    state_mgr.add_actor_knowledge("DB_Server_01", "RedTeam_Alpha") # Red team discovers DB
    print(f"Does RedTeam_Alpha know Web_Server_01? {state_mgr.actor_knows_node('RedTeam_Alpha', 'Web_Server_01')}")
    print(f"Does RedTeam_Alpha know DB_Server_01? {state_mgr.actor_knows_node('RedTeam_Alpha', 'DB_Server_01')}")
    print(f"Does RedTeam_Alpha know BlueTeam_Workstation_01? {state_mgr.actor_knows_node('RedTeam_Alpha', 'BlueTeam_Workstation_01')}")
    assert state_mgr.actor_knows_node('RedTeam_Alpha', 'Web_Server_01')
    assert not state_mgr.actor_knows_node('RedTeam_Alpha', 'BlueTeam_Workstation_01') # Assuming not in initial knowledge

    # Test 5: IP Blocking
    print("\nTesting IP blocking...")
    attacker_ip = "1.2.3.4"
    print(f"Is {attacker_ip} blocked initially? {state_mgr.is_ip_blocked(attacker_ip)}")
    state_mgr.add_blocked_ip(attacker_ip)
    print(f"Is {attacker_ip} blocked now? {state_mgr.is_ip_blocked(attacker_ip)}")
    assert state_mgr.is_ip_blocked(attacker_ip)
    state_mgr.remove_blocked_ip(attacker_ip)
    print(f"Is {attacker_ip} blocked after removal? {state_mgr.is_ip_blocked(attacker_ip)}")
    assert not state_mgr.is_ip_blocked(attacker_ip)

    # Test 6: Action Points
    print("\nTesting Actor Action Points...")
    rt_ap = state_mgr.get_actor_action_points("RedTeam_Alpha")
    print(f"RedTeam_Alpha initial AP: {rt_ap}") # Should be 10 from mvp_scenario
    assert rt_ap == 10
    can_spend_5 = state_mgr.spend_actor_action_points("RedTeam_Alpha", 5)
    print(f"Spent 5 AP: {can_spend_5}, Remaining AP: {state_mgr.get_actor_action_points('RedTeam_Alpha')}")
    assert can_spend_5 and state_mgr.get_actor_action_points('RedTeam_Alpha') == 5
    can_spend_10 = state_mgr.spend_actor_action_points("RedTeam_Alpha", 10) # Should fail
    print(f"Spent 10 AP: {can_spend_10}, Remaining AP: {state_mgr.get_actor_action_points('RedTeam_Alpha')}")
    assert not can_spend_10 and state_mgr.get_actor_action_points('RedTeam_Alpha') == 5
    state_mgr.reset_actor_action_points("RedTeam_Alpha")
    print(f"AP after reset: {state_mgr.get_actor_action_points('RedTeam_Alpha')}")
    assert state_mgr.get_actor_action_points('RedTeam_Alpha') == 10


    # Test 7: Reset state
    print("\nResetting state with a new seed...")
    state_mgr.reset_state(seed=999)
    assert state_mgr.current_time == 0
    assert len(state_mgr.network_graph.get_all_nodes()) == 0
    assert not state_mgr.blocked_ips
    new_random_num = state_mgr.rng.random()
    print(f"First random number after reset with new seed: {new_random_num}")
    assert new_random_num != initial_random_num # Should be different with a different seed


    print("\n--- State Manager Test Complete ---")