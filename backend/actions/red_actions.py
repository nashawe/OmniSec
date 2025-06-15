# cybersec_project/backend/actions/red_actions.py

from typing import List, Dict, Any, Optional, Tuple

from backend.actions.base_action import SimulationAction
from backend.entities.vulnerabilities import VULN_REGISTRY # Access to predefined vulnerabilities

# Type hinting for StateManager and SimulationEvent to avoid circular imports at module load time
# Actual import will happen where needed, or type checking tools will understand this.
if False: # TYPE_CHECKING
    from backend.core.state_manager import StateManager # type: ignore
    from backend.core.event_manager import SimulationEvent # type: ignore


class ExploitPublicFacingApplication(SimulationAction):
    """
    Red Team action to exploit a known vulnerability on an internet-facing application
    to gain initial access.
    """
    def __init__(self,
                 target_vulnerability_id: str, # e.g., "SQLi_WebApp_Login_001"
                 action_id: Optional[str] = None,
                 name: str = "Exploit Public Facing Application",
                 description: str = "Attempts to exploit a specific vulnerability on a public-facing application.",
                 cost_time_units: int = 3,
                 cost_action_points: int = 5,
                 base_success_probability: float = 0.7, # Base chance, can be modified
                 mitre_attack_id: str = "T1190" # Default to general T1190
                 ):
        """
        Initializes the ExploitPublicFacingApplication action.

        Args:
            target_vulnerability_id (str): The specific vuln_id (from VulnerabilityRegistry)
                                           that this exploit targets.
            action_id (Optional[str], optional): Unique ID for this action instance. Defaults to None.
            name (str, optional): Name of the action.
            description (str, optional): Description of the action.
            cost_time_units (int, optional): Time units this action takes.
            cost_action_points (int, optional): Action points this action costs.
            base_success_probability (float, optional): Base success chance.
            mitre_attack_id (str, optional): Associated MITRE ATT&CK ID.
        """
        super().__init__(
            action_id=action_id,
            name=name,
            description=description,
            team="Red", # This is a Red Team action
            cost_time_units=cost_time_units,
            cost_action_points=cost_action_points,
            success_probability=base_success_probability,
            mitre_attack_id=mitre_attack_id,
            mitre_d3fend_id=None # Red Team actions typically don't have D3FEND IDs
        )
        self.target_vulnerability_id: str = target_vulnerability_id
        self.vulnerability_details = VULN_REGISTRY.get_vulnerability(target_vulnerability_id)
        if self.vulnerability_details:
            # If a more specific MITRE ID is on the vulnerability, use it
            if self.vulnerability_details.mitre_attack_ids:
                self.mitre_attack_id = self.vulnerability_details.mitre_attack_ids[0] # Take the first one for now

    def check_prerequisites(self, state_manager: 'StateManager', target_node_id: Optional[str] = None, source_node_id: Optional[str] = None, actor_id: Optional[str] = None) -> bool:
        """
        Checks if the target node is public-facing, operational, and has the specific vulnerability.
        """
        if not super().check_prerequisites(state_manager, target_node_id, source_node_id, actor_id):
            return False # Basic checks from parent failed

        if not target_node_id:
            return False # This action requires a target

        target_node = state_manager.network_graph.get_node_object(target_node_id)
        if not target_node:
            return False # Target node doesn't exist

        # Check 1: Is the node operational?
        if target_node.status != "operational":
            return False

        # Check 2: Does the node have the target vulnerability?
        # Node vulnerabilities are stored as a list of vuln_ids
        if self.target_vulnerability_id not in target_node.vulnerabilities:
            return False

        # Check 3: Is the node public-facing? (Assumed if source_node_id is "Internet" or None)
        # A more robust check might involve checking connectivity from an "Internet" node.
        # For this MVP, if source_node_id is not provided, we assume it's from the internet.
        if source_node_id and source_node_id != "Internet":
            # If attack is from an internal node, this isn't "public-facing exploit" in the same way.
            # This logic can be refined. For now, allow if source is specified and connected.
            if not state_manager.network_graph.graph.has_edge(source_node_id, target_node_id):
                return False # No direct path from internal source
        elif not source_node_id: # Implies attack from "Internet"
            if not state_manager.network_graph.graph.has_edge("Internet", target_node_id):
                 # Or check a "publicly_accessible" flag on the node, if we model an explicit "Internet" node.
                 # For now, this check assumes an "Internet" node must be defined in the scenario.
                return False


        return True

    def calculate_success_chance(self, state_manager: 'StateManager', target_node_id: Optional[str] = None, source_node_id: Optional[str] = None, actor_id: Optional[str] = None) -> float:
        """
        Calculates success probability based on base chance, vulnerability exploit difficulty,
        and target node's security posture.
        """
        if not target_node_id:
            return 0.0

        target_node = state_manager.network_graph.get_node_object(target_node_id)
        if not target_node or not self.vulnerability_details:
            return 0.0 # Cannot exploit if target or vuln details are missing

        # Start with base probability
        current_prob = self.base_success_probability

        # Factor in vulnerability exploit difficulty (lower is easier to exploit)
        # Assuming exploit_difficulty is 1-10 (1 very easy, 10 very hard)
        # We want to *increase* prob for low difficulty, *decrease* for high.
        # This is a simple linear model, can be made more sophisticated.
        difficulty_modifier = (5.5 - self.vulnerability_details.exploit_difficulty) / 10.0 # Range from +0.45 to -0.45
        current_prob += difficulty_modifier

        # Factor in target node's security posture (higher is more secure)
        # Assuming security_posture is 1-10 (1 very insecure, 10 very secure)
        # We want to *decrease* prob for high posture, *increase* for low.
        posture_modifier = (5.5 - target_node.security_posture) / 20.0 # Smaller impact than exploit difficulty
        current_prob += posture_modifier
        
        # TODO: Factor in actor's skill level if we model that
        # TODO: Factor in active Blue Team defenses (e.g., WAF, IDS) reducing success chance

        # Ensure probability is within [0, 1]
        return max(0.0, min(1.0, current_prob))

    def execute(self,
                state_manager: 'StateManager',
                current_time: int,
                target_node_id: Optional[str] = None,
                source_node_id: Optional[str] = None, # Typically "Internet" or None for initial access
                actor_id: Optional[str] = "RedTeam_Default", # Default actor if not specified
                **kwargs: Any) -> Tuple[List['SimulationEvent'], List[Dict[str, Any]], List[str]]:
        """
        Executes the exploit attempt.
        If successful, marks the target node as compromised by the Red Team.
        """
        new_events: List['SimulationEvent'] = []
        state_changes: List[Dict[str, Any]] = []
        log_messages: List[str] = []

        if not target_node_id:
            log_messages.append(f"{current_time}: [{actor_id}] {self.name} failed: No target node specified.")
            return new_events, state_changes, log_messages

        if not self.check_prerequisites(state_manager, target_node_id, source_node_id, actor_id):
            log_messages.append(f"{current_time}: [{actor_id}] {self.name} on {target_node_id} failed: Prerequisites not met.")
            return new_events, state_changes, log_messages

        success_chance = self.calculate_success_chance(state_manager, target_node_id, source_node_id, actor_id)
        
        # Use the centralized random number generator from state_manager for reproducibility
        if state_manager.rng.random() < success_chance:
            # --- Action Successful ---
            log_messages.append(f"{current_time}: [{actor_id}] SUCCESS: {self.name} on {target_node_id} (vuln: {self.target_vulnerability_id}). Success chance: {success_chance:.2f}.")
            
            # Update target node state
            state_manager.update_node_attribute(target_node_id, "compromised_by", self.team)
            state_manager.update_node_attribute(target_node_id, "status", "compromised")
            state_changes.append({"type": "node_attribute_change", "node_id": target_node_id, "attribute": "compromised_by", "value": self.team})
            state_changes.append({"type": "node_attribute_change", "node_id": target_node_id, "attribute": "status", "value": "compromised"})

            # Red Team now "knows" about this node if they didn't before
            state_manager.add_actor_knowledge(target_node_id, self.team) # self.team is "Red"
            state_changes.append({"type": "actor_knowledge_add", "node_id": target_node_id, "actor_id": self.team})


            # Potentially schedule follow-up events (e.g., C2 beaconing, data staging)
            # Example: Schedule a "ScanLocalNetwork" action from the compromised host
            # from backend.core.event_manager import SimulationEvent # Import here if needed
            # scan_action = ScanLocalNetwork(source_node_id=target_node_id)
            # scan_event = SimulationEvent(
            #     timestamp=current_time + scan_action.cost_time_units, # Occurs after this action completes
            #     event_type="PerformAction",
            #     actor_id=actor_id,
            #     action=scan_action, # The action object itself
            #     target_node_id=None, # Scan doesn't have a single target node
            #     source_node_id=target_node_id # Scan originates from the compromised node
            # )
            # new_events.append(scan_event)
            # log_messages.append(f"{current_time}: [{actor_id}] Scheduled: ScanLocalNetwork from {target_node_id} at {scan_event.timestamp}.")

        else:
            # --- Action Failed ---
            log_messages.append(f"{current_time}: [{actor_id}] FAILED: {self.name} on {target_node_id} (vuln: {self.target_vulnerability_id}). Success chance: {success_chance:.2f}.")
            # Potentially, a failed attempt could still be detected by Blue Team.
            # This could schedule a "BlueTeamDetection" event.

        return new_events, state_changes, log_messages


# --- Other Red Team actions would be defined below ---
# Example:
# class ScanLocalNetwork(SimulationAction): ...
# class LateralMovementRDP(SimulationAction): ...
# class ExfiltrateData(SimulationAction): ...

if __name__ == '__main__':
    # This section is for basic testing of this file's classes.
    # Full integration testing requires the StateManager, EventManager, etc.
    print("--- Red Actions Test ---")

    # We need a mock StateManager and Node for realistic testing
    # For now, just instantiate the action to check constructor
    exploit_action = ExploitPublicFacingApplication(target_vulnerability_id="SQLi_WebApp_Login_001")
    print(f"Created Action: {exploit_action}")
    print(f"  Description: {exploit_action.description}")
    print(f"  Target Vuln ID: {exploit_action.target_vulnerability_id}")
    print(f"  MITRE ID: {exploit_action.mitre_attack_id}")
    if exploit_action.vulnerability_details:
        print(f"  Target Vuln Name: {exploit_action.vulnerability_details.name}")
        print(f"  Target Vuln Exploit Difficulty: {exploit_action.vulnerability_details.exploit_difficulty}")


    # A more involved test would look like this (pseudo-code, needs imports and mocks):
    # from backend.core.state_manager import StateManager
    # from backend.entities.network_elements import Node
    # from backend.scenarios.mvp_scenario import load_mvp_network_into_state # Assuming this function exists
    #
    # mock_state = StateManager()
    # load_mvp_network_into_state(mock_state) # This would populate mock_state.network_graph
    # mock_state.network_graph.add_node("Internet", type="internet") # Ensure Internet node exists
    # mock_state.network_graph.add_edge("Internet", "web_srv_01") # Ensure connectivity for prerequisite check
    #
    # # Ensure the web_srv_01 in your mvp_scenario.py has "SQLi_WebApp_Login_001" vulnerability
    # if mock_state.network_graph.get_node_object("web_srv_01"):
    #     if "SQLi_WebApp_Login_001" not in mock_state.network_graph.get_node_object("web_srv_01").vulnerabilities:
    #           mock_state.network_graph.get_node_object("web_srv_01").vulnerabilities.append("SQLi_WebApp_Login_001")


    # print("\n--- Testing Prerequisite Check (Illustrative - requires StateManager) ---")
    # if mock_state: # Check if mock_state was successfully initialized
    #     prereqs_met = exploit_action.check_prerequisites(mock_state, target_node_id="web_srv_01", source_node_id="Internet")
    #     print(f"Prerequisites met for web_srv_01 from Internet: {prereqs_met}")

    # print("\n--- Testing Success Chance Calculation (Illustrative - requires StateManager) ---")
    # if mock_state and mock_state.network_graph.get_node_object("web_srv_01"): # Check if node exists
    #     success_c = exploit_action.calculate_success_chance(mock_state, target_node_id="web_srv_01")
    #     print(f"Calculated success chance for web_srv_01: {success_c:.2f}")

    # print("\n--- Testing Execution (Illustrative - requires StateManager) ---")
    # if mock_state:
    #     events, changes, logs = exploit_action.execute(mock_state, current_time=10, target_node_id="web_srv_01", source_node_id="Internet", actor_id="TestRedAgent")
    #     print("Execution Logs:")
    #     for log in logs:
    #         print(f"  - {log}")
    #     print("Generated Events:", events)
    #     print("State Changes:", changes)
    #     # Check the node state
    #     web_node_after_exploit = mock_state.network_graph.get_node_object("web_srv_01")
    #     if web_node_after_exploit:
    #         print(f"web_srv_01 status after exploit attempt: {web_node_after_exploit.status}, compromised_by: {web_node_after_exploit.compromised_by}")

    print("\nRed Actions structure seems OK.")