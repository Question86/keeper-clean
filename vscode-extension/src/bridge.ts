import * as vscode from 'vscode';
import WebSocket from 'ws';
import { StatusBarManager } from './statusBar';
import { openFile, runTerminalCommand, getSelection } from './extension';

interface CockpitStatus {
    loop: number;
    status: string;
    lastTaskWorked?: string;
    summary?: string;
}

interface CockpitMessage {
    type: string;
    id?: string;
    command?: string;
    path?: string;
    text?: string;
    data?: any;
}

interface CockpitResponse {
    type: string;
    id?: string;
    success: boolean;
    data?: any;
    error?: string;
}

export class CockpitBridge implements vscode.Disposable {
    private ws: WebSocket | null = null;
    private reconnectTimer: NodeJS.Timeout | null = null;
    private pollTimer: NodeJS.Timeout | null = null;
    private readonly cockpitUrl: string;
    private readonly wsUrl: string;
    private readonly statusBar: StatusBarManager;
    private readonly pollInterval: number;
    private isConnecting = false;

    constructor(cockpitUrl: string, statusBar: StatusBarManager, pollInterval: number) {
        this.cockpitUrl = cockpitUrl;
        // WebSocket endpoint on cockpit
        this.wsUrl = cockpitUrl.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws/extension';
        this.statusBar = statusBar;
        this.pollInterval = pollInterval;
    }

    async connect(): Promise<boolean> {
        if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
            return true;
        }

        this.isConnecting = true;
        this.statusBar.setConnecting();

        try {
            // First check if cockpit is reachable via HTTP
            const statusUrl = `${this.cockpitUrl}/api/status`;
            const response = await fetch(statusUrl);
            
            if (!response.ok) {
                throw new Error(`Cockpit not reachable: ${response.status}`);
            }

            const status = await response.json() as CockpitStatus;
            this.statusBar.setConnected(status.loop, status.status);

            // Start polling for status updates (WebSocket is optional enhancement)
            this.startPolling();
            
            this.isConnecting = false;
            return true;
        } catch (error) {
            console.error('Failed to connect to cockpit:', error);
            this.statusBar.setDisconnected();
            this.isConnecting = false;
            this.scheduleReconnect();
            return false;
        }
    }

    private startPolling(): void {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
        }

        this.pollTimer = setInterval(async () => {
            try {
                const response = await fetch(`${this.cockpitUrl}/api/status`);
                if (response.ok) {
                    const status = await response.json() as CockpitStatus;
                    this.statusBar.setConnected(status.loop, status.status);
                }
            } catch (error) {
                console.warn('Status poll failed:', error);
                this.statusBar.setDisconnected();
            }
        }, this.pollInterval);
    }

    private scheduleReconnect(): void {
        if (this.reconnectTimer) {
            return;
        }

        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.connect();
        }, 10000); // Retry in 10 seconds
    }

    async reconnect(): Promise<void> {
        this.disconnect();
        await this.connect();
    }

    private disconnect(): void {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
        }
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.statusBar.setDisconnected();
    }

    // Handle incoming commands from cockpit (for future WebSocket implementation)
    private async handleMessage(message: CockpitMessage): Promise<CockpitResponse> {
        try {
            switch (message.command) {
                case 'openFile':
                    if (message.path) {
                        const success = await openFile(message.path);
                        return { type: 'response', id: message.id, success };
                    }
                    return { type: 'response', id: message.id, success: false, error: 'No path provided' };

                case 'runTerminal':
                    if (message.text) {
                        await runTerminalCommand(message.text);
                        return { type: 'response', id: message.id, success: true };
                    }
                    return { type: 'response', id: message.id, success: false, error: 'No command provided' };

                case 'getSelection':
                    const selection = getSelection();
                    return { type: 'response', id: message.id, success: true, data: selection };

                case 'getActiveFile':
                    const editor = vscode.window.activeTextEditor;
                    if (editor) {
                        return {
                            type: 'response',
                            id: message.id,
                            success: true,
                            data: {
                                path: editor.document.uri.fsPath,
                                language: editor.document.languageId,
                                lineCount: editor.document.lineCount
                            }
                        };
                    }
                    return { type: 'response', id: message.id, success: false, error: 'No active editor' };

                default:
                    return { type: 'response', id: message.id, success: false, error: `Unknown command: ${message.command}` };
            }
        } catch (error) {
            return {
                type: 'response',
                id: message.id,
                success: false,
                error: error instanceof Error ? error.message : String(error)
            };
        }
    }

    dispose(): void {
        this.disconnect();
    }
}
