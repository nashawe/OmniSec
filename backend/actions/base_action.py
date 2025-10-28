# backend/actions/base_action.py

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import TYPE_CHECKING
import uuid

# This is a common pattern to avoid circular imports.
# The engine needs to know about actions, and actions need to know about the engine's components.
if TYPE_CHECKING:
    from backend.simulation.state_manager import StateManager
    from backend.simulation.event_bus import EventBus

class Team(Enum):
    RED = auto()
    BLUE = auto()

class BaseAction(ABC):
    """
    Abstract base class for all actions in the simulation.
    It defines the common interface and execution flow.
    """
    def __init__(self,
                 state_manager: 'StateManager',
                 event_bus: 'EventBus',
                 actor_team: Team,
                 target_node_id: str,
                 duration: float,
                 resource_cost: float):
        
        self.action_id = str(uuid.uuid4()) # A unique ID for this specific action instance
        self._state_manager = state_manager
        self._event_bus = event_bus
        
        # Core attributes defined by subclasses
        self.actor_team = actor_team
        self.target_node_id = target_node_id
        self.duration = duration
        self.resource_cost = resource_cost

    @abstractmethod
    def execute_logic(self) -> bool:
        """
        Contains the core success/failure logic of the action.
        This is where the "dice roll" happens.
        Must be implemented by subclasses.
        Returns True for success, False for failure.
        """
        pass

    @abstractmethod
    def apply_effects_on_success(self):
        """
        Defines what happens to the simulation state if execute_logic() is True.
        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def apply_effects_on_failure(self):
        """
        Defines what happens to the simulation state if execute_logic() is False.
        Must be implemented by subclasses.
        """
        pass

    def complete(self):
        """
        This is the callback function that the TimeManager will execute.
        It orchestrates the action's conclusion. This method is NOT abstract.
        """
        print(f"\nACTION: Completing action {self.__class__.__name__} on {self.target_node_id}")
        
        if self.execute_logic():
            self.apply_effects_on_success()
            self._event_bus.publish('ACTION_SUCCESS', {'action': self.__class__.__name__, 'target': self.target_node_id})
        else:
            self.apply_effects_on_failure()
            self._event_bus.publish('ACTION_FAILURE', {'action': self.__class__.__name__, 'target': self.target_node_id})
        
        self._event_bus.publish('ACTION_COMPLETED', {'action_id': self.action_id})