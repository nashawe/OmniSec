# backend/api/main.py

import sys
import os

# Get the absolute path of the project's root directory (OmniSec)
# and add it to the Python path. This is the most robust method.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Now that the project root is on the path, we can use absolute imports
# starting from the 'backend' package.
from backend.simulation.engine import SimulationEngine
from fastapi import FastAPI
from fastapi.responses import HTMLResponse


# --- Global Simulation Engine Instance ---
print("API: Creating global SimulationEngine instance...")
simulation_engine = SimulationEngine()
# Use an absolute path for the scenario file to avoid CWD issues
scenario_path = os.path.join(PROJECT_ROOT, "backend", "scenarios", "small_business.json")
simulation_engine.reset_simulation(scenario_path) # We'll adjust the method signature next


app = FastAPI(
    title="OmniSec Cyber Conflict Simulation API",
    description="API for managing and interacting with the OmniSec simulation.",
    version="0.0.1",
)

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
    # Construct the full path to the scenario file
    path = os.path.join(PROJECT_ROOT, "backend", "scenarios", f"{scenario_name}.json")
    simulation_engine.reset_simulation(path)
    return {"message": f"Simulation reset command sent to engine for scenario '{scenario_name}'."}

@app.post("/api/simulation/speed/{factor}")
async def set_simulation_speed(factor: float):
    simulation_engine.set_simulation_speed(factor)
    return {"message": f"Simulation speed set to {factor}x."}