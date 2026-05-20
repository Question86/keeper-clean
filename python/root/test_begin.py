# MODE: SCRIPT

"""Deterministic generators and guardrails for the Keeper loop system.

This module is intentionally dependency-free (stdlib only) so it can be used
by both the Flask cockpit and simple CLI invocations.

Design goals:
- Deterministic ordering and stable output (sorted lists).
- Zero archive edits.
- Pointer-first artifacts (no large inline dumps).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

