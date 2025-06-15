# cybersec_project/backend/core/event_manager.py

import heapq
from typing import List, Any, Optional, Callable

# Forward reference for type hinting SimulationAction without circular imports
if False: # TYPE_CHECKING
    from backend.actions.base_action import SimulationAction # type: ignore

class SimulationEvent:
    """
    Represents an event scheduled to occur in the simulation.
    Events are processed in chronological order based on their timestamp.
    """
    # Class variable to ensure unique IDs for events with the same timestamp for stable sorting
    _next_event_seq = 0

    def __init__(self,
                 timestamp: int,
                 event_type: str, # e.g., "PerformAction", "NodeStateChange", "DynamicVulnerability"
                 actor_id: Optional[str] = None, # ID of the actor initiating or affected by the event
                 action: Optional['SimulationAction'] = None, # The specific action to perform, if event_type is "PerformAction"
                 target_node_id: Optional[str] = None, # Target of the action/event
                 source_node_id: Optional[str] = None, # Source of the action/event
                 priority: int = 0, # Lower numbers have higher priority for events at same timestamp
                 data: Optional[dict] = None): # Any additional data associated with the event
        """
        Initializes a SimulationEvent.

        Args:
            timestamp (int): The simulation time at which this event should occur.
            event_type (str): A string identifying the type of event.
            actor_id (Optional[str], optional): ID of the actor involved. Defaults to None.
            action (Optional[SimulationAction], optional): The action object to execute. Defaults to None.
            target_node_id (Optional[str], optional): Target node ID. Defaults to None.
            source_node_id (Optional[str], optional): Source node ID. Defaults to None.
            priority (int, optional): Priority for events at the same timestamp. Lower is earlier. Defaults to 0.
            data (Optional[dict], optional): Additional event-specific data. Defaults to None.
        """
        self.timestamp: int = timestamp
        self.event_type: str = event_type
        self.actor_id: Optional[str] = actor_id
        self.action: Optional['SimulationAction'] = action
        self.target_node_id: Optional[str] = target_node_id
        self.source_node_id: Optional[str] = source_node_id
        self.priority: int = priority
        self.data: dict = data if data is not None else {}

        # Sequence number for tie-breaking in the priority queue
        self.sequence_num: int = SimulationEvent._next_event_seq
        SimulationEvent._next_event_seq += 1

        # Unique ID for the event instance, useful for logging or referencing
        import uuid
        self.event_id: str = str(uuid.uuid4())


    def __lt__(self, other: 'SimulationEvent') -> bool:
        """
        Comparison method for the priority queue (heapq).
        Events are primarily sorted by timestamp, then by priority, then by sequence number.
        """
        if self.timestamp != other.timestamp:
            return self.timestamp < other.timestamp
        if self.priority != other.priority:
            return self.priority < other.priority # Lower priority number means higher actual priority
        return self.sequence_num < other.sequence_num

    def __repr__(self) -> str:
        action_name = self.action.name if self.action else "N/A"
        return (f"Event(id={self.event_id[:8]}, ts={self.timestamp}, type='{self.event_type}', "
                f"actor='{self.actor_id}', action='{action_name}', target='{self.target_node_id}')")


class EventManager:
    """
    Manages the scheduling and retrieval of simulation events using a min-priority queue (heapq).
    Events are processed based on their timestamp.
    """
    def __init__(self):
        self._event_queue: List[SimulationEvent] = [] # Stores (timestamp, priority, seq_num, event_object)
        SimulationEvent._next_event_seq = 0 # Reset sequence for each EventManager instance

    def schedule_event(self, event: SimulationEvent) -> None:
        """
        Adds a new event to the event queue.

        Args:
            event (SimulationEvent): The event object to schedule.
        """
        heapq.heappush(self._event_queue, event)
        # print(f"Scheduled: {event}") # For debugging

    def get_next_event(self) -> Optional[SimulationEvent]:
        """
        Retrieves and removes the next event (earliest timestamp) from the queue.

        Returns:
            Optional[SimulationEvent]: The next event, or None if the queue is empty.
        """
        if not self._event_queue:
            return None
        return heapq.heappop(self._event_queue)

    def peek_next_event_timestamp(self) -> Optional[int]:
        """
        Returns the timestamp of the next event without removing it from the queue.

        Returns:
            Optional[int]: The timestamp of the next event, or None if the queue is empty.
        """
        if not self._event_queue:
            return None
        return self._event_queue[0].timestamp # The first element in a min-heap is the smallest

    def is_empty(self) -> bool:
        """
        Checks if the event queue is empty.

        Returns:
            bool: True if the queue is empty, False otherwise.
        """
        return not bool(self._event_queue)

    def clear_events(self) -> None:
        """
        Removes all events from the queue.
        """
        self._event_queue = []
        SimulationEvent._next_event_seq = 0 # Reset sequence counter
        # print("Event queue cleared.")


# --- Example Usage and Testing ---
if __name__ == '__main__':
    print("--- Testing Event Manager ---")

    # Mock SimulationAction for testing event scheduling
    class MockAction:
        def __init__(self, name="MockAction"):
            self.name = name

    action1 = MockAction("ScanNetwork")
    action2 = MockAction("ExploitService")

    # Create some events
    event1 = SimulationEvent(timestamp=10, event_type="PerformAction", action=action1, actor_id="RedTeam_A", target_node_id="Server1")
    event2 = SimulationEvent(timestamp=5, event_type="PerformAction", action=action2, actor_id="RedTeam_B", target_node_id="Server2", priority=-1) # Higher priority
    event3 = SimulationEvent(timestamp=10, event_type="NodeStateChange", data={"new_status": "down"}, target_node_id="Firewall1") # Same time as event1, default priority
    event4 = SimulationEvent(timestamp=10, event_type="PerformAction", action=MockAction("PatchSystem"), actor_id="BlueTeam_X", target_node_id="Server1", priority=1) # Lower priority

    # Test EventManager
    event_manager = EventManager()
    print(f"Is queue empty initially? {event_manager.is_empty()}")

    event_manager.schedule_event(event1)
    event_manager.schedule_event(event2)
    event_manager.schedule_event(event3)
    event_manager.schedule_event(event4)

    print(f"Is queue empty after scheduling? {event_manager.is_empty()}")
    print(f"Timestamp of next event: {event_manager.peek_next_event_timestamp()}")

    print("\nProcessing events:")
    processed_order = []
    while not event_manager.is_empty():
        next_event = event_manager.get_next_event()
        if next_event:
            processed_order.append(next_event)
            print(f"  Processing: {next_event}")

    # Verify the order of processing
    # Expected order: event2 (ts=5, prio=-1), event1 (ts=10, prio=0, seq earlier), event3 (ts=10, prio=0, seq later), event4 (ts=10, prio=1)
    assert len(processed_order) == 4
    assert processed_order[0] == event2, f"Expected event2 first, got {processed_order[0].event_id}"
    assert processed_order[1] == event1, f"Expected event1 second, got {processed_order[1].event_id}"
    assert processed_order[2] == event3, f"Expected event3 third, got {processed_order[2].event_id}"
    assert processed_order[3] == event4, f"Expected event4 fourth, got {processed_order[3].event_id}"


    print(f"\nIs queue empty after processing all events? {event_manager.is_empty()}")

    # Test clearing events
    event_manager.schedule_event(SimulationEvent(timestamp=100, event_type="Test"))
    print(f"Queue size before clear: {len(event_manager._event_queue)}")
    event_manager.clear_events()
    print(f"Queue size after clear: {len(event_manager._event_queue)}")
    assert event_manager.is_empty()

    print("\n--- Event Manager Test Complete ---")