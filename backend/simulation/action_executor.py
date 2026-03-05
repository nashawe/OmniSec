# backend/simulation/action_executor.py

from typing import TYPE_CHECKING
from backend.actions.base_action import BaseAction, Team

if TYPE_CHECKING:
    from backend.simulation.state_manager import StateManager
    from backend.simulation.time_manager import TimeManager
    from backend.simulation.event_bus import EventBus

class ActionExecutor:
    """
    Validates and schedules actions. Supports immediate or absolute start times.
    """
    def __init__(self,
                 state_manager: 'StateManager',
                 time_manager: 'TimeManager',
                 event_bus: 'EventBus'):
        self._state_manager = state_manager
        self._time_manager = time_manager
        self._event_bus = event_bus
        print("DEBUG: ActionExecutor initialized.")

    def execute_action(self, action: BaseAction, start_time: float | None = None):
        """
        Processes an action. If start_time is provided and in the future,
        it schedules the action to start then. Otherwise, it starts immediately.
        """
        # If no start_time is given, default to starting now.
        if start_time is None:
            start_time = self._time_manager.current_time

        # Calculate the required delay.
        # Ensure the delay is not negative if a past start_time was provided.
        delay = max(0.0, start_time - self._time_manager.current_time)

        if delay > 0:
            # Schedule the _start_action method to be called in the future.
            print(f"\nACTION_EXEC: Scheduling {action.name} to START at sim time {start_time:.2f} (in {delay:.2f} minutes).")
            self._time_manager.schedule_event(self._start_action, delay, action=action)
        else:
            # Execute immediately.
            self._start_action(action)

    def _start_action(self, action: BaseAction):
        """
        This private method contains the logic for actually starting an action.
        It is called either immediately by execute_action or later by the TimeManager.
        """
        print(f"\nACTION_EXEC: Starting {action.name} on {action.target_node_id} at SIM TIME {self._time_manager.current_time:.2f}")

        # 1. Validate resources AT THE TIME OF EXECUTION.
        actor_team = action.actor_team
        cost = action.resource_cost
        
        current_resources = self._state_manager.red_resources if actor_team == Team.RED else self._state_manager.blue_resources
        
        if current_resources < cost:
            print(f"ACTION_EXEC: FAILED. {actor_team.name} has {current_resources:.1f} resources, but {cost} are required.")
            self._event_bus.publish('ACTION_FAILED', {'reason': 'Insufficient Resources', 'action': action.name})
            return

        # 2. Deduct resources.
        if actor_team == Team.RED:
            self._state_manager.red_resources -= cost
        else:
            self._state_manager.blue_resources -= cost
        print(f"ACTION_EXEC: Deducted {cost} from {actor_team.name}. New total: {self._state_manager.red_resources if actor_team == Team.RED else self._state_manager.blue_resources:.1f}")
        
        # 3. Schedule the action's completion.
        completion_time = self._time_manager.current_time + action.duration
        self._time_manager.schedule_event(action.complete, action.duration)
        print(f"ACTION_EXEC: Scheduled {action.name} to COMPLETE in {action.duration:.2f} sim minutes (at sim time {completion_time:.2f}).")

        # 4. Publish an event that the action has started.
        self._event_bus.publish('ACTION_INITIATED', {'action': action.name, 'target': action.target_node_id}) 