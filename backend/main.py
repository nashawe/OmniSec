import uvicorn
from api.main import app as fastapi_app # Import the FastAPI app instance

def run_backend():
    """
    Function to start the FastAPI Uvicorn server.
    This is the main entry point for the backend.
    """
    print("Starting OmniSec Backend (FastAPI + Uvicorn)...")
    # The 'api.main:app' string tells Uvicorn to look for 'app'
    # inside 'main.py' within the 'api' directory.
    uvicorn.run(fastapi_app, host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    run_backend()