# backend/simulation/objects/node.py

from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import List
from .service import Service
from .vulnerability import Vulnerability


class NodeStatus(Enum):
    # Blue territory — node is clean
    OPERATIONAL = auto()

    # Reconnaissance — Red is looking but not yet inside
    PORT_SCANNED = auto()           # Red knows which ports are open
    SERVICE_FINGERPRINTED = auto()  # Red knows exactly what software is running

    # Initial Access — Red is inside
    INITIAL_ACCESS_GAINED = auto()  # Exploit or phish succeeded

    # Escalation — Red has full control of this machine
    PRIVILEGED_ACCESS = auto()      # Red has admin / root on this node

    # Credential theft — Red has stolen auth material from this node
    CREDENTIALS_DUMPED = auto()     # Passwords or hashes stolen from this node

    # Lateral movement — Red reached this node from another
    LATERAL_ACCESS = auto()         # Red hopped here using stolen creds

    # Evasion — Red has gone quiet on this node
    EVASION_ACTIVE = auto()         # Logs cleared, AV disabled

    # Command & Control — Red has a persistent backdoor here
    C2_ESTABLISHED = auto()         # Beacon is active and phoning home

    # Exfiltration — data is being stolen
    DATA_STAGED = auto()            # Data copied locally, ready to send out
    DATA_EXFILTRATED = auto()       # Data successfully sent outside the network

    # Blue response
    ISOLATED_QUARANTINED = auto()   # Blue team cut this node off


@dataclass
class Node:
    """Represents a single device or system in the network."""

    id: str
    name: str
    node_type: str  # "Server", "Workstation", "Firewall", "Router"

    # Static config — set at load time, does not change during sim
    services_running: List[Service] = field(default_factory=list)
    vulnerabilities: List[Vulnerability] = field(default_factory=list)
    security_posture_score: float = 0.5       # 0.0-1.0, higher = harder to attack
    detection_chance_modifier: float = 0.1    # 0.1-1.0, higher = more likely to catch Red
    value: float = 1.0                        # How valuable this node is as a target
    c2_resource_generation_rate: float = 0.0  # Resources per tick if C2 is active here
    exposed_to_internet: bool = False
    has_admin_users: bool = False             # True if privileged users log into this node
    smb_enabled: bool = False                 # True if SMB file sharing is running
    rdp_enabled: bool = False                 # True if RDP remote desktop is enabled

    # Dynamic state — changes as the sim runs
    current_status: NodeStatus = NodeStatus.OPERATIONAL

    def __post_init__(self):
        # Handles nodes loaded from JSON as plain dicts
        self.services_running = [
            Service(**s) if isinstance(s, dict) else s
            for s in self.services_running
        ]
        self.vulnerabilities = [
            Vulnerability(**v) if isinstance(v, dict) else v
            for v in self.vulnerabilities
        ]

    def to_dict(self):
        """Returns a JSON-serialisable dict. Converts Enum to string."""
        d = asdict(self)
        d['current_status'] = self.current_status.name
        return d