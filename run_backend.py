import sys
import os

# Add the project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.main import run_backend

if __name__ == "__main__":
    run_backend()
