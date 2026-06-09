import os
import time
import subprocess
import logging
from typing import Dict, Any

logger = logging.getLogger("Sovereign.Failsafe")

class FailsafeMonitor:
    """
    Sovereign Restore Point & Mathematical Stability Monitor.
    - Evaluates stability via mathematical metrics (error counts, uptimes).
    - NEVER inspects payloads or secrets (Zero-Trust / Blind evaluation).
    """
    def __init__(self, matrix_root: str):
        self.matrix_root = matrix_root
        self.metrics = {
            "total_events": 0,
            "error_events": 0,
            "last_error_time": 0.0,
            "start_time": time.time()
        }

    def record_event(self, is_error: bool = False):
        """Mathematically track events without seeing the payload"""
        self.metrics["total_events"] += 1
        if is_error:
            self.metrics["error_events"] += 1
            self.metrics["last_error_time"] = time.time()

    def calculate_stability_score(self) -> float:
        """
        Calculates a golden score (0-100) based on error rates and uptime.
        Pure math, no data inspection.
        """
        if self.metrics["total_events"] == 0:
            return 100.0
            
        error_rate = self.metrics["error_events"] / self.metrics["total_events"]
        uptime = time.time() - self.metrics["start_time"]
        
        # Penalize for recent errors
        time_since_error = time.time() - self.metrics["last_error_time"]
        recent_penalty = 0
        if self.metrics["last_error_time"] > 0 and time_since_error < 300: # within 5 mins
            recent_penalty = 20.0
            
        score = 100.0 - (error_rate * 100.0) - recent_penalty
        return max(0.0, min(100.0, score))

    def check_and_propose_golden_point(self) -> bool:
        """
        If the system is highly stable, propose a Golden Restore Point.
        This triggers a notification to the Commander.
        """
        score = self.calculate_stability_score()
        uptime = time.time() - self.metrics["start_time"]
        
        # Require 95+ score and at least 1 hour of simulated uptime (or 50 events)
        if score >= 95.0 and self.metrics["total_events"] > 50:
            return True
        return False

    def create_pre_danger_restore_point(self, operation_name: str) -> str:
        """
        Executes a blind Git Tag and Stash before a dangerous operation.
        Treats all data mathematically (SHA-1 via Git).
        """
        safe_name = operation_name.replace(" ", "_").replace("/", "_")
        timestamp = int(time.time())
        tag_name = f"PRE_DANGER_{safe_name}_{timestamp}"
        
        try:
            logger.info(f"Creating Pre-Danger Restore Point: {tag_name}")
            
            # 1. Stash any uncommitted tracked files
            subprocess.run(["git", "stash"], cwd=self.matrix_root, capture_output=True, check=True)
            
            # 2. Tag the current stable commit
            subprocess.run(["git", "tag", "-a", tag_name, "-m", f"Automated Failsafe before {operation_name}"], 
                           cwd=self.matrix_root, capture_output=True, check=True)
            
            logger.info("Restore point created successfully.")
            return tag_name
        except subprocess.CalledProcessError as e:
            logger.error("Failed to create restore point mathematically.")
            raise RuntimeError(f"Failsafe Git Error: {e.stderr}")

    def create_golden_restore_point(self, approval_signature: str) -> str:
        """
        Can only be executed if the Commander's approval signature is provided.
        """
        if not approval_signature:
            raise PermissionError("Sovereign Commander Approval Required!")
            
        timestamp = int(time.time())
        tag_name = f"GOLDEN_STATE_{timestamp}"
        
        subprocess.run(["git", "tag", "-a", tag_name, "-m", f"Approved Golden State by Commander. Sig: {approval_signature}"], 
                       cwd=self.matrix_root, capture_output=True, check=True)
        return tag_name

if __name__ == "__main__":
    # Test execution
    monitor = FailsafeMonitor(os.getcwd())
    print("Stability Score:", monitor.calculate_stability_score())
