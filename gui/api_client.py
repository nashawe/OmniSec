# gui/api_client.py

import requests
from PySide6.QtCore import QObject, QRunnable, QThreadPool

class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
    def run(self):
        """Execute the work function."""
        try:
            # THE FIX IS HERE
            self.fn(*self.args, **self.kwargs)
        except Exception as e:
            print(f"Error in worker thread: {e}")

class APIClient(QObject):
    def __init__(self, base_url="http://127.0.0.1:8000"):
        super().__init__()
        self.base_url = base_url
        self.thread_pool = QThreadPool()
        print(f"APIClient initialized for base URL: {self.base_url}")

    def _send_post_request(self, endpoint: str):
        try:
            url = f"{self.base_url}{endpoint}"
            print(f"[5] Worker Thread: Sending POST request to {url}...")
            response = requests.post(url, timeout=5) 
            response.raise_for_status()
            print(f"--- SUCCESS ---")
            print(f"Request to {endpoint} successful. Status: {response.status_code}")
        except requests.exceptions.ConnectionError as e:
            print(f"--- CONNECTION FAILED ---")
            print(f"Could not connect to the backend at {self.base_url}.")
            print(f"Is the Uvicorn server running?")
        except requests.exceptions.RequestException as e:
            print(f"--- REQUEST FAILED ---")
            print(f"An error occurred: {e}")

    def _execute_in_thread(self, endpoint: str):
        worker = Worker(self._send_post_request, endpoint)
        self.thread_pool.start(worker)

    def start_simulation(self):
        # --- TRACER ---
        print("[4] APIClient: start_simulation() called. Executing in thread.")
        self._execute_in_thread("/api/simulation/start")

    def pause_simulation(self):
        self._execute_in_thread("/api/simulation/pause")
    def reset_simulation(self):
        self._execute_in_thread("/api/simulation/reset/small_business")
    def set_simulation_speed(self, speed: float):
        self._execute_in_thread(f"/api/simulation/speed/{speed}")