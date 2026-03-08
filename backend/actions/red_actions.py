# backend/actions/red_actions.py

import random
from .base_action import BaseAction, Team
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.simulation.state_manager import StateManager
    from backend.simulation.event_bus import EventBus


# ============================================================================
# TACTIC 1 — RECONNAISSANCE
# ============================================================================

class PortScan(BaseAction):
    """T1046 — Network Service Scanning. Discovers open ports on a target."""

    def __init__(self, state_manager: 'StateManager', event_bus: 'EventBus', target_node_id: str):
        super().__init__(
            state_manager=state_manager,
            event_bus=event_bus,
            actor_team=Team.RED,
            target_node_id=target_node_id,
            duration=5.0,
            resource_cost=2.0,
        )
        self.name = "Port Scan"

    @staticmethod
    def check_preconditions(state_manager, target_node_id) -> tuple[bool, str]:
        if target_node_id in state_manager.port_scanned_nodes:
            return False, "Node already port-scanned."
        return True, ""

    def execute_logic(self) -> bool:
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        if not node:
            return False
        return random.random() < (1.0 - node.security_posture_score + 0.2)

    def apply_effects_on_success(self):
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        from backend.simulation.objects.node import NodeStatus
        node.current_status = NodeStatus.PORT_SCANNED
        self._state_manager.port_scanned_nodes.add(self.target_node_id)

        services = [s.id for s in node.services_running]
        self._state_manager.known_services[self.target_node_id] = services

        self._state_manager.record_kill_chain_event(
            "Reconnaissance", "PortScan", self.target_node_id,
            f"Discovered services: {services}"
        )
        self._event_bus.publish("RED_TEAM_INFO_GAINED", {
            "target_id": self.target_node_id, "services": services
        })

    def apply_effects_on_failure(self):
        self._state_manager.record_kill_chain_event(
            "Reconnaissance", "PortScan", self.target_node_id, "FAILED — detected"
        )
        self._event_bus.publish("BLUE_ALERT", {
            "alert": "Suspicious scan detected", "target_id": self.target_node_id
        })


class ServiceFingerprint(BaseAction):
    """T1592 — Gather Victim Host Information. Identifies exact software versions."""

    def __init__(self, state_manager: 'StateManager', event_bus: 'EventBus', target_node_id: str):
        super().__init__(
            state_manager=state_manager,
            event_bus=event_bus,
            actor_team=Team.RED,
            target_node_id=target_node_id,
            duration=8.0,
            resource_cost=3.0,
        )
        self.name = "Service Fingerprint"

    @staticmethod
    def check_preconditions(state_manager, target_node_id) -> tuple[bool, str]:
        if target_node_id not in state_manager.port_scanned_nodes:
            return False, "Must port-scan first."
        if target_node_id in state_manager.fingerprinted_nodes:
            return False, "Already fingerprinted."
        return True, ""

    def execute_logic(self) -> bool:
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        if not node:
            return False
        return random.random() < (1.0 - node.security_posture_score + 0.3)

    def apply_effects_on_success(self):
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        from backend.simulation.objects.node import NodeStatus
        node.current_status = NodeStatus.SERVICE_FINGERPRINTED
        self._state_manager.fingerprinted_nodes.add(self.target_node_id)

        vulns = [v.cve_id for v in node.vulnerabilities]
        self._state_manager.known_vulnerabilities[self.target_node_id] = vulns

        self._state_manager.record_kill_chain_event(
            "Reconnaissance", "ServiceFingerprint", self.target_node_id,
            f"Discovered vulns: {vulns}"
        )

    def apply_effects_on_failure(self):
        self._state_manager.record_kill_chain_event(
            "Reconnaissance", "ServiceFingerprint", self.target_node_id, "FAILED"
        )


# ============================================================================
# TACTIC 2 — INITIAL ACCESS
# ============================================================================

class ExploitPublicFacingApp(BaseAction):
    """T1190 — Exploit Public-Facing Application."""

    def __init__(self, state_manager: 'StateManager', event_bus: 'EventBus', target_node_id: str):
        super().__init__(
            state_manager=state_manager,
            event_bus=event_bus,
            actor_team=Team.RED,
            target_node_id=target_node_id,
            duration=12.0,
            resource_cost=8.0,
        )
        self.name = "Exploit Public-Facing App"

    @staticmethod
    def check_preconditions(state_manager, target_node_id) -> tuple[bool, str]:
        if target_node_id not in state_manager.fingerprinted_nodes:
            return False, "Must fingerprint first."
        if target_node_id in state_manager.initial_access_nodes:
            return False, "Already have initial access."
        node = state_manager.network_graph.get_node_by_id(target_node_id)
        if not node or not node.exposed_to_internet:
            return False, "Node is not internet-facing."
        vulns = state_manager.known_vulnerabilities.get(target_node_id, [])
        if not vulns:
            return False, "No known vulnerabilities to exploit."
        return True, ""

    def execute_logic(self) -> bool:
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        if not node:
            return False
        best = max(node.vulnerabilities, key=lambda v: v.exploitability)
        return random.random() < best.exploitability

    def apply_effects_on_success(self):
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        from backend.simulation.objects.node import NodeStatus
        node.current_status = NodeStatus.INITIAL_ACCESS_GAINED
        self._state_manager.initial_access_nodes.add(self.target_node_id)
        self._state_manager.record_kill_chain_event(
            "Initial Access", "ExploitPublicFacingApp", self.target_node_id,
            "Shell obtained on internet-facing node"
        )

    def apply_effects_on_failure(self):
        self._state_manager.record_kill_chain_event(
            "Initial Access", "ExploitPublicFacingApp", self.target_node_id, "FAILED — exploit blocked"
        )
        self._event_bus.publish("BLUE_ALERT", {
            "alert": "Exploit attempt blocked", "target_id": self.target_node_id
        })


class PhishingEmail(BaseAction):
    """T1566 — Phishing. Social-engineering a user on the node."""

    def __init__(self, state_manager: 'StateManager', event_bus: 'EventBus', target_node_id: str):
        super().__init__(
            state_manager=state_manager,
            event_bus=event_bus,
            actor_team=Team.RED,
            target_node_id=target_node_id,
            duration=15.0,
            resource_cost=5.0,
        )
        self.name = "Phishing Email"

    @staticmethod
    def check_preconditions(state_manager, target_node_id) -> tuple[bool, str]:
        if target_node_id in state_manager.initial_access_nodes:
            return False, "Already have initial access."
        node = state_manager.network_graph.get_node_by_id(target_node_id)
        if not node or node.node_type not in ("Workstation", "Server"):
            return False, "Phishing requires a Workstation or Server target."
        return True, ""

    def execute_logic(self) -> bool:
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        if not node:
            return False
        base = 0.5
        if node.security_posture_score > 0.7:
            base -= 0.2
        return random.random() < base

    def apply_effects_on_success(self):
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        from backend.simulation.objects.node import NodeStatus
        node.current_status = NodeStatus.INITIAL_ACCESS_GAINED
        self._state_manager.initial_access_nodes.add(self.target_node_id)
        self._state_manager.record_kill_chain_event(
            "Initial Access", "PhishingEmail", self.target_node_id,
            "User clicked malicious link — shell obtained"
        )

    def apply_effects_on_failure(self):
        self._state_manager.record_kill_chain_event(
            "Initial Access", "PhishingEmail", self.target_node_id, "FAILED — user reported phishing"
        )
        self._event_bus.publish("BLUE_ALERT", {
            "alert": "Phishing email reported", "target_id": self.target_node_id
        })


# ============================================================================
# TACTIC 3 — PRIVILEGE ESCALATION
# ============================================================================

class ExploitSUID(BaseAction):
    """T1548 — Abuse Elevation Control. Exploit misconfigured SUID binaries."""

    def __init__(self, state_manager: 'StateManager', event_bus: 'EventBus', target_node_id: str):
        super().__init__(
            state_manager=state_manager,
            event_bus=event_bus,
            actor_team=Team.RED,
            target_node_id=target_node_id,
            duration=6.0,
            resource_cost=4.0,
        )
        self.name = "Exploit SUID"

    @staticmethod
    def check_preconditions(state_manager, target_node_id) -> tuple[bool, str]:
        if target_node_id not in state_manager.initial_access_nodes and \
           target_node_id not in state_manager.lateral_access_nodes:
            return False, "Need initial or lateral access first."
        if target_node_id in state_manager.privileged_nodes:
            return False, "Already privileged."
        return True, ""

    def execute_logic(self) -> bool:
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        if not node:
            return False
        return random.random() < (0.6 - node.security_posture_score * 0.3)

    def apply_effects_on_success(self):
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        from backend.simulation.objects.node import NodeStatus
        node.current_status = NodeStatus.PRIVILEGED_ACCESS
        self._state_manager.privileged_nodes.add(self.target_node_id)
        self._state_manager.record_kill_chain_event(
            "Privilege Escalation", "ExploitSUID", self.target_node_id,
            "Root access via SUID binary"
        )

    def apply_effects_on_failure(self):
        self._state_manager.record_kill_chain_event(
            "Privilege Escalation", "ExploitSUID", self.target_node_id, "FAILED"
        )


class TokenImpersonation(BaseAction):
    """T1134 — Access Token Manipulation."""

    def __init__(self, state_manager: 'StateManager', event_bus: 'EventBus', target_node_id: str):
        super().__init__(
            state_manager=state_manager,
            event_bus=event_bus,
            actor_team=Team.RED,
            target_node_id=target_node_id,
            duration=7.0,
            resource_cost=5.0,
        )
        self.name = "Token Impersonation"

    @staticmethod
    def check_preconditions(state_manager, target_node_id) -> tuple[bool, str]:
        if target_node_id not in state_manager.initial_access_nodes and \
           target_node_id not in state_manager.lateral_access_nodes:
            return False, "Need initial or lateral access first."
        if target_node_id in state_manager.privileged_nodes:
            return False, "Already privileged."
        node = state_manager.network_graph.get_node_by_id(target_node_id)
        if not node or not node.has_admin_users:
            return False, "No admin tokens available on this node."
        return True, ""

    def execute_logic(self) -> bool:
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        if not node:
            return False
        return random.random() < 0.65

    def apply_effects_on_success(self):
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        from backend.simulation.objects.node import NodeStatus
        node.current_status = NodeStatus.PRIVILEGED_ACCESS
        self._state_manager.privileged_nodes.add(self.target_node_id)
        self._state_manager.record_kill_chain_event(
            "Privilege Escalation", "TokenImpersonation", self.target_node_id,
            "Impersonated admin token — elevated privileges"
        )

    def apply_effects_on_failure(self):
        self._state_manager.record_kill_chain_event(
            "Privilege Escalation", "TokenImpersonation", self.target_node_id, "FAILED — suspicious token usage logged"
        )
        self._event_bus.publish("BLUE_ALERT", {
            "alert": "Suspicious token usage", "target_id": self.target_node_id
        })


# ============================================================================
# TACTIC 4 — CREDENTIAL ACCESS
# ============================================================================

class DumpCredentials(BaseAction):
    """T1003 — OS Credential Dumping (e.g. Mimikatz, /etc/shadow)."""

    def __init__(self, state_manager: 'StateManager', event_bus: 'EventBus', target_node_id: str):
        super().__init__(
            state_manager=state_manager,
            event_bus=event_bus,
            actor_team=Team.RED,
            target_node_id=target_node_id,
            duration=5.0,
            resource_cost=4.0,
        )
        self.name = "Dump Credentials"

    @staticmethod
    def check_preconditions(state_manager, target_node_id) -> tuple[bool, str]:
        if target_node_id not in state_manager.privileged_nodes:
            return False, "Need privileged access to dump credentials."
        if target_node_id in state_manager.credential_stores:
            return False, "Credentials already dumped."
        return True, ""

    def execute_logic(self) -> bool:
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        if not node:
            return False
        return random.random() < 0.80

    def apply_effects_on_success(self):
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        from backend.simulation.objects.node import NodeStatus
        node.current_status = NodeStatus.CREDENTIALS_DUMPED

        creds = [f"hash_{self.target_node_id}_admin", f"hash_{self.target_node_id}_svc"]
        self._state_manager.credential_stores[self.target_node_id] = creds

        self._state_manager.record_kill_chain_event(
            "Credential Access", "DumpCredentials", self.target_node_id,
            f"Dumped {len(creds)} credential hashes"
        )

    def apply_effects_on_failure(self):
        self._state_manager.record_kill_chain_event(
            "Credential Access", "DumpCredentials", self.target_node_id, "FAILED — AV blocked hash dump"
        )
        self._event_bus.publish("BLUE_ALERT", {
            "alert": "Credential dump attempt detected", "target_id": self.target_node_id
        })


class Kerberoasting(BaseAction):
    """T1558.003 — Kerberoasting. Offline cracking of service-account tickets."""

    def __init__(self, state_manager: 'StateManager', event_bus: 'EventBus', target_node_id: str):
        super().__init__(
            state_manager=state_manager,
            event_bus=event_bus,
            actor_team=Team.RED,
            target_node_id=target_node_id,
            duration=10.0,
            resource_cost=6.0,
        )
        self.name = "Kerberoasting"

    @staticmethod
    def check_preconditions(state_manager, target_node_id) -> tuple[bool, str]:
        if target_node_id not in state_manager.privileged_nodes:
            return False, "Need privileged access."
        node = state_manager.network_graph.get_node_by_id(target_node_id)
        if not node or not node.has_admin_users:
            return False, "No service accounts to roast."
        if target_node_id in state_manager.credential_stores:
            return False, "Credentials already obtained."
        return True, ""

    def execute_logic(self) -> bool:
        return random.random() < 0.70

    def apply_effects_on_success(self):
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        from backend.simulation.objects.node import NodeStatus
        node.current_status = NodeStatus.CREDENTIALS_DUMPED

        creds = [f"kerb_{self.target_node_id}_svc"]
        self._state_manager.credential_stores[self.target_node_id] = creds

        self._state_manager.record_kill_chain_event(
            "Credential Access", "Kerberoasting", self.target_node_id,
            "Cracked service-account ticket"
        )

    def apply_effects_on_failure(self):
        self._state_manager.record_kill_chain_event(
            "Credential Access", "Kerberoasting", self.target_node_id, "FAILED — tickets uncrackable"
        )


# ============================================================================
# TACTIC 5 — LATERAL MOVEMENT
# ============================================================================

class PassTheHashMove(BaseAction):
    """T1550.002 — Pass the Hash. Use stolen NTLM hashes to authenticate."""

    def __init__(self, state_manager: 'StateManager', event_bus: 'EventBus',
                 source_node_id: str, target_node_id: str):
        super().__init__(
            state_manager=state_manager,
            event_bus=event_bus,
            actor_team=Team.RED,
            target_node_id=target_node_id,
            duration=6.0,
            resource_cost=5.0,
        )
        self.source_node_id = source_node_id
        self.name = "Pass the Hash"

    @staticmethod
    def check_preconditions(state_manager, source_node_id, target_node_id) -> tuple[bool, str]:
        if source_node_id not in state_manager.credential_stores:
            return False, "No credentials available on source node."
        if target_node_id in state_manager.get_owned_nodes():
            return False, "Already own target node."
        target = state_manager.network_graph.get_node_by_id(target_node_id)
        if not target or not target.smb_enabled:
            return False, "Target does not have SMB enabled."
        neighbors = state_manager.network_graph.get_neighbors(source_node_id)
        neighbor_ids = [n.id for n in neighbors]
        if target_node_id not in neighbor_ids:
            return False, "Target is not adjacent to source."
        return True, ""

    def execute_logic(self) -> bool:
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        if not node:
            return False
        return random.random() < (0.75 - node.security_posture_score * 0.2)

    def apply_effects_on_success(self):
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        from backend.simulation.objects.node import NodeStatus
        node.current_status = NodeStatus.LATERAL_ACCESS
        self._state_manager.lateral_access_nodes.add(self.target_node_id)
        self._state_manager.record_kill_chain_event(
            "Lateral Movement", "PassTheHashMove", self.target_node_id,
            f"Pivoted from {self.source_node_id} via SMB/PtH"
        )

    def apply_effects_on_failure(self):
        self._state_manager.record_kill_chain_event(
            "Lateral Movement", "PassTheHashMove", self.target_node_id, "FAILED — authentication rejected"
        )
        self._event_bus.publish("BLUE_ALERT", {
            "alert": "Failed lateral auth attempt", "target_id": self.target_node_id
        })


class RDPLateralMove(BaseAction):
    """T1021.001 — Remote Desktop Protocol lateral movement."""

    def __init__(self, state_manager: 'StateManager', event_bus: 'EventBus',
                 source_node_id: str, target_node_id: str):
        super().__init__(
            state_manager=state_manager,
            event_bus=event_bus,
            actor_team=Team.RED,
            target_node_id=target_node_id,
            duration=8.0,
            resource_cost=5.0,
        )
        self.source_node_id = source_node_id
        self.name = "RDP Lateral Move"

    @staticmethod
    def check_preconditions(state_manager, source_node_id, target_node_id) -> tuple[bool, str]:
        if source_node_id not in state_manager.credential_stores:
            return False, "No credentials available on source node."
        if target_node_id in state_manager.get_owned_nodes():
            return False, "Already own target node."
        target = state_manager.network_graph.get_node_by_id(target_node_id)
        if not target or not target.rdp_enabled:
            return False, "Target does not have RDP enabled."
        neighbors = state_manager.network_graph.get_neighbors(source_node_id)
        neighbor_ids = [n.id for n in neighbors]
        if target_node_id not in neighbor_ids:
            return False, "Target is not adjacent to source."
        return True, ""

    def execute_logic(self) -> bool:
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        if not node:
            return False
        return random.random() < (0.70 - node.security_posture_score * 0.2)

    def apply_effects_on_success(self):
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        from backend.simulation.objects.node import NodeStatus
        node.current_status = NodeStatus.LATERAL_ACCESS
        self._state_manager.lateral_access_nodes.add(self.target_node_id)
        self._state_manager.record_kill_chain_event(
            "Lateral Movement", "RDPLateralMove", self.target_node_id,
            f"Pivoted from {self.source_node_id} via RDP"
        )

    def apply_effects_on_failure(self):
        self._state_manager.record_kill_chain_event(
            "Lateral Movement", "RDPLateralMove", self.target_node_id, "FAILED — RDP connection refused"
        )
        self._event_bus.publish("BLUE_ALERT", {
            "alert": "Suspicious RDP session attempt", "target_id": self.target_node_id
        })


# ============================================================================
# TACTIC 6 — DEFENSE EVASION
# ============================================================================

class ClearEventLogs(BaseAction):
    """T1070.001 — Indicator Removal: Clear Windows Event Logs."""

    def __init__(self, state_manager: 'StateManager', event_bus: 'EventBus', target_node_id: str):
        super().__init__(
            state_manager=state_manager,
            event_bus=event_bus,
            actor_team=Team.RED,
            target_node_id=target_node_id,
            duration=3.0,
            resource_cost=2.0,
        )
        self.name = "Clear Event Logs"

    @staticmethod
    def check_preconditions(state_manager, target_node_id) -> tuple[bool, str]:
        if target_node_id not in state_manager.privileged_nodes:
            return False, "Need privileged access."
        if target_node_id in state_manager.evasion_active_nodes:
            return False, "Evasion already active."
        return True, ""

    def execute_logic(self) -> bool:
        return random.random() < 0.90

    def apply_effects_on_success(self):
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        from backend.simulation.objects.node import NodeStatus
        node.current_status = NodeStatus.EVASION_ACTIVE
        self._state_manager.evasion_active_nodes.add(self.target_node_id)
        node.detection_chance_modifier = max(0.02, node.detection_chance_modifier - 0.3)
        self._state_manager.record_kill_chain_event(
            "Defense Evasion", "ClearEventLogs", self.target_node_id,
            "Logs wiped — detection chance reduced"
        )

    def apply_effects_on_failure(self):
        self._state_manager.record_kill_chain_event(
            "Defense Evasion", "ClearEventLogs", self.target_node_id, "FAILED — log-clearing detected"
        )
        self._event_bus.publish("BLUE_ALERT", {
            "alert": "Log tampering detected", "target_id": self.target_node_id
        })


class DisableAV(BaseAction):
    """T1562.001 — Impair Defenses: Disable or Modify Tools."""

    def __init__(self, state_manager: 'StateManager', event_bus: 'EventBus', target_node_id: str):
        super().__init__(
            state_manager=state_manager,
            event_bus=event_bus,
            actor_team=Team.RED,
            target_node_id=target_node_id,
            duration=4.0,
            resource_cost=3.0,
        )
        self.name = "Disable AV"

    @staticmethod
    def check_preconditions(state_manager, target_node_id) -> tuple[bool, str]:
        if target_node_id not in state_manager.privileged_nodes:
            return False, "Need privileged access."
        if target_node_id in state_manager.evasion_active_nodes:
            return False, "Evasion already active."
        return True, ""

    def execute_logic(self) -> bool:
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        if not node:
            return False
        return random.random() < (0.7 - node.security_posture_score * 0.3)

    def apply_effects_on_success(self):
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        from backend.simulation.objects.node import NodeStatus
        node.current_status = NodeStatus.EVASION_ACTIVE
        self._state_manager.evasion_active_nodes.add(self.target_node_id)
        node.detection_chance_modifier = max(0.02, node.detection_chance_modifier - 0.4)
        self._state_manager.record_kill_chain_event(
            "Defense Evasion", "DisableAV", self.target_node_id,
            "AV disabled — significantly reduced detection"
        )

    def apply_effects_on_failure(self):
        self._state_manager.record_kill_chain_event(
            "Defense Evasion", "DisableAV", self.target_node_id, "FAILED — AV tamper protection triggered"
        )
        self._event_bus.publish("BLUE_ALERT", {
            "alert": "AV tamper attempt detected", "target_id": self.target_node_id
        })


# ============================================================================
# TACTIC 7 — COMMAND AND CONTROL
# ============================================================================

class EstablishC2(BaseAction):
    """T1071 — Application Layer Protocol C2 channel."""

    def __init__(self, state_manager: 'StateManager', event_bus: 'EventBus', target_node_id: str):
        super().__init__(
            state_manager=state_manager,
            event_bus=event_bus,
            actor_team=Team.RED,
            target_node_id=target_node_id,
            duration=10.0,
            resource_cost=8.0,
        )
        self.name = "Establish C2"

    @staticmethod
    def check_preconditions(state_manager, target_node_id) -> tuple[bool, str]:
        owned = state_manager.get_owned_nodes()
        if target_node_id not in owned:
            return False, "Must have access to establish C2."
        if target_node_id in state_manager.c2_nodes:
            return False, "C2 already active."
        return True, ""

    def execute_logic(self) -> bool:
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        if not node:
            return False
        bonus = 0.15 if self.target_node_id in self._state_manager.evasion_active_nodes else 0.0
        return random.random() < (0.65 + bonus)

    def apply_effects_on_success(self):
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        from backend.simulation.objects.node import NodeStatus
        node.current_status = NodeStatus.C2_ESTABLISHED
        self._state_manager.c2_nodes.add(self.target_node_id)
        self._state_manager.record_kill_chain_event(
            "Command and Control", "EstablishC2", self.target_node_id,
            "C2 beacon active — persistent access secured"
        )

    def apply_effects_on_failure(self):
        self._state_manager.record_kill_chain_event(
            "Command and Control", "EstablishC2", self.target_node_id, "FAILED — outbound C2 traffic blocked"
        )
        self._event_bus.publish("BLUE_ALERT", {
            "alert": "Suspicious outbound beacon detected", "target_id": self.target_node_id
        })


class C2BeaconKeepAlive(BaseAction):
    """T1071 — Beacon keep-alive. Generates resources for Red team."""

    def __init__(self, state_manager: 'StateManager', event_bus: 'EventBus', target_node_id: str):
        super().__init__(
            state_manager=state_manager,
            event_bus=event_bus,
            actor_team=Team.RED,
            target_node_id=target_node_id,
            duration=2.0,
            resource_cost=0.5,
        )
        self.name = "C2 Beacon Keep-Alive"

    @staticmethod
    def check_preconditions(state_manager, target_node_id) -> tuple[bool, str]:
        if target_node_id not in state_manager.c2_nodes:
            return False, "No C2 channel on this node."
        return True, ""

    def execute_logic(self) -> bool:
        return True  # Keep-alive always succeeds

    def apply_effects_on_success(self):
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        resource_gain = node.c2_resource_generation_rate if node else 2.0
        if resource_gain <= 0:
            resource_gain = 2.0
        self._state_manager.red_resources += resource_gain
        self._state_manager.record_kill_chain_event(
            "Command and Control", "C2BeaconKeepAlive", self.target_node_id,
            f"Beacon OK — +{resource_gain:.1f} resources"
        )

    def apply_effects_on_failure(self):
        pass  # Keep-alive cannot fail


# ============================================================================
# TACTIC 8 — EXFILTRATION
# ============================================================================

class StageData(BaseAction):
    """T1074 — Data Staged. Collect and stage data before exfiltration."""

    def __init__(self, state_manager: 'StateManager', event_bus: 'EventBus', target_node_id: str):
        super().__init__(
            state_manager=state_manager,
            event_bus=event_bus,
            actor_team=Team.RED,
            target_node_id=target_node_id,
            duration=8.0,
            resource_cost=4.0,
        )
        self.name = "Stage Data"

    @staticmethod
    def check_preconditions(state_manager, target_node_id) -> tuple[bool, str]:
        if target_node_id not in state_manager.c2_nodes:
            return False, "Needs C2 for staging."
        if target_node_id in state_manager.staged_data_nodes:
            return False, "Data already staged."
        node = state_manager.network_graph.get_node_by_id(target_node_id)
        if not node or node.value < 3.0:
            return False, "Node value too low — nothing worth staging."
        return True, ""

    def execute_logic(self) -> bool:
        return random.random() < 0.85

    def apply_effects_on_success(self):
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        from backend.simulation.objects.node import NodeStatus
        node.current_status = NodeStatus.DATA_STAGED
        self._state_manager.staged_data_nodes.add(self.target_node_id)
        self._state_manager.record_kill_chain_event(
            "Exfiltration", "StageData", self.target_node_id,
            f"Data staged — value={node.value}"
        )

    def apply_effects_on_failure(self):
        self._state_manager.record_kill_chain_event(
            "Exfiltration", "StageData", self.target_node_id, "FAILED — DLP blocked staging"
        )


class ExfilOverHTTPS(BaseAction):
    """T1048 — Exfiltration Over Alternative Protocol (HTTPS)."""

    def __init__(self, state_manager: 'StateManager', event_bus: 'EventBus', target_node_id: str):
        super().__init__(
            state_manager=state_manager,
            event_bus=event_bus,
            actor_team=Team.RED,
            target_node_id=target_node_id,
            duration=12.0,
            resource_cost=6.0,
        )
        self.name = "Exfil Over HTTPS"

    @staticmethod
    def check_preconditions(state_manager, target_node_id) -> tuple[bool, str]:
        if target_node_id not in state_manager.staged_data_nodes:
            return False, "Data must be staged before exfiltration."
        if state_manager.exfil_complete:
            return False, "Exfiltration already completed."
        return True, ""

    def execute_logic(self) -> bool:
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        if not node:
            return False
        bonus = 0.15 if self.target_node_id in self._state_manager.evasion_active_nodes else 0.0
        return random.random() < (0.60 + bonus)

    def apply_effects_on_success(self):
        node = self._state_manager.network_graph.get_node_by_id(self.target_node_id)
        from backend.simulation.objects.node import NodeStatus
        node.current_status = NodeStatus.DATA_EXFILTRATED
        self._state_manager.exfil_complete = True
        self._state_manager.record_kill_chain_event(
            "Exfiltration", "ExfilOverHTTPS", self.target_node_id,
            "DATA EXFILTRATED — RED TEAM WINS"
        )

    def apply_effects_on_failure(self):
        self._state_manager.record_kill_chain_event(
            "Exfiltration", "ExfilOverHTTPS", self.target_node_id, "FAILED — egress blocked by proxy"
        )
        self._event_bus.publish("BLUE_ALERT", {
            "alert": "Large HTTPS exfil attempt blocked", "target_id": self.target_node_id
        })