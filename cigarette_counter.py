#!/usr/bin/env python3
"""
Cigarette Counter Panel - Motivational Desktop Widget
Tracks cigarettes not smoked since quit date (January 2, 2025)
"""

import tkinter as tk
from tkinter import ttk
import json
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Configuration file
CONFIG_FILE = Path(__file__).parent / "cigarette_counter_config.json"

# Default configuration
DEFAULT_CONFIG = {
    "quit_date": "2025-01-02",
    "cigarettes_per_day": 20,
    "price_per_pack": 7.50,
    "cigarettes_per_pack": 20,
    "currency": "€",
    "always_on_top": True,
    "update_interval_ms": 1000,
    "window_x": 100,
    "window_y": 100
}

# Health milestones (hours after quitting)
HEALTH_MILESTONES = [
    (20/60, "20 minutes", "Heart rate and blood pressure drop"),
    (12, "12 hours", "Carbon monoxide level normalizes"),
    (24*1, "1 day", "Heart attack risk begins to drop"),
    (24*2, "2 days", "Nerve endings regrow, taste/smell improve"),
    (24*7, "1 week", "Circulation improves significantly"),
    (24*30, "1 month", "Lung function increases up to 30%"),
    (24*90, "3 months", "Coughing and shortness of breath decrease"),
    (24*365, "1 year", "Heart disease risk drops by 50%"),
    (24*365*5, "5 years", "Stroke risk same as non-smoker"),
    (24*365*10, "10 years", "Lung cancer risk drops by 50%"),
]


def load_config():
    """Load or create configuration file."""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Merge with defaults for any missing keys
                return {**DEFAULT_CONFIG, **config}
        except:
            pass
    
    # Create default config
    save_config(DEFAULT_CONFIG)
    return DEFAULT_CONFIG.copy()


def save_config(config):
    """Save configuration to file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)


class CigaretteCounterPanel:
    def __init__(self, root):
        self.root = root
        self.config = load_config()
        
        # Parse quit date
        self.quit_date = datetime.strptime(self.config['quit_date'], '%Y-%m-%d')
        
        # Setup window
        self.root.title("🚭 Smoke Free Tracker")
        self.root.geometry(f"380x340+{self.config['window_x']}+{self.config['window_y']}")
        self.root.configure(bg='#1a1f3a')
        
        if self.config['always_on_top']:
            self.root.attributes('-topmost', True)
        
        # Make window draggable
        self.root.bind('<Button-1>', self.start_move)
        self.root.bind('<B1-Motion>', self.on_move)
        
        # Setup UI
        self.setup_ui()
        
        # Start update loop
        self.update_display()
        
        # Save position on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def start_move(self, event):
        self.x = event.x
        self.y = event.y
    
    def on_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")
    
    def setup_ui(self):
        """Create the user interface."""
        # Main container
        main_frame = tk.Frame(self.root, bg='#1a1f3a', padx=20, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(
            main_frame,
            text="🚭 SMOKE FREE TRACKER",
            font=('Courier New', 16, 'bold'),
            bg='#1a1f3a',
            fg='#00ff88'
        )
        title_label.pack(pady=(0, 15))
        
        # Days counter
        self.days_label = tk.Label(
            main_frame,
            text="",
            font=('Courier New', 36, 'bold'),
            bg='#1a1f3a',
            fg='#00ccff'
        )
        self.days_label.pack()
        
        days_text_label = tk.Label(
            main_frame,
            text="DAYS SMOKE FREE",
            font=('Courier New', 10),
            bg='#1a1f3a',
            fg='#00ccff'
        )
        days_text_label.pack(pady=(0, 15))
        
        # Cigarettes not smoked
        self.cigarettes_label = tk.Label(
            main_frame,
            text="",
            font=('Courier New', 14, 'bold'),
            bg='#1a1f3a',
            fg='#00ff88'
        )
        self.cigarettes_label.pack(pady=5)
        
        # Money saved
        self.money_label = tk.Label(
            main_frame,
            text="",
            font=('Courier New', 14, 'bold'),
            bg='#1a1f3a',
            fg='#ffaa00'
        )
        self.money_label.pack(pady=5)
        
        # Separator
        separator = tk.Frame(main_frame, height=2, bg='#00ff88')
        separator.pack(fill=tk.X, pady=10)
        
        # Current milestone
        milestone_title = tk.Label(
            main_frame,
            text="HEALTH MILESTONE:",
            font=('Courier New', 9, 'bold'),
            bg='#1a1f3a',
            fg='#00ccff'
        )
        milestone_title.pack()
        
        self.milestone_label = tk.Label(
            main_frame,
            text="",
            font=('Courier New', 9),
            bg='#1a1f3a',
            fg='#00ff88',
            wraplength=340,
            justify=tk.LEFT
        )
        self.milestone_label.pack(pady=5)
        
        # Next milestone
        self.next_milestone_label = tk.Label(
            main_frame,
            text="",
            font=('Courier New', 8),
            bg='#1a1f3a',
            fg='#666666',
            wraplength=340,
            justify=tk.LEFT
        )
        self.next_milestone_label.pack(pady=5)
    
    def get_current_milestone(self, hours_free):
        """Get current and next health milestone."""
        current = None
        next_milestone = None
        
        for i, (milestone_hours, name, description) in enumerate(HEALTH_MILESTONES):
            if hours_free >= milestone_hours:
                current = (name, description)
            else:
                if next_milestone is None:
                    next_milestone = (milestone_hours, name, description)
                break
        
        return current, next_milestone
    
    def update_display(self):
        """Update all display values."""
        now = datetime.now()
        time_free = now - self.quit_date
        
        # Calculate values
        days_free = time_free.days
        hours_free = time_free.total_seconds() / 3600
        cigarettes_not_smoked = int(days_free * self.config['cigarettes_per_day'])
        
        # Calculate money saved
        price_per_cigarette = self.config['price_per_pack'] / self.config['cigarettes_per_pack']
        money_saved = cigarettes_not_smoked * price_per_cigarette
        
        # Update labels
        self.days_label.config(text=f"{days_free}")
        self.cigarettes_label.config(text=f"🚬 {cigarettes_not_smoked:,} cigarettes NOT smoked")
        self.money_label.config(text=f"💰 {self.config['currency']}{money_saved:.2f} saved")
        
        # Update milestone
        current, next_m = self.get_current_milestone(hours_free)
        
        if current:
            self.milestone_label.config(text=f"✓ {current[0]}: {current[1]}")
        else:
            self.milestone_label.config(text="Building towards first milestone...")
        
        if next_m:
            hours_until = next_m[0] - hours_free
            if hours_until < 24:
                time_str = f"{int(hours_until)} hours"
            else:
                time_str = f"{int(hours_until / 24)} days"
            self.next_milestone_label.config(
                text=f"Next: {next_m[1]} in {time_str}\n{next_m[2]}"
            )
        else:
            self.next_milestone_label.config(text="All major milestones achieved! 🎉")
        
        # Schedule next update
        self.root.after(self.config['update_interval_ms'], self.update_display)
    
    def on_close(self):
        """Save window position before closing."""
        self.config['window_x'] = self.root.winfo_x()
        self.config['window_y'] = self.root.winfo_y()
        save_config(self.config)
        self.root.destroy()


def main():
    root = tk.Tk()
    app = CigaretteCounterPanel(root)
    root.mainloop()


if __name__ == '__main__':
    main()
