"""Tests for Security Gateway."""

import pytest
from datetime import datetime, timedelta
from tool_execution import (
    SecurityGateway,
    ToolDefinition,
    ToolCategory,
    ToolVendor,
    PermissionScope,
    PermissionStatus,
)


@pytest.fixture
def gateway():
    """Create a fresh security gateway for each test."""
    return SecurityGateway()


@pytest.fixture
def sample_tool():
    """Create a sample tool definition."""
    return ToolDefinition(
        tool_name="google_sheets_read",
        description="Read from Google Sheets",
        category=ToolCategory.DATA,
        vendor=ToolVendor.GOOGLE,
        required_permissions=["google.sheets.read"],
    )


@pytest.fixture
def sample_permissions():
    """Create sample user permissions."""
    return PermissionScope(
        user_id="user123",
        office_id="office456",
        granted_scopes=["google.sheets.read", "google.sheets.write"],
        oauth_tokens={"google": "valid_token_12345678901234567890"},
        token_expiry={"google": datetime.utcnow() + timedelta(hours=1)},
    )


class TestSecurityGateway:
    """Test cases for SecurityGateway."""
    
    def test_check_permissions_granted(self, gateway, sample_tool, sample_permissions):
        """Test permission check when user has required permissions."""
        result = gateway.check_permissions(sample_tool, sample_permissions)
        
        assert result.allowed
        assert result.status == PermissionStatus.GRANTED
    
    def test_check_permissions_denied(self, gateway, sample_permissions):
        """Test permission check when user lacks permissions."""
        tool = ToolDefinition(
            tool_name="gmail_send",
            description="Send email",
            category=ToolCategory.COMMUNICATION,
            vendor=ToolVendor.GOOGLE,
            required_permissions=["google.gmail.send"],
        )
        
        result = gateway.check_permissions(tool, sample_permissions)
        
        assert not result.allowed
        assert result.status == PermissionStatus.INSUFFICIENT_SCOPE
        assert "google.gmail.send" in result.missing_permissions
    
    def test_check_permissions_internal_tool_always_allowed(self, gateway):
        """Test that internal tools with no permissions are always allowed."""
        tool = ToolDefinition(
            tool_name="data_transform",
            description="Transform data",
            category=ToolCategory.DATA,
            vendor=ToolVendor.INTERNAL,
            required_permissions=[],
        )
        
        permissions = PermissionScope(
            user_id="user123",
            office_id="office456",
            granted_scopes=[],
        )
        
        result = gateway.check_permissions(tool, permissions)
        
        assert result.allowed
        assert result.status == PermissionStatus.GRANTED
    
    def test_validate_oauth_token_valid(self, gateway, sample_permissions):
        """Test OAuth token validation with valid token."""
        result = gateway.validate_oauth_token(
            sample_permissions,
            ToolVendor.GOOGLE,
            ["google.sheets.read"],
        )
        
        assert result.allowed
        assert result.status == PermissionStatus.GRANTED
    
    def test_validate_oauth_token_missing(self, gateway):
        """Test OAuth token validation with missing token."""
        permissions = PermissionScope(
            user_id="user123",
            office_id="office456",
            granted_scopes=["google.sheets.read"],
            oauth_tokens={},
        )
        
        result = gateway.validate_oauth_token(
            permissions,
            ToolVendor.GOOGLE,
            ["google.sheets.read"],
        )
        
        assert not result.allowed
        assert result.status == PermissionStatus.DENIED
    
    def test_validate_oauth_token_expired(self, gateway):
        """Test OAuth token validation with expired token."""
        permissions = PermissionScope(
            user_id="user123",
            office_id="office456",
            granted_scopes=["google.sheets.read"],
            oauth_tokens={"google": "valid_token_12345678901234567890"},
            token_expiry={"google": datetime.utcnow() - timedelta(hours=1)},
        )
        
        result = gateway.validate_oauth_token(
            permissions,
            ToolVendor.GOOGLE,
            ["google.sheets.read"],
        )
        
        assert not result.allowed
        assert result.status == PermissionStatus.TOKEN_EXPIRED
    
    def test_enforce_scope_exact_match(self, gateway):
        """Test scope enforcement with exact match."""
        granted = ["google.sheets.read", "google.sheets.write"]
        required = ["google.sheets.read"]
        
        result = gateway.enforce_scope(granted, required)
        
        assert result is True
    
    def test_enforce_scope_wildcard_match(self, gateway):
        """Test scope enforcement with wildcard."""
        granted = ["google.*"]
        required = ["google.sheets.read", "google.drive.write"]
        
        result = gateway.enforce_scope(granted, required)
        
        assert result is True
    
    def test_enforce_scope_no_match(self, gateway):
        """Test scope enforcement when scope not granted."""
        granted = ["google.sheets.read"]
        required = ["google.gmail.send"]
        
        result = gateway.enforce_scope(granted, required)
        
        assert result is False
    
    def test_validate_execution_context_success(self, gateway, sample_permissions):
        """Test execution context validation success."""
        result = gateway.validate_execution_context(
            user_id="user123",
            office_id="office456",
            user_scopes=sample_permissions,
        )
        
        assert result.allowed
        assert result.status == PermissionStatus.GRANTED
    
    def test_validate_execution_context_user_mismatch(self, gateway, sample_permissions):
        """Test execution context validation with user mismatch."""
        result = gateway.validate_execution_context(
            user_id="wrong_user",
            office_id="office456",
            user_scopes=sample_permissions,
        )
        
        assert not result.allowed
        assert result.status == PermissionStatus.DENIED
    
    def test_validate_execution_context_office_mismatch(self, gateway, sample_permissions):
        """Test execution context validation with office mismatch."""
        result = gateway.validate_execution_context(
            user_id="user123",
            office_id="wrong_office",
            user_scopes=sample_permissions,
        )
        
        assert not result.allowed
        assert result.status == PermissionStatus.DENIED
