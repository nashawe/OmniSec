# cybersec_project/backend/app/schemas/simulation.py

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from backend.app.schemas.network import NetworkGraphStateSchema # If we embed full state

# --- Simulation Control Schemas ---

class StartSimulationRequest(BaseModel):
    """
    Schema for a request to start or initialize a new simulation.
    """
    scenario_id: str = Field(..., description="Identifier for the scenario to load (e.g., 'mvp_scenario').")
    seed: Optional[int] = Field(default=None, description="Optional seed for the random number generator for reproducibility.")
    # Add other simulation parameters here if needed, e.g., difficulty, specific actor settings

class SimulationStatusResponse(BaseModel):
    """
    Schema for responding with the current status of the simulation.
    """
    simulation_id: Optional[str] = Field(default=None, description="Unique ID of the current simulation instance.")
    is_running: bool = Field(..., description="True if the simulation is currently active or has events to process.")
    current_time: int = Field(..., description="Current simulation time step.")
    total_events_processed: int = Field(default=0, description="Total number of events processed so far in this run.")
    # Could also include a summary of the network state or key metrics here if desired,
    # or direct client to use the /network/state endpoint for full graph details.
    # For example:
    # compromised_nodes_count: int = Field(default=0)
    # active_alerts_count: int = Field(default=0)

class SimulationStepRequest(BaseModel):
    """
    Schema for requesting the simulation to advance by a certain number of steps or until a time.
    """
    steps: Optional[int] = Field(default=1, description="Number of events to process. If specified, 'until_time' is ignored.")
    until_time: Optional[int] = Field(default=None, description="Run simulation until this specific time step is reached or passed. Used if 'steps' is not provided or is 0.")

# --- Event and Log Schemas (for API responses) ---

class LogEntrySchema(BaseModel):
    """
    Pydantic schema for a single log entry from the HistoryManager.
    """
    sim_time: int = Field(..., description="Simulation time step of the log entry.")
    log_type: str = Field(..., description="Category or type of the log entry.")
    message: str = Field(..., description="Human-readable message for the log.")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional structured details of the log.")
    wall_clock_time: str = Field(..., description="ISO formatted real-world timestamp of the log entry.") # Comes as isoformat string

    class Config:
        # Pydantic V2:
        # from_attributes = True
        # Pydantic V1:
        orm_mode = True # For easy conversion from LogEntry entity


class EventLogResponse(BaseModel):
    """
    Schema for responding with a list of simulation log entries.
    """
    logs: List[LogEntrySchema] = Field(..., description="A list of simulation log entries.")
    total_logs_available: int = Field(..., description="Total number of logs available that match the query (if pagination was used).")


# --- Action Related Schemas (Optional, if API exposes actions directly) ---
# For now, actions are internal to events, but you might have API endpoints
# to list available actions or get details about a specific action in the future.

class ActionDetailSchema(BaseModel):
    """
    Schema for providing details about a specific simulation action.
    """
    action_id: str
    name: str
    description: str
    team: str
    cost_time_units: int
    cost_action_points: int
    mitre_attack_id: Optional[str] = None
    mitre_d3fend_id: Optional[str] = None
    # Add other relevant details

# --- Full Simulation State (Combines Network and Status) ---
# This could be used for an endpoint that returns everything in one go.
class FullSimulationStateResponse(BaseModel):
    """
    Schema for returning the complete current state of the simulation,
    including network graph, status, and recent logs.
    """
    status: SimulationStatusResponse
    network_graph: NetworkGraphStateSchema
    recent_logs: List[LogEntrySchema] = Field(default_factory=list, description="A list of recent simulation log entries.")


# --- Example Usage (for ensuring correctness) ---
if __name__ == '__main__':
    print("--- Testing Simulation Schemas ---")

    # Example StartSimulationRequest
    start_req_data = {"scenario_id": "mvp_scenario_v2", "seed": 9876}
    start_req_instance = StartSimulationRequest(**start_req_data)
    print("\nStartSimulationRequest Instance:")
    print(start_req_instance.model_dump_json(indent=2) if hasattr(start_req_instance, 'model_dump_json') else start_req_instance.json(indent=2))
    assert start_req_instance.seed == 9876

    # Example SimulationStatusResponse
    status_res_data = {"simulation_id": "sim_abc_123", "is_running": True, "current_time": 55}
    status_res_instance = SimulationStatusResponse(**status_res_data)
    print("\nSimulationStatusResponse Instance:")
    print(status_res_instance.model_dump_json(indent=2) if hasattr(status_res_instance, 'model_dump_json') else status_res_instance.json(indent=2))
    assert status_res_instance.is_running is True

    # Example LogEntrySchema
    import datetime
    log_entry_data = {
        "sim_time": 50,
        "log_type": "ACTION_LOG",
        "message": "RedTeam_Alpha exploited Web_Server_01",
        "details": {"success_chance": 0.75, "vulnerability": "SQLi_001"},
        "wall_clock_time": datetime.datetime.utcnow().isoformat()
    }
    log_entry_instance = LogEntrySchema(**log_entry_data)
    print("\nLogEntrySchema Instance:")
    print(log_entry_instance.model_dump_json(indent=2) if hasattr(log_entry_instance, 'model_dump_json') else log_entry_instance.json(indent=2))
    assert log_entry_instance.details["success_chance"] == 0.75

    # Example EventLogResponse
    event_log_res_data = {
        "logs": [log_entry_data, log_entry_data], # Using same data for simplicity
        "total_logs_available": 100
    }
    event_log_res_instance = EventLogResponse(
        logs=[LogEntrySchema(**log_entry_data), LogEntrySchema(**log_entry_data)],
        total_logs_available=100
    )
    print("\nEventLogResponse Instance:")
    print(event_log_res_instance.model_dump_json(indent=2) if hasattr(event_log_res_instance, 'model_dump_json') else event_log_res_instance.json(indent=2))
    assert len(event_log_res_instance.logs) == 2

    print("\n--- Simulation Schemas Test Complete ---")