# backend/simulation/state_manager.py

from typing import Any, Dict
from backend.simulation.objects.network_graph import NetworkGraph


class StateManager:
    """
    Single source of truth for everything happening in the simulation.
    Every action reads from and writes to this object.
    """

    def __init__(self):
        self.network_graph: NetworkGraph | None = None
        self.red_resources: float = 100.0
        self.blue_resources: float = 100.0
        self.is_running: bool = False

        # --- Kill chain tracking ---
        # Each set holds node IDs that have reached that stage.
        # Actions write to these on success.
        # Other actions read from these to check preconditions.

        self.port_scanned_nodes: set = set()
        self.fingerprinted_nodes: set = set()
        self.known_vulnerabilities: dict = {}   # node_id -> [cve_id, ...]
        self.known_services: dict = {}          # node_id -> [service_id, ...]
        self.initial_access_nodes: set = set()
        self.privileged_nodes: set = set()
        self.credential_stores: dict = {}       # node_id -> [credential, ...]
        self.lateral_access_nodes: set = set()
        self.evasion_active_nodes: set = set()
        self.c2_nodes: set = set()
        self.staged_data_nodes: set = set()
        self.exfil_complete: bool = False

        # --- Kill chain log ---
        # Every time something significant happens, it gets appended here.
        # The GUI event feed will consume this.
        self.kill_chain_log: list = []

        print("DEBUG: StateManager initialized.")

    def record_kill_chain_event(self, tactic: str, technique: str, node_id: str, detail: str = ""):
        """
        Called by every action on success or failure.
        Appends a structured entry to the log and prints a clear console marker.
        """
        entry = {
            "tactic": tactic,
            "technique": technique,
            "node_id": node_id,
            "detail": detail
        }
        self.kill_chain_log.append(entry)
        print(f"[KILL CHAIN] {tactic} | {technique} -> {node_id}  {detail}")

    # --- Serialisation for WebSocket broadcast ---

    def record_event(self, event_type: str, payload: dict):
        """Called by the API EventBus hook to store raw events for the GUI."""
        if not hasattr(self, 'recent_events'):
            self.recent_events: list = []
        self.recent_events.append({"event_type": event_type, "payload": payload})

    def to_dict(self, sim_time: float = 0.0) -> Dict[str, Any]:
        """Returns the full state snapshot consumed by the WebSocket broadcaster."""
        network_data = self.network_graph.to_dict() if self.network_graph else {"nodes": [], "edges": []}

        # Build a per-node kill chain progress summary
        kill_chain_progress = {}
        if self.network_graph:
            for node in self.network_graph.get_all_nodes():
                nid = node.id
                stages = []
                if nid in self.port_scanned_nodes:    stages.append("PORT_SCANNED")
                if nid in self.fingerprinted_nodes:   stages.append("FINGERPRINTED")
                if nid in self.initial_access_nodes:  stages.append("INITIAL_ACCESS")
                if nid in self.privileged_nodes:       stages.append("PRIVILEGED")
                if nid in self.credential_stores:      stages.append("CREDS_DUMPED")
                if nid in self.lateral_access_nodes:   stages.append("LATERAL")
                if nid in self.evasion_active_nodes:   stages.append("EVASION")
                if nid in self.c2_nodes:               stages.append("C2")
                if nid in self.staged_data_nodes:      stages.append("DATA_STAGED")
                kill_chain_progress[nid] = stages

        return {
            "sim_time": sim_time,
            "is_running": self.is_running,
            "red_resources": self.red_resources,
            "blue_resources": self.blue_resources,
            "network": network_data,
            "kill_chain_progress": kill_chain_progress,
            "exfil_complete": self.exfil_complete,
            "kill_chain_log": self.kill_chain_log[-50:],
            "recent_events": getattr(self, 'recent_events', []),
        }

    def get_owned_nodes(self) -> set:
        """
        Returns all node IDs that Red currently has any level of access to.
        Used by the AI to find pivot points for lateral movement.
        """
        return (
            self.initial_access_nodes |
            self.privileged_nodes |
            self.lateral_access_nodes |
            self.c2_nodes
        )

    def load_scenario(self, scenario_path: str):
        """Loads a network graph from a scenario JSON file."""
        print(f"DEBUG: StateManager loading scenario from {scenario_path}...")
        try:
            self.network_graph = NetworkGraph.load_from_json(scenario_path)
            print("DEBUG: Scenario loaded successfully.")
        except FileNotFoundError:
            print(f"ERROR: Scenario file not found at {scenario_path}")
            self.network_graph = NetworkGraph()
        except Exception as e:
            print(f"ERROR: Failed to load scenario: {e}")
            self.network_graph = NetworkGraph()

    def reset(self, scenario_path: str):
        """
        Wipes all state and reloads a fresh scenario.
        Call this at the start of every new simulation run.
        """
        print("DEBUG: StateManager resetting state...")
        self.load_scenario(scenario_path)

        self.red_resources = 100.0
        self.blue_resources = 100.0
        self.is_running = False

        self.port_scanned_nodes = set()
        self.fingerprinted_nodes = set()
        self.known_vulnerabilities = {}
        self.known_services = {}
        self.initial_access_nodes = set()
        self.privileged_nodes = set()
        self.credential_stores = {}
        self.lateral_access_nodes = set()
        self.evasion_active_nodes = set()
        self.c2_nodes = set()
        self.staged_data_nodes = set()
        self.exfil_complete = False
        self.kill_chain_log = []
        self.recent_events = []

        print("DEBUG: StateManager has been reset.")