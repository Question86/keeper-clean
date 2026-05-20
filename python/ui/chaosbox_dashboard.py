#!/usr/bin/env python3
"""
Chaosbox Dashboard - Web UI Integration for Quality Control System

Provides HTML/CSS/JS components for the chaosbox quality control system
integrated into the loop cockpit web interface.
"""

from typing import Dict, List, Any
import json
from datetime import datetime, timezone

def get_chaosbox_dashboard_html() -> str:
    """Generate HTML for the chaosbox dashboard."""
    return """
<div id="chaosbox-dashboard" class="dashboard-section">
    <h3>🌀 Chaosbox - Seed Idea Quality Control</h3>

    <div class="chaosbox-stats">
        <div class="stat-card">
            <h4>Total Ideas</h4>
            <span id="total-ideas" class="stat-value">0</span>
        </div>
        <div class="stat-card">
            <h4>Processing</h4>
            <span id="processing-count" class="stat-value">0</span>
        </div>
        <div class="stat-card">
            <h4>Accepted</h4>
            <span id="accepted-count" class="stat-value">0</span>
        </div>
        <div class="stat-card">
            <h4>Rejected</h4>
            <span id="rejected-count" class="stat-value">0</span>
        </div>
    </div>

    <div class="chaosbox-controls">
        <button id="refresh-chaosbox" class="btn btn-primary">🔄 Refresh Status</button>
        <button id="submit-test-idea" class="btn btn-secondary">🧪 Submit Test Idea</button>
    </div>

    <div class="chaosbox-queue">
        <h4>Recent Ideas</h4>
        <div id="recent-ideas" class="ideas-list">
            <div class="loading">Loading chaosbox status...</div>
        </div>
    </div>

    <div class="chaosbox-submit-form" style="display: none;">
        <h4>Submit New Idea</h4>
        <form id="idea-submit-form">
            <div class="form-group">
                <label for="idea-title">Title:</label>
                <input type="text" id="idea-title" required maxlength="200" placeholder="Brief, descriptive title">
            </div>

            <div class="form-group">
                <label for="idea-description">Description:</label>
                <textarea id="idea-description" required maxlength="2000" rows="6"
                    placeholder="Detailed description of the idea, including objectives, approach, and expected benefits"></textarea>
            </div>

            <div class="form-group">
                <label for="idea-tags">Tags (comma-separated):</label>
                <input type="text" id="idea-tags" placeholder="ai, automation, integration (optional)">
            </div>

            <div class="form-actions">
                <button type="submit" class="btn btn-success">📤 Submit to Chaosbox</button>
                <button type="button" id="cancel-submit" class="btn btn-secondary">Cancel</button>
            </div>
        </form>
    </div>
</div>

<style>
#chaosbox-dashboard {
    margin: 20px 0;
    padding: 20px;
    border: 1px solid #ddd;
    border-radius: 8px;
    background: #f9f9f9;
}

.chaosbox-stats {
    display: flex;
    gap: 15px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}

.stat-card {
    background: white;
    padding: 15px;
    border-radius: 6px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    text-align: center;
    min-width: 100px;
}

.stat-card h4 {
    margin: 0 0 8px 0;
    color: #666;
    font-size: 0.9em;
}

.stat-value {
    font-size: 1.8em;
    font-weight: bold;
    color: #333;
}

.chaosbox-controls {
    margin-bottom: 20px;
}

.btn {
    padding: 8px 16px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9em;
    margin-right: 10px;
}

.btn-primary {
    background: #007bff;
    color: white;
}

.btn-secondary {
    background: #6c757d;
    color: white;
}

.btn-success {
    background: #28a745;
    color: white;
}

.btn:hover {
    opacity: 0.9;
}

.ideas-list {
    background: white;
    border-radius: 6px;
    padding: 15px;
    min-height: 200px;
}

.idea-item {
    border: 1px solid #eee;
    border-radius: 4px;
    padding: 12px;
    margin-bottom: 10px;
    background: white;
}

.idea-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.idea-title {
    font-weight: bold;
    color: #333;
}

.idea-status {
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.8em;
    font-weight: bold;
}

.status-received { background: #e3f2fd; color: #1976d2; }
.status-validating { background: #fff3e0; color: #f57c00; }
.status-transforming { background: #f3e5f5; color: #7b1fa2; }
.status-queued { background: #e8f5e8; color: #388e3c; }
.status-accepted { background: #e8f5e8; color: #2e7d32; }
.status-rejected { background: #ffebee; color: #d32f2f; }
.status-error { background: #fafafa; color: #616161; }

.idea-meta {
    font-size: 0.9em;
    color: #666;
    margin-bottom: 8px;
}

.idea-description {
    font-size: 0.9em;
    color: #555;
    margin-bottom: 8px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.idea-score {
    font-size: 0.9em;
    font-weight: bold;
}

.score-excellent { color: #2e7d32; }
.score-good { color: #388e3c; }
.score-fair { color: #f57c00; }
.score-poor { color: #d32f2f; }
.score-unacceptable { color: #616161; }

.chaosbox-submit-form {
    background: white;
    padding: 20px;
    border-radius: 6px;
    margin-top: 20px;
}

.form-group {
    margin-bottom: 15px;
}

.form-group label {
    display: block;
    margin-bottom: 5px;
    font-weight: bold;
    color: #333;
}

.form-group input,
.form-group textarea {
    width: 100%;
    padding: 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-family: inherit;
}

.form-group textarea {
    resize: vertical;
}

.form-actions {
    display: flex;
    gap: 10px;
    justify-content: flex-end;
}

.loading {
    text-align: center;
    color: #666;
    padding: 40px;
}
</style>
"""

def get_chaosbox_dashboard_js() -> str:
    """Generate JavaScript for chaosbox dashboard functionality."""
    return """
// Chaosbox Dashboard JavaScript
class ChaosboxDashboard {
    constructor() {
        this.apiBase = '/api';
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadStatus();
    }

    bindEvents() {
        // Refresh button
        const refreshBtn = document.getElementById('refresh-chaosbox');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadStatus());
        }

        // Test idea button
        const testBtn = document.getElementById('submit-test-idea');
        if (testBtn) {
            testBtn.addEventListener('click', () => this.showSubmitForm());
        }

        // Cancel submit
        const cancelBtn = document.getElementById('cancel-submit');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.hideSubmitForm());
        }

        // Form submission
        const form = document.getElementById('idea-submit-form');
        if (form) {
            form.addEventListener('submit', (e) => this.submitIdea(e));
        }
    }

    async loadStatus() {
        try {
            const response = await fetch(`${this.apiBase}/chaosbox/status`);
            const data = await response.json();

            if (data.success) {
                this.updateStats(data.status);
                this.updateIdeasList(data.status.recent_ideas);
            } else {
                this.showError('Failed to load chaosbox status: ' + data.error);
            }
        } catch (error) {
            this.showError('Network error loading chaosbox status');
        }
    }

    updateStats(status) {
        document.getElementById('total-ideas').textContent = status.total_ideas || 0;
        document.getElementById('processing-count').textContent = status.queue_size || 0;
        document.getElementById('accepted-count').textContent = status.status_counts?.accepted || 0;
        document.getElementById('rejected-count').textContent = status.status_counts?.rejected || 0;
    }

    updateIdeasList(ideas) {
        const container = document.getElementById('recent-ideas');

        if (!ideas || ideas.length === 0) {
            container.innerHTML = '<div class="loading">No ideas in chaosbox yet.</div>';
            return;
        }

        const html = ideas.map(idea => `
            <div class="idea-item">
                <div class="idea-header">
                    <span class="idea-title">${this.escapeHtml(idea.title)}</span>
                    <span class="idea-status status-${idea.status}">${idea.status.toUpperCase()}</span>
                </div>
                <div class="idea-meta">
                    Submitted: ${new Date(idea.submitted_at).toLocaleString()}
                </div>
                <div class="idea-description">
                    ${this.escapeHtml(idea.result_summary || 'Processing...')}
                </div>
                ${idea.quality_score ? `<div class="idea-score score-${this.getScoreTier(idea.quality_score)}">
                    Quality Score: ${(idea.quality_score * 100).toFixed(1)}%
                </div>` : ''}
            </div>
        `).join('');

        container.innerHTML = html;
    }

    getScoreTier(score) {
        if (score >= 0.8) return 'excellent';
        if (score >= 0.7) return 'good';
        if (score >= 0.6) return 'fair';
        if (score >= 0.5) return 'poor';
        return 'unacceptable';
    }

    showSubmitForm() {
        document.querySelector('.chaosbox-submit-form').style.display = 'block';
        document.getElementById('idea-title').focus();
    }

    hideSubmitForm() {
        document.querySelector('.chaosbox-submit-form').style.display = 'none';
        document.getElementById('idea-submit-form').reset();
    }

    async submitIdea(event) {
        event.preventDefault();

        const formData = new FormData(event.target);
        const ideaData = {
            title: formData.get('idea-title').trim(),
            description: formData.get('idea-description').trim(),
            tags: formData.get('idea-tags').split(',').map(tag => tag.trim()).filter(tag => tag),
            submitted_by: 'web_ui'
        };

        try {
            const response = await fetch(`${this.apiBase}/chaosbox/submit`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(ideaData)
            });

            const result = await response.json();

            if (result.success) {
                this.showSuccess(`Idea submitted successfully! ID: ${result.idea_id}`);
                this.hideSubmitForm();
                this.loadStatus(); // Refresh the list
            } else {
                this.showError('Failed to submit idea: ' + result.error);
            }
        } catch (error) {
            this.showError('Network error submitting idea');
        }
    }

    showSuccess(message) {
        this.showMessage(message, 'success');
    }

    showError(message) {
        this.showMessage(message, 'error');
    }

    showMessage(message, type) {
        // Simple alert for now - could be enhanced with a proper notification system
        alert(`${type.toUpperCase()}: ${message}`);
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.chaosboxDashboard = new ChaosboxDashboard();
});

// Auto-refresh every 30 seconds
setInterval(() => {
    if (window.chaosboxDashboard) {
        window.chaosboxDashboard.loadStatus();
    }
}, 30000);
"""

def get_chaosbox_status_data() -> Dict[str, Any]:
    """Get current chaosbox status data for API responses."""
    try:
        from chaosbox.chaosbox_manager import get_chaosbox_manager
        manager = get_chaosbox_manager()
        return manager.get_queue_status()
    except Exception as e:
        return {
            "error": str(e),
            "total_ideas": 0,
            "status_counts": {},
            "queue_size": 0,
            "recent_ideas": []
        }

def submit_idea_via_api(title: str, description: str, submitted_by: str = "api",
                       tags: List[str] = None) -> Dict[str, Any]:
    """API function to submit an idea."""
    try:
        from chaosbox.chaosbox_manager import get_chaosbox_manager
        manager = get_chaosbox_manager()

        idea_id = manager.submit_idea(title, description, submitted_by, tags)
        return {
            "success": True,
            "idea_id": idea_id,
            "message": "Idea submitted to chaosbox for quality control processing"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def get_idea_details_via_api(idea_id: str) -> Dict[str, Any]:
    """API function to get idea details."""
    try:
        from chaosbox.chaosbox_manager import get_chaosbox_manager
        manager = get_chaosbox_manager()

        idea = manager.get_idea_status(idea_id)
        if idea:
            return {
                "success": True,
                "idea": {
                    "idea_id": idea.idea_id,
                    "title": idea.title,
                    "description": idea.description,
                    "status": idea.status.value,
                    "quality_score": idea.quality_score,
                    "submitted_at": idea.submitted_at,
                    "submitted_by": idea.submitted_by,
                    "tags": idea.tags,
                    "processing_history": idea.processing_history
                }
            }
        else:
            return {
                "success": False,
                "error": "Idea not found"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)