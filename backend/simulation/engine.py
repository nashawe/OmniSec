# backend/simulation/engine.py

import time
import threading
from backend.simulation.time_manager import TimeManager
from backend.simulation.event_bus import event_bus
from backend.simulation.state_manager import StateManager

class SimulationEngine:
    """
    The main orchestrator of the simulation. Initializes the state,
    runs the main loop, and manages AI agent turns.
    """
    def __init__(self):
        self.time_manager = TimeManager()
        self.event_bus = event_bus
        self.state_manager = StateManager()
        
        self._loop_thread = None
        self._stop_event = threading.Event()

        print("DEBUG: SimulationEngine initialized.")

    def _simulation_loop(self):
        """The core loop that drives the simulation forward in time."""
        print("ENGINE_LOOP: Simulation loop thread started.")
        last_real_time = time.time()

        while not self._stop_event.is_set():
            if not self.state_manager.is_running:
                time.sleep(0.1)
                last_real_time = time.time()
                continue
            
            current_real_time = time.time()
            real_delta_t = current_real_time - last_real_time
            last_real_time = current_real_time
            sim_delta_t = real_delta_t * self.time_manager.get_speed()
            target_sim_time = self.time_manager.current_time + sim_delta_t

            self.time_manager.process_events_until(target_sim_time)
            
            # Placeholder for AI Agent Actions
            # self.red_team_ai.decide_actions(...)
            # self.blue_team_ai.decide_actions(...)
            
            # Use carriage return '\r' to print on the same line.
            print(f"\rSIM TIME: {self.time_manager.current_time:.2f}", end="")

            time.sleep(0.01)

        print("\nENGINE_LOOP: Simulation loop thread has stopped.")

    def start_simulation(self):
        if not self.state_manager.network_graph:
            print("\nERROR: Cannot start simulation. No scenario loaded.")
            return

        if self.state_manager.is_running:
            print("\nDEBUG: Simulation is already running.")
            return

        print("\nENGINE: Starting simulation...")
        
        self.state_manager.is_running = True
        
        if self._loop_thread is None or not self._loop_thread.is_alive():
            self._stop_event.clear()
            self._loop_thread = threading.Thread(target=self._simulation_loop, daemon=True)
            self._loop_thread.start()

        self.time_manager.resume()

    def pause_simulation(self):
        if not self.state_manager.is_running:
            print("\nDEBUG: Simulation is not running.")
            return
        # A newline is needed to move off the 'SIM TIME' line.
        print("\nENGINE: Pausing simulation...")
        self.state_manager.is_running = False
        self.time_manager.pause()

    def reset_simulation(self, scenario_path: str):
        print(f"\nENGINE: Resetting simulation with scenario at '{scenario_path}'...")
        if self._loop_thread and self._loop_thread.is_alive():
            self.state_manager.is_running = False
            self._stop_event.set()
            self._loop_thread.join()

        self.state_manager.reset(scenario_path)
        self.time_manager.reset()
        print("ENGINE: Simulation reset complete. Ready to start.")

    def set_simulation_speed(self, factor: float):
        # A newline is needed to move off the 'SIM TIME' line.
        print(f"\nENGINE: Setting simulation speed to {factor}x.")
        self.time_manager.set_speed(factor)