"""Tests for Quota Manager."""

import pytest
from tool_execution import (
    QuotaManager,
    ToolVendor,
    QuotaConfig,
)


@pytest.fixture
def quota_manager():
    """Create a fresh quota manager for each test."""
    return QuotaManager()


class TestQuotaManager:
    """Test cases for QuotaManager."""
    
    def test_check_quota_allowed(self, quota_manager):
        """Test quota check when within limits."""
        result = quota_manager.check_quota(
            tool="google_sheets_read",
            vendor=ToolVendor.GOOGLE,
            user_id="user123",
        )
        
        assert result.allowed
        assert result.current_usage == 0
    
    def test_check_quota_after_usage(self, quota_manager):
        """Test quota check after recording usage."""
        # Record some usage
        for _ in range(5):
            quota_manager.record_usage(
                tool="google_sheets_read",
                vendor=ToolVendor.GOOGLE,
                user_id="user123",
            )
        
        result = quota_manager.check_quota(
            tool="google_sheets_read",
            vendor=ToolVendor.GOOGLE,
            user_id="user123",
        )
        
        assert result.allowed
        assert result.current_usage == 5
    
    def test_check_quota_exceeded(self, quota_manager):
        """Test quota check when limit exceeded."""
        # Set a very low limit
        quota_manager.set_quota(
            ToolVendor.GOOGLE,
            QuotaConfig(
                vendor=ToolVendor.GOOGLE,
                requests_per_minute=5,
                requests_per_hour=10,
                requests_per_day=20,
            ),
        )
        
        # Record up to the limit
        for _ in range(5):
            quota_manager.record_usage(
                tool="google_sheets_read",
                vendor=ToolVendor.GOOGLE,
                user_id="user123",
            )
        
        result = quota_manager.check_quota(
            tool="google_sheets_read",
            vendor=ToolVendor.GOOGLE,
            user_id="user123",
        )
        
        assert not result.allowed
        assert "Rate limit exceeded" in result.reason
    
    def test_get_remaining_quota(self, quota_manager):
        """Test getting remaining quota."""
        # Record some usage
        for _ in range(3):
            quota_manager.record_usage(
                tool="google_sheets_read",
                vendor=ToolVendor.GOOGLE,
                user_id="user123",
            )
        
        status = quota_manager.get_remaining_quota(
            vendor=ToolVendor.GOOGLE,
            user_id="user123",
        )
        
        assert status.vendor == ToolVendor.GOOGLE
        assert status.user_id == "user123"
        assert status.minute_remaining == 57  # 60 - 3
    
    def test_concurrent_request_limit(self, quota_manager):
        """Test concurrent request limiting."""
        # Set low concurrent limit
        quota_manager.set_quota(
            ToolVendor.GOOGLE,
            QuotaConfig(
                vendor=ToolVendor.GOOGLE,
                concurrent_requests=2,
            ),
        )
        
        # Simulate concurrent requests
        quota_manager.increment_active("user123", ToolVendor.GOOGLE)
        quota_manager.increment_active("user123", ToolVendor.GOOGLE)
        
        result = quota_manager.check_quota(
            tool="google_sheets_read",
            vendor=ToolVendor.GOOGLE,
            user_id="user123",
        )
        
        assert not result.allowed
        assert "concurrent" in result.reason.lower()
        
        # Release one
        quota_manager.decrement_active("user123", ToolVendor.GOOGLE)
        
        result = quota_manager.check_quota(
            tool="google_sheets_read",
            vendor=ToolVendor.GOOGLE,
            user_id="user123",
        )
        
        assert result.allowed
    
    def test_reset_user_quota(self, quota_manager):
        """Test resetting user quota."""
        # Record some usage
        for _ in range(5):
            quota_manager.record_usage(
                tool="google_sheets_read",
                vendor=ToolVendor.GOOGLE,
                user_id="user123",
            )
        
        # Verify usage recorded
        status = quota_manager.get_remaining_quota(ToolVendor.GOOGLE, "user123")
        assert status.minute_remaining == 55
        
        # Reset
        quota_manager.reset_user_quota("user123", ToolVendor.GOOGLE)
        
        # Verify reset
        status = quota_manager.get_remaining_quota(ToolVendor.GOOGLE, "user123")
        assert status.minute_remaining == 60
    
    def test_get_usage_summary(self, quota_manager):
        """Test getting usage summary for all vendors."""
        quota_manager.record_usage("test", ToolVendor.GOOGLE, "user123")
        quota_manager.record_usage("test", ToolVendor.INTERNAL, "user123")
        
        summary = quota_manager.get_usage_summary("user123")
        
        assert "google" in summary
        assert "internal" in summary
    
    def test_custom_quota_config(self, quota_manager):
        """Test setting custom quota configuration."""
        custom_quota = QuotaConfig(
            vendor=ToolVendor.CUSTOM,
            requests_per_minute=10,
            requests_per_hour=100,
            requests_per_day=1000,
            concurrent_requests=3,
        )
        
        quota_manager.set_quota(ToolVendor.CUSTOM, custom_quota)
        
        retrieved = quota_manager.get_quota(ToolVendor.CUSTOM)
        
        assert retrieved.requests_per_minute == 10
        assert retrieved.requests_per_hour == 100
        assert retrieved.concurrent_requests == 3
