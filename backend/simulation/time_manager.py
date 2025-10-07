# backend/simulation/time_manager.py

import heapq
import time
from typing import Callable, Any

class TimeManager:
    def __init__(self, initial_time: float = 0.0):
        self.current_time: float = initial_time
        self.event_queue: list[tuple[float, int, Callable, tuple, dict]] = []
        self._next_id: int = 0
        self._is_paused: bool = False
        self._simulation_speed: float = 1.0

    def schedule_event(self, callback: Callable, delay: float, *args, **kwargs):
        event_time = self.current_time + delay
        heapq.heappush(self.event_queue, (event_time, self._next_id, callback, args, kwargs))
        self._next_id += 1
        # A new debug print to confirm scheduling
        print(f"\n[TM_DEBUG] Event '{callback.__name__}' scheduled for time {event_time:.2f}")

    def next_event_time(self) -> float | None:
        if not self.event_queue:
            return None
        return self.event_queue[0][0]

# In backend/simulation/time_manager.py

    def process_events_until(self, target_time: float):
        if self._is_paused:
            return

        # --- THE FIX IS HERE ---
        # 1. Get the next event time.
        next_event_t = self.next_event_time()
        # 2. Format the time string OUTSIDE the main print statement.
        next_event_str = f"{next_event_t:.2f}" if next_event_t is not None else "N/A"

        # 3. Use the pre-formatted string in the print statement.
        print(f"\r[TM_DEBUG] Processing... Current Time: {self.current_time:.2f} | Target Time: {target_time:.2f} | Next Event @ {next_event_str}", end="")

        events_to_execute = []
        while self.event_queue and self.event_queue[0][0] <= target_time:
            print("\n[TM_DEBUG] >>> Event condition MET! <<<")
            event_time, _, callback, args, kwargs = heapq.heappop(self.event_queue)
            events_to_execute.append((event_time, callback, args, kwargs))

        for event_time, callback, args, kwargs in events_to_execute:
            self.current_time = event_time
            try:
                callback(*args, **kwargs)
            except Exception as e:
                print(f"\nERROR: Callback '{callback.__name__}' failed during execution: {e}")

        self.current_time = max(self.current_time, target_time)


    def set_speed(self, speed: float):
        if speed < 0:
            raise ValueError("Simulation speed cannot be negative.")
        self._simulation_speed = speed
        print(f"\nDEBUG: Simulation speed set to {speed}x.")

    def get_speed(self) -> float:
        return self._simulation_speed

    def pause(self):
        self._is_paused = True
        print("\nDEBUG: Simulation paused.")

    def resume(self):
        self._is_paused = False
        print("\nDEBUG: Simulation resumed.")

    def is_paused(self) -> bool:
        return self._is_paused

    def reset(self, initial_time: float = 0.0):
        self.current_time = initial_time
        self.event_queue = []
        self._next_id = 0
        self._is_paused = False
        self._simulation_speed = 1.0
        print("\nDEBUG: TimeManager reset.")

# We don't need a global instance here, the engine will manage it.
# So we comment this out to avoid confusion.
# time_manager = TimeManager()