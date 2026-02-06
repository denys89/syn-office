"""
Rate Limiter and Cost Guardrails for the Agent Orchestrator.

This module provides:
- CreditRateLimiter: Prevent runaway credit consumption
- AnomalyDetector: Detect unusual spending patterns
- CircuitBreaker: Prevent cascading failures
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


class RateLimitAction(Enum):
    """Actions to take when rate limit is hit."""
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    PAUSE = "pause"


@dataclass
class BudgetCheckResult:
    """Result of a budget check."""
    allowed: bool
    action: RateLimitAction
    reason: Optional[str] = None
    current_hourly_usage: int = 0
    hourly_limit: Optional[int] = None
    current_daily_usage: int = 0
    daily_limit: Optional[int] = None
    credits_remaining: int = 0
    cooldown_seconds: int = 0


@dataclass
class ConsumptionRecord:
    """Record of credit consumption."""
    timestamp: datetime
    credits: int
    model_name: str
    task_id: str


@dataclass
class OfficeUsageState:
    """Tracks usage state for an office."""
    hourly_records: list = field(default_factory=list)
    daily_credits: int = 0
    last_reset_hour: int = -1
    last_reset_day: int = -1
    avg_hourly_usage: float = 0.0
    workflow_depth: int = 0


class CreditRateLimiter:
    """
    Rate limiter for credit consumption.
    
    Implements:
    - Hourly credit limits
    - Daily credit limits
    - Spike detection
    - Cooldown periods
    """
    
    # Default limits (can be overridden per office via subscription)
    DEFAULT_HOURLY_LIMIT = 1000  # Credits per hour
    DEFAULT_DAILY_LIMIT = 10000  # Credits per day
    COOLDOWN_SECONDS = 60  # Wait time after hitting limit
    
    def __init__(self):
        self._office_state: dict[str, OfficeUsageState] = defaultdict(OfficeUsageState)
        self._lock = asyncio.Lock()
    
    async def check_budget(
        self,
        office_id: str,
        estimated_credits: int,
        hourly_limit: Optional[int] = None,
        daily_limit: Optional[int] = None,
        credits_remaining: int = 0,
        budget_pause_enabled: bool = False,
    ) -> BudgetCheckResult:
        """
        Check if the office can consume the estimated credits.
        
        Args:
            office_id: The office to check
            estimated_credits: Estimated credits for this task
            hourly_limit: Custom hourly limit (from subscription)
            daily_limit: Custom daily limit (from subscription)
            credits_remaining: Current wallet balance
            budget_pause_enabled: Whether to block on limit exceeded
            
        Returns:
            BudgetCheckResult with decision and details
        """
        hourly_limit = hourly_limit or self.DEFAULT_HOURLY_LIMIT
        daily_limit = daily_limit or self.DEFAULT_DAILY_LIMIT
        
        async with self._lock:
            state = self._office_state[office_id]
            self._cleanup_old_records(state)
            
            # Calculate current usage
            current_hour_usage = sum(r.credits for r in state.hourly_records)
            
            # Check hourly limit
            if current_hour_usage + estimated_credits > hourly_limit:
                action = RateLimitAction.BLOCK if budget_pause_enabled else RateLimitAction.WARN
                return BudgetCheckResult(
                    allowed=not budget_pause_enabled,
                    action=action,
                    reason=f"Hourly limit exceeded: {current_hour_usage}/{hourly_limit}",
                    current_hourly_usage=current_hour_usage,
                    hourly_limit=hourly_limit,
                    current_daily_usage=state.daily_credits,
                    daily_limit=daily_limit,
                    credits_remaining=credits_remaining,
                    cooldown_seconds=self.COOLDOWN_SECONDS if budget_pause_enabled else 0,
                )
            
            # Check daily limit
            if state.daily_credits + estimated_credits > daily_limit:
                action = RateLimitAction.BLOCK if budget_pause_enabled else RateLimitAction.WARN
                return BudgetCheckResult(
                    allowed=not budget_pause_enabled,
                    action=action,
                    reason=f"Daily limit exceeded: {state.daily_credits}/{daily_limit}",
                    current_hourly_usage=current_hour_usage,
                    hourly_limit=hourly_limit,
                    current_daily_usage=state.daily_credits,
                    daily_limit=daily_limit,
                    credits_remaining=credits_remaining,
                    cooldown_seconds=self.COOLDOWN_SECONDS if budget_pause_enabled else 0,
                )
            
            # Check remaining balance
            if credits_remaining < estimated_credits:
                return BudgetCheckResult(
                    allowed=False,
                    action=RateLimitAction.BLOCK,
                    reason=f"Insufficient credits: {credits_remaining} < {estimated_credits}",
                    current_hourly_usage=current_hour_usage,
                    hourly_limit=hourly_limit,
                    current_daily_usage=state.daily_credits,
                    daily_limit=daily_limit,
                    credits_remaining=credits_remaining,
                )
            
            return BudgetCheckResult(
                allowed=True,
                action=RateLimitAction.ALLOW,
                current_hourly_usage=current_hour_usage,
                hourly_limit=hourly_limit,
                current_daily_usage=state.daily_credits,
                daily_limit=daily_limit,
                credits_remaining=credits_remaining,
            )
    
    async def record_consumption(
        self,
        office_id: str,
        credits: int,
        model_name: str = "",
        task_id: str = "",
    ):
        """Record credit consumption for rate limiting."""
        async with self._lock:
            state = self._office_state[office_id]
            self._cleanup_old_records(state)
            
            record = ConsumptionRecord(
                timestamp=datetime.now(),
                credits=credits,
                model_name=model_name,
                task_id=task_id,
            )
            state.hourly_records.append(record)
            state.daily_credits += credits
            
            logger.debug(
                f"Recorded {credits} credits for office {office_id}, "
                f"hourly: {sum(r.credits for r in state.hourly_records)}, "
                f"daily: {state.daily_credits}"
            )
    
    def _cleanup_old_records(self, state: OfficeUsageState):
        """Remove records older than 1 hour and reset daily if needed."""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        
        # Remove old hourly records
        state.hourly_records = [
            r for r in state.hourly_records 
            if r.timestamp > one_hour_ago
        ]
        
        # Reset daily at midnight
        if now.day != state.last_reset_day:
            state.daily_credits = 0
            state.last_reset_day = now.day


class AnomalyDetector:
    """
    Detect anomalous credit consumption patterns.
    
    Protects against:
    - Consumption spikes (sudden high usage)
    - Excessive single-task costs
    - Recursive workflow loops
    """
    
    # Alert if hourly consumption > N times average
    CONSUMPTION_SPIKE_THRESHOLD = 5.0
    
    # Maximum credits for a single task
    MAX_CREDITS_PER_TASK = 1000
    
    # Maximum workflow recursion depth
    MAX_WORKFLOW_RECURSION = 10
    
    # Minimum samples for spike detection
    MIN_SAMPLES_FOR_SPIKE_DETECTION = 5
    
    def __init__(self):
        self._office_history: dict[str, list[int]] = defaultdict(list)
        self._workflow_depth: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()
    
    async def check_task_credits(
        self,
        office_id: str,
        estimated_credits: int,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if task credits are within acceptable range.
        
        Returns:
            Tuple of (allowed, reason if blocked)
        """
        if estimated_credits > self.MAX_CREDITS_PER_TASK:
            return False, f"Task credits ({estimated_credits}) exceed max ({self.MAX_CREDITS_PER_TASK})"
        return True, None
    
    async def check_consumption_spike(
        self,
        office_id: str,
        current_hourly_usage: int,
    ) -> tuple[bool, Optional[str]]:
        """
        Detect consumption spikes compared to historical average.
        
        Returns:
            Tuple of (is_spike, reason)
        """
        async with self._lock:
            history = self._office_history[office_id]
            
            if len(history) < self.MIN_SAMPLES_FOR_SPIKE_DETECTION:
                # Not enough data to detect spikes
                return False, None
            
            avg = sum(history) / len(history)
            if avg == 0:
                return False, None
            
            ratio = current_hourly_usage / avg
            if ratio > self.CONSUMPTION_SPIKE_THRESHOLD:
                return True, f"Consumption spike detected: {current_hourly_usage} is {ratio:.1f}x average ({avg:.0f})"
            
            return False, None
    
    async def record_hourly_usage(self, office_id: str, usage: int):
        """Record hourly usage for spike detection."""
        async with self._lock:
            history = self._office_history[office_id]
            history.append(usage)
            # Keep last 24 hours
            if len(history) > 24:
                history.pop(0)
    
    async def check_workflow_depth(
        self,
        office_id: str,
        workflow_id: str,
    ) -> tuple[bool, Optional[str]]:
        """
        Check if workflow recursion is within limits.
        
        Returns:
            Tuple of (allowed, reason if blocked)
        """
        async with self._lock:
            key = f"{office_id}:{workflow_id}"
            depth = self._workflow_depth[key]
            
            if depth >= self.MAX_WORKFLOW_RECURSION:
                return False, f"Workflow recursion limit ({self.MAX_WORKFLOW_RECURSION}) exceeded"
            
            return True, None
    
    async def increment_workflow_depth(self, office_id: str, workflow_id: str):
        """Increment workflow depth counter."""
        async with self._lock:
            key = f"{office_id}:{workflow_id}"
            self._workflow_depth[key] += 1
    
    async def reset_workflow_depth(self, office_id: str, workflow_id: str):
        """Reset workflow depth counter."""
        async with self._lock:
            key = f"{office_id}:{workflow_id}"
            self._workflow_depth[key] = 0


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failures detected, blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerStats:
    """Statistics for a circuit breaker."""
    failures: int = 0
    successes: int = 0
    last_failure_time: Optional[float] = None
    state: CircuitBreakerState = CircuitBreakerState.CLOSED


class CircuitBreaker:
    """
    Circuit breaker pattern for provider calls.
    
    Prevents cascading failures when a provider is down.
    """
    
    # Number of failures before opening circuit
    FAILURE_THRESHOLD = 5
    
    # Time to wait before attempting recovery
    RECOVERY_TIMEOUT_SECONDS = 60
    
    # Number of successes needed to close circuit
    SUCCESS_THRESHOLD = 3
    
    def __init__(self):
        self._circuits: dict[str, CircuitBreakerStats] = defaultdict(CircuitBreakerStats)
        self._lock = asyncio.Lock()
    
    async def can_execute(self, provider: str) -> tuple[bool, Optional[str]]:
        """
        Check if calls to this provider are allowed.
        
        Returns:
            Tuple of (allowed, reason if blocked)
        """
        async with self._lock:
            stats = self._circuits[provider]
            
            if stats.state == CircuitBreakerState.CLOSED:
                return True, None
            
            if stats.state == CircuitBreakerState.OPEN:
                # Check if recovery timeout has passed
                if stats.last_failure_time:
                    elapsed = time.time() - stats.last_failure_time
                    if elapsed >= self.RECOVERY_TIMEOUT_SECONDS:
                        stats.state = CircuitBreakerState.HALF_OPEN
                        logger.info(f"Circuit breaker for {provider} entering half-open state")
                        return True, None
                
                return False, f"Circuit breaker open for {provider}"
            
            # HALF_OPEN - allow requests to test recovery
            return True, None
    
    async def record_success(self, provider: str):
        """Record a successful call."""
        async with self._lock:
            stats = self._circuits[provider]
            stats.successes += 1
            
            if stats.state == CircuitBreakerState.HALF_OPEN:
                if stats.successes >= self.SUCCESS_THRESHOLD:
                    stats.state = CircuitBreakerState.CLOSED
                    stats.failures = 0
                    stats.successes = 0
                    logger.info(f"Circuit breaker for {provider} closed (recovered)")
    
    async def record_failure(self, provider: str):
        """Record a failed call."""
        async with self._lock:
            stats = self._circuits[provider]
            stats.failures += 1
            stats.last_failure_time = time.time()
            
            if stats.state == CircuitBreakerState.HALF_OPEN:
                # Failure during recovery - reopen circuit
                stats.state = CircuitBreakerState.OPEN
                stats.successes = 0
                logger.warning(f"Circuit breaker for {provider} reopened after failure during recovery")
            elif stats.failures >= self.FAILURE_THRESHOLD:
                stats.state = CircuitBreakerState.OPEN
                logger.warning(f"Circuit breaker for {provider} opened after {stats.failures} failures")
    
    async def reset(self, provider: str):
        """Reset circuit breaker for a provider."""
        async with self._lock:
            self._circuits[provider] = CircuitBreakerStats()


# Singleton instances
_rate_limiter: Optional[CreditRateLimiter] = None
_anomaly_detector: Optional[AnomalyDetector] = None
_circuit_breaker: Optional[CircuitBreaker] = None


def get_rate_limiter() -> CreditRateLimiter:
    """Get singleton rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = CreditRateLimiter()
    return _rate_limiter


def get_anomaly_detector() -> AnomalyDetector:
    """Get singleton anomaly detector instance."""
    global _anomaly_detector
    if _anomaly_detector is None:
        _anomaly_detector = AnomalyDetector()
    return _anomaly_detector


def get_circuit_breaker() -> CircuitBreaker:
    """Get singleton circuit breaker instance."""
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreaker()
    return _circuit_breaker
