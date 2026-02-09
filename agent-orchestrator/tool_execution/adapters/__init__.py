"""Tool Adapters - Vendor-specific API implementations.

This package contains adapters that translate generic tool actions
into vendor-specific API calls.
"""

from .base import BaseToolAdapter
from .google_workspace import GoogleWorkspaceAdapter
from .internal import InternalToolAdapter

__all__ = [
    "BaseToolAdapter",
    "GoogleWorkspaceAdapter",
    "InternalToolAdapter",
]
