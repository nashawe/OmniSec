# gui/api_client.py

import json
import asyncio
import threading
import requests
import websockets

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal


# ---------------------------------------------------------------------------
# Worker — runs a plain function in Qt's thread pool (used for HTTP calls)
# ---------------------------------------------------------------------------
class Worker(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.fn(*self.args, **self.kwargs)
        except Exception as e:
            print(f"Error in worker thread: {e}")


# ---------------------------------------------------------------------------
# APIClient
# Handles all communication with the FastAPI backend:
#   - HTTP POST requests for control commands (start, pause, reset, speed)
#   - A persistent WebSocket connection that receives state snapshots
#     and emits them as a Qt signal so the GUI can react
# ---------------------------------------------------------------------------
class APIClient(QObject):

    # This signal is emitted every time a new state snapshot arrives
    # over the WebSocket. The GUI connects to this to update itself.
    # It carries the full snapshot as a Python dict.
    state_updated = Signal(dict)

    def __init__(self, base_url="http://127.0.0.1:8000"):
        super().__init__()
        self.base_url = base_url
        self.thread_pool = QThreadPool()
        self._ws_thread = None
        print(f"APIClient initialized for base URL: {self.base_url}")

    # -----------------------------------------------------------------------
    # WebSocket listener
    # Runs in a separate background thread so it doesn't block the GUI.
    # -----------------------------------------------------------------------
    def start_websocket_listener(self):
        """
        Starts the WebSocket listener in a background thread.
        Call this once when the GUI starts up.
        """
        self._ws_thread = threading.Thread(
            target=self._run_websocket_loop,
            daemon=True  # Thread dies automatically when the app closes
        )
        self._ws_thread.start()
        print("APIClient: WebSocket listener thread started.")

    def _run_websocket_loop(self):
        """
        Runs an asyncio event loop in the background thread.
        This is the thread that actually connects to the WebSocket
        and listens for incoming messages.
        """
        asyncio.run(self._websocket_listener())

    async def _websocket_listener(self):
        """
        Connects to the backend WebSocket and listens forever.
        If the connection drops, it waits 2 seconds and reconnects.
        """
        uri = f"ws://{self.base_url.replace('http://', '')}/ws/state"
        print(f"APIClient: Connecting to WebSocket at {uri}...")

        while True:  # Reconnect loop
            try:
                async with websockets.connect(uri) as ws:
                    print("APIClient: WebSocket connected successfully.")
                    async for message in ws:
                        try:
                            snapshot = json.loads(message)
                            # Emit the Qt signal — this safely crosses the
                            # thread boundary into the GUI thread
                            self.state_updated.emit(snapshot)
                        except json.JSONDecodeError as e:
                            print(f"APIClient: Failed to parse snapshot: {e}")

            except Exception as e:
                print(f"APIClient: WebSocket connection failed: {e}")
                print("APIClient: Retrying in 2 seconds...")
                await asyncio.sleep(2)

    # -----------------------------------------------------------------------
    # HTTP control commands
    # -----------------------------------------------------------------------
    def _send_post_request(self, endpoint: str):
        try:
            url = f"{self.base_url}{endpoint}"
            print(f"APIClient: Sending POST to {url}...")
            response = requests.post(url, timeout=5)
            response.raise_for_status()
            print(f"APIClient: POST to {endpoint} succeeded.")
        except requests.exceptions.ConnectionError:
            print(f"APIClient: Could not connect to backend at {self.base_url}.")
        except requests.exceptions.RequestException as e:
            print(f"APIClient: Request failed: {e}")

    def _execute_in_thread(self, endpoint: str):
        worker = Worker(self._send_post_request, endpoint)
        self.thread_pool.start(worker)

    def start_simulation(self):
        self._execute_in_thread("/api/simulation/start")

    def pause_simulation(self):
        self._execute_in_thread("/api/simulation/pause")

    def reset_simulation(self):
        self._execute_in_thread("/api/simulation/reset/corporate_network")

    def set_simulation_speed(self, speed: float):
        self._execute_in_thread(f"/api/simulation/speed/{speed}")