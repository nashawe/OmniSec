# OmniSec: Cyber Conflict Simulation Platform (In Development)

## 🎯 Project Thesis & Rationale

OmniSec is a dynamic, multi-agent simulation (MAS) platform conceived to address a critical need in modern cybersecurity research: the ability to observe and test emergent adversarial strategies in a controlled, realistic environment.

This project was initiated to move beyond static network defense analysis and build a system where two autonomous, competing AI agents (Red Team and Blue Team) learn, adapt, and compete in real-time. By building this platform, the focus is placed not just on *what* an attack is, but on the *when* and *why*—creating a research foundation for future **autonomous cyber resilience** using advanced Multi-Agent Reinforcement Learning (MARL) techniques.

## ✨ Key Technical Highlights (In Development)

The core strength of OmniSec lies in its robust, scalable, and highly decoupled architecture.

### 1. Robust Event-Driven Core

*   **Continuous-Time Modeling:** Implemented a sophisticated, asynchronous core utilizing a custom `TimeManager` (backed by a min-heap) to handle complex, variable-duration actions (e.g., Scan: 5.0m, Patch: 10.0m). This design guarantees simulation fidelity and maximum efficiency by eliminating unnecessary checks.
*   **Decoupled Action Flow:** A central `ActionExecutor` processes strategic commands by translating the AI's high-level desire (an **Absolute Start Time** like `t=7.0`) into the required low-level relative delay. This separation ensures AI development is intuitive and strategic, not bogged down in temporal calculations.
*   **Concurrency & Performance:** The simulation runs entirely on a multi-threaded Python backend, safely isolating the simulation loop from the FastAPI control plane to ensure high performance and zero blocking I/O.

### 2. Autonomous Agent Design & MARL Foundation

*   **Heuristic Baseline:** Currently features operational, competitive Red and Blue Team AI agents based on heuristic logic, allowing for continuous, zero-human-input skirmishes.
*   **MARL Architecture Ready:** The entire agent structure is engineered for direct adoption of the **Centralized-Training / Decentralized-Execution (CTDE)** MARL paradigm. This foundation allows for the future integration of algorithms like **MAPPO** or **QMIX**, enabling coordinated, intelligent strategies far beyond rule-based capabilities.

### 3. Scalable Data Modeling

*   **NetworkX Graph Structure:** The virtual network topology is modeled entirely using the **NetworkX** graph library. This is a critical architectural choice that ensures the system is ready for complex operations, including advanced pathfinding for lateral movement and encoding the network state using **Graph Neural Networks (GNNs)** for future AI input.
*   **Single Source of Truth:** A dedicated `StateManager` ensures atomic, consistent updates to all network assets (`Node`, `Vulnerability`, `Edge`), preventing race conditions and maintaining a reliable state snapshot for the AI agents.

### 4. Professional Software Engineering

*   **Clean Separation of Concerns:** The project adheres to robust architectural standards by separating the core simulation logic (FastAPI backend) from the visualization (PySide6 Desktop GUI client).

## 🛠 Tech Stack

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Backend Core** | Python (3.11+) | Simulation logic, AI agents, concurrency. |
| **API** | FastAPI, Uvicorn | Control plane for the desktop GUI. |
| **Network Modeling** | NetworkX | Graph structure, pathfinding, and topology management. |
| **GUI (WIP)** | PySide6 (Qt) | Local desktop application for visualization. |

## ➡️ Next Milestones

The project is currently finalizing the autonomous baseline and preparing for advanced feature development.

1.  **Develop Core Offensive/Defensive Actions:** Implement high-impact actions like `ExploitVulnerability`, `ContainThreat`, and `LateralMovement`.
2.  **Implement Event Feed Visualization:** Build the `EventFeed` widget in the PySide6 GUI to stream and display all critical simulation events (`NODE_COMPROMISED`, `VULNERABILITY_PATCHED`) in real-time.
3.  **Visualization of State:** Implement the core logic for the `NetworkGraphCanvas` to display nodes, edges, and changing node statuses (e.g., color-coding compromise status) based on real-time state updates.
4.  **Zero-Day Mechanics:** Introduce dynamic event handlers to randomly inject new, unknown vulnerabilities into the network during simulation runtime, challenging the defensive AI.
