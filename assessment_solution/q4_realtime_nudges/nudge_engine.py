"""
nudge_engine.py — Q4 Real-Time Nudges
State manager that applies cooldown rules, deduplication,
and formatting to raw signals before they hit the dashboard.
"""

import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import NUDGE_COOLDOWN_SECONDS
from q4_realtime_nudges.signal_extractor import SignalMatch

class NudgeEngine:
    def __init__(self):
        # type -> timestamp of last fired nudge
        self.cooldown_state: dict[str, float] = {}
        self.active_nudges: list[dict] = []
        self.nudge_counter = 0

    def process_signal(self, match: Optional[SignalMatch]) -> Optional[dict]:
        """
        Receives a raw signal. 
        Returns a formatted Nudge dict if it passes cooldown/dedup.
        Returns None if suppressed.
        """
        if not match:
            return None

        current_time = time.time()
        sig_type = match.signal_type

        # Check cooldown
        last_fired = self.cooldown_state.get(sig_type, 0.0)
        if current_time - last_fired < NUDGE_COOLDOWN_SECONDS:
            # Suppressed due to cooldown (Dedup)
            return None

        # Determine visual severity
        severity = "info"
        if sig_type in ["compliance_gap", "churn_risk"]:
            severity = "critical"
        elif sig_type == "frustration":
            severity = "warning"

        # State update
        self.cooldown_state[sig_type] = current_time
        self.nudge_counter += 1

        nudge = {
            "id": self.nudge_counter,
            "timestamp": time.strftime("%H:%M:%S"),
            "type": sig_type,
            "message": match.recommended_nudge,
            "reasoning": match.reasoning,
            "confidence": match.confidence,
            "severity": severity
        }
        
        self.active_nudges.append(nudge)
        
        # Keep only the latest 10 nudges in history
        if len(self.active_nudges) > 10:
            self.active_nudges.pop(0)

        return nudge

    def clear(self):
        self.cooldown_state.clear()
        self.active_nudges.clear()
        self.nudge_counter = 0
