# backend/simulation/time_manager.py

import heapq
import time
from typing import Callable, Any

class TimeManager:
    """
    Manages the continuous, asynchronous simulation clock and schedules future events.
    """
    def __init__(self, initial_time: float = 0.0):
        self.current_time: float = initial_time
        # Min-heap of (event_time, unique_id, callback_function, *args, **kwargs) tuples
        self.event_queue: list[tuple[float, int, Callable, tuple, dict]] = []
        self._next_id: int = 0
        self._is_paused: bool = False
        self._simulation_speed: float = 1.0

    def schedule_event(self, callback: Callable, delay: float, *args, **kwargs):
        """Schedules callback to run delay units from current_time."""
        event_time = self.current_time + delay
        heapq.heappush(self.event_queue, (event_time, self._next_id, callback, args, kwargs))
        self._next_id += 1

    def next_event_time(self) -> float | None:
        """Returns time of the next scheduled event without removing it."""
        if not self.event_queue:
            return None
        return self.event_queue[0][0]

    def process_events_until(self, target_time: float):
        """
        Advances current_time to target_time. Executes all callbacks in event_queue
        whose event_time is <= target_time.
        """
        if self._is_paused:
            return

        events_to_execute = []
        while self.event_queue and self.event_queue[0][0] <= target_time:
            event_time, _, callback, args, kwargs = heapq.heappop(self.event_queue)
            events_to_execute.append((event_time, callback, args, kwargs))

        for event_time, callback, args, kwargs in events_to_execute:
            # Update current_time to the time of the event being executed
            self.current_time = event_time
            try:
                callback(*args, **kwargs)
            except Exception as e:
                print(f"\nERROR: Callback '{callback.__name__}' failed during execution: {e}")

        # After processing all due events, set current_time to the target_time
        self.current_time = max(self.current_time, target_time)

    def set_speed(self, speed: float):
        """Sets the simulation speed multiplier."""
        if speed < 0:
            raise ValueError("Simulation speed cannot be negative.")
        self._simulation_speed = speed

    def get_speed(self) -> float:
        """Returns the current simulation speed."""
        return self._simulation_speed

    def pause(self):
        """Pauses the simulation."""
        self._is_paused = True

    def resume(self):
        """Resumes the simulation."""
        self._is_paused = False

    def is_paused(self) -> bool:
        """Returns True if the simulation is paused, False otherwise."""
        return self._is_paused

    def reset(self, initial_time: float = 0.0):
        """Resets the time manager to its initial state."""
        self.current_time = initial_time
        self.event_queue = []
        self._next_id = 0
        self._is_paused = False
        self._simulation_speed = 1.0