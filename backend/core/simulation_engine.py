# cybersec_project/backend/core/simulation_engine.py

from typing import Optional, List, Dict, Any

from backend.core.state_manager import StateManager
from backend.core.event_manager import EventManager, SimulationEvent
from backend.core.history_manager import HistoryManager
from backend.actions.base_action import SimulationAction # For type checking

# For loading scenarios
from backend.scenarios.mvp_scenario import load_mvp_scenario # Example, can be made more generic

class SimulationEngine:
    """
    Orchestrates the entire simulation.
    Manages the simulation loop, event processing, state updates, and history logging.
    """
    def __init__(self, seed: Optional[int] = None):
        """
        Initializes the SimulationEngine.

        Args:
            seed (Optional[int], optional): Seed for the simulation's random number generator. Ensures reproducibility. Defaults to None (uses default seed).
        """
        self.state_manager: StateManager = StateManager(seed=seed)
        self.event_manager: EventManager = EventManager()
        self.history_manager: HistoryManager = HistoryManager(max_history_size=1000) # Keep last 1000 log entries

        self.current_time: int = 0 # Current discrete simulation time step
        self.is_running: bool = False
        self.simulation_id: Optional[str] = None # Could be used for tracking multiple sim instances

        self.history_manager.add_log_entry(
            sim_time=self.current_time,
            log_type="ENGINE_INIT",
            message=f"SimulationEngine initialized. RNG Seed: {self.state_manager.rng.getstate()[1][0] if hasattr(self.state_manager.rng, 'getstate') else 'N/A'}."
        )

    def load_scenario(self, scenario_loader_func: callable, *args, **kwargs) -> None:
        """
        Loads a scenario into the simulation using a provided loader function.

        Args:
            scenario_loader_func (callable): A function that takes the StateManager as an argument and populates it.
            *args: Additional arguments for the scenario loader.
            **kwargs: Additional keyword arguments for the scenario loader.
        """
        self.history_manager.add_log_entry(
            sim_time=self.current_time,
            log_type="SCENARIO_LOAD_START",
            message=f"Attempting to load scenario using: {scenario_loader_func.__name__}"
        )
        scenario_loader_func(self.state_manager, *args, **kwargs) # Pass StateManager to the loader
        # After loading, the StateManager's network_graph should be populated.
        # Actors defined in the scenario should also be registered with StateManager.
        self.history_manager.add_log_entry(
            sim_time=self.current_time,
            log_type="SCENARIO_LOAD_COMPLETE",
            message=f"Scenario '{scenario_loader_func.__name__}' loaded successfully."
        )
        # Example: Schedule initial AI agent decision events if scenario dictates
        # self._schedule_initial_actor_events()


    def _schedule_initial_actor_events(self) -> None:
        """
        (Example internal method)
        Schedules initial events for AI actors after a scenario is loaded.
        For instance, schedule a "DecideAction" event for each AI actor at time 0 or 1.
        """
        for actor_id, actor_data in self.state_manager.actors_data.items():
            # Example: Schedule an "ActorDecideAction" event for each AI at time 1
            initial_decision_event = SimulationEvent(
                timestamp=1, # Start decision making at the first step
                event_type="ActorDecideAction", # AI will handle this event type
                actor_id=actor_id,
                priority=0 # Default priority for AI decisions
            )
            self.event_manager.schedule_event(initial_decision_event)
            self.history_manager.add_log_entry(
                sim_time=self.current_time, # Logged at current time (0)
                log_type="EVENT_SCHEDULED",
                message=f"Initial decision event scheduled for actor '{actor_id}' at time {initial_decision_event.timestamp}.",
                details=initial_decision_event.to_dict()
            )


    def run_step(self) -> Optional[SimulationEvent]:
        """
        Advances the simulation by one event.
        Processes the next event from the event queue, updates the state,
        and logs the outcome.

        Returns:
            Optional[SimulationEvent]: The event that was processed, or None if no events.
        """
        if self.event_manager.is_empty():
            self.history_manager.add_log_entry(
                sim_time=self.current_time,
                log_type="SIM_MESSAGE",
                message="No more events to process. Simulation may be complete."
            )
            self.is_running = False
            return None

        processed_event = self.event_manager.get_next_event()
        if not processed_event: # Should not happen if is_empty() was false, but good check
            return None

        # Advance simulation time to the timestamp of the event being processed
        if processed_event.timestamp < self.current_time:
            # This should ideally not happen if events are always scheduled for the future.
            # Could indicate a bug in event scheduling or manual manipulation of timestamps.
            self.history_manager.add_log_entry(
                sim_time=self.current_time,
                log_type="ENGINE_WARNING",
                message=f"Processing event from the past! Event ts: {processed_event.timestamp}, Current ts: {self.current_time}. Event: {processed_event}"
            )
            # Optionally, adjust current_time or handle as an error. For now, log and proceed.
        
        self.current_time = processed_event.timestamp
        self.state_manager.current_time = self.current_time # Keep StateManager's time synced

        self.history_manager.add_log_entry(
            sim_time=self.current_time,
            log_type="EVENT_PROCESSING_START",
            message=f"Processing event: {processed_event.event_type} for actor '{processed_event.actor_id}'",
            details=processed_event.to_dict()
        )

        # --- Event Processing Logic ---
        new_scheduled_events: List[SimulationEvent] = []
        state_changes_made: List[Dict[str, Any]] = []
        action_log_messages: List[str] = []

        if processed_event.event_type == "PerformAction" and processed_event.action:
            action_to_execute = processed_event.action
            # Delegate execution to the action object itself
            try:
                new_scheduled_events, state_changes_made, action_log_messages = action_to_execute.execute(
                    state_manager=self.state_manager,
                    current_time=self.current_time,
                    target_node_id=processed_event.target_node_id,
                    source_node_id=processed_event.source_node_id,
                    actor_id=processed_event.actor_id
                    # **processed_event.data # Pass any extra data from the event to the action
                )
                self.history_manager.add_action_logs(self.current_time, processed_event.actor_id or "System", action_to_execute.name, action_log_messages)
            except Exception as e:
                error_message = f"Error executing action '{action_to_execute.name}': {e}"
                self.history_manager.add_log_entry(self.current_time, "ACTION_ERROR", error_message, {"action_id": action_to_execute.action_id, "error": str(e)})
                print(f"ERROR: {error_message}") # Also print to console for immediate visibility

        elif processed_event.event_type == "ActorDecideAction":
            # This is where AI logic would be invoked for an actor to choose its next action.
            # The AI would then schedule a "PerformAction" event.
            # For now, we'll just log it.
            # In a real system, this would call:
            #   chosen_action = self.state_manager.get_actor_ai(processed_event.actor_id).decide_action(self.state_manager)
            #   if chosen_action:
            #       perform_event = SimulationEvent(timestamp=self.current_time + 1, event_type="PerformAction", action=chosen_action, ...)
            #       new_scheduled_events.append(perform_event)
            message = f"Actor '{processed_event.actor_id}' to decide next action."
            self.history_manager.add_log_entry(self.current_time, "AI_DECISION_PHASE", message, {"actor_id": processed_event.actor_id})
            # For MVP testing, we might manually schedule the next specific action here.

        # Add other event_type handlers here (e.g., "DynamicVulnerabilitySpawn", "NodeRecovery")

        # Schedule any new events generated by the processed event/action
        for new_event in new_scheduled_events:
            self.event_manager.schedule_event(new_event)
            self.history_manager.add_log_entry(
                sim_time=self.current_time, # Logged at the time of scheduling
                log_type="EVENT_SCHEDULED",
                message=f"New event '{new_event.event_type}' scheduled by '{processed_event.event_type}' for actor '{new_event.actor_id}' at time {new_event.timestamp}.",
                details=new_event.to_dict()
            )
        
        # Record state changes (if any were returned by the action)
        # For now, StateManager's update methods are assumed to handle their own logging if needed,
        # or the action logs cover it. A more robust state change tracking can be added.
        if state_changes_made:
            for change in state_changes_made:
                 self.history_manager.add_log_entry(self.current_time, "STATE_CHANGE_DIRECT", f"Direct state change: {change.get('type', 'Unknown')}", change)


        self.history_manager.add_log_entry(
            sim_time=self.current_time,
            log_type="EVENT_PROCESSING_END",
            message=f"Finished processing event: {processed_event.event_type}",
            details={"event_id": processed_event.event_id}
        )
        return processed_event


    def run_until_time(self, target_time: int) -> None:
        """
        Runs the simulation until the current_time reaches target_time
        or no more events are available.

        Args:
            target_time (int): The simulation time to run until.
        """
        self.is_running = True
        self.history_manager.add_log_entry(self.current_time, "SIM_CONTROL", f"Running simulation until time {target_time}.")
        
        while self.current_time < target_time and not self.event_manager.is_empty():
            next_event_ts = self.event_manager.peek_next_event_timestamp()
            if next_event_ts is None or next_event_ts > target_time:
                # If no more events or next event is past target_time, advance time and stop.
                # If there are no events, current_time remains. If next event is too far,
                # we effectively fast-forward to target_time if no events occur before it.
                if next_event_ts is None and self.current_time < target_time :
                    self.current_time = target_time # No events, just advance time
                    self.state_manager.current_time = target_time
                elif next_event_ts is not None and next_event_ts > target_time and self.current_time < target_time:
                     self.current_time = target_time # Next event is too late, advance time
                     self.state_manager.current_time = target_time
                break 
            
            self.run_step()
            if not self.is_running: # run_step might set is_running to False if queue empty
                break

        # If loop finished due to time, but there might be events AT target_time
        while not self.event_manager.is_empty() and self.event_manager.peek_next_event_timestamp() == target_time:
            self.run_step()
            if not self.is_running:
                break

        if self.current_time < target_time and self.event_manager.is_empty():
             self.current_time = target_time # Fast forward if queue emptied before target time
             self.state_manager.current_time = target_time

        self.is_running = not self.event_manager.is_empty() # Still running if events exist
        self.history_manager.add_log_entry(self.current_time, "SIM_CONTROL", f"Simulation run until time {target_time} complete. Current time: {self.current_time}.")


    def run_all_events(self) -> None:
        """Runs the simulation until the event queue is empty."""
        self.is_running = True
        self.history_manager.add_log_entry(self.current_time, "SIM_CONTROL", "Running all scheduled events.")
        while not self.event_manager.is_empty():
            self.run_step()
            if not self.is_running: # run_step sets this if queue becomes empty
                break
        self.history_manager.add_log_entry(self.current_time, "SIM_CONTROL", "All events processed. Simulation complete.")


# --- Example Usage and Testing ---
if __name__ == '__main__':
    from backend.actions.red_actions import ExploitPublicFacingApplication # For testing
    from backend.actions.blue_actions import BlockIPAddress

    print("--- Testing Simulation Engine ---")

    # Initialize Engine (this also initializes StateManager with a seed)
    sim_engine = SimulationEngine(seed=42)

    # Load the MVP scenario
    print("\nLoading MVP Scenario...")
    sim_engine.load_scenario(load_mvp_scenario)

    # Manually schedule an initial Red Team exploit event for testing
    # In a full AI system, an "ActorDecideAction" event would lead to this.
    # We need the web server node ID from our scenario
    web_server_id = "Web_Server_01" # From mvp_scenario.py
    attacker_ip_for_block_test = "5.6.7.8" # An example IP to block later

    # Ensure the web server node has the target vulnerability for the exploit
    web_node = sim_engine.state_manager.get_node(web_server_id)
    target_vuln_id = "SQLi_WebApp_Login_001" # From vulnerabilities.py & mvp_scenario.py
    if web_node and target_vuln_id not in web_node.vulnerabilities:
        # This should ideally be part of scenario setup or node definition.
        # For testing, ensure it's there.
        sim_engine.state_manager.update_node_attribute(web_server_id, "vulnerabilities", web_node.vulnerabilities + [target_vuln_id])
        print(f"Manually added {target_vuln_id} to {web_server_id} for testing.")


    exploit_action = ExploitPublicFacingApplication(target_vulnerability_id=target_vuln_id)
    initial_exploit_event = SimulationEvent(
        timestamp=1, # Schedule for time step 1
        event_type="PerformAction",
        actor_id="RedTeam_Alpha",
        action=exploit_action,
        target_node_id=web_server_id,
        source_node_id="Internet" # Attack originates from "Internet"
    )
    sim_engine.event_manager.schedule_event(initial_exploit_event)
    sim_engine.history_manager.add_log_entry(0, "TEST_SETUP", f"Manually scheduled initial exploit for {web_server_id} at t=1")

    # Manually schedule a Blue Team block IP event after the exploit attempt
    block_action = BlockIPAddress(ip_to_block=attacker_ip_for_block_test) # Assume attacker IP is known
    blue_team_block_event = SimulationEvent(
        timestamp=5, # Schedule for time step 5 (after exploit)
        event_type="PerformAction",
        actor_id="BlueTeam_Delta",
        action=block_action
        # target_node_id is not strictly needed for BlockIPAddress if IP is global
    )
    sim_engine.event_manager.schedule_event(blue_team_block_event)
    sim_engine.history_manager.add_log_entry(0, "TEST_SETUP", f"Manually scheduled Blue Team IP block at t=5")


    print("\nRunning simulation step-by-step (first 3 steps):")
    for i in range(3): # Process first exploit event and potentially some time passing
        print(f"\n--- Sim Step (Request {i+1}) ---")
        processed = sim_engine.run_step()
        if processed:
            print(f"Processed event type: {processed.event_type} at time {sim_engine.current_time}")
            web_node_state = sim_engine.state_manager.get_node(web_server_id)
            if web_node_state:
                 print(f"  {web_server_id} status: {web_node_state.status}, compromised_by: {web_node_state.compromised_by}")
        else:
            print("No event processed.")
            break
    
    print(f"\nSimulation time after 3 run_step calls: {sim_engine.current_time}")

    print("\nRunning simulation until time 10...")
    sim_engine.run_until_time(10)
    print(f"Simulation time after run_until_time(10): {sim_engine.current_time}")

    web_node_final_state = sim_engine.state_manager.get_node(web_server_id)
    if web_node_final_state:
        print(f"Final state of {web_server_id}: Status={web_node_final_state.status}, CompromisedBy={web_node_final_state.compromised_by}")
    
    print(f"Is IP {attacker_ip_for_block_test} blocked? {sim_engine.state_manager.is_ip_blocked(attacker_ip_for_block_test)}")


    print("\n--- Simulation Engine Full History Log ---")
    for entry in sim_engine.history_manager.get_history():
        print(f"  [{entry.sim_time}] ({entry.log_type}) {entry.message}")
        if entry.details:
            pass # print(f"    Details: {entry.details}") # Can be verbose


    # Test running all remaining events
    # sim_engine.run_all_events()
    # print(f"\nSimulation time after run_all_events: {sim_engine.current_time}")

    print("\n--- Simulation Engine Test Complete ---")