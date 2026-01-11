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
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.CockpitBridge = void 0;
const vscode = __importStar(require("vscode"));
const ws_1 = __importDefault(require("ws"));
const extension_1 = require("./extension");
class CockpitBridge {
    ws = null;
    reconnectTimer = null;
    pollTimer = null;
    cockpitUrl;
    wsUrl;
    statusBar;
    pollInterval;
    isConnecting = false;
    constructor(cockpitUrl, statusBar, pollInterval) {
        this.cockpitUrl = cockpitUrl;
        // WebSocket endpoint on cockpit
        this.wsUrl = cockpitUrl.replace('http://', 'ws://').replace('https://', 'wss://') + '/ws/extension';
        this.statusBar = statusBar;
        this.pollInterval = pollInterval;
    }
    async connect() {
        if (this.isConnecting || (this.ws && this.ws.readyState === ws_1.default.OPEN)) {
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
            const status = await response.json();
            this.statusBar.setConnected(status.loop, status.status);
            // Start polling for status updates (WebSocket is optional enhancement)
            this.startPolling();
            this.isConnecting = false;
            return true;
        }
        catch (error) {
            console.error('Failed to connect to cockpit:', error);
            this.statusBar.setDisconnected();
            this.isConnecting = false;
            this.scheduleReconnect();
            return false;
        }
    }
    startPolling() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
        }
        this.pollTimer = setInterval(async () => {
            try {
                const response = await fetch(`${this.cockpitUrl}/api/status`);
                if (response.ok) {
                    const status = await response.json();
                    this.statusBar.setConnected(status.loop, status.status);
                }
            }
            catch (error) {
                console.warn('Status poll failed:', error);
                this.statusBar.setDisconnected();
            }
        }, this.pollInterval);
    }
    scheduleReconnect() {
        if (this.reconnectTimer) {
            return;
        }
        this.reconnectTimer = setTimeout(() => {
            this.reconnectTimer = null;
            this.connect();
        }, 10000); // Retry in 10 seconds
    }
    async reconnect() {
        this.disconnect();
        await this.connect();
    }
    disconnect() {
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
    async handleMessage(message) {
        try {
            switch (message.command) {
                case 'openFile':
                    if (message.path) {
                        const success = await (0, extension_1.openFile)(message.path);
                        return { type: 'response', id: message.id, success };
                    }
                    return { type: 'response', id: message.id, success: false, error: 'No path provided' };
                case 'runTerminal':
                    if (message.text) {
                        await (0, extension_1.runTerminalCommand)(message.text);
                        return { type: 'response', id: message.id, success: true };
                    }
                    return { type: 'response', id: message.id, success: false, error: 'No command provided' };
                case 'getSelection':
                    const selection = (0, extension_1.getSelection)();
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
        }
        catch (error) {
            return {
                type: 'response',
                id: message.id,
                success: false,
                error: error instanceof Error ? error.message : String(error)
            };
        }
    }
    dispose() {
        this.disconnect();
    }
}
exports.CockpitBridge = CockpitBridge;
//# sourceMappingURL=bridge.js.map