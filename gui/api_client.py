# gui/api_client.py

import requests
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool

class Worker(QRunnable):
    """
    Worker thread for running blocking tasks like network requests
    without freezing the GUI.
    """
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """Execute the work function."""
        try:
            self.fn(*self.args, **self.kwargs)
        except Exception as e:
            print(f"Error in worker thread: {e}")

class APIClient(QObject):
    """
    Handles all communication with the backend FastAPI server.
    Runs requests in a separate thread pool to keep the GUI responsive.
    """
    # Define signals that can be emitted to notify the GUI of results.
    # We can add more later, e.g., for success/failure messages.
    
    def __init__(self, base_url="http://127.0.0.1:8000"):
        super().__init__()
        self.base_url = base_url
        self.thread_pool = QThreadPool()
        print(f"APIClient initialized for base URL: {self.base_url}")
        print(f"Max threads in pool: {self.thread_pool.maxThreadCount()}")

    def _send_post_request(self, endpoint: str):
        """Helper function to send a POST request."""
        try:
            url = f"{self.base_url}{endpoint}"
            print(f"Sending POST request to {url}...")
            response = requests.post(url)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            print(f"Request to {endpoint} successful. Status: {response.status_code}")
            # We could emit a signal with response.json() if needed
        except requests.exceptions.RequestException as e:
            print(f"Error making request to {endpoint}: {e}")

    def _execute_in_thread(self, endpoint: str):
        """Executes the POST request in a worker thread."""
        worker = Worker(self._send_post_request, endpoint)
        self.thread_pool.start(worker)

    # --- Public methods to be called by the GUI ---
    
    def start_simulation(self):
        self._execute_in_thread("/api/simulation/start")

    def pause_simulation(self):
        self._execute_in_thread("/api/simulation/pause")

    def reset_simulation(self):
        # Note: The blueprint specified a scenario name, we'll hardcode 'default' for now
        self._execute_in_thread("/api/simulation/reset/default")

    def set_simulation_speed(self, speed: float):
        self._execute_in_thread(f"/api/simulation/speed/{speed}")