"""Security Gateway - Permission and access control enforcement.

The Security Gateway ensures all executions strictly comply with
user-granted permissions. Zero-trust by default.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from .types import (
    ToolDefinition,
    PermissionScope,
    PermissionResult,
    PermissionStatus,
    ToolVendor,
)

logger = logging.getLogger(__name__)


class SecurityGateway:
    """
    Zero-trust permission enforcement.
    
    Responsibilities:
    - OAuth token validation
    - Scope enforcement
    - Tool-level access control
    - User identity binding
    
    Principles:
    - Zero-trust by default
    - Least privilege
    - Explicit user consent
    - Fail fast with clear errors
    """
    
    # Mapping of vendor to permission prefix
    VENDOR_PERMISSION_PREFIX = {
        ToolVendor.GOOGLE: "google.",
        ToolVendor.MICROSOFT: "microsoft.",
        ToolVendor.AWS: "aws.",
        ToolVendor.INTERNAL: "",
        ToolVendor.CUSTOM: "custom.",
    }
    
    def __init__(self):
        self._initialized: bool = False
        # Cache for token validation results (short TTL)
        self._token_cache: Dict[str, tuple[bool, datetime]] = {}
        self._cache_ttl = timedelta(minutes=5)
    
    async def initialize(self) -> None:
        """Initialize the security gateway."""
        self._initialized = True
        logger.info("Security Gateway initialized")
    
    def check_permissions(
        self,
        tool: ToolDefinition,
        user_scopes: PermissionScope,
    ) -> PermissionResult:
        """
        Verify user has required permissions for a tool.
        
        Args:
            tool: Tool definition with required permissions
            user_scopes: User's granted permission scope
            
        Returns:
            PermissionResult with status and any missing permissions
        """
        required = set(tool.required_permissions)
        granted = set(user_scopes.granted_scopes)
        
        # Internal tools with no required permissions are always allowed
        if not required:
            return PermissionResult(
                status=PermissionStatus.GRANTED,
                allowed=True,
            )
        
        # Check for missing permissions
        missing = required - granted
        
        if missing:
            logger.warning(
                f"Permission denied for tool '{tool.tool_name}'. "
                f"Missing: {missing}"
            )
            return PermissionResult(
                status=PermissionStatus.INSUFFICIENT_SCOPE,
                allowed=False,
                missing_permissions=list(missing),
                reason=f"Missing permissions: {', '.join(missing)}",
            )
        
        # Check for valid OAuth token if vendor requires it
        if tool.vendor != ToolVendor.INTERNAL:
            token_result = self.validate_oauth_token(
                user_scopes,
                tool.vendor,
                list(required)
            )
            if not token_result.allowed:
                return token_result
        
        return PermissionResult(
            status=PermissionStatus.GRANTED,
            allowed=True,
        )
    
    def validate_oauth_token(
        self,
        user_scopes: PermissionScope,
        vendor: ToolVendor,
        required_scopes: List[str],
    ) -> PermissionResult:
        """
        Validate OAuth token for a vendor.
        
        Args:
            user_scopes: User's permission scope with tokens
            vendor: The vendor requiring authentication
            required_scopes: Scopes needed for the operation
            
        Returns:
            PermissionResult with validation status
        """
        vendor_key = vendor.value
        
        # Check if token exists
        if vendor_key not in user_scopes.oauth_tokens:
            return PermissionResult(
                status=PermissionStatus.DENIED,
                allowed=False,
                reason=f"No OAuth token for {vendor_key}",
            )
        
        token = user_scopes.oauth_tokens[vendor_key]
        
        # Check token expiry
        if vendor_key in user_scopes.token_expiry:
            expiry = user_scopes.token_expiry[vendor_key]
            if datetime.utcnow() > expiry:
                return PermissionResult(
                    status=PermissionStatus.TOKEN_EXPIRED,
                    allowed=False,
                    reason=f"OAuth token for {vendor_key} has expired",
                )
        
        # Basic token validation (non-empty)
        if not token or len(token) < 10:
            return PermissionResult(
                status=PermissionStatus.TOKEN_INVALID,
                allowed=False,
                reason=f"Invalid OAuth token for {vendor_key}",
            )
        
        return PermissionResult(
            status=PermissionStatus.GRANTED,
            allowed=True,
        )
    
    def enforce_scope(
        self,
        granted_scopes: List[str],
        required_scopes: List[str],
    ) -> bool:
        """
        Check if granted scopes satisfy required scopes.
        
        Supports wildcard matching:
        - "google.*" matches any google scope
        - "google.sheets.*" matches google.sheets.read, google.sheets.write, etc.
        
        Args:
            granted_scopes: User's granted scopes
            required_scopes: Scopes required for operation
            
        Returns:
            True if all required scopes are satisfied
        """
        for required in required_scopes:
            if not self._scope_matches(granted_scopes, required):
                return False
        return True
    
    def _scope_matches(self, granted: List[str], required: str) -> bool:
        """Check if any granted scope satisfies the required scope."""
        for scope in granted:
            # Exact match
            if scope == required:
                return True
            
            # Wildcard match (e.g., "google.*" matches "google.sheets.read")
            if scope.endswith(".*"):
                prefix = scope[:-1]  # Remove "*"
                if required.startswith(prefix):
                    return True
        
        return False
    
    def get_user_scopes_for_vendor(
        self,
        user_scopes: PermissionScope,
        vendor: ToolVendor,
    ) -> List[str]:
        """
        Get user's granted scopes for a specific vendor.
        
        Args:
            user_scopes: User's permission scope
            vendor: Vendor to filter by
            
        Returns:
            List of scopes for the vendor
        """
        prefix = self.VENDOR_PERMISSION_PREFIX.get(vendor, "")
        if not prefix:
            return user_scopes.granted_scopes
        
        return [
            scope for scope in user_scopes.granted_scopes
            if scope.startswith(prefix)
        ]
    
    def validate_execution_context(
        self,
        user_id: str,
        office_id: str,
        user_scopes: PermissionScope,
    ) -> PermissionResult:
        """
        Validate that execution context is properly bound.
        
        Ensures:
        - User ID matches scope's user
        - Office ID matches scope's office
        
        Args:
            user_id: User requesting execution
            office_id: Office context for execution
            user_scopes: User's permission scope
            
        Returns:
            PermissionResult with validation status
        """
        if user_scopes.user_id != user_id:
            logger.warning(
                f"User ID mismatch: request={user_id}, scope={user_scopes.user_id}"
            )
            return PermissionResult(
                status=PermissionStatus.DENIED,
                allowed=False,
                reason="User ID does not match permission scope",
            )
        
        if user_scopes.office_id != office_id:
            logger.warning(
                f"Office ID mismatch: request={office_id}, scope={user_scopes.office_id}"
            )
            return PermissionResult(
                status=PermissionStatus.DENIED,
                allowed=False,
                reason="Office ID does not match permission scope",
            )
        
        return PermissionResult(
            status=PermissionStatus.GRANTED,
            allowed=True,
        )
    
    def clear_token_cache(self) -> None:
        """Clear the token validation cache."""
        self._token_cache.clear()


# Singleton instance
_gateway: Optional[SecurityGateway] = None


async def get_security_gateway() -> SecurityGateway:
    """Get or create the security gateway singleton."""
    global _gateway
    if _gateway is None:
        _gateway = SecurityGateway()
        await _gateway.initialize()
    return _gateway
