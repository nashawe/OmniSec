# backend/simulation/engine.py

# CHANGE: Use absolute imports starting from the 'backend' package.
from backend.simulation.time_manager import time_manager
from backend.simulation.event_bus import event_bus
from backend.simulation.state_manager import StateManager

class SimulationEngine:
    """
    The main orchestrator of the simulation. Initializes the state,
    runs the main loop, and manages AI agent turns.
    """
    def __init__(self):
        self.time_manager = time_manager
        self.event_bus = event_bus
        self.state_manager = StateManager()
        print("DEBUG: SimulationEngine initialized.")

    def start_simulation(self):
        if not self.state_manager.network_graph:
            print("ERROR: Cannot start simulation. No scenario loaded.")
            return
        if self.state_manager.is_running:
            print("DEBUG: Simulation is already running.")
            return
        print("ENGINE: Starting simulation...")
        self.state_manager.is_running = True
        self.time_manager.resume()

    def pause_simulation(self):
        if not self.state_manager.is_running:
            print("DEBUG: Simulation is not running.")
            return
        print("ENGINE: Pausing simulation...")
        self.state_manager.is_running = False
        self.time_manager.pause()

    def reset_simulation(self, scenario_path: str):
        print(f"ENGINE: Resetting simulation with scenario at '{scenario_path}'...")
        self.state_manager.reset(scenario_path)
        self.time_manager.reset()
        print(f"ENGINE: Simulation reset complete. Ready to start.")

    def set_simulation_speed(self, factor: float):
        print(f"ENGINE: Setting simulation speed to {factor}x.")
        self.time_manager.set_speed(factor)