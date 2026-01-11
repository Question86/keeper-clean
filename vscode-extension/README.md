# Keeper Cockpit Bridge

VS Code extension that bridges the Keeper Loop Cockpit with VS Code functionality.

## Features

- **Status Bar Integration**: Shows current loop number and status in VS Code status bar
- **File Operations**: Open files from cockpit commands
- **Terminal Control**: Execute terminal commands from cockpit
- **Selection Access**: Get current editor selection
- **AI Agent Spawning**: Spawn GitHub Copilot agents for parallel task execution

## Installation

### Development Install

1. Open this folder in VS Code
2. Run `npm install`
3. Run `npm run compile`
4. Press F5 to launch Extension Development Host

### Production Install (future)

```bash
# Package the extension
npx vsce package

# Install the .vsix file
code --install-extension keeper-cockpit-bridge-0.1.0.vsix
```

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `keeper.cockpitUrl` | `http://localhost:5000` | URL of the Keeper Loop Cockpit |
| `keeper.autoConnect` | `true` | Auto-connect on startup |
| `keeper.pollInterval` | `5000` | Status polling interval (ms) |

## Commands

### Core Commands
- **Keeper: Open File** - Open a file in the editor
- **Keeper: Run Terminal Command** - Execute a command in terminal
- **Keeper: Get Current Selection** - Get the current editor selection
- **Keeper: Reconnect to Cockpit** - Manually reconnect

### Agent Commands
- **Keeper: Check Agent Capability** - Check if Copilot models are available
- **Keeper: Spawn AI Agent** - Spawn an agent to work on a task
- **Keeper: Show Agent Output** - Show agent output channel

## Status Bar

The status bar shows:
- 🔴 Disconnected (red background)
- 🔄 Connecting (spinning icon)
- 💓 Loop N: ACTIVE (yellow background)
- ✓ Loop N: FINALIZED (prominent background)
- ↻ Loop N: READY_FOR_RESET

Click the status bar item to manually reconnect.

## Architecture

```
┌─────────────────┐     HTTP/Poll      ┌──────────────────┐
│   VS Code       │◄──────────────────►│  Loop Cockpit    │
│   Extension     │                    │  (Flask server)  │
├─────────────────┤                    ├──────────────────┤
│ - StatusBar     │  /api/status       │ - current.json   │
│ - Commands      │                    │ - NEU.md         │
│ - File Ops      │                    │ - loop state     │
└─────────────────┘                    └──────────────────┘
```

## Development

```bash
# Install dependencies
npm install

# Compile TypeScript
npm run compile

# Watch mode
npm run watch

# Lint
npm run lint
```

## Future Enhancements

- WebSocket for real-time bidirectional communication
- Chat API integration for agent spawning
- Task navigation commands
- Report template generation

---

Part of the Keeper Loop Workflow System.
