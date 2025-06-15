# cybersec_project/backend/actions/blue_actions.py

from typing import List, Dict, Any, Optional, Tuple

from backend.actions.base_action import SimulationAction
# No direct dependency on VulnerabilityRegistry for this specific action,
# but other Blue Team actions like "PatchVulnerability" would need it.

# Type hinting for StateManager and SimulationEvent
if False: # TYPE_CHECKING
    from backend.core.state_manager import StateManager # type: ignore
    from backend.core.event_manager import SimulationEvent # type: ignore

class BlockIPAddress(SimulationAction):
    """
    Blue Team action to block a specified IP address, typically at a network perimeter
    or on a host-based firewall.
    """
    def __init__(self,
                 ip_to_block: str, # The IP address that needs to be blocked
                 action_id: Optional[str] = None,
                 name: str = "Block IP Address",
                 description: str = "Blocks incoming/outgoing traffic from/to a specified IP address.",
                 cost_time_units: int = 1, # Relatively quick action
                 cost_action_points: int = 2,
                 base_success_probability: float = 0.95, # Usually quite effective if IP is known
                 mitre_d3fend_id: str = "D3-IPBA" # IP Blocklist Artifact
                 ):
        """
        Initializes the BlockIPAddress action.

        Args:
            ip_to_block (str): The IP address to be blocked.
            action_id (Optional[str], optional): Unique ID for this action instance.
            name (str, optional): Name of the action.
            description (str, optional): Description of the action.
            cost_time_units (int, optional): Time units this action takes.
            cost_action_points (int, optional): Action points this action costs.
            base_success_probability (float, optional): Base success chance.
            mitre_d3fend_id (str, optional): Associated MITRE D3FEND ID.
        """
        super().__init__(
            action_id=action_id,
            name=name,
            description=description,
            team="Blue", # This is a Blue Team action
            cost_time_units=cost_time_units,
            cost_action_points=cost_action_points,
            success_probability=base_success_probability,
            mitre_d3fend_id=mitre_d3fend_id
        )
        self.ip_to_block: str = ip_to_block

    def check_prerequisites(self, state_manager: 'StateManager', target_node_id: Optional[str] = None, source_node_id: Optional[str] = None, actor_id: Optional[str] = None) -> bool:
        """
        Checks if the action can be performed.
        For blocking an IP, prerequisites are usually minimal, assuming the Blue Team
        has the capability (e.g., access to a firewall).
        """
        if not super().check_prerequisites(state_manager, target_node_id, source_node_id, actor_id):
            return False

        if not self.ip_to_block: # Must have an IP to block
            return False

        # In a more complex model, we might check if the `actor_id` (Blue Team agent)
        # has control over a firewall or the necessary privileges.
        # For now, we assume capability if the action is chosen.
        return True

    def calculate_success_chance(self, state_manager: 'StateManager', target_node_id: Optional[str] = None, source_node_id: Optional[str] = None, actor_id: Optional[str] = None) -> float:
        """
        Calculates success probability. Blocking an IP is usually deterministic if the capability exists.
        However, we can model things like misconfigurations or attacker evasion.
        """
        current_prob = self.base_success_probability

        # Example: If Red Team is using a sophisticated proxy network, blocking one IP might be less effective.
        # This would require more state about the attacker's infrastructure.
        # For now, we keep it simple.

        # TODO: Factor in Blue Team's tool capabilities or Red Team's evasion tactics.
        return max(0.0, min(1.0, current_prob))

    def execute(self,
                state_manager: 'StateManager',
                current_time: int,
                target_node_id: Optional[str] = None, # Not directly used, IP is global
                source_node_id: Optional[str] = None, # Typically the Blue Team's workstation/system
                actor_id: Optional[str] = "BlueTeam_Default",
                **kwargs: Any) -> Tuple[List['SimulationEvent'], List[Dict[str, Any]], List[str]]:
        """
        Executes the IP blocking action.
        Adds the specified IP to a global or perimeter blocklist within the simulation state.
        """
        new_events: List['SimulationEvent'] = []
        state_changes: List[Dict[str, Any]] = []
        log_messages: List[str] = []

        if not self.check_prerequisites(state_manager, target_node_id, source_node_id, actor_id):
            log_messages.append(f"{current_time}: [{actor_id}] {self.name} for IP {self.ip_to_block} failed: Prerequisites not met.")
            return new_events, state_changes, log_messages

        success_chance = self.calculate_success_chance(state_manager, target_node_id, source_node_id, actor_id)

        if state_manager.rng.random() < success_chance:
            # --- Action Successful ---
            # The StateManager should have a way to manage blocked IPs.
            # This could be a set of strings: state_manager.blocked_ips
            already_blocked = state_manager.is_ip_blocked(self.ip_to_block)
            state_manager.add_blocked_ip(self.ip_to_block)
            
            if not already_blocked:
                log_messages.append(f"{current_time}: [{actor_id}] SUCCESS: {self.name} - IP {self.ip_to_block} has been blocked. Success chance: {success_chance:.2f}.")
                state_changes.append({"type": "ip_block_add", "ip_address": self.ip_to_block})
            else:
                log_messages.append(f"{current_time}: [{actor_id}] INFO: {self.name} - IP {self.ip_to_block} was already blocked.")

            # This action might trigger other events, e.g., logging the block,
            # or Red Team detecting the block and attempting to change IP.
            # For now, it's a direct state change.

        else:
            # --- Action Failed ---
            log_messages.append(f"{current_time}: [{actor_id}] FAILED: {self.name} - Could not block IP {self.ip_to_block}. Success chance: {success_chance:.2f}.")
            # Failure could be due to various reasons in a more complex model
            # (e.g., firewall misconfiguration, lack of privileges).

        return new_events, state_changes, log_messages


# --- Other Blue Team actions would be defined below ---
# Example:
# class PatchVulnerability(SimulationAction): ...
# class IsolateHost(SimulationAction): ...
# class AnalyzeLogs(SimulationAction): ...

if __name__ == '__main__':
    print("--- Blue Actions Test ---")

    # Instantiate the action to check constructor
    block_action = BlockIPAddress(ip_to_block="123.45.67.89")
    print(f"Created Action: {block_action}")
    print(f"  Description: {block_action.description}")
    print(f"  IP to Block: {block_action.ip_to_block}")
    print(f"  MITRE D3FEND ID: {block_action.mitre_d3fend_id}")

    # More involved testing requires a mock StateManager.
    # Illustrative pseudo-code for testing execute:
    # from backend.core.state_manager import StateManager # Assuming StateManager has manage_blocked_ips
    #
    # mock_state_blue = StateManager() # This StateManager needs `add_blocked_ip` and `is_ip_blocked`
    #
    # # Setup mock StateManager for IP blocking
    # if not hasattr(mock_state_blue, 'blocked_ips_set'): # Simple way to add if not present
    #    mock_state_blue.blocked_ips_set = set()
    # def add_blocked_ip_mock(ip):
    #    mock_state_blue.blocked_ips_set.add(ip)
    # def is_ip_blocked_mock(ip):
    #    return ip in mock_state_blue.blocked_ips_set
    # mock_state_blue.add_blocked_ip = add_blocked_ip_mock
    # mock_state_blue.is_ip_blocked = is_ip_blocked_mock
    #
    # print("\n--- Testing Execution (Illustrative - requires StateManager with IP blocking logic) ---")
    # if hasattr(mock_state_blue, 'add_blocked_ip'): # Check if our mock setup is complete
    #     events_b, changes_b, logs_b = block_action.execute(mock_state_blue, current_time=15, actor_id="BlueTeamAnalyst")
    #     print("Execution Logs:")
    #     for log_item in logs_b:
    #         print(f"  - {log_item}")
    #     print("Generated Events:", events_b)
    #     print("State Changes:", changes_b)
    #     print(f"Blocked IPs in mock state: {mock_state_blue.blocked_ips_set}")
    #
    #     # Test blocking an already blocked IP
    #     events_b2, changes_b2, logs_b2 = block_action.execute(mock_state_blue, current_time=20, actor_id="BlueTeamAnalyst")
    #     print("\nExecution Logs (attempting to block same IP again):")
    #     for log_item_2 in logs_b2:
    #         print(f"  - {log_item_2}")


    print("\nBlue Actions structure seems OK.")