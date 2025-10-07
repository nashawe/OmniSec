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
        # A threading.Event is a safe way to signal the thread to stop.
        self._stop_event = threading.Event()

        print("DEBUG: SimulationEngine initialized.")

    def _simulation_loop(self):
        """The core loop that drives the simulation forward in time."""
        print("ENGINE_LOOP: Simulation loop thread started.")
        
        # Keep track of the last real-world time we updated
        last_real_time = time.time()

        # The loop continues as long as the stop event hasn't been set.
        while not self._stop_event.is_set():
            if not self.state_manager.is_running:
                # If paused, we just sleep briefly and check again.
                time.sleep(0.1)
                # Reset last_real_time to avoid a large time jump on resume
                last_real_time = time.time()
                continue
            
            # --- Main Loop Logic ---
            current_real_time = time.time()
            # How much real-world time has passed since the last tick
            real_delta_t = current_real_time - last_real_time
            last_real_time = current_real_time

            # How much simulation time should pass in this tick
            # This is affected by the simulation speed multiplier
            sim_delta_t = real_delta_t * self.time_manager.get_speed()
            
            # The target simulation time for this tick
            target_sim_time = self.time_manager.current_time + sim_delta_t

            # Tell the TimeManager to process all scheduled events up to this point
            self.time_manager.process_events_until(target_sim_time)
            
            # --- Placeholder for AI Agent Actions ---
            # self.red_team_ai.decide_actions(...)
            # self.blue_team_ai.decide_actions(...)
            
            # We can print the current simulation time to see it advancing.
            # Use carriage return '\r' to print on the same line.
            print(f"\rSIM TIME: {self.time_manager.current_time:.2f}", end="")

            # Sleep for a very short duration to prevent this loop from
            # consuming 100% of a CPU core.
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
        
        # --- FIX IS HERE ---
        # 1. Schedule the first event while the simulation is still 'paused'.
        # This ensures there is something in the event queue before the loop starts.
        self.schedule_test_event()

        # 2. Set the running flag.
        self.state_manager.is_running = True
        
        # 3. If the thread doesn't exist, create and start it.
        if self._loop_thread is None or not self._loop_thread.is_alive():
            self._stop_event.clear()
            self._loop_thread = threading.Thread(target=self._simulation_loop, daemon=True)
            self._loop_thread.start()

        # 4. Finally, tell the TimeManager (and the loop) that it's okay to run.
        self.time_manager.resume()
            
    def test_event_callback(self):
        """This function will be called by the TimeManager."""
        current_time = self.time_manager.current_time
        print(f"\n*** EVENT: Test event fired at sim time {current_time:.2f} ***")
        # Re-schedule the event to fire again in 10 simulation seconds
        self.schedule_test_event()

    def schedule_test_event(self):
        """Schedules the test event to fire in 10 sim seconds."""
        delay = 10.0 # 10 simulation seconds
        self.time_manager.schedule_event(self.test_event_callback, delay)

    def pause_simulation(self):
        if not self.state_manager.is_running:
            print("DEBUG: Simulation is not running.")
            return
        # The print statement for time needs a newline before we print other things.
        print("\nENGINE: Pausing simulation...")
        self.state_manager.is_running = False
        self.time_manager.pause()

    def reset_simulation(self, scenario_path: str):
        print(f"\nENGINE: Resetting simulation with scenario at '{scenario_path}'...")
        # Stop the current simulation loop if it's running
        if self._loop_thread and self._loop_thread.is_alive():
            self.state_manager.is_running = False # Tell the loop to pause
            self._stop_event.set() # Signal the thread to terminate
            self._loop_thread.join() # Wait for the thread to finish cleanly

        self.state_manager.reset(scenario_path)
        self.time_manager.reset()
        print(f"ENGINE: Simulation reset complete. Ready to start.")

    def set_simulation_speed(self, factor: float):
        print(f"\nENGINE: Setting simulation speed to {factor}x.")
        self.time_manager.set_speed(factor)