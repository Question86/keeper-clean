#!/usr/bin/env python3
"""
Knowledge Butler - Autonomous Knowledge Gathering and Database Integration System

Core autonomous orchestration system for TASK_0185. Coordinates:
- Breadcrumb scanning for knowledge gaps
- Autonomous search agent spawning
- Parallel database updates
- Knowledge forecasting

Runs continuously in background with minimal human intervention.
"""

import json
import os
import sys
import time
import threading
import logging
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict

# Add workspace root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.breadcrumb_scanner import BreadcrumbScanner
from agents.search_agent import SearchAgent
from integration.parallel_updater import ParallelUpdater
from forecast.knowledge_forecaster import KnowledgeForecaster
from knowledge_db import KnowledgeDB

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('knowledge_butler.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@dataclass
class KnowledgeGap:
    """Represents a detected knowledge gap."""
    topic: str
    confidence: float
    sources: List[str]
    priority: str  # 'high', 'medium', 'low'
    detected_at: str
    search_queries: List[str]

@dataclass
class ButlerConfig:
    """Configuration for the Knowledge Butler."""
    scan_interval: int = 300  # 5 minutes
    max_concurrent_searches: int = 3
    max_concurrent_updates: int = 5
    forecast_horizon_days: int = 7
    min_gap_confidence: float = 0.7
    enable_autonomous_mode: bool = True

class KnowledgeButler:
    """
    Autonomous knowledge gathering and database integration system.

    Continuously monitors for knowledge gaps and orchestrates:
    1. Breadcrumb analysis for gap detection
    2. Search agent spawning for web research
    3. Parallel database updates
    4. Knowledge requirement forecasting
    """

    def __init__(self, workspace_root: Path, config: Optional[ButlerConfig] = None):
        self.workspace_root = Path(workspace_root)
        self.config = config or ButlerConfig()

        # Initialize components
        self.knowledge_db = KnowledgeDB(workspace_root)
        self.scanner = BreadcrumbScanner(workspace_root)
        self.search_agent = SearchAgent()
        self.updater = ParallelUpdater(workspace_root, self.knowledge_db)
        self.forecaster = KnowledgeForecaster(workspace_root)

        # State tracking
        self.active_gaps: Dict[str, KnowledgeGap] = {}
        self.completed_gaps: Set[str] = set()
        self.running = False
        self.scan_thread: Optional[threading.Thread] = None
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_searches)

        # Load persisted state
        self._load_state()

    def start(self) -> None:
        """Start the autonomous knowledge butler."""
        if self.running:
            logger.warning("Knowledge Butler already running")
            return

        logger.info("Starting Knowledge Butler in autonomous mode")
        self.running = True

        # Start background scanning thread
        self.scan_thread = threading.Thread(target=self._continuous_scan, daemon=True)
        self.scan_thread.start()

        # Initial scan
        self._perform_scan()

    def stop(self) -> None:
        """Stop the autonomous knowledge butler."""
        logger.info("Stopping Knowledge Butler")
        self.running = False

        if self.scan_thread:
            self.scan_thread.join(timeout=10)

        self.executor.shutdown(wait=True)
        self.knowledge_db.close()
        self._save_state()

    def _continuous_scan(self) -> None:
        """Continuous background scanning loop."""
        while self.running:
            try:
                self._perform_scan()
                time.sleep(self.config.scan_interval)
            except Exception as e:
                logger.error(f"Error in continuous scan: {e}")
                time.sleep(60)  # Wait before retry

    def _perform_scan(self) -> None:
        """Perform a complete knowledge gap scan and processing cycle."""
        try:
            logger.info("Performing knowledge gap scan")

            # 1. Scan breadcrumbs for gaps
            gaps = self.scanner.scan_for_gaps()

            # 2. Filter and prioritize gaps
            valid_gaps = [
                gap for gap in gaps
                if gap.confidence >= self.config.min_gap_confidence
            ]

            # 3. Forecast future needs
            forecast = self.forecaster.forecast_requirements(self.config.forecast_horizon_days)
            forecast_gaps = self._convert_forecast_to_gaps(forecast)
            valid_gaps.extend(forecast_gaps)

            # 4. Process gaps autonomously
            if self.config.enable_autonomous_mode:
                self._process_gaps_autonomously(valid_gaps)

            # 5. Update state
            for gap in valid_gaps:
                self.active_gaps[gap.topic] = gap

        except Exception as e:
            logger.error(f"Error during scan: {e}")

    def _process_gaps_autonomously(self, gaps: List[KnowledgeGap]) -> None:
        """Process knowledge gaps autonomously using search agents."""
        if not gaps:
            return

        logger.info(f"Processing {len(gaps)} knowledge gaps autonomously")

        # Submit search tasks
        futures = []
        for gap in gaps:
            if gap.topic not in self.completed_gaps:
                future = self.executor.submit(self._search_and_update, gap)
                futures.append((gap.topic, future))

        # Monitor completion
        for topic, future in futures:
            try:
                success = future.result(timeout=300)  # 5 minute timeout
                if success:
                    self.completed_gaps.add(topic)
                    if topic in self.active_gaps:
                        del self.active_gaps[topic]
                    logger.info(f"Successfully processed knowledge gap: {topic}")
            except Exception as e:
                logger.error(f"Failed to process gap {topic}: {e}")

    def _search_and_update(self, gap: KnowledgeGap) -> bool:
        """Search for information and update database for a single gap."""
        try:
            # Perform searches
            search_results = []
            for query in gap.search_queries:
                results = self.search_agent.search(query)
                search_results.extend(results)

            if not search_results:
                logger.warning(f"No search results found for gap: {gap.topic}")
                return False

            # Update database in parallel
            success = self.updater.update_knowledge(gap.topic, search_results)
            return success

        except Exception as e:
            logger.error(f"Error searching and updating for {gap.topic}: {e}")
            return False

    def _convert_forecast_to_gaps(self, forecast: Dict[str, Any]) -> List[KnowledgeGap]:
        """Convert forecast requirements to knowledge gaps."""
        gaps = []
        for topic, data in forecast.get('predicted_needs', {}).items():
            if data.get('confidence', 0) >= self.config.min_gap_confidence:
                gap = KnowledgeGap(
                    topic=topic,
                    confidence=data['confidence'],
                    sources=['forecast'],
                    priority=data.get('priority', 'medium'),
                    detected_at=datetime.now(timezone.utc).isoformat(),
                    search_queries=data.get('search_queries', [topic])
                )
                gaps.append(gap)
        return gaps

    def get_status(self) -> Dict[str, Any]:
        """Get current status of the knowledge butler."""
        return {
            'running': self.running,
            'active_gaps': len(self.active_gaps),
            'completed_gaps': len(self.completed_gaps),
            'config': asdict(self.config),
            'last_scan': getattr(self, '_last_scan_time', None)
        }

    def _load_state(self) -> None:
        """Load persisted state from disk."""
        state_file = self.workspace_root / 'knowledge_butler_state.json'
        if state_file.exists():
            try:
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    self.completed_gaps = set(state.get('completed_gaps', []))
                    self.active_gaps = {
                        k: KnowledgeGap(**v) for k, v in state.get('active_gaps', {}).items()
                    }
                logger.info("Loaded persisted state")
            except Exception as e:
                logger.error(f"Failed to load state: {e}")

    def _save_state(self) -> None:
        """Save current state to disk."""
        state_file = self.workspace_root / 'knowledge_butler_state.json'
        try:
            state = {
                'completed_gaps': list(self.completed_gaps),
                'active_gaps': {k: asdict(v) for k, v in self.active_gaps.items()},
                'saved_at': datetime.now(timezone.utc).isoformat()
            }
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
            logger.info("Saved state to disk")
        except Exception as e:
            logger.error(f"Failed to save state: {e}")


def main():
    """Main entry point for running the Knowledge Butler."""
    import argparse

    parser = argparse.ArgumentParser(description="Knowledge Butler - Autonomous Knowledge Gathering")
    parser.add_argument('--workspace', type=Path, default=Path('.'),
                       help='Workspace root directory')
    parser.add_argument('--scan-interval', type=int, default=300,
                       help='Scan interval in seconds')
    parser.add_argument('--max-searches', type=int, default=3,
                       help='Maximum concurrent searches')
    parser.add_argument('--daemon', action='store_true',
                       help='Run as daemon (background)')

    args = parser.parse_args()

    # Configure butler
    config = ButlerConfig(
        scan_interval=args.scan_interval,
        max_concurrent_searches=args.max_searches
    )

    butler = KnowledgeButler(args.workspace, config)

    if args.daemon:
        # Run as daemon
        butler.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            butler.stop()
    else:
        # Run single scan
        butler._perform_scan()
        print(f"Scan complete. Active gaps: {len(butler.active_gaps)}")


if __name__ == '__main__':
    main()