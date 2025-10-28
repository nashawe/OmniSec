# backend/actions/red_actions.py

import random
from .base_action import BaseAction, Team
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.simulation.state_manager import StateManager
    from backend.simulation.event_bus import EventBus

class ScanNode(BaseAction):
    """
    Red Team action to scan a node for vulnerabilities and services.
    """
    def __init__(self, state_manager: 'StateManager', event_bus: 'EventBus', target_node_id: str):
        # Call the parent constructor with this action's specific properties
        super().__init__(
            state_manager=state_manager,
            event_bus=event_bus,
            actor_team=Team.RED,
            target_node_id=target_node_id,
            duration=5.0,  # Takes 5 simulation minutes
            resource_cost=2.0 # Costs 2 resources
        )
        self.name = "Scan Node"

    def execute_logic(self) -> bool:
        """
        The success of a scan depends on the target's security posture.
        A higher security score makes a successful scan less likely.
        """
        target_node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        if not target_node:
            return False
        
        # The higher the security score, the lower the chance of success
        success_chance = 1.0 - target_node.security_posture_score
        
        # Add a small random element
        return random.random() < (success_chance + 0.1)

    def apply_effects_on_success(self):
        """
        If successful, the Red Team learns about the services and vulnerabilities
        on the target node. We'll simulate this by publishing an event with the info.
        """
        target_node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        
        discovered_services = [s.id for s in target_node.services_running]
        discovered_vulns = [v.cve_id for v in target_node.vulnerabilities]
        
        print(f"SUCCESS: {self.name} on {target_node.name} discovered services: {discovered_services} and vulns: {discovered_vulns}")
        
        self._event_bus.publish(
            "RED_TEAM_INFO_GAINED",
            {
                "target_id": self.target_node_id,
                "services": discovered_services,
                "vulnerabilities": discovered_vulns
            }
        )

    def apply_effects_on_failure(self):
        """
        If the scan fails, it might be detected. For now, we'll just log it.
        Later, this could trigger a "SUSPICIOUS_ACTIVITY" event for the Blue Team.
        """
        target_node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        print(f"FAILURE: {self.name} on {target_node.name} failed or was detected.")