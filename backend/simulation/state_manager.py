# backend/simulation/state_manager.py

from backend.simulation.objects.network_graph import NetworkGraph

class StateManager:
    """
    Central repository for the entire mutable simulation state.
    Provides a single, consistent source of truth.
    """
    def __init__(self):
        self.network_graph: NetworkGraph | None = None
        self.red_resources: float = 100.0
        self.blue_resources: float = 100.0
        self.is_running: bool = False
        print("DEBUG: StateManager initialized.")

    def load_scenario(self, scenario_path: str):
        """Loads a network graph from a scenario file."""
        print(f"DEBUG: StateManager loading scenario from {scenario_path}...")
        try:
            self.network_graph = NetworkGraph.load_from_json(scenario_path)
            print("DEBUG: Scenario loaded successfully.")
        except FileNotFoundError:
            print(f"ERROR: Scenario file not found at {scenario_path}")
            self.network_graph = NetworkGraph() # Load an empty graph
        except Exception as e:
            print(f"ERROR: Failed to load scenario: {e}")
            self.network_graph = NetworkGraph()

    def reset(self, scenario_path: str):
        """Resets the entire simulation state and reloads a scenario."""
        print(f"DEBUG: StateManager resetting state...")
        self.load_scenario(scenario_path)
        self.red_resources = 100.0
        self.blue_resources = 100.0
        self.is_running = False
        print("DEBUG: StateManager has been reset.")