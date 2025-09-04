# backend/simulation/objects/service.py

from dataclasses import dataclass, asdict

@dataclass
class Service:
    """Represents a running service or application on a node."""
    id: str  # e.g., "HTTP_Web_Server", "SSH_Access"
    protocol: str  # e.g., "TCP/80", "TCP/22"

    def to_dict(self):
        """Converts the dataclass to a dictionary."""
        return asdict(self)