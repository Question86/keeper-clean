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
exports.StatusBarManager = void 0;
const vscode = __importStar(require("vscode"));
class StatusBarManager {
    statusBarItem;
    currentLoop = 0;
    currentStatus = 'UNKNOWN';
    constructor() {
        this.statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
        this.statusBarItem.command = 'keeper.reconnect';
        this.statusBarItem.tooltip = 'Click to reconnect to Keeper Cockpit';
        this.setDisconnected();
        this.statusBarItem.show();
    }
    setConnecting() {
        this.statusBarItem.text = '$(sync~spin) Keeper: Connecting...';
        this.statusBarItem.backgroundColor = undefined;
    }
    setConnected(loop, status) {
        this.currentLoop = loop;
        this.currentStatus = status;
        const icon = this.getStatusIcon(status);
        this.statusBarItem.text = `${icon} Loop ${loop}: ${status}`;
        this.statusBarItem.tooltip = `Keeper Cockpit - Loop ${loop}\nStatus: ${status}\nClick to refresh`;
        // Color based on status
        if (status === 'ACTIVE') {
            this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
        }
        else if (status === 'FINALIZED') {
            this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.prominentBackground');
        }
        else {
            this.statusBarItem.backgroundColor = undefined;
        }
    }
    setDisconnected() {
        this.statusBarItem.text = '$(circle-slash) Keeper: Disconnected';
        this.statusBarItem.tooltip = 'Click to connect to Keeper Cockpit';
        this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
    }
    getStatusIcon(status) {
        switch (status) {
            case 'ACTIVE':
                return '$(pulse)';
            case 'FINALIZED':
                return '$(check)';
            case 'READY_FOR_RESET':
                return '$(refresh)';
            default:
                return '$(circle-outline)';
        }
    }
    getLoop() {
        return this.currentLoop;
    }
    getStatus() {
        return this.currentStatus;
    }
    dispose() {
        this.statusBarItem.dispose();
    }
}
exports.StatusBarManager = StatusBarManager;
//# sourceMappingURL=statusBar.js.map