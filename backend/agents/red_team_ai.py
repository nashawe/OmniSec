# backend/agents/red_team_ai.py

"""
FSM-based Red Team AI brain.

States follow the MITRE ATT&CK kill chain:
    RECON → INITIAL_ACCESS → PRIV_ESC → CRED_ACCESS →
    LATERAL_MOVE → EVASION → C2 → EXFIL → DONE

On each tick the AI:
  1. Evaluates the current FSM state.
  2. Picks a technique whose check_preconditions() passes.
  3. Fires the action through the ActionExecutor.
  4. Listens to EventBus for ACTION_COMPLETED / ACTION_SUCCESS / ACTION_FAILURE
     and transitions to the next state when conditions are met.
"""

import random
from enum import Enum, auto
from .base_agent import BaseAgent
from backend.actions.base_action import Team
from backend.actions.red_actions import (
    PortScan, ServiceFingerprint,
    ExploitPublicFacingApp, PhishingEmail,
    ExploitSUID, TokenImpersonation,
    DumpCredentials, Kerberoasting,
    PassTheHashMove, RDPLateralMove,
    ClearEventLogs, DisableAV,
    EstablishC2, C2BeaconKeepAlive,
    StageData, ExfilOverHTTPS,
)


class KillChainState(Enum):
    RECON           = auto()
    INITIAL_ACCESS  = auto()
    PRIV_ESC        = auto()
    CRED_ACCESS     = auto()
    LATERAL_MOVE    = auto()
    EVASION         = auto()
    C2              = auto()
    EXFIL           = auto()
    DONE            = auto()


class RedTeamAI(BaseAgent):
    """
    FSM-driven Red Team AI that walks the MITRE ATT&CK kill chain.
    """

    # How many sim-time ticks to wait between retries on failure
    RETRY_COOLDOWN_TICKS = 3

    def __init__(self, state_manager, action_executor, event_bus):
        super().__init__(Team.RED, state_manager, action_executor, event_bus)

        self._state = KillChainState.RECON
        self._is_busy = False
        self._cooldown = 0

        # Queues populated by scanning results
        self._recon_queue: list[str] = []        # nodes yet to port-scan
        self._fingerprint_queue: list[str] = []  # nodes yet to fingerprint
        self._initial_access_candidates: list[str] = []
        self._lateral_targets: list[str] = []

        self._initialize_queues()
        self._subscribe_events()

        print(f"RED_AI: FSM initialized in state {self._state.name}")

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------
    def _initialize_queues(self):
        """Fill the recon queue with all node IDs, shuffled."""
        all_ids = list(self._state_manager.network_graph.graph.nodes())
        random.shuffle(all_ids)
        self._recon_queue = all_ids[:]
        print(f"RED_AI: Recon queue loaded with {len(self._recon_queue)} targets")

    def _subscribe_events(self):
        self._event_bus.subscribe("ACTION_COMPLETED", self._on_action_completed)
        self._event_bus.subscribe("ACTION_SUCCESS", self._on_action_success)
        self._event_bus.subscribe("ACTION_FAILURE", self._on_action_failure)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _on_action_completed(self, event_type, payload):
        self._is_busy = False

    def _on_action_success(self, event_type, payload):
        """Advance FSM state based on what just succeeded."""
        action = payload.get("action", "")
        target = payload.get("target", "")

        # IMPORTANT: Payload 'action' is self.__class__.__name__ from BaseAction.complete()
        if action == "PortScan":
            if target not in self._fingerprint_queue:
                self._fingerprint_queue.append(target)
                print(f"RED_AI: Added {target} to fingerprint queue")

        elif action == "ServiceFingerprint":
            if target not in self._initial_access_candidates:
                self._initial_access_candidates.append(target)
                print(f"RED_AI: Added {target} to initial access candidates")

        # Re-evaluate FSM after success
        self._evaluate_state_transition()

    def _on_action_failure(self, event_type, payload):
        self._cooldown = self.RETRY_COOLDOWN_TICKS

    # ------------------------------------------------------------------
    # FSM transition logic
    # ------------------------------------------------------------------
    def _evaluate_state_transition(self):
        """Move to the next state when the current state has done enough work."""
        sm = self._state_manager

        if self._state == KillChainState.RECON:
            # Move on once we have at least one fingerprinted, internet-facing node
            if sm.fingerprinted_nodes:
                internet_facing = [
                    nid for nid in sm.fingerprinted_nodes
                    if sm.network_graph.get_node_by_id(nid) and
                       sm.network_graph.get_node_by_id(nid).exposed_to_internet
                ]
                if internet_facing or len(sm.fingerprinted_nodes) >= 2:
                    print("RED_AI: ✱ Transitioning → INITIAL_ACCESS")
                    self._state = KillChainState.INITIAL_ACCESS

        elif self._state == KillChainState.INITIAL_ACCESS:
            if sm.initial_access_nodes:
                print("RED_AI: ✱ Transitioning → PRIV_ESC")
                self._state = KillChainState.PRIV_ESC

        elif self._state == KillChainState.PRIV_ESC:
            if sm.privileged_nodes:
                print("RED_AI: ✱ Transitioning → CRED_ACCESS")
                self._state = KillChainState.CRED_ACCESS

        elif self._state == KillChainState.CRED_ACCESS:
            if sm.credential_stores:
                print("RED_AI: ✱ Transitioning → LATERAL_MOVE")
                self._state = KillChainState.LATERAL_MOVE
                self._build_lateral_targets()

        elif self._state == KillChainState.LATERAL_MOVE:
            if sm.lateral_access_nodes:
                print("RED_AI: ✱ Transitioning → EVASION")
                self._state = KillChainState.EVASION

        elif self._state == KillChainState.EVASION:
            if sm.evasion_active_nodes:
                print("RED_AI: ✱ Transitioning → C2")
                self._state = KillChainState.C2

        elif self._state == KillChainState.C2:
            if sm.c2_nodes:
                print("RED_AI: ✱ Transitioning → EXFIL")
                self._state = KillChainState.EXFIL

        elif self._state == KillChainState.EXFIL:
            if sm.exfil_complete:
                print(f"\n{'='*60}\nRED_AI: ✱✱✱ KILL CHAIN COMPLETE — RED TEAM WINS ✱✱✱\n{'='*60}\n")
                self._state = KillChainState.DONE

    def _build_lateral_targets(self):
        """Find neighbors of owned nodes that are not yet owned."""
        owned = self._state_manager.get_owned_nodes()
        targets = set()
        for nid in owned:
            for neighbor in self._state_manager.network_graph.get_neighbors(nid):
                if neighbor.id not in owned:
                    targets.add(neighbor.id)
        self._lateral_targets = list(targets)
        random.shuffle(self._lateral_targets)
        print(f"RED_AI: Built lateral target list: {self._lateral_targets}")

    # ------------------------------------------------------------------
    # Main decision loop (called every tick by the engine)
    # ------------------------------------------------------------------
    def decide_actions(self):
        if self._is_busy or self._state == KillChainState.DONE:
            return

        if self._cooldown > 0:
            self._cooldown -= 1
            return

        # Safety re-check for transitions
        self._evaluate_state_transition()

        sm = self._state_manager
        action = None

        # ----- RECON -----
        if self._state == KillChainState.RECON:
            action = self._decide_recon()

        # ----- INITIAL ACCESS -----
        elif self._state == KillChainState.INITIAL_ACCESS:
            action = self._decide_initial_access()

        # ----- PRIV ESC -----
        elif self._state == KillChainState.PRIV_ESC:
            action = self._decide_priv_esc()

        # ----- CRED ACCESS -----
        elif self._state == KillChainState.CRED_ACCESS:
            action = self._decide_cred_access()

        # ----- LATERAL -----
        elif self._state == KillChainState.LATERAL_MOVE:
            action = self._decide_lateral()

        # ----- EVASION -----
        elif self._state == KillChainState.EVASION:
            action = self._decide_evasion()

        # ----- C2 -----
        elif self._state == KillChainState.C2:
            action = self._decide_c2()

        # ----- EXFIL -----
        elif self._state == KillChainState.EXFIL:
            action = self._decide_exfil()

        if action:
            self._is_busy = True
            self._action_executor.execute_action(action)

    # ------------------------------------------------------------------
    # Per-state decision helpers
    # ------------------------------------------------------------------
    def _decide_recon(self):
        sm = self._state_manager

        # First fingerprint anything we can
        for nid in list(self._fingerprint_queue):
            ok, _ = ServiceFingerprint.check_preconditions(sm, nid)
            if ok:
                self._fingerprint_queue.remove(nid)
                print(f"RED_AI [RECON]: Fingerprinting {nid}")
                return ServiceFingerprint(sm, self._event_bus, nid)

        # Otherwise port-scan the next target
        while self._recon_queue:
            nid = self._recon_queue.pop(0)
            ok, _ = PortScan.check_preconditions(sm, nid)
            if ok:
                print(f"RED_AI [RECON]: Port-scanning {nid}")
                return PortScan(sm, self._event_bus, nid)

        # All scanned — force transition
        if sm.fingerprinted_nodes:
            self._state = KillChainState.INITIAL_ACCESS
        return None

    def _decide_initial_access(self):
        sm = self._state_manager

        # Prefer ExploitPublicFacingApp on internet-facing nodes
        for nid in list(self._initial_access_candidates):
            ok, _ = ExploitPublicFacingApp.check_preconditions(sm, nid)
            if ok:
                print(f"RED_AI [INITIAL_ACCESS]: Exploiting public app on {nid}")
                return ExploitPublicFacingApp(sm, self._event_bus, nid)

        # Fallback: phishing on any Workstation / Server
        all_nodes = sm.network_graph.get_all_nodes()
        random.shuffle(all_nodes)
        for node in all_nodes:
            ok, _ = PhishingEmail.check_preconditions(sm, node.id)
            if ok:
                print(f"RED_AI [INITIAL_ACCESS]: Phishing {node.id}")
                return PhishingEmail(sm, self._event_bus, node.id)

        return None

    def _decide_priv_esc(self):
        sm = self._state_manager
        # Try TokenImpersonation first (requires has_admin_users)
        for nid in sm.initial_access_nodes | sm.lateral_access_nodes:
            ok, _ = TokenImpersonation.check_preconditions(sm, nid)
            if ok:
                print(f"RED_AI [PRIV_ESC]: Token impersonation on {nid}")
                return TokenImpersonation(sm, self._event_bus, nid)

        # Fallback to ExploitSUID
        for nid in sm.initial_access_nodes | sm.lateral_access_nodes:
            ok, _ = ExploitSUID.check_preconditions(sm, nid)
            if ok:
                print(f"RED_AI [PRIV_ESC]: SUID exploit on {nid}")
                return ExploitSUID(sm, self._event_bus, nid)

        return None

    def _decide_cred_access(self):
        sm = self._state_manager
        for nid in list(sm.privileged_nodes):
            # Prefer Kerberoasting on nodes with admin users
            ok, _ = Kerberoasting.check_preconditions(sm, nid)
            if ok:
                print(f"RED_AI [CRED_ACCESS]: Kerberoasting on {nid}")
                return Kerberoasting(sm, self._event_bus, nid)

            ok, _ = DumpCredentials.check_preconditions(sm, nid)
            if ok:
                print(f"RED_AI [CRED_ACCESS]: Dumping credentials on {nid}")
                return DumpCredentials(sm, self._event_bus, nid)

        return None

    def _decide_lateral(self):
        sm = self._state_manager
        self._build_lateral_targets()

        # Find a source node that has dumped creds
        source_nodes = [nid for nid in sm.credential_stores]

        for target_id in list(self._lateral_targets):
            for source_id in source_nodes:
                # Try PtH (needs SMB)
                ok, _ = PassTheHashMove.check_preconditions(sm, source_id, target_id)
                if ok:
                    print(f"RED_AI [LATERAL]: PtH {source_id} → {target_id}")
                    return PassTheHashMove(sm, self._event_bus, source_id, target_id)

                # Try RDP
                ok, _ = RDPLateralMove.check_preconditions(sm, source_id, target_id)
                if ok:
                    print(f"RED_AI [LATERAL]: RDP {source_id} → {target_id}")
                    return RDPLateralMove(sm, self._event_bus, source_id, target_id)

        # If no lateral targets exist, skip ahead
        if not self._lateral_targets:
            print("RED_AI: No lateral targets — skipping to EVASION")
            self._state = KillChainState.EVASION
        return None

    def _decide_evasion(self):
        sm = self._state_manager
        # Run evasion on every privileged + lateral node
        candidates = (sm.privileged_nodes | sm.lateral_access_nodes) - sm.evasion_active_nodes
        for nid in candidates:
            ok, _ = ClearEventLogs.check_preconditions(sm, nid)
            if ok:
                print(f"RED_AI [EVASION]: Clearing logs on {nid}")
                return ClearEventLogs(sm, self._event_bus, nid)

            ok, _ = DisableAV.check_preconditions(sm, nid)
            if ok:
                print(f"RED_AI [EVASION]: Disabling AV on {nid}")
                return DisableAV(sm, self._event_bus, nid)

        # If nothing to evade, skip ahead
        if not candidates:
            print("RED_AI: No evasion targets — skipping to C2")
            self._state = KillChainState.C2
        return None

    def _decide_c2(self):
        sm = self._state_manager
        owned = sm.get_owned_nodes() - sm.c2_nodes
        for nid in owned:
            ok, _ = EstablishC2.check_preconditions(sm, nid)
            if ok:
                print(f"RED_AI [C2]: Establishing C2 on {nid}")
                return EstablishC2(sm, self._event_bus, nid)

        # Keep-alive on existing C2 nodes to generate resources
        for nid in list(sm.c2_nodes):
            ok, _ = C2BeaconKeepAlive.check_preconditions(sm, nid)
            if ok:
                print(f"RED_AI [C2]: Keep-alive beacon on {nid}")
                return C2BeaconKeepAlive(sm, self._event_bus, nid)

        return None

    def _decide_exfil(self):
        sm = self._state_manager

        # Stage data first
        for nid in list(sm.c2_nodes):
            ok, _ = StageData.check_preconditions(sm, nid)
            if ok:
                print(f"RED_AI [EXFIL]: Staging data on {nid}")
                return StageData(sm, self._event_bus, nid)

        # Then exfil
        for nid in list(sm.staged_data_nodes):
            ok, _ = ExfilOverHTTPS.check_preconditions(sm, nid)
            if ok:
                print(f"RED_AI [EXFIL]: Exfiltrating over HTTPS from {nid}")
                return ExfilOverHTTPS(sm, self._event_bus, nid)

        return None