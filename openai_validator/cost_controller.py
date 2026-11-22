"""
Cost Controller - Manage API budget and prevent overspending
"""

import os
from datetime import datetime, timedelta

class CostController:
    """Track and enforce API costs"""

    def __init__(self):
        self.max_per_review = float(os.getenv("OPENAI_VALIDATOR_MAX_COST_PER_REVIEW", "0.10"))
        self.daily_budget = float(os.getenv("OPENAI_VALIDATOR_DAILY_BUDGET", "5.00"))
        self.monthly_budget = float(os.getenv("OPENAI_VALIDATOR_MONTHLY_BUDGET", "50.00"))
        self.daily_spent = 0.0
        self.monthly_spent = 0.0
        self.validation_cache = {}

    def check_cost_limit(self, estimated_cost: float) -> bool:
        """Check if cost is within limits"""
        return estimated_cost <= self.max_per_review

    def check_daily_limit(self, estimated_cost: float) -> bool:
        """Check if daily limit would be exceeded"""
        return (self.daily_spent + estimated_cost) <= self.daily_budget

    def check_monthly_limit(self, estimated_cost: float) -> bool:
        """Check if monthly limit would be exceeded"""
        return (self.monthly_spent + estimated_cost) <= self.monthly_budget

    def can_validate(self, estimated_cost: float, task_id: str) -> bool:
        """Determine if validation can proceed within budgets"""

        # Check if already validated (prevent duplicates)
        if task_id in self.validation_cache:
            if self.validation_cache[task_id]["timestamp"] > (datetime.now() - timedelta(hours=24)):
                return False  # Duplicate within 24h

        # Check all limits
        return (
            self.check_cost_limit(estimated_cost) and
            self.check_daily_limit(estimated_cost) and
            self.check_monthly_limit(estimated_cost)
        )

    def record_validation(self, task_id: str, cost: float):
        """Record validation execution and cost"""
        self.daily_spent += cost
        self.monthly_spent += cost
        self.validation_cache[task_id] = {
            "timestamp": datetime.now(),
            "cost": cost
        }

    def get_budget_status(self) -> dict:
        """Get current budget status"""
        return {
            "daily_budget": self.daily_budget,
            "daily_spent": self.daily_spent,
            "daily_remaining": self.daily_budget - self.daily_spent,
            "monthly_budget": self.monthly_budget,
            "monthly_spent": self.monthly_spent,
            "monthly_remaining": self.monthly_budget - self.monthly_spent
        }
