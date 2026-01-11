import * as vscode from 'vscode';
import { CockpitBridge } from './bridge';
import { StatusBarManager } from './statusBar';
import { AgentSpawner, generateAgentPrompt, AgentSession } from './agentSpawner';

let bridge: CockpitBridge | undefined;
let statusBar: StatusBarManager | undefined;
let agentSpawner: AgentSpawner | undefined;

export function activate(context: vscode.ExtensionContext) {
    console.log('Keeper Cockpit Bridge activating...');

    // Initialize status bar
    statusBar = new StatusBarManager();
    context.subscriptions.push(statusBar);

    // Initialize agent spawner
    agentSpawner = new AgentSpawner();
    context.subscriptions.push(agentSpawner);

    // Initialize bridge
    const config = vscode.workspace.getConfiguration('keeper');
    const cockpitUrl = config.get<string>('cockpitUrl', 'http://localhost:5000');
    const autoConnect = config.get<boolean>('autoConnect', true);
    const pollInterval = config.get<number>('pollInterval', 5000);

    bridge = new CockpitBridge(cockpitUrl, statusBar, pollInterval);
    context.subscriptions.push(bridge);

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('keeper.openFile', async (filePath?: string) => {
            if (!filePath) {
                filePath = await vscode.window.showInputBox({
                    prompt: 'Enter file path to open',
                    placeHolder: 'NEU.md'
                });
            }
            if (filePath) {
                await openFile(filePath);
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('keeper.runTerminalCommand', async (command?: string) => {
            if (!command) {
                command = await vscode.window.showInputBox({
                    prompt: 'Enter command to run',
                    placeHolder: 'python loop_cockpit.py --lint'
                });
            }
            if (command) {
                await runTerminalCommand(command);
            }
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('keeper.getSelection', async () => {
            const selection = getSelection();
            if (selection) {
                vscode.window.showInformationMessage(`Selection: ${selection.text.substring(0, 100)}...`);
            }
            return selection;
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('keeper.reconnect', async () => {
            await bridge?.reconnect();
        })
    );

    // Agent spawning commands
    context.subscriptions.push(
        vscode.commands.registerCommand('keeper.checkAgentCapability', async () => {
            const result = await agentSpawner?.checkModelAvailability();
            if (result?.available) {
                vscode.window.showInformationMessage(`Copilot models available: ${result.models.join(', ')}`);
            } else {
                vscode.window.showWarningMessage('No Copilot chat models available. Check GitHub Copilot extension.');
            }
            return result;
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('keeper.spawnAgent', async (sessionData?: AgentSession) => {
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
                if (!taskId) return false;

                const description = await vscode.window.showInputBox({
                    prompt: 'Enter task description',
                    placeHolder: 'Implement feature X'
                });
                if (!description) return false;

                const workspaceFolder = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || '';
                sessionData = {
                    agentId: `agent_${Date.now()}`,
                    taskId,
                    worktreePath: workspaceFolder,
                    prompt: generateAgentPrompt(
                        `agent_${Date.now()}`,
                        taskId,
                        workspaceFolder,
                        description,
                        55  // Default loop number
                    ),
                    status: 'pending',
                    progress: 0
                };
            }

            agentSpawner.showOutput();
            const success = await agentSpawner.spawnAgent(sessionData);
            
            if (success) {
                vscode.window.showInformationMessage(`Agent ${sessionData.agentId} completed successfully`);
            } else {
                vscode.window.showErrorMessage(`Agent ${sessionData.agentId} failed: ${sessionData.error}`);
            }
            
            return success;
        })
    );

    context.subscriptions.push(
        vscode.commands.registerCommand('keeper.showAgentOutput', () => {
            agentSpawner?.showOutput();
        })
    );

    // Auto-connect if enabled
    if (autoConnect) {
        bridge.connect();
    }

    console.log('Keeper Cockpit Bridge activated');
}

export function deactivate() {
    bridge?.dispose();
    statusBar?.dispose();
    agentSpawner?.dispose();
}

// Command implementations
async function openFile(filePath: string): Promise<boolean> {
    try {
        // Resolve path relative to workspace
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        let fullPath: vscode.Uri;
        
        if (filePath.includes(':') || filePath.startsWith('/')) {
            // Absolute path
            fullPath = vscode.Uri.file(filePath);
        } else if (workspaceFolder) {
            // Relative to workspace
            fullPath = vscode.Uri.joinPath(workspaceFolder.uri, filePath);
        } else {
            vscode.window.showErrorMessage('No workspace folder open');
            return false;
        }

        const doc = await vscode.workspace.openTextDocument(fullPath);
        await vscode.window.showTextDocument(doc);
        return true;
    } catch (error) {
        vscode.window.showErrorMessage(`Failed to open file: ${error}`);
        return false;
    }
}

async function runTerminalCommand(command: string): Promise<void> {
    const terminal = vscode.window.createTerminal('Keeper Command');
    terminal.show();
    terminal.sendText(command);
}

function getSelection(): { text: string; file: string; startLine: number; endLine: number } | null {
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

// Export for bridge to use
export { openFile, runTerminalCommand, getSelection };
