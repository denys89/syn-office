"""Quota Manager - Rate limiting and cost control.

Prevents API abuse, cost explosion, and vendor throttling.
Integrates with the existing rate_limiter.py module.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from collections import defaultdict
from dataclasses import dataclass, field

from .types import (
    ToolVendor,
    QuotaConfig,
    QuotaCheckResult,
    QuotaStatus,
    UsageRecord,
)

logger = logging.getLogger(__name__)


@dataclass
class VendorUsageState:
    """Tracks usage state for a vendor per user."""
    minute_records: List[datetime] = field(default_factory=list)
    hour_records: List[datetime] = field(default_factory=list)
    day_records: List[datetime] = field(default_factory=list)
    last_request_time: Optional[datetime] = None


class QuotaManager:
    """
    API quota and rate limit management.
    
    Responsibilities:
    - Track per-user usage
    - Track per-tool usage
    - Track per-vendor quotas
    - Enforce time-window limits
    
    Strategies:
    - Hard limit enforcement
    - Soft limit warnings
    - Request batching
    - Delayed execution
    """
    
    # Default quotas per vendor
    DEFAULT_QUOTAS: Dict[ToolVendor, QuotaConfig] = {
        ToolVendor.GOOGLE: QuotaConfig(
            vendor=ToolVendor.GOOGLE,
            requests_per_minute=60,
            requests_per_hour=1000,
            requests_per_day=10000,
            concurrent_requests=10,
        ),
        ToolVendor.MICROSOFT: QuotaConfig(
            vendor=ToolVendor.MICROSOFT,
            requests_per_minute=60,
            requests_per_hour=1000,
            requests_per_day=10000,
            concurrent_requests=10,
        ),
        ToolVendor.AWS: QuotaConfig(
            vendor=ToolVendor.AWS,
            requests_per_minute=100,
            requests_per_hour=5000,
            requests_per_day=50000,
            concurrent_requests=20,
        ),
        ToolVendor.INTERNAL: QuotaConfig(
            vendor=ToolVendor.INTERNAL,
            requests_per_minute=120,
            requests_per_hour=3000,
            requests_per_day=30000,
            concurrent_requests=50,
        ),
        ToolVendor.CUSTOM: QuotaConfig(
            vendor=ToolVendor.CUSTOM,
            requests_per_minute=30,
            requests_per_hour=500,
            requests_per_day=5000,
            concurrent_requests=5,
        ),
    }
    
    def __init__(self):
        self._initialized: bool = False
        # User -> Vendor -> UsageState
        self._usage: Dict[str, Dict[ToolVendor, VendorUsageState]] = defaultdict(
            lambda: defaultdict(VendorUsageState)
        )
        # Custom quotas (override defaults)
        self._custom_quotas: Dict[ToolVendor, QuotaConfig] = {}
        # Active request counts for concurrency limiting
        self._active_requests: Dict[str, Dict[ToolVendor, int]] = defaultdict(
            lambda: defaultdict(int)
        )
    
    async def initialize(self) -> None:
        """Initialize the quota manager."""
        self._initialized = True
        logger.info("Quota Manager initialized")
    
    def set_quota(self, vendor: ToolVendor, config: QuotaConfig) -> None:
        """Set custom quota for a vendor."""
        self._custom_quotas[vendor] = config
        logger.info(f"Set custom quota for {vendor}: {config}")
    
    def get_quota(self, vendor: ToolVendor) -> QuotaConfig:
        """Get quota config for a vendor."""
        return self._custom_quotas.get(vendor, self.DEFAULT_QUOTAS.get(
            vendor,
            QuotaConfig(vendor=vendor)  # Fallback to defaults
        ))
    
    def check_quota(
        self,
        tool: str,
        vendor: ToolVendor,
        user_id: str,
    ) -> QuotaCheckResult:
        """
        Check if user can make a request to a vendor.
        
        Args:
            tool: Tool name being used
            vendor: Vendor/provider
            user_id: User making the request
            
        Returns:
            QuotaCheckResult with allowed status and details
        """
        quota = self.get_quota(vendor)
        state = self._usage[user_id][vendor]
        now = datetime.utcnow()
        
        # Cleanup old records
        self._cleanup_records(state, now)
        
        # Check minute limit
        minute_count = len(state.minute_records)
        if minute_count >= quota.requests_per_minute:
            cooldown = 60 - (now - state.minute_records[0]).seconds
            return QuotaCheckResult(
                allowed=False,
                reason=f"Rate limit exceeded: {minute_count}/{quota.requests_per_minute} requests per minute",
                current_usage=minute_count,
                limit=quota.requests_per_minute,
                cooldown_seconds=max(0, cooldown),
            )
        
        # Check hour limit
        hour_count = len(state.hour_records)
        if hour_count >= quota.requests_per_hour:
            cooldown = 3600 - (now - state.hour_records[0]).seconds
            return QuotaCheckResult(
                allowed=False,
                reason=f"Hourly limit exceeded: {hour_count}/{quota.requests_per_hour} requests per hour",
                current_usage=hour_count,
                limit=quota.requests_per_hour,
                cooldown_seconds=max(0, cooldown),
            )
        
        # Check day limit
        day_count = len(state.day_records)
        if day_count >= quota.requests_per_day:
            # Reset at midnight UTC
            tomorrow = (now + timedelta(days=1)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            cooldown = int((tomorrow - now).total_seconds())
            return QuotaCheckResult(
                allowed=False,
                reason=f"Daily limit exceeded: {day_count}/{quota.requests_per_day} requests per day",
                current_usage=day_count,
                limit=quota.requests_per_day,
                cooldown_seconds=cooldown,
            )
        
        # Check concurrent requests
        active = self._active_requests[user_id][vendor]
        if active >= quota.concurrent_requests:
            return QuotaCheckResult(
                allowed=False,
                reason=f"Too many concurrent requests: {active}/{quota.concurrent_requests}",
                current_usage=active,
                limit=quota.concurrent_requests,
                cooldown_seconds=1,  # Short cooldown for concurrency
            )
        
        return QuotaCheckResult(
            allowed=True,
            current_usage=minute_count,
            limit=quota.requests_per_minute,
        )
    
    def record_usage(
        self,
        tool: str,
        vendor: ToolVendor,
        user_id: str,
    ) -> None:
        """
        Record a completed API request.
        
        Args:
            tool: Tool that was used
            vendor: Vendor/provider
            user_id: User who made the request
        """
        state = self._usage[user_id][vendor]
        now = datetime.utcnow()
        
        state.minute_records.append(now)
        state.hour_records.append(now)
        state.day_records.append(now)
        state.last_request_time = now
        
        logger.debug(f"Recorded usage: user={user_id}, vendor={vendor}, tool={tool}")
    
    def increment_active(self, user_id: str, vendor: ToolVendor) -> None:
        """Increment active request count."""
        self._active_requests[user_id][vendor] += 1
    
    def decrement_active(self, user_id: str, vendor: ToolVendor) -> None:
        """Decrement active request count."""
        if self._active_requests[user_id][vendor] > 0:
            self._active_requests[user_id][vendor] -= 1
    
    def get_remaining_quota(
        self,
        vendor: ToolVendor,
        user_id: str,
    ) -> QuotaStatus:
        """
        Get current quota status for a user.
        
        Args:
            vendor: Vendor to check
            user_id: User to check
            
        Returns:
            QuotaStatus with remaining quotas
        """
        quota = self.get_quota(vendor)
        state = self._usage[user_id][vendor]
        now = datetime.utcnow()
        
        # Cleanup old records
        self._cleanup_records(state, now)
        
        minute_remaining = quota.requests_per_minute - len(state.minute_records)
        hour_remaining = quota.requests_per_hour - len(state.hour_records)
        day_remaining = quota.requests_per_day - len(state.day_records)
        
        # Calculate percentage used (based on day limit as primary)
        percentage_used = (len(state.day_records) / quota.requests_per_day) * 100
        
        return QuotaStatus(
            vendor=vendor,
            user_id=user_id,
            minute_remaining=max(0, minute_remaining),
            hour_remaining=max(0, hour_remaining),
            day_remaining=max(0, day_remaining),
            percentage_used=min(100.0, percentage_used),
        )
    
    def get_usage_summary(self, user_id: str) -> Dict[str, QuotaStatus]:
        """Get usage summary for all vendors."""
        summary = {}
        for vendor in ToolVendor:
            summary[vendor.value] = self.get_remaining_quota(vendor, user_id)
        return summary
    
    def _cleanup_records(self, state: VendorUsageState, now: datetime) -> None:
        """Remove expired records from usage state."""
        minute_ago = now - timedelta(minutes=1)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)
        
        state.minute_records = [
            t for t in state.minute_records if t > minute_ago
        ]
        state.hour_records = [
            t for t in state.hour_records if t > hour_ago
        ]
        state.day_records = [
            t for t in state.day_records if t > day_ago
        ]
    
    def reset_user_quota(self, user_id: str, vendor: Optional[ToolVendor] = None) -> None:
        """
        Reset quota for a user.
        
        Args:
            user_id: User to reset
            vendor: Specific vendor to reset, or None for all
        """
        if vendor:
            self._usage[user_id][vendor] = VendorUsageState()
            self._active_requests[user_id][vendor] = 0
        else:
            self._usage[user_id] = defaultdict(VendorUsageState)
            self._active_requests[user_id] = defaultdict(int)
        
        logger.info(f"Reset quota for user {user_id}, vendor={vendor or 'all'}")


# Singleton instance
_manager: Optional[QuotaManager] = None


async def get_quota_manager() -> QuotaManager:
    """Get or create the quota manager singleton."""
    global _manager
    if _manager is None:
        _manager = QuotaManager()
        await _manager.initialize()
    return _manager
