# backend/simulation/objects/node.py

from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import List
from .service import Service
from .vulnerability import Vulnerability

class NodeStatus(Enum):
    OPERATIONAL = auto()
    COMPROMISED_COVERT_FOOTHOLD = auto()
    CONFIRMED_BREACH_PERSISTENT_ACCESS = auto()
    ISOLATED_QUARANTINED = auto()

@dataclass
class Node:
    """Represents an individual device or system in the network."""
    id: str
    name: str  # e.g., "DMZ_WebApp_01"
    node_type: str  # e.g., "Server", "Workstation", "Router", "Firewall"
    
    # Initial configuration (generally static after load)
    services_running: List[Service] = field(default_factory=list)
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    security_posture_score: float = 0.5  # 0.0-1.0, higher is better
    detection_chance_modifier: float = 0.1 # 0.1-1.0, higher is better
    value: float = 1.0  # Criticality/importance for objective calculations
    c2_resource_generation_rate: float = 0.0 # Resources per sim-time if compromised
    exposed_to_internet: bool = False

    # Dynamic state attributes (managed by StateManager)
    current_status: NodeStatus = NodeStatus.OPERATIONAL

    def __post_init__(self):
        # Ensure lists are of the correct type, useful for when loading from JSON
        self.services_running = [Service(**s) if isinstance(s, dict) else s for s in self.services_running]
        self.vulnerabilities = [Vulnerability(**v) if isinstance(v, dict) else v for v in self.vulnerabilities]

    def to_dict(self):
        """Converts the dataclass to a dictionary, handling Enum types."""
        d = asdict(self)
        d['current_status'] = self.current_status.name
        # The asdict function will have already converted nested dataclasses
        return d