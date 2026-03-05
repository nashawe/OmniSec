# backend/agents/red_team_ai.py

import random
from .base_agent import BaseAgent
from backend.actions.base_action import Team
from backend.actions.red_actions import ScanNode

class RedTeamAI(BaseAgent):
    """
    A simple, rule-based AI for the Red Team.
    """
    def __init__(self, state_manager, action_executor, event_bus):
        super().__init__(Team.RED, state_manager, action_executor, event_bus)
        
        # --- AI's Internal State ---
        # A simple flag to prevent the AI from taking multiple actions at once.
        self._is_busy = False 
        
        # A simple knowledge base: a list of node IDs it wants to scan.
        self._unscanned_targets = []
        
        self.initialize_knowledge()

        # Subscribe to the event bus to know when its actions are complete.
        self._event_bus.subscribe("ACTION_COMPLETED", self._on_action_completed)

    def initialize_knowledge(self):
        """Populates the AI's list of targets from the current state."""
        all_node_ids = self._state_manager.network_graph.graph.nodes()
        self._unscanned_targets = list(all_node_ids)
        random.shuffle(self._unscanned_targets) # Randomize the scan order
        print(f"RED_AI: Initialized with {len(self._unscanned_targets)} unscanned targets.")

    def _on_action_completed(self, event_type, payload):
        """Event handler that resets the 'busy' flag."""
        # A more advanced AI would check if the completed action was its own.
        # For our simple AI, we'll assume any completed action frees it up.
        print("\nRED_AI: Action completed. Ready for new task.")
        self._is_busy = False

    def decide_actions(self):
        """
        The AI's "brain". Called on every tick of the simulation loop.
        """
        # If the AI is already waiting for an action to complete, do nothing.
        if self._is_busy:
            return

        # If there are still targets to scan, pick one.
        if self._unscanned_targets:
            # Get the next target and remove it from the list.
            target_id = self._unscanned_targets.pop(0)
            
            print(f"\nRED_AI: Decided to scan target '{target_id}'.")
            
            # Create the action.
            scan_action = ScanNode(self._state_manager, self._event_bus, target_id)
            
            # Execute the action (this will start immediately).
            self._action_executor.execute_action(scan_action)
            
            # Set the busy flag so we don't try to do anything else.
            self._is_busy = True