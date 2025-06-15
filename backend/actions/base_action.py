# cybersec_project/backend/actions/base_action.py

import uuid
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple

# Forward reference for type hinting StateManager without circular imports
# This is a common pattern when classes depend on each other for type hints.
# The actual import will happen at runtime or within methods.
if False: # TYPE_CHECKING
    from backend.core.state_manager import StateManager # type: ignore
    from backend.core.event_manager import SimulationEvent # type: ignore


class SimulationAction(ABC):
    """
    Abstract Base Class for all actions that can be performed in the simulation.
    Specific actions (e.g., Exploit, Patch, Scan) will inherit from this class.
    """
    def __init__(self,
                 action_id: Optional[str] = None,
                 name: str = "Unnamed Action",
                 description: str = "No description provided.",
                 team: str = "Neutral", # "Red", "Blue", "Neutral", "Green" (for automated/environmental)
                 cost_time_units: int = 1, # Default time units this action takes to complete
                 cost_action_points: int = 1, # Default action points consumed by the actor
                 success_probability: float = 1.0, # Base probability of success (0.0 to 1.0)
                 mitre_attack_id: Optional[str] = None, # e.g., "T1190"
                 mitre_d3fend_id: Optional[str] = None, # e.g., "D3-IPBA"
                 prerequisites: Optional[List[Dict[str, Any]]] = None, # e.g., [{"node_status": "operational"}, {"vulnerability_present": "SQLi_001"}]
                 effects: Optional[List[Dict[str, Any]]] = None # e.g., [{"node_attribute_change": {"status": "compromised"}}]
                 ):
        """
        Initializes a SimulationAction.

        Args:
            action_id (Optional[str], optional): A unique identifier for this specific action instance. Defaults to a new UUID if None.
            name (str, optional): Human-readable name of the action. Defaults to "Unnamed Action".
            description (str, optional): Detailed description of the action. Defaults to "No description provided.".
            team (str, optional): The team performing the action (e.g., "Red", "Blue"). Defaults to "Neutral".
            cost_time_units (int, optional): Number of simulation time units the action takes. Defaults to 1.
            cost_action_points (int, optional): Number of action points this action costs the actor. Defaults to 1.
            success_probability (float, optional): Base probability of the action succeeding. Defaults to 1.0.
            mitre_attack_id (Optional[str], optional): Associated MITRE ATT&CK Technique ID. Defaults to None.
            mitre_d3fend_id (Optional[str], optional): Associated MITRE D3FEND Technique ID. Defaults to None.
            prerequisites (Optional[List[Dict[str, Any]]], optional): Conditions that must be met for the action to be attempted. Defaults to None.
            effects (Optional[List[Dict[str, Any]]], optional): Expected outcomes if the action is successful. Defaults to None.
        """
        self.action_id: str = action_id if action_id is not None else str(uuid.uuid4())
        self.name: str = name
        self.description: str = description
        self.team: str = team
        self.cost_time_units: int = cost_time_units
        self.cost_action_points: int = cost_action_points
        self.base_success_probability: float = success_probability # Store the base, can be modified by context

        self.mitre_attack_id: Optional[str] = mitre_attack_id
        self.mitre_d3fend_id: Optional[str] = mitre_d3fend_id

        # These are more for declarative definition and could be used by AI for planning
        # The actual logic might be more complex in the execute() method.
        self.prerequisites: List[Dict[str, Any]] = prerequisites if prerequisites is not None else []
        self.effects_on_success: List[Dict[str, Any]] = effects if effects is not None else []

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id='{self.action_id}', name='{self.name}', team='{self.team}')"

    def check_prerequisites(self, state_manager: 'StateManager', target_node_id: Optional[str] = None, source_node_id: Optional[str] = None, actor_id: Optional[str] = None) -> bool:
        """
        Checks if all prerequisites for this action are met in the current simulation state.
        This is a generic checker; specific actions might override or extend this.

        Args:
            state_manager (StateManager): The current state of the simulation.
            target_node_id (Optional[str]): The ID of the target node, if applicable.
            source_node_id (Optional[str]): The ID of the source node, if applicable (e.g., for lateral movement).
            actor_id (Optional[str]): The ID of the actor attempting the action.

        Returns:
            bool: True if all prerequisites are met, False otherwise.
        """
        # Basic implementation - can be expanded for more complex declarative prerequisites
        # For now, we'll assume prerequisite logic is handled within the execute method of subclasses
        # or that the AI planning the action will check these.
        # Example:
        # if self.prerequisites:
        #     for prereq in self.prerequisites:
        #         if "node_status" in prereq and target_node_id:
        #             node = state_manager.network_graph.get_node_object(target_node_id)
        #             if not node or node.status != prereq["node_status"]:
        #                 return False
        #         # Add more prerequisite checks here
        return True # Defaulting to True for now, subclasses will implement more specific checks

    @abstractmethod
    def execute(self,
                state_manager: 'StateManager',
                current_time: int,
                target_node_id: Optional[str] = None,
                source_node_id: Optional[str] = None,
                actor_id: Optional[str] = None,
                **kwargs: Any) -> Tuple[List['SimulationEvent'], List[Dict[str, Any]], List[str]]:
        """
        Executes the action, updating the simulation state and potentially scheduling new events.
        This method MUST be implemented by all concrete action subclasses.

        Args:
            state_manager (StateManager): The manager for the current simulation state.
                                          Allows the action to query and modify the state.
            current_time (int): The current simulation timestamp when the action's effects occur.
            target_node_id (Optional[str]): The ID of the primary target node for this action.
            source_node_id (Optional[str]): The ID of the source node (e.g., for attacks originating from a compromised host).
            actor_id (Optional[str]): The ID of the actor performing the action.
            **kwargs: Additional action-specific parameters.

        Returns:
            Tuple[List[SimulationEvent], List[Dict[str, Any]], List[str]]:
                - A list of new SimulationEvent objects to be scheduled.
                - A list of dictionaries representing direct state changes made by this action.
                  (e.g., [{"type": "node_update", "node_id": "X", "attribute": "status", "value": "compromised"}])
                - A list of log messages describing the outcome of the action.
        """
        pass # Subclasses must implement this

    def calculate_success_chance(self, state_manager: 'StateManager', target_node_id: Optional[str] = None, source_node_id: Optional[str] = None, actor_id: Optional[str] = None) -> float:
        """
        Calculates the actual probability of success for this action instance,
        considering the base probability and any contextual factors from the simulation state
        (e.g., target's security posture, actor's skill, active defenses).

        Args:
            state_manager (StateManager): The current state of the simulation.
            target_node_id (Optional[str]): The ID of the target node, if applicable.
            source_node_id (Optional[str]): The ID of the source node, if applicable.
            actor_id (Optional[str]): The ID of the actor attempting the action.

        Returns:
            float: The calculated success probability (between 0.0 and 1.0).
        """
        # Default implementation: just returns the base probability.
        # Subclasses can override this to add more complex logic.
        # For example, an exploit might be less likely against a node with high security_posture.
        return self.base_success_probability

if __name__ == '__main__':
    # This class is abstract, so direct instantiation is not intended for use.
    # This section is primarily for ensuring the file is syntactically correct
    # and to illustrate how subclasses might look.

    print("--- SimulationAction Base Class ---")
    print("This is an abstract base class. Subclasses will implement specific actions.")

    # Example of how a concrete class might look (illustrative, not functional here)
    class DummyAction(SimulationAction):
        def __init__(self, name="Dummy Action"):
            super().__init__(name=name, description="A simple dummy action.", team="Neutral")

        def execute(self, state_manager: 'StateManager', current_time: int, target_node_id: Optional[str] = None, source_node_id: Optional[str] = None, actor_id: Optional[str] = None, **kwargs: Any) -> Tuple[List['SimulationEvent'], List[Dict[str, Any]], List[str]]:
            log_message = f"{current_time}: Actor '{actor_id}' performed '{self.name}'"
            if target_node_id:
                log_message += f" on target '{target_node_id}'"
            print(log_message)
            # In a real action, you'd interact with state_manager and return actual events/changes.
            return [], [], [log_message]

    # Note: Cannot instantiate StateManager or SimulationEvent here without full imports,
    # so a true test of DummyAction execution would be in a more integrated test file.
    dummy = DummyAction()
    print(f"Created: {dummy}")
    # dummy_events, dummy_changes, dummy_logs = dummy.execute(None, 0, "node1", actor_id="TestActor") # This would fail without a real StateManager
    print("Base class structure seems OK.")