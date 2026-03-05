# backend/api/main.py

import sys
import os
import asyncio
import json
from enum import Enum
from typing import Set

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.simulation.engine import SimulationEngine
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse


# ---------------------------------------------------------------------------
# Custom JSON encoder — handles Enums and anything else non-serializable
# ---------------------------------------------------------------------------
class SimulationEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.name  # converts PatchStatus.UNPATCHED → "UNPATCHED"
        return super().default(obj)


# ---------------------------------------------------------------------------
# Global simulation engine
# ---------------------------------------------------------------------------
print("API: Creating global SimulationEngine instance...")
simulation_engine = SimulationEngine()
scenario_path = os.path.join(PROJECT_ROOT, "backend", "scenarios", "small_business.json")
simulation_engine.reset_simulation(scenario_path)


# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        print(f"WS: Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)
        print(f"WS: Client disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        dead_connections = set()
        for connection in self.active_connections.copy():
            try:
                await connection.send_text(message)
            except Exception:
                dead_connections.add(connection)
        for dead in dead_connections:
            self.active_connections.discard(dead)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="OmniSec Cyber Conflict Simulation API",
    description="API for managing and interacting with the OmniSec simulation.",
    version="0.0.1",
)


# ---------------------------------------------------------------------------
# Hook EventBus into StateManager
# ---------------------------------------------------------------------------
def _record_all_events(event_type: str, payload: dict):
    simulation_engine.state_manager.record_event(event_type, payload)

_EVENTS_TO_RECORD = [
    "ACTION_INITIATED",
    "ACTION_SUCCESS",
    "ACTION_FAILURE",
    "ACTION_COMPLETED",
    "ACTION_FAILED",
    "RED_TEAM_INFO_GAINED",
    "BLUE_TEAM_VULN_DISCOVERED",
]
for _event_type in _EVENTS_TO_RECORD:
    simulation_engine.event_bus.subscribe(_event_type, _record_all_events)


# ---------------------------------------------------------------------------
# Background broadcast task
# ---------------------------------------------------------------------------
async def state_broadcaster():
    print("WS: State broadcaster started.")
    while True:
        await asyncio.sleep(0.1)

        if manager.active_connections:
            try:
                snapshot = simulation_engine.state_manager.to_dict(
                    simulation_engine.time_manager.current_time
                )
                # SimulationEncoder handles Enum → string automatically
                await manager.broadcast(json.dumps(snapshot, cls=SimulationEncoder))
            except Exception as e:
                print(f"WS: Error building/broadcasting snapshot: {e}")


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(state_broadcaster())
    print("API: Background state broadcaster task created.")


# ---------------------------------------------------------------------------
# HTTP endpoints
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def read_root():
    return "<h1>OmniSec Backend Running</h1><p>Visit <a href='/docs'>/docs</a> for API documentation.</p>"

@app.post("/api/simulation/start")
async def start_simulation():
    simulation_engine.start_simulation()
    return {"message": "Simulation start command sent to engine."}

@app.post("/api/simulation/pause")
async def pause_simulation():
    simulation_engine.pause_simulation()
    return {"message": "Simulation pause command sent to engine."}

@app.post("/api/simulation/reset/{scenario_name}")
async def reset_simulation(scenario_name: str):
    path = os.path.join(PROJECT_ROOT, "backend", "scenarios", f"{scenario_name}.json")
    simulation_engine.reset_simulation(path)
    return {"message": f"Simulation reset command sent to engine for scenario '{scenario_name}'."}

@app.post("/api/simulation/speed/{factor}")
async def set_simulation_speed(factor: float):
    simulation_engine.set_simulation_speed(factor)
    return {"message": f"Simulation speed set to {factor}x."}


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------
@app.websocket("/ws/state")
async def websocket_state(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)