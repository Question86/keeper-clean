"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
exports.openFile = openFile;
exports.runTerminalCommand = runTerminalCommand;
exports.getSelection = getSelection;
const vscode = __importStar(require("vscode"));
const bridge_1 = require("./bridge");
const statusBar_1 = require("./statusBar");
const agentSpawner_1 = require("./agentSpawner");
let bridge;
let statusBar;
let agentSpawner;
let sessionPoller;
// Session poller for multi-agent orchestration
class SessionPoller {
    pollTimer = null;
    cockpitUrl;
    agentSpawner;
    processing = new Set();
    outputChannel;
    isPolling = false;
    constructor(cockpitUrl, agentSpawner) {
        this.cockpitUrl = cockpitUrl;
        this.agentSpawner = agentSpawner;
        this.outputChannel = vscode.window.createOutputChannel('Keeper Session Poller');
    }
    start(intervalMs = 2000) {
        if (this.isPolling)
            return;
        this.isPolling = true;
        this.outputChannel.appendLine(`[${new Date().toISOString()}] Session poller started (interval: ${intervalMs}ms)`);
        this.outputChannel.show();
        this.pollTimer = setInterval(() => this.poll(), intervalMs);
        this.poll(); // Immediate first poll
    }
    stop() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
        this.isPolling = false;
        this.outputChannel.appendLine(`[${new Date().toISOString()}] Session poller stopped`);
    }
    async poll() {
        try {
            const response = await fetch(`${this.cockpitUrl}/api/orchestrator/sessions/pending`);
            if (!response.ok)
                return;
            const data = await response.json();
            if (!data.sessions || data.sessions.length === 0)
                return;
            this.outputChannel.appendLine(`[${new Date().toISOString()}] Found ${data.sessions.length} pending sessions`);
            for (const session of data.sessions) {
                if (this.processing.has(session.agent_id))
                    continue;
                // Claim and process
                await this.processSession(session);
            }
        }
        catch (error) {
            // Silently fail - cockpit might not be running
        }
    }
    async processSession(sessionData) {
        const agentId = sessionData.agent_id;
        this.processing.add(agentId);
        try {
            // Claim the session
            this.outputChannel.appendLine(`[${new Date().toISOString()}] Claiming session ${agentId}...`);
            const claimResponse = await fetch(`${this.cockpitUrl}/api/orchestrator/sessions/${agentId}/claim`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            if (!claimResponse.ok) {
                this.outputChannel.appendLine(`Failed to claim session ${agentId}: ${claimResponse.status}`);
                return;
            }
            const claimed = await claimResponse.json();
            if (!claimed.success || !claimed.session) {
                this.outputChannel.appendLine(`Claim failed for ${agentId}: ${claimed.error}`);
                return;
            }
            const session = {
                agentId: claimed.session.agentId,
                taskId: claimed.session.taskId,
                worktreePath: claimed.session.worktreePath,
                prompt: claimed.session.prompt,
                status: 'pending',
                progress: 0
            };
            this.outputChannel.appendLine(`[${new Date().toISOString()}] Spawning agent for ${session.taskId}...`);
            this.agentSpawner.showOutput();
            const success = await this.agentSpawner.spawnAgent(session);
            // Report status back to orchestrator
            await this.reportStatus(agentId, success, session);
        }
        catch (error) {
            this.outputChannel.appendLine(`Error processing session ${agentId}: ${error}`);
        }
        finally {
            this.processing.delete(agentId);
        }
    }
    async reportStatus(agentId, success, session) {
        try {
            await fetch(`${this.cockpitUrl}/api/orchestrator/sessions/${agentId}/status`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    status: success ? 'completed' : 'failed',
                    progress: 100,
                    summary: success ? `Task completed: ${session.response?.substring(0, 200)}` : session.error,
                    error: session.error
                })
            });
            this.outputChannel.appendLine(`[${new Date().toISOString()}] Reported ${success ? 'success' : 'failure'} for ${agentId}`);
        }
        catch (error) {
            this.outputChannel.appendLine(`Failed to report status for ${agentId}: ${error}`);
        }
    }
    showOutput() {
        this.outputChannel.show();
    }
    isActive() {
        return this.isPolling;
    }
    dispose() {
        this.stop();
        this.outputChannel.dispose();
    }
}
function activate(context) {
    console.log('Keeper Cockpit Bridge activating...');
    // Initialize status bar
    statusBar = new statusBar_1.StatusBarManager();
    context.subscriptions.push(statusBar);
    // Initialize agent spawner
    agentSpawner = new agentSpawner_1.AgentSpawner();
    context.subscriptions.push(agentSpawner);
    // Initialize bridge
    const config = vscode.workspace.getConfiguration('keeper');
    const cockpitUrl = config.get('cockpitUrl', 'http://localhost:5000');
    const autoConnect = config.get('autoConnect', true);
    const pollInterval = config.get('pollInterval', 5000);
    bridge = new bridge_1.CockpitBridge(cockpitUrl, statusBar, pollInterval);
    context.subscriptions.push(bridge);
    // Register commands
    context.subscriptions.push(vscode.commands.registerCommand('keeper.openFile', async (filePath) => {
        if (!filePath) {
            filePath = await vscode.window.showInputBox({
                prompt: 'Enter file path to open',
                placeHolder: 'NEU.md'
            });
        }
        if (filePath) {
            await openFile(filePath);
        }
    }));
    context.subscriptions.push(vscode.commands.registerCommand('keeper.runTerminalCommand', async (command) => {
        if (!command) {
            command = await vscode.window.showInputBox({
                prompt: 'Enter command to run',
                placeHolder: 'python loop_cockpit.py --lint'
            });
        }
        if (command) {
            await runTerminalCommand(command);
        }
    }));
    context.subscriptions.push(vscode.commands.registerCommand('keeper.getSelection', async () => {
        const selection = getSelection();
        if (selection) {
            vscode.window.showInformationMessage(`Selection: ${selection.text.substring(0, 100)}...`);
        }
        return selection;
    }));
    context.subscriptions.push(vscode.commands.registerCommand('keeper.reconnect', async () => {
        await bridge?.reconnect();
    }));
    // Agent spawning commands
    context.subscriptions.push(vscode.commands.registerCommand('keeper.checkAgentCapability', async () => {
        const result = await agentSpawner?.checkModelAvailability();
        if (result?.available) {
            vscode.window.showInformationMessage(`Copilot models available: ${result.models.join(', ')}`);
        }
        else {
            vscode.window.showWarningMessage('No Copilot chat models available. Check GitHub Copilot extension.');
        }
        return result;
    }));
    context.subscriptions.push(vscode.commands.registerCommand('keeper.spawnAgent', async (sessionData) => {
        if (!agentSpawner) {
            vscode.window.showErrorMessage('Agent spawner not initialized');
            return false;
        }
        if (!sessionData) {
            // Interactive mode - prompt for details
            const taskId = await vscode.window.showInputBox({
                prompt: 'Enter task ID',
                placeHolder: 'TASK_0001'
            });
            if (!taskId)
                return false;
            const description = await vscode.window.showInputBox({
                prompt: 'Enter task description',
                placeHolder: 'Implement feature X'
            });
            if (!description)
                return false;
            const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || '';
            sessionData = {
                agentId: `agent_${Date.now()}`,
                taskId,
                worktreePath: workspaceFolder,
                prompt: (0, agentSpawner_1.generateAgentPrompt)(`agent_${Date.now()}`, taskId, workspaceFolder, description, 55 // Default loop number
                ),
                status: 'pending',
                progress: 0
            };
        }
        agentSpawner.showOutput();
        const success = await agentSpawner.spawnAgent(sessionData);
        if (success) {
            vscode.window.showInformationMessage(`Agent ${sessionData.agentId} completed successfully`);
        }
        else {
            vscode.window.showErrorMessage(`Agent ${sessionData.agentId} failed: ${sessionData.error}`);
        }
        return success;
    }));
    context.subscriptions.push(vscode.commands.registerCommand('keeper.showAgentOutput', () => {
        agentSpawner?.showOutput();
    }));
    // Session poller commands for multi-agent orchestration
    context.subscriptions.push(vscode.commands.registerCommand('keeper.startSessionPoller', () => {
        if (!sessionPoller) {
            sessionPoller = new SessionPoller(cockpitUrl, agentSpawner);
            context.subscriptions.push(sessionPoller);
        }
        sessionPoller.start(2000);
        vscode.window.showInformationMessage('Multi-agent session poller started. Watching for pending sessions...');
    }));
    context.subscriptions.push(vscode.commands.registerCommand('keeper.stopSessionPoller', () => {
        sessionPoller?.stop();
        vscode.window.showInformationMessage('Multi-agent session poller stopped.');
    }));
    context.subscriptions.push(vscode.commands.registerCommand('keeper.showPollerOutput', () => {
        sessionPoller?.showOutput();
    }));
    context.subscriptions.push(vscode.commands.registerCommand('keeper.pollerStatus', () => {
        if (sessionPoller?.isActive()) {
            vscode.window.showInformationMessage('Session poller is ACTIVE and watching for pending orchestrator sessions.');
        }
        else {
            vscode.window.showInformationMessage('Session poller is INACTIVE. Use "Keeper: Start Session Poller" to begin.');
        }
    }));
    // Auto-connect if enabled
    if (autoConnect) {
        bridge.connect();
    }
    console.log('Keeper Cockpit Bridge activated');
}
function deactivate() {
    bridge?.dispose();
    statusBar?.dispose();
    agentSpawner?.dispose();
    sessionPoller?.dispose();
}
// Command implementations
async function openFile(filePath) {
    try {
        // Resolve path relative to workspace
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        let fullPath;
        if (filePath.includes(':') || filePath.startsWith('/')) {
            // Absolute path
            fullPath = vscode.Uri.file(filePath);
        }
        else if (workspaceFolder) {
            // Relative to workspace
            fullPath = vscode.Uri.joinPath(workspaceFolder.uri, filePath);
        }
        else {
            vscode.window.showErrorMessage('No workspace folder open');
            return false;
        }
        const doc = await vscode.workspace.openTextDocument(fullPath);
        await vscode.window.showTextDocument(doc);
        return true;
    }
    catch (error) {
        vscode.window.showErrorMessage(`Failed to open file: ${error}`);
        return false;
    }
}
async function runTerminalCommand(command) {
    const terminal = vscode.window.createTerminal('Keeper Command');
    terminal.show();
    terminal.sendText(command);
}
function getSelection() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        return null;
    }
    const selection = editor.selection;
    const text = editor.document.getText(selection);
    return {
        text,
        file: editor.document.uri.fsPath,
        startLine: selection.start.line + 1,
        endLine: selection.end.line + 1
    };
}
//# sourceMappingURL=extension.js.map