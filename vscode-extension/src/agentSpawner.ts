import * as vscode from 'vscode';

export interface AgentSession {
    agentId: string;
    taskId: string;
    worktreePath: string;
    prompt: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    progress: number;
    startedAt?: string;
    completedAt?: string;
    error?: string;
    response?: string;
}

export class AgentSpawner implements vscode.Disposable {
    private activeSessions: Map<string, AgentSession> = new Map();
    private outputChannel: vscode.OutputChannel;

    constructor() {
        this.outputChannel = vscode.window.createOutputChannel('Keeper Agents');
    }

    async spawnAgent(session: AgentSession): Promise<boolean> {
        this.outputChannel.appendLine(`[${new Date().toISOString()}] Spawning agent ${session.agentId} for ${session.taskId}`);
        
        session.status = 'running';
        session.startedAt = new Date().toISOString();
        this.activeSessions.set(session.agentId, session);

        try {
            // Select a Copilot chat model
            const models = await vscode.lm.selectChatModels({
                vendor: 'copilot',
                family: 'gpt-4o'
            });

            if (models.length === 0) {
                throw new Error('No Copilot chat models available. Make sure GitHub Copilot extension is installed and authenticated.');
            }

            const model = models[0];
            this.outputChannel.appendLine(`Using model: ${model.name} (${model.vendor}/${model.family})`);

            // Prepare messages
            const messages = [
                vscode.LanguageModelChatMessage.User(session.prompt)
            ];

            // Create cancellation token
            const tokenSource = new vscode.CancellationTokenSource();

            // Send request and collect response
            this.outputChannel.appendLine(`Sending request to model...`);
            const response = await model.sendRequest(messages, {}, tokenSource.token);

            // Collect full response
            let fullResponse = '';
            for await (const chunk of response.text) {
                fullResponse += chunk;
                session.progress = Math.min(95, session.progress + 5);
            }

            session.response = fullResponse;
            session.status = 'completed';
            session.progress = 100;
            session.completedAt = new Date().toISOString();

            this.outputChannel.appendLine(`Agent ${session.agentId} completed successfully`);
            this.outputChannel.appendLine(`Response length: ${fullResponse.length} characters`);

            return true;
        } catch (error) {
            session.status = 'failed';
            session.error = error instanceof Error ? error.message : String(error);
            session.completedAt = new Date().toISOString();

            this.outputChannel.appendLine(`Agent ${session.agentId} failed: ${session.error}`);

            if (error instanceof vscode.LanguageModelError) {
                this.outputChannel.appendLine(`Error code: ${error.code}`);
                if (error.code === 'NoAccess') {
                    vscode.window.showErrorMessage(
                        'GitHub Copilot access denied. Please check your Copilot subscription and permissions.'
                    );
                }
            }

            return false;
        }
    }

    async checkModelAvailability(): Promise<{available: boolean; models: string[]}> {
        try {
            const models = await vscode.lm.selectChatModels({ vendor: 'copilot' });
            return {
                available: models.length > 0,
                models: models.map(m => `${m.vendor}/${m.family}: ${m.name}`)
            };
        } catch (error) {
            return { available: false, models: [] };
        }
    }

    getSession(agentId: string): AgentSession | undefined {
        return this.activeSessions.get(agentId);
    }

    getAllSessions(): AgentSession[] {
        return Array.from(this.activeSessions.values());
    }

    clearCompleted(): void {
        for (const [id, session] of this.activeSessions) {
            if (session.status === 'completed' || session.status === 'failed') {
                this.activeSessions.delete(id);
            }
        }
    }

    showOutput(): void {
        this.outputChannel.show();
    }

    dispose(): void {
        this.outputChannel.dispose();
    }
}

// Generate standard agent prompt
export function generateAgentPrompt(
    agentId: string,
    taskId: string,
    worktreePath: string,
    taskDescription: string,
    loop: number
): string {
    return `You are Agent ${agentId} working on ${taskId}.

## Working Directory
${worktreePath}

## Task
${taskDescription}

## Instructions
1. Read the task specification carefully
2. Create a report file following REPORT-FIRST law:
   - File: reports/report_${taskId}_L${loop}_v01.md
   - Include: objective, approach, implementation details, outcome
3. Implement the task as specified
4. Test your implementation
5. Summarize results

## Critical Rules
- Follow all rules in PROJECT_TECH_BASELINE.md
- Never modify files outside your worktree
- Document all work in the report
- Report any blockers or issues

## Output Format
Return your results in this format:

STATUS: [COMPLETED|FAILED|BLOCKED]
PROGRESS: [0-100]
SUMMARY: [Brief description of work done]
FILES_CREATED: [List of files created/modified]
NEXT_STEPS: [Any follow-up needed]

Begin work now.`;
}
