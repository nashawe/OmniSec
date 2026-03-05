# backend/simulation/state_manager.py

from collections import deque
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

        # A rolling buffer of the last 50 events for the GUI event feed.
        # deque with maxlen automatically drops old events when full.
        self.recent_events: deque = deque(maxlen=50)

        print("DEBUG: StateManager initialized.")

    def record_event(self, event_type: str, payload: dict):
        """
        Adds an event to the recent_events buffer so it can be
        included in the next WebSocket snapshot sent to the GUI.
        """
        self.recent_events.append({
            "event_type": event_type,
            "payload": payload
        })

    def load_scenario(self, scenario_path: str):
        """Loads a network graph from a scenario file."""
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
        """Resets the entire simulation state and reloads a scenario."""
        print(f"DEBUG: StateManager resetting state...")
        self.load_scenario(scenario_path)
        self.red_resources = 100.0
        self.blue_resources = 100.0
        self.is_running = False
        self.recent_events.clear()
        print("DEBUG: StateManager has been reset.")

    def to_dict(self, sim_time: float) -> dict:
        """
        Serializes the entire simulation state into a dictionary.
        This is what gets broadcast over the WebSocket to the GUI
        on every tick.
        """
        return {
            "sim_time": round(sim_time, 2),
            "is_running": self.is_running,
            "red_resources": round(self.red_resources, 2),
            "blue_resources": round(self.blue_resources, 2),
            "network": self.network_graph.to_dict() if self.network_graph else {"nodes": [], "edges": []},
            "recent_events": list(self.recent_events)
        }