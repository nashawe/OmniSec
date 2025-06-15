# cybersec_project/backend/core/history_manager.py

from typing import List, Dict, Any, Optional
import datetime # For timestamping log entries

class LogEntry:
    """
    Represents a single entry in the simulation's history log.
    """
    def __init__(self,
                 sim_time: int, # Simulation time step when this log entry was created
                 log_type: str, # e.g., "EVENT_PROCESSED", "STATE_CHANGE", "ACTION_LOG", "SIM_MESSAGE"
                 message: str,
                 details: Optional[Dict[str, Any]] = None, # Structured data related to the log
                 wall_clock_time: Optional[datetime.datetime] = None):
        """
        Initializes a LogEntry.

        Args:
            sim_time (int): The simulation time (discrete step) of the log.
            log_type (str): The category or type of the log entry.
            message (str): A human-readable message for the log.
            details (Optional[Dict[str, Any]], optional): Additional structured details.
                                                          Defaults to None.
            wall_clock_time (Optional[datetime.datetime], optional): Real-world timestamp.
                                                                    Defaults to current UTC time.
        """
        self.sim_time: int = sim_time
        self.log_type: str = log_type
        self.message: str = message
        self.details: Dict[str, Any] = details if details is not None else {}
        self.wall_clock_time: datetime.datetime = wall_clock_time if wall_clock_time is not None else datetime.datetime.utcnow()

    def __repr__(self) -> str:
        return f"LogEntry(SimTime={self.sim_time}, Type='{self.log_type}', Msg='{self.message[:50]}...')"

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the LogEntry to a dictionary."""
        return {
            "sim_time": self.sim_time,
            "log_type": self.log_type,
            "message": self.message,
            "details": self.details,
            "wall_clock_time": self.wall_clock_time.isoformat() # ISO format for easy serialization
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogEntry':
        """Creates a LogEntry from a dictionary."""
        return cls(
            sim_time=data["sim_time"],
            log_type=data["log_type"],
            message=data["message"],
            details=data.get("details"),
            wall_clock_time=datetime.datetime.fromisoformat(data["wall_clock_time"]) if "wall_clock_time" in data else datetime.datetime.utcnow()
        )


class HistoryManager:
    """
    Manages the historical record of simulation events, state changes, and log messages.
    Provides an interface to add log entries and retrieve the history.
    """
    def __init__(self, max_history_size: Optional[int] = None):
        """
        Initializes the HistoryManager.

        Args:
            max_history_size (Optional[int], optional): The maximum number of log entries
                                                        to keep in memory. If None, history
                                                        is unbounded (be careful with memory).
                                                        Defaults to None.
        """
        self._history: List[LogEntry] = []
        self.max_history_size: Optional[int] = max_history_size

    def add_log_entry(self,
                      sim_time: int,
                      log_type: str,
                      message: str,
                      details: Optional[Dict[str, Any]] = None) -> None:
        """
        Creates and adds a new log entry to the history.

        Args:
            sim_time (int): The current simulation time.
            log_type (str): The type of log entry.
            message (str): The log message.
            details (Optional[Dict[str, Any]], optional): Structured details for the log.
        """
        entry = LogEntry(sim_time=sim_time, log_type=log_type, message=message, details=details)
        self._history.append(entry)

        if self.max_history_size is not None and len(self._history) > self.max_history_size:
            # Trim old entries if max size is exceeded (FIFO)
            self._history.pop(0)
        
        # For immediate feedback during development, can be removed later
        # print(f"Log[{entry.sim_time}][{entry.log_type}]: {entry.message}")


    def add_action_logs(self, sim_time: int, actor_id: str, action_name: str, log_messages: List[str]):
        """
        Helper method to add multiple log messages from an action's execution.
        """
        for msg in log_messages:
            self.add_log_entry(
                sim_time=sim_time,
                log_type="ACTION_LOG",
                message=msg, # The message already contains actor_id and action_name from action's execute
                details={"actor_id": actor_id, "action_name": action_name}
            )

    def get_history(self, limit: Optional[int] = None, start_time: Optional[int] = None, end_time: Optional[int] = None) -> List[LogEntry]:
        """
        Retrieves the recorded history, with optional filtering.

        Args:
            limit (Optional[int], optional): Maximum number of recent entries to return.
            start_time (Optional[int], optional): Filter entries from this sim_time onwards.
            end_time (Optional[int], optional): Filter entries up to this sim_time.

        Returns:
            List[LogEntry]: A list of log entries.
        """
        filtered_history = self._history

        if start_time is not None:
            filtered_history = [entry for entry in filtered_history if entry.sim_time >= start_time]
        
        if end_time is not None:
            filtered_history = [entry for entry in filtered_history if entry.sim_time <= end_time]

        if limit is not None and len(filtered_history) > limit:
            return filtered_history[-limit:] # Return the most recent 'limit' entries
        
        return filtered_history

    def clear_history(self) -> None:
        """Clears all recorded history."""
        self._history = []
        # print("History cleared.")

    def get_history_as_dicts(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Retrieves history as a list of dictionaries, suitable for API responses.
        Accepts the same arguments as get_history.
        """
        return [entry.to_dict() for entry in self.get_history(**kwargs)]


# --- Example Usage and Testing ---
if __name__ == '__main__':
    print("--- Testing History Manager ---")

    history_mgr = HistoryManager(max_history_size=5) # Keep only last 5 entries

    # Add some initial log entries
    history_mgr.add_log_entry(sim_time=0, log_type="SIM_MESSAGE", message="Simulation started.")
    history_mgr.add_log_entry(sim_time=1, log_type="EVENT_PROCESSED", message="Processed Init Event.", details={"event_id": "evt_001"})
    history_mgr.add_log_entry(sim_time=5, log_type="ACTION_LOG", message="RedTeam_A performed Scan on NodeX.", details={"actor": "RedTeam_A", "action": "Scan"})
    history_mgr.add_log_entry(sim_time=5, log_type="STATE_CHANGE", message="NodeX status changed to 'scanned'.", details={"node": "NodeX", "attr": "status"})
    history_mgr.add_log_entry(sim_time=8, log_type="ACTION_LOG", message="BlueTeam_B performed Patch on NodeX.", details={"actor": "BlueTeam_B", "action": "Patch"})

    print("\n--- Full History (should be max 5 entries) ---")
    for entry in history_mgr.get_history():
        print(f"  SimTime: {entry.sim_time}, Type: {entry.log_type}, Message: {entry.message}, Details: {entry.details}, WallClock: {entry.wall_clock_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    assert len(history_mgr.get_history()) <= 5

    # Add more entries to test max_history_size
    history_mgr.add_log_entry(sim_time=10, log_type="EVENT_PROCESSED", message="Processed Exploit Event.", details={"event_id": "evt_002"})
    history_mgr.add_log_entry(sim_time=10, log_type="ACTION_LOG", message="RedTeam_A performed Exploit on NodeY.", details={"actor": "RedTeam_A", "action": "Exploit"})
    
    print("\n--- History after more entries (still max 5) ---")
    current_history = history_mgr.get_history()
    for entry in current_history:
        print(f"  SimTime: {entry.sim_time}, Type: {entry.log_type}, Message: {entry.message}")
    assert len(current_history) == 5
    assert current_history[0].sim_time == 5 # Oldest entry should now be the one at sim_time 5 (the STATE_CHANGE one)

    print("\n--- Filtered History (last 2 entries) ---")
    for entry in history_mgr.get_history(limit=2):
        print(f"  SimTime: {entry.sim_time}, Message: {entry.message}")
    assert len(history_mgr.get_history(limit=2)) == 2

    print("\n--- Filtered History (from sim_time 8 onwards) ---")
    for entry in history_mgr.get_history(start_time=8):
        print(f"  SimTime: {entry.sim_time}, Message: {entry.message}")
    assert all(entry.sim_time >= 8 for entry in history_mgr.get_history(start_time=8))


    print("\n--- History as Dictionaries (last 1 entry) ---")
    dict_history = history_mgr.get_history_as_dicts(limit=1)
    print(dict_history)
    assert isinstance(dict_history, list) and len(dict_history) == 1
    assert isinstance(dict_history[0], dict)
    assert "wall_clock_time" in dict_history[0] and isinstance(dict_history[0]["wall_clock_time"], str)


    history_mgr.clear_history()
    print(f"\nHistory size after clear: {len(history_mgr.get_history())}")
    assert len(history_mgr.get_history()) == 0


    print("\n--- History Manager Test Complete ---")