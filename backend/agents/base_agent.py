# backend/agents/base_agent.py

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from ..actions.base_action import Team

if TYPE_CHECKING:
    from ..simulation.state_manager import StateManager
    from ..simulation.action_executor import ActionExecutor
    from ..simulation.event_bus import EventBus

class BaseAgent(ABC):
    """
    Abstract base class for AI agents (Red and Blue Teams).
    """
    def __init__(self,
                 team: Team,
                 state_manager: 'StateManager',
                 action_executor: 'ActionExecutor',
                 event_bus: 'EventBus'):
        self.team = team
        self._state_manager = state_manager
        self._action_executor = action_executor
        self._event_bus = event_bus

    @abstractmethod
    def decide_actions(self):
        """
        The core logic of the AI agent. This method is called on each
        tick of the simulation loop, and the agent decides what to do.
        """
        pass