# backend/actions/blue_actions.py

import random
from .base_action import BaseAction, Team
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..simulation.state_manager import StateManager
    from ..simulation.event_bus import EventBus

class VulnerabilityScan(BaseAction):
    """
    Blue Team action to perform an internal scan on a node to discover
    vulnerabilities that are not yet known to the Blue Team.
    """
    def __init__(self, state_manager: 'StateManager', event_bus: 'EventBus', target_node_id: str):
        # Call the parent constructor with this action's specific properties
        super().__init__(
            state_manager=state_manager,
            event_bus=event_bus,
            actor_team=Team.BLUE,
            target_node_id=target_node_id,
            duration=15.0, # An internal scan is more thorough, so it takes longer
            resource_cost=3.0
        )
        self.name = "Vulnerability Scan"

    def execute_logic(self) -> bool:
        """
        An internal scan is very likely to succeed, but we can add a small
        chance of failure to represent misconfigurations or complex environments.
        """
        return random.random() < 0.95 # 95% chance of success

    def apply_effects_on_success(self):
        """
        If successful, the Blue Team discovers a subset of the vulnerabilities
        on the target node that they did not previously know about.
        """
        target_node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        if not target_node:
            return

        newly_discovered_vulns = []
        for vuln in target_node.vulnerabilities:
            if not vuln.known_to_blue:
                # Let's say the scan finds 70% of unknown vulnerabilities
                if random.random() < 0.70:
                    vuln.known_to_blue = True
                    newly_discovered_vulns.append(vuln.cve_id)
        
        if newly_discovered_vulns:
            print(f"SUCCESS: {self.name} on {target_node.name} discovered new vulnerabilities: {newly_discovered_vulns}")
            self._event_bus.publish(
                "BLUE_TEAM_VULN_DISCOVERED",
                {
                    "target_id": self.target_node_id,
                    "vulnerabilities": newly_discovered_vulns
                }
            )
        else:
            print(f"SUCCESS: {self.name} on {target_node.name} completed, but found no new vulnerabilities.")


    def apply_effects_on_failure(self):
        """
        If the scan fails, it means the security tool was ineffective.
        """
        target_node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        print(f"FAILURE: {self.name} on {target_node.name} failed to complete successfully.")