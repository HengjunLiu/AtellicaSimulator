# AGENTS.md

This file provides guidance to Qoder (qoder.com) when working with code in this repository.

## Project Overview

AtellicaSimulator is a medical device simulator for the Siemens Atellica laboratory analyzer. It implements dual communication protocols (uRAP for LAS, ASTM for LIS) and provides real-time GUI monitoring with headless server deployment support.

**Tech Stack:**
- Python 3.8+ (tested on 3.12.10)
- Pure Python - zero external dependencies (stdlib only)
- Tkinter for GUI
- SQLite3 for data persistence
- Threading for concurrency

## Common Commands

### Running the Application

```bash
# UI mode (default)
python main.py

# Headless mode (server/container deployment)
python main.py --no-ui

# With custom configuration
python main.py --config custom_config.json

# Headless with custom config
python main.py --no-ui --config custom_config.json
```

### Debugging

- VSCode: Press F5 (configured in `.vscode/launch.json`)
- Uses debugpy for Python debugging

### Testing & Linting

**Current Status:** No automated test suite or linting configuration exists.

The codebase uses manual testing via:
- UI mode for interactive testing
- Headless mode for CI/CD scenarios
- Protocol validation through communication logs

If adding tests, use Python's built-in `unittest` module (no external dependencies policy).

## Architecture

### Layered Architecture

```
┌─────────────────────────────────────┐
│     Presentation Layer (UI)         │  ui/ui.py, ui/lisui.py
├─────────────────────────────────────┤
│     Business Logic Layer (Core)     │  core/core.py
├─────────────────────────────────────┤
│     Communication Layer             │  las/las.py, lis/lis.py
├─────────────────────────────────────┤
│     Data Persistence Layer          │  SQLite (data/atellica.db), JSON config
├─────────────────────────────────────┤
│     Cross-Cutting (Logger)          │  logger/logger.py
└─────────────────────────────────────┘
```

### Module Structure

**Entry Point:** `main.py`
- Parses CLI arguments (`--no-ui`, `--config`)
- Initializes components: ConfigManager → Logger → AtellicaCore → LASServer → LISClient → AtellicaUI
- Manages application lifecycle and graceful shutdown

**Core Modules:**

- **`config/config.py`** - `ConfigManager` class
  - Loads/merges JSON configuration with defaults
  - Provides hierarchical key access (e.g., `'las.host'`)
  - Default config: `config.json`

- **`core/core.py`** - `AtellicaCore` class (~2,183 lines)
  - Central business logic and state management
  - Sample lifecycle (creation, queue, results)
  - Inventory tracking (tests, consumables)
  - SQLite database operations
  - Thread-safe coordination between LAS/LIS

- **`las/las.py`** - `LASServer` class (~3,324 lines)
  - Implements uRAP protocol server (Laboratory Automation System)
  - Multi-threaded socket server
  - Handles: handshake, health queries, queue management, load/unload operations
  - Session state and timeout management

- **`lis/lis.py`** - `LISClient` class
  - Implements ASTM protocol client (Laboratory Information System)
  - Connects to external LIS server
  - Sample queries, result transmission, reconnection logic

- **`logger/logger.py`** - `Logger` class
  - Multi-channel async logging (main, LAS, LIS, raw data)
  - File rotation support
  - UI callbacks for real-time display

- **`ui/ui.py`** - `AtellicaUI` class (~2,759 lines)
  - Tkinter-based desktop GUI
  - Real-time device state visualization
  - Queue display, manual controls, config editing

### Threading Model

- Main thread: UI event loop (Tkinter)
- LAS thread: Socket listener
- LIS thread: Connection management
- Core thread: Result generation and state updates
- Logger thread: Async log queue processor

### Component Interaction

```
LASServer (uRAP) ──┐
                   ├──→ AtellicaCore ←── LISClient (ASTM)
AtellicaUI ────────┘        ↑
                            ↓
                     ConfigManager
                     Logger (all modules)
                     SQLite Database
```

## Key Development Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point, component orchestration |
| `config.json` | Default configuration |
| `core/core.py` | Central business logic |
| `las/las.py` | uRAP protocol implementation |
| `lis/lis.py` | ASTM protocol implementation |
| `ui/ui.py` | Main GUI application |
| `logger/logger.py` | Multi-channel logging system |
| `config/config.py` | Configuration management |

## Configuration

Configuration is stored in `config.json` with these key sections:

- `logger`: Logging level, output modes, file rotation
- `las`: uRAP server settings (host, port, protocol version, timeouts)
- `lis`: ASTM client settings (host, port, result delay)
- `core`: Device state defaults (automation status, positions, locks)
- `test_inventory`: Available tests and counts
- `consumable_inventory`: Consumable modules and tracking

## Database

SQLite database at `data/atellica.db` (auto-created at runtime) stores:
- Sample records (ID, status, position, timestamps)
- Test results
- Queue state
- Inventory tracking

## URAP Protocol Compliance

**CRITICAL REQUIREMENT:** All modifications to URAP protocol implementation code (primarily `las/las.py` and related protocol handling) **MUST strictly adhere** to the specifications defined in the `URAP_WIKI/` directory documentation.

### Mandatory Rules:

1. **Reference Protocol Documentation First**: Before making any changes to uRAP protocol-related code, you MUST review the relevant documentation in `URAP_WIKI/` to understand the correct message formats, state machines, timing requirements, and error handling procedures.

2. **Strict Compliance**: All protocol implementations must follow the exact specifications defined in URAP_WIKI documents, including but not limited to:
   - Message formats and field definitions
   - Command sequences and state transitions
   - Timeout values and retry mechanisms
   - Error codes and error handling procedures
   - Data encoding/decoding rules
   - Handshake and initialization sequences

3. **Conflict Detection and Warning**: If you discover any discrepancy between the existing code implementation and the URAP_WIKI documentation, you **MUST**:
   - Immediately alert the developer with a clear, explicit warning message
   - Specify exactly which code deviates from which documentation
   - Describe the nature of the conflict
   - Do NOT silently "fix" protocol behavior without notifying the developer

4. **Documentation as Source of Truth**: When in doubt about protocol behavior, treat URAP_WIKI documentation as the authoritative source. If the code differs from the documentation, this is a potential bug that requires developer attention.

### Key Protocol Documentation Locations:

- `URAP_WIKI/` - Comprehensive uRAP protocol specification (70+ markdown files)
- Covers: LAS interface specification, SHC interface specification, communication protocols, sample processing workflows, configuration parameters, troubleshooting guides

**Rationale:** This ensures protocol implementation consistency and standardization, critical for interoperability with actual Siemens Atellica laboratory equipment.

## Important Notes

- **Zero external dependencies** - use only Python standard library modules
- **Medical device simulator** - designed for Siemens Atellica analyzer
- **Protocol expertise** - implements uRAP (Siemens proprietary) and ASTM standards
- **Dual-mode operation** - supports GUI and headless deployment
- **Documentation** - comprehensive Chinese docs in `.qoder/` and `URAP_WIKI/` directories
- **UTF-8 encoding** required for all Python files
- **Thread safety** - Core module coordinates state between LAS/LIS with proper locking

## Git Workflow

- Repository: https://github.com/HengjunLiu/AtellicaSimulator
- Main branch with versioned releases (current: v1.9.0)
- Recent releases focus on protocol fixes and concurrency improvements
