# OmniSec: Cyber Conflict Simulation Platform

OmniSec is a real-time cyber attack simulation platform featuring an autonomous AI adversary that walks the full **MITRE ATT&CK kill chain** against a configurable network topology. A FastAPI backend drives the simulation engine while a PySide6 desktop GUI visualizes every stage of the attack in real time over WebSocket.

---

## Table of Contents

- [Overview](#overview)
- [Demo](#demo)
- [Architecture](#architecture)
- [Backend Deep Dive](#backend-deep-dive)
  - [Simulation Engine](#simulation-engine)
  - [Time Manager](#time-manager)
  - [Event Bus](#event-bus)
  - [Action System](#action-system)
  - [State Manager](#state-manager)
  - [Red Team AI (FSM)](#red-team-ai-fsm)
  - [Network Graph](#network-graph)
  - [REST & WebSocket API](#rest--websocket-api)
- [GUI Deep Dive](#gui-deep-dive)
  - [API Client](#api-client)
  - [Network Graph Canvas](#network-graph-canvas)
  - [Event Feed](#event-feed)
  - [Theme Engine](#theme-engine)
- [Scenarios](#scenarios)
- [MITRE ATT&CK Coverage](#mitre-attck-coverage)
- [Tech Stack](#tech-stack)
- [Running the Project](#running-the-project)

---

## Overview

OmniSec simulates a complete adversarial intrusion from initial reconnaissance all the way through to data exfiltration — with no human input once the simulation starts. The Red Team AI uses a **Finite State Machine (FSM)** whose states are drawn directly from the MITRE ATT&CK framework. Every action taken by the AI modifies the shared `StateManager`, publishes events to an `EventBus`, and is scheduled by a continuous-time `TimeManager`. The desktop GUI receives the full simulation state 10 times per second over a WebSocket connection and renders every node's current compromise status, a live event feed, and per-node kill chain history.

**Key capabilities:**

- Fully autonomous Red Team AI that progresses through 9 MITRE ATT&CK-aligned kill chain stages
- 16 distinct attack techniques, each with its own preconditions, probabilistic success logic, and state effects
- Real CVE identifiers embedded in node vulnerability profiles (including CVE-2020-1472 ZeroLogon and CVE-2017-0144 EternalBlue/WannaCry)
- Continuous-time simulation with variable-speed playback (0.5× to 10×)
- Real-time WebSocket broadcast of full state snapshots at 100 ms intervals
- PySide6 desktop GUI with hexagonal node rendering, animated pulse effects, and dark/light theming
- JSON-driven scenario loader — network topology, vulnerabilities, and node attributes are fully data-defined

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────-┐
│                        PySide6 Desktop GUI                       │
│                                                                  │
│  NetworkGraphCanvas │ EventFeedWidget │ ControlBar │ NodePopup   │
│         │                   │               │            │       │
│         └───────────────────┴───────────────┘            │       │
│                          APIClient                       │       │
│                    (WebSocket + HTTP POST)               │       │
└──────────────────────────┬──────────────────────────────-┘       │
                           │ ws://localhost:8000/ws/state          │
                           │ POST /api/simulation/{start,pause...} │
┌──────────────────────────▼──────────────────────────────────────-┘
│                       FastAPI + Uvicorn Backend                  │
│                                                                  │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────────────────┐ │
│  │  Simulation │   │  TimeManager│   │      EventBus           │ │
│  │   Engine    │──▶│ (min-heap   │   │   (pub/sub callbacks)   │ │
│  │  (daemon    │   │  event queue│   └──────────┬──────────────┘ │
│  │   thread)   │   └──────┬──────┘              │                │
│  └──────┬──────┘          │                     │                │
│         │                 │              ┌───────▼──────────┐    │
│         │         ┌───────▼──────────┐   │  StateManager    │    │
│         │         │  ActionExecutor  │──▶│  (single source  │    │
│         │         │  (validates +    │   │   of truth,      │    │
│         │         │   schedules)     │   │   kill chain log)│    │
│         │         └─────────────────-┘   └──────────────────┘    │
│         │                                                        │
│  ┌──────▼──────────────────────────────────────────────────────┐ │
│  │  RedTeamAI (FSM)                                            │ │
│  │  RECON → INITIAL_ACCESS → PRIV_ESC → CRED_ACCESS →          │ │
│  │  LATERAL_MOVE → EVASION → C2 → EXFIL → DONE                 │ │
│  └──────────────────────────────────────────────────────────-──┘ │
│                                                                  │
│  NetworkGraph (NetworkX DiGraph)                                 │
│  Nodes: Firewall, Servers, Workstations, Database                │
│  Loaded from JSON scenario files                                 │
└──────────────────────────────────────────────────────────────────┘
```

The backend and GUI are fully decoupled — they communicate exclusively over HTTP and WebSocket. The GUI never touches simulation state directly.

---

## Backend Deep Dive

### Simulation Engine

`backend/simulation/engine.py`

The `SimulationEngine` is the central orchestrator. It owns all subsystems and runs the main simulation loop on a **daemon thread**, keeping it completely isolated from FastAPI's async I/O threads.

On every loop tick (~10 ms wall time):

1. Computes `sim_delta_t = real_delta_t × speed_multiplier`
2. Calls `TimeManager.process_events_until(target_sim_time)` to fire any scheduled callbacks
3. Calls `RedTeamAI.decide_actions()` to give the AI a turn
4. The loop pauses cleanly when `is_running = False` without terminating the thread

Starting, pausing, resetting, and changing speed are all thread-safe operations triggered by the REST API.

### Time Manager

`backend/simulation/time_manager.py`

A purpose-built **discrete-event, continuous-time scheduler**. Events are stored in a **min-heap priority queue** (`heapq`) keyed by `event_time`. This gives O(log n) insertion and O(log n) extraction — the simulation can have many concurrent in-flight actions without any performance degradation.

- `schedule_event(callback, delay)` — inserts `(current_time + delay, unique_id, callback, args, kwargs)` into the heap
- `process_events_until(target_time)` — pops and executes all events with `event_time ≤ target_time`, advancing `current_time` precisely to each event's scheduled moment before firing its callback
- Supports a configurable **speed multiplier** (`0.5×` to `10×`) that scales how much sim time passes per real second
- Full pause/resume support with no event loss

This design means attack durations are naturally variable: a `PortScan` takes 5.0 sim-minutes, an `ExploitPublicFacingApp` takes 12.0, and they can all be in-flight simultaneously without interference.

### Event Bus

`backend/simulation/event_bus.py`

A **publish/subscribe message broker** that decouples all simulation components. No component holds a direct reference to any other — they communicate exclusively by publishing and subscribing to named event types.

```
Publisher (Action)         EventBus          Subscriber
─────────────────    ──────────────────    ──────────────
publish("ACTION_SUCCESS", payload)
                      → find all subscribers for "ACTION_SUCCESS"
                      → call each callback(event_type, payload)
                                          RedTeamAI._on_action_success()
                                          StateManager.record_event()
                                          API broadcaster
```

Events used: `ACTION_INITIATED`, `ACTION_SUCCESS`, `ACTION_FAILURE`, `ACTION_COMPLETED`, `ACTION_FAILED`, `RED_TEAM_INFO_GAINED`, `BLUE_ALERT`, `BLUE_TEAM_VULN_DISCOVERED`

### Action System

`backend/actions/base_action.py`, `red_actions.py`, `blue_actions.py`

Every attack technique is a class that inherits from `BaseAction`. The abstract base enforces a three-method interface:

| Method                                          | Responsibility                                                                         |
| ----------------------------------------------- | -------------------------------------------------------------------------------------- |
| `check_preconditions(state_manager, target_id)` | Static method. Returns `(bool, reason_str)`. AI calls this before creating the action. |
| `execute_logic()`                               | Probabilistic success/failure roll. Called at completion time by TimeManager.          |
| `apply_effects_on_success()`                    | Mutates `StateManager` and publishes events on success.                                |
| `apply_effects_on_failure()`                    | Records failure to kill chain log, publishes BLUE_ALERT if appropriate.                |

The `complete()` method (called by TimeManager at the scheduled time) orchestrates the flow: `execute_logic()` → branch → `apply_effects_on_success/failure()` → publish `ACTION_SUCCESS/FAILURE` → publish `ACTION_COMPLETED`.

Each action has a `duration` (sim-minutes) and `resource_cost`. The `ActionExecutor` deducts resources at execution time and verifies the team has enough before proceeding.

**Success probability** is not flat — it is modulated by the target node's `security_posture_score`:

- A node with `security_posture_score = 0.85` (Edge Firewall) is significantly harder to compromise than one with `0.35` (Dev Workstation)
- Evasion active on a node grants a `+0.15` bonus to C2 establishment and exfiltration, rewarding strategic sequencing

### State Manager

`backend/simulation/state_manager.py`

The **single source of truth** for all mutable simulation state. Every action reads from and writes to this object exclusively. Key tracked sets:

| Attribute               | Type   | Meaning                                                   |
| ----------------------- | ------ | --------------------------------------------------------- |
| `port_scanned_nodes`    | `set`  | Nodes Red has completed a port scan on                    |
| `fingerprinted_nodes`   | `set`  | Nodes whose services and vulnerabilities are known to Red |
| `known_vulnerabilities` | `dict` | `node_id → [cve_id, ...]`                                 |
| `initial_access_nodes`  | `set`  | Nodes Red has foothold access on                          |
| `privileged_nodes`      | `set`  | Nodes where Red has root/admin                            |
| `credential_stores`     | `dict` | `node_id → [credential_hash, ...]`                        |
| `lateral_access_nodes`  | `set`  | Nodes Red reached via lateral movement                    |
| `evasion_active_nodes`  | `set`  | Nodes where logs are cleared or AV is disabled            |
| `c2_nodes`              | `set`  | Nodes with active C2 beacons                              |
| `staged_data_nodes`     | `set`  | Nodes where data is staged for exfiltration               |
| `exfil_complete`        | `bool` | Win condition — Red has exfiltrated data                  |

`to_dict()` serializes the full state (including the kill chain log and network graph) into a JSON-serializable snapshot that is broadcast over WebSocket every 100 ms. A custom `SimulationEncoder` handles Python `Enum` and `set` types transparently.

### Red Team AI (FSM)

`backend/agents/red_team_ai.py`

The Red Team AI is a **Finite State Machine** with 9 states that map directly to MITRE ATT&CK tactics:

```
RECON → INITIAL_ACCESS → PRIV_ESC → CRED_ACCESS → LATERAL_MOVE → EVASION → C2 → EXFIL → DONE
```

On each simulation tick, `decide_actions()` is called. The AI:

1. Checks `_is_busy` — only one action in flight at a time (preventing resource exhaustion)
2. Checks `_cooldown` — a brief wait after any failure before retrying
3. Calls `_evaluate_state_transition()` — advances FSM state if exit conditions are met
4. Dispatches to a per-state decision helper that selects the highest-priority applicable technique

**State transition logic** is data-driven from `StateManager`:

- `RECON → INITIAL_ACCESS`: triggers once at least one internet-facing node is fingerprinted
- `INITIAL_ACCESS → PRIV_ESC`: triggers once any `initial_access_nodes` exists
- `PRIV_ESC → CRED_ACCESS`: triggers once any `privileged_nodes` exists
- `CRED_ACCESS → LATERAL_MOVE`: triggers once any `credential_stores` entry exists, then calls `_build_lateral_targets()` to find graph neighbors of owned nodes
- `LATERAL_MOVE → EVASION`: triggers once any `lateral_access_nodes` exists
- `EVASION → C2`: triggers once any `evasion_active_nodes` exists (or no evasion candidates remain)
- `C2 → EXFIL`: triggers once any `c2_nodes` exists
- `EXFIL → DONE`: triggers when `exfil_complete = True`

**Technique selection** within each state is prioritized. For example, in `INITIAL_ACCESS`, the AI prefers `ExploitPublicFacingApp` on internet-facing nodes (higher-value, deterministic target) and falls back to `PhishingEmail` if no exploitable nodes are available. In `PRIV_ESC`, `TokenImpersonation` (requires admin users on the node) is preferred over `ExploitSUID` (SUID misconfiguration).

The AI subscribes to `ACTION_SUCCESS` events to populate its internal queues: a successful `PortScan` adds the node to `_fingerprint_queue`; a successful `ServiceFingerprint` adds it to `_initial_access_candidates`.

`BaseAgent` (`base_agent.py`) is an abstract class that enforces the `decide_actions()` interface and serves as the extension point for a future Blue Team AI.

### Network Graph

`backend/simulation/objects/network_graph.py`

The network topology is modeled as a **NetworkX `DiGraph`** (directed graph). This was a deliberate architectural choice:

- Directed edges enable asymmetric network rules (traffic from A→B does not imply B→A)
- NetworkX's `shortest_path()` is available for future pathfinding-based lateral movement strategies
- The `DiGraph` structure is a natural fit for encoding network state as input to **Graph Neural Networks** in future MARL work

Each graph node stores a full `Node` dataclass as an attribute. Each edge stores an `Edge` dataclass with `traffic_type` and `bidirectional` flag. `get_neighbors()` returns both successors and predecessors of a node, giving a complete adjacency list for undirected-style queries where needed.

The graph is loaded from a JSON scenario file at reset time via `NetworkGraph.load_from_json()`.

`Node` properties include:

- `security_posture_score` (0–1) — probability modifier for all attacks against this node
- `detection_chance_modifier` — how likely Blue will receive alerts
- `detection_chance_modifier` is actively reduced by successful evasion actions
- `value` — used to gate `StageData` (only nodes with `value ≥ 3.0` are worth exfiltrating)
- `c2_resource_generation_rate` — resources gained per `C2BeaconKeepAlive` tick on this node
- `exposed_to_internet`, `has_admin_users`, `smb_enabled`, `rdp_enabled` — used as precondition checks by specific techniques

`Vulnerability` objects carry a `cve_id`, `exploitability` score (0–1), and `severity`. `ExploitPublicFacingApp` selects the highest-exploitability vulnerability on a node when rolling its success check.

### REST & WebSocket API

`backend/api/main.py`

Built with **FastAPI** and served by **Uvicorn**.

**REST endpoints:**
| Method | Path | Action |
|---|---|---|
| `POST` | `/api/simulation/start` | Start the simulation loop |
| `POST` | `/api/simulation/pause` | Pause the simulation loop |
| `POST` | `/api/simulation/reset/{scenario_name}` | Load a new scenario and reset all state |
| `POST` | `/api/simulation/speed/{factor}` | Set the time multiplier |
| `GET` | `/api/state/nodes` | Current status of every node |
| `GET` | `/api/state/resources` | Red and Blue team resource levels |
| `GET` | `/api/state/kill_chain` | Per-node kill chain stage progress |
| `GET` | `/api/state/kill_chain_log` | Last 100 kill chain log entries |

**WebSocket endpoint:** `ws://localhost:8000/ws/state`

A `ConnectionManager` tracks all active WebSocket connections. On startup, a background `asyncio.Task` runs `state_broadcaster()`, which wakes every 100 ms and pushes the full `StateManager.to_dict()` snapshot to every connected client. Dead connections are automatically pruned from the active set.

The API also hooks the EventBus on startup to record `ACTION_INITIATED`, `ACTION_SUCCESS`, `ACTION_FAILURE`, `RED_TEAM_INFO_GAINED`, and `BLUE_ALERT` events into `StateManager.recent_events`, which are included in every WebSocket snapshot for the GUI's event feed.

---

## GUI Deep Dive

### API Client

`gui/api_client.py`

`APIClient` bridges the Qt world and the async network world cleanly:

- **WebSocket listener** runs in a dedicated background **daemon thread** with its own `asyncio` event loop. When a snapshot arrives, it emits a Qt `Signal(dict)` — Qt's signal/slot mechanism handles the thread-boundary crossing safely, dispatching the update to the GUI thread.
- The listener has an **auto-reconnect loop** — if the connection drops, it waits 2 seconds and retries indefinitely.
- **HTTP control commands** (start, pause, reset, speed) are dispatched through Qt's `QThreadPool` using a `QRunnable` worker, keeping them off the GUI thread entirely.

### Network Graph Canvas

`gui/widgets/network_graph_canvas.py`

Built on **Qt's Graphics View Framework** (`QGraphicsScene` / `QGraphicsView`). The scene is 6000×6000 units, giving unlimited pan-and-zoom space.

**Node rendering** (`NodeItem`): Each node is drawn with a triple-hexagon design in `paint()`:

- Outer hexagon: status-colored border (rotated 30°)
- Middle hexagon: dimmed border (rotated 0°, for a layered "tactical" look)
- Inner hexagon: radial gradient fill using `QRadialGradient`
- Corner bracket accents drawn manually with `QPainter.drawLine()`
- Node type abbreviation (e.g., `SRV`, `FW`, `DB`) centered in the inner hex at 22pt bold
- Status tag (`BREACH`, `C2 ACTIVE`, `EXFILTRATED`, etc.) at top-right at 11pt
- Node name below the hex at 22pt bold, node ID at 14pt

Every status maps to a unique color set (fill gradient, border, glow color, label color) defined in `theme.py` — both for dark and light modes.

`QGraphicsDropShadowEffect` provides the glow effect that changes color with status. Compromised nodes (INITIAL_ACCESS through EXFILTRATED) **pulse** — a `QTimer` fires every 900 ms and toggles between blur radius 30 and 45 on all compromised nodes.

Nodes are **draggable** (`ItemIsMovable` flag). Clicking a node emits `node_clicked(node_id)` which triggers the popup.

**Edge rendering** (`EdgeItem`): Edges are drawn as **quadratic Bézier curves** using `QPainterPath.quadTo()` with a slight perpendicular offset for the control point, giving a gentle arc that prevents edge overlap on dense graphs. Attack edges render in red, active edges in the accent color, idle edges in muted grey.

**Zoom**: Trackpad scroll uses `pixelDelta` for smooth damped zoom (2× per 100 pixels); mouse wheel uses `angleDelta` for stepped zoom. Per-event scale is clamped to `[0.92, 1.08]` to prevent jumps. A `zoom_changed` signal keeps the control bar slider synchronized.

**Initial layout**: On first render, nodes are arranged in an evenly-spaced circle (`radius = max(220, n × 90)`) and the view auto-fits to the scene bounds.

### Event Feed

`gui/widgets/event_feed.py`

A scrollable, filterable activity log that receives the same WebSocket snapshot as the canvas:

- **Deduplication**: tracks `_last_event_count` so only genuinely new events from `recent_events` are processed each tick — no re-rendering of already-displayed events.
- **Classification**: each event is classified by `classify_event()` into team (RED/BLUE), criticality, and border color. Noise events (`ACTION_INITIATED`, `ACTION_COMPLETED`) are silently dropped.
- **Human-readable descriptions**: `format_event_text()` maps every `(event_type, action_name)` pair to a natural-language sentence (e.g., "Red pivoted to File Server using a stolen hash").
- **Pinned alerts panel**: the 3 most recent critical actions (exploitation, lateral movement, C2 establishment, exfiltration) are pinned at the top of the feed in bold red with a lightning bolt icon.
- **Filter bar**: ALL / RED / BLUE / CRITICAL buttons toggle which event categories are shown; switching filter calls `_rebuild_feed()` which re-renders from the in-memory `_all_events` list.
- **LATEST banner**: always shows the most recent event text regardless of active filter.
- Maximum 300 events retained in memory; oldest are pruned when the limit is exceeded.

### Theme Engine

`gui/theme.py`

A **singleton** `ThemeManager` (accessed via `ThemeManager.instance()`) holds the active color palette. Every widget calls `ThemeManager.instance().colors()` to resolve colors at render time — no hardcoded hex values anywhere in widget code.

Two palettes are defined: `DARK` (default, a dark navy/charcoal aesthetic) and `LIGHT` (muted greys and pastels). Toggling theme calls `toggle()` which emits `theme_changed` and triggers `apply_theme()` on every widget.

`status_style(status_key)` returns the full style dict for a given node status in the current theme — fill gradient colors, border color, glow color, label text color, and tag string. This is the single place where the visual identity of each kill chain stage is defined.

---

## Scenarios

Scenarios are JSON files in `backend/scenarios/`. Two are included:

### `corporate_network.json`

An 8-node corporate network that models a realistic attack surface:

| Node              | Type        | Internet-Facing | Key Vulnerability           | Exploitability |
| ----------------- | ----------- | --------------- | --------------------------- | -------------- |
| Edge Firewall     | Firewall    | Yes             | —                           | —              |
| DMZ Web Server    | Server      | Yes             | CVE-2024-3094               | 0.85           |
| Mail Server       | Server      | No              | CVE-2024-21413              | 0.70           |
| Domain Controller | Server      | No              | CVE-2020-1472 (ZeroLogon)   | 0.50           |
| File Server       | Server      | No              | CVE-2017-0144 (EternalBlue) | 0.80           |
| Database Server   | Database    | No              | CVE-2022-29885              | 0.55           |
| Exec Workstation  | Workstation | No              | CVE-2023-36884              | 0.75           |
| Dev Workstation   | Workstation | No              | CVE-2023-38831              | 0.65           |

The network topology creates a realistic attack path:

```
Internet → Edge Firewall → DMZ Web Server → Domain Controller → File Server → Exec Workstation → Database Server
                         ↘ Mail Server → Domain Controller
```

### `small_business.json`

A simpler topology for faster simulation runs and testing.

---

## MITRE ATT&CK Coverage

Every technique is annotated with its ATT&CK ID in the source code:

| Kill Chain Stage     | Technique Class          | ATT&CK ID | Description                                 |
| -------------------- | ------------------------ | --------- | ------------------------------------------- |
| Reconnaissance       | `PortScan`               | T1046     | Network Service Scanning                    |
| Reconnaissance       | `ServiceFingerprint`     | T1592     | Gather Victim Host Information              |
| Initial Access       | `ExploitPublicFacingApp` | T1190     | Exploit Public-Facing Application           |
| Initial Access       | `PhishingEmail`          | T1566     | Phishing                                    |
| Privilege Escalation | `ExploitSUID`            | T1548     | Abuse Elevation Control Mechanism           |
| Privilege Escalation | `TokenImpersonation`     | T1134     | Access Token Manipulation                   |
| Credential Access    | `DumpCredentials`        | T1003     | OS Credential Dumping                       |
| Credential Access    | `Kerberoasting`          | T1558.003 | Steal or Forge Kerberos Tickets             |
| Lateral Movement     | `PassTheHashMove`        | T1550.002 | Pass the Hash                               |
| Lateral Movement     | `RDPLateralMove`         | T1021.001 | Remote Desktop Protocol                     |
| Defense Evasion      | `ClearEventLogs`         | T1070.001 | Indicator Removal: Clear Windows Event Logs |
| Defense Evasion      | `DisableAV`              | T1562.001 | Impair Defenses: Disable or Modify Tools    |
| Command and Control  | `EstablishC2`            | T1071     | Application Layer Protocol                  |
| Command and Control  | `C2BeaconKeepAlive`      | T1071     | Beacon Keep-Alive                           |
| Exfiltration         | `StageData`              | T1074     | Data Staged                                 |
| Exfiltration         | `ExfilOverHTTPS`         | T1048     | Exfiltration Over Alternative Protocol      |

---

## Tech Stack

| Layer            | Technology         | Purpose                                          |
| ---------------- | ------------------ | ------------------------------------------------ |
| Backend language | Python 3.12        | Simulation core, AI agents                       |
| API framework    | FastAPI + Uvicorn  | REST control plane + WebSocket broadcaster       |
| Graph library    | NetworkX           | Network topology, adjacency queries, pathfinding |
| GUI framework    | PySide6 (Qt 6)     | Desktop application, graphics rendering          |
| HTTP client      | requests           | GUI → Backend control commands                   |
| WebSocket client | websockets         | GUI ← Backend state stream                       |
| Concurrency      | threading, asyncio | Isolated sim loop; non-blocking GUI networking   |

---

## Running the Project

**Requirements:** Python 3.10+

```bash
pip install -r backend/requirements.txt
```

**Start the backend** (in one terminal):

```bash
python run_backend.py
```

The backend starts on `http://localhost:8000`. Visit `/docs` for the interactive API explorer.

**Start the GUI** (in a second terminal, from the `gui/` directory):

```bash
cd gui
python main.py
```

Click **START** to begin the simulation. The Red Team AI will immediately begin working through the kill chain. Use the speed slider to fast-forward up to **10×**. Click any node to open its detail panel showing services, vulnerabilities, security posture, and kill chain history for that specific node.
