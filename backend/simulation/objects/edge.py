# backend/simulation/objects/edge.py

from dataclasses import dataclass, asdict

@dataclass
class Edge:
    """Represents a network connection between two nodes."""
    source_node_id: str
    target_node_id: str
    bidirectional: bool = False
    traffic_type: str = "Generic"  # e.g., "HTTP", "SMB", "Database"
    # Placeholder for more complex firewall logic
    firewall_rules: dict | None = None

    def to_dict(self):
        """Converts the dataclass to a dictionary."""
        return asdict(self)