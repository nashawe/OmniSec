from collections import defaultdict
from typing import Callable, Any

# This component of the OmniSec system allows for all of the moving parts of this simulation to communicate with each other. 
# It works like a PA system. When something happens, that event is published. 
# Whoever is "subscribed" to those types of events will be notified of it. If they are not subscribed, nothing will happen.

class EventBus:
    """
    Central pub-sub messaging system for decoupled communication
    between simulation components.
    """
    def __init__(self):
        self.subscribers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, callback: Callable):
        """Registers a callback function to be invoked when event_type is published."""
        self.subscribers[event_type].append(callback)
        print(f"DEBUG: Subscribed {callback.__name__} to '{event_type}'")

    def unsubscribe(self, event_type: str, callback: Callable):
        """Removes a callback from event_type subscribers."""
        if callback in self.subscribers[event_type]:
            self.subscribers[event_type].remove(callback)
            print(f"DEBUG: Unsubscribed {callback.__name__} from '{event_type}'")

    def publish(self, event_type: str, payload: dict):
        """Notifies all registered subscribers for event_type."""
        # print(f"DEBUG: Publishing event '{event_type}' with payload: {payload}")
        for callback in self.subscribers[event_type]:
            try:
                callback(event_type, payload)
            except Exception as e:
                print(f"ERROR: Event handler {callback.__name__} for '{event_type}' failed: {e}")

# Global instance of EventBus to be used throughout the simulation
# This makes it a singleton, accessible everywhere.
event_bus = EventBus()