import * as vscode from 'vscode';

export class StatusBarManager implements vscode.Disposable {
    private statusBarItem: vscode.StatusBarItem;
    private currentLoop: number = 0;
    private currentStatus: string = 'UNKNOWN';

    constructor() {
        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Left,
            100
        );
        this.statusBarItem.command = 'keeper.reconnect';
        this.statusBarItem.tooltip = 'Click to reconnect to Keeper Cockpit';
        this.setDisconnected();
        this.statusBarItem.show();
    }

    setConnecting(): void {
        this.statusBarItem.text = '$(sync~spin) Keeper: Connecting...';
        this.statusBarItem.backgroundColor = undefined;
    }

    setConnected(loop: number, status: string): void {
        this.currentLoop = loop;
        this.currentStatus = status;
        
        const icon = this.getStatusIcon(status);
        this.statusBarItem.text = `${icon} Loop ${loop}: ${status}`;
        this.statusBarItem.tooltip = `Keeper Cockpit - Loop ${loop}\nStatus: ${status}\nClick to refresh`;
        
        // Color based on status
        if (status === 'ACTIVE') {
            this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
        } else if (status === 'FINALIZED') {
            this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.prominentBackground');
        } else {
            this.statusBarItem.backgroundColor = undefined;
        }
    }

    setDisconnected(): void {
        this.statusBarItem.text = '$(circle-slash) Keeper: Disconnected';
        this.statusBarItem.tooltip = 'Click to connect to Keeper Cockpit';
        this.statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.errorBackground');
    }

    private getStatusIcon(status: string): string {
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

    getLoop(): number {
        return this.currentLoop;
    }

    getStatus(): string {
        return this.currentStatus;
    }

    dispose(): void {
        this.statusBarItem.dispose();
    }
}
