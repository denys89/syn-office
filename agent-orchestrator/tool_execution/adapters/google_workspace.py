"""Google Workspace Adapter - Integration with Google Sheets, Slides, and Drive APIs.

This adapter translates generic tool actions into Google Workspace API calls.
"""

import logging
import time
from typing import Optional, Dict, Any, List

from .base import BaseToolAdapter
from ..types import (
    ActionStep, AdapterResult, ExecutionContext, ToolVendor, Artifact
)

logger = logging.getLogger(__name__)

# Google API imports - optional to allow running without credentials
try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False
    logger.warning("Google API libraries not installed. Install with: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib")


class GoogleWorkspaceAdapter(BaseToolAdapter):
    """
    Adapter for Google Workspace APIs.
    
    Supports:
    - Google Sheets: Create, read, update, append
    - Google Slides: Create presentations, add slides
    - Google Drive: List, share files
    
    Authentication:
    - Uses OAuth2 credentials from the execution context
    - Tokens should be pre-obtained and passed in context.permissions.oauth_tokens
    """
    
    # Tool name -> (service_name, service_version)
    TOOL_SERVICE_MAP = {
        "google_sheets_create": ("sheets", "v4"),
        "google_sheets_read": ("sheets", "v4"),
        "google_sheets_append_row": ("sheets", "v4"),
        "google_sheets_update": ("sheets", "v4"),
        "google_slides_create": ("slides", "v1"),
        "google_slides_add_slide": ("slides", "v1"),
        "google_drive_share": ("drive", "v3"),
        "google_drive_list": ("drive", "v3"),
    }
    
    def __init__(self):
        super().__init__()
        self.name = "google_workspace"
        self.vendor = ToolVendor.GOOGLE
        self._services: Dict[str, Any] = {}
    
    async def initialize(self) -> None:
        """Initialize the adapter."""
        if not GOOGLE_API_AVAILABLE:
            logger.warning("Google API not available - adapter will run in mock mode")
            self._available = False
        else:
            self._available = True
        
        self._initialized = True
        logger.info(f"Google Workspace adapter initialized (available: {self._available})")
    
    async def execute(
        self,
        action: ActionStep,
        context: ExecutionContext,
    ) -> AdapterResult:
        """Execute a Google Workspace tool action."""
        start_time = time.time()
        
        tool_name = action.tool
        inputs = action.inputs
        
        # Get credentials from context
        credentials = self._get_credentials(context)
        
        if not GOOGLE_API_AVAILABLE:
            # Mock mode for development/testing
            return await self._mock_execute(action, context)
        
        if not credentials:
            return AdapterResult(
                success=False,
                error="No Google OAuth credentials provided",
                error_code="NO_CREDENTIALS",
                latency_ms=int((time.time() - start_time) * 1000)
            )
        
        try:
            # Route to appropriate handler
            if tool_name == "google_sheets_create":
                result = await self._sheets_create(credentials, inputs)
            elif tool_name == "google_sheets_read":
                result = await self._sheets_read(credentials, inputs)
            elif tool_name == "google_sheets_append_row":
                result = await self._sheets_append(credentials, inputs)
            elif tool_name == "google_sheets_update":
                result = await self._sheets_update(credentials, inputs)
            elif tool_name == "google_slides_create":
                result = await self._slides_create(credentials, inputs)
            elif tool_name == "google_slides_add_slide":
                result = await self._slides_add_slide(credentials, inputs)
            elif tool_name == "google_drive_share":
                result = await self._drive_share(credentials, inputs)
            elif tool_name == "google_drive_list":
                result = await self._drive_list(credentials, inputs)
            else:
                return AdapterResult(
                    success=False,
                    error=f"Unknown tool: {tool_name}",
                    error_code="UNKNOWN_TOOL",
                    latency_ms=int((time.time() - start_time) * 1000)
                )
            
            result.latency_ms = int((time.time() - start_time) * 1000)
            return result
            
        except HttpError as e:
            logger.error(f"Google API error: {e}")
            return AdapterResult(
                success=False,
                error=f"Google API error: {e.reason}",
                error_code=f"GOOGLE_API_{e.resp.status}",
                latency_ms=int((time.time() - start_time) * 1000),
                raw_response=e.content.decode() if e.content else None
            )
        except Exception as e:
            logger.exception(f"Unexpected error in Google adapter: {e}")
            return AdapterResult(
                success=False,
                error=str(e),
                error_code="INTERNAL_ERROR",
                latency_ms=int((time.time() - start_time) * 1000)
            )
    
    async def health_check(self) -> bool:
        """Check if Google APIs are accessible."""
        if not GOOGLE_API_AVAILABLE:
            return False
        # Basic check - could be extended to ping API
        return True
    
    def supports_tool(self, tool_name: str) -> bool:
        """Check if this adapter supports a tool."""
        return tool_name in self.TOOL_SERVICE_MAP
    
    def _get_credentials(self, context: ExecutionContext) -> Optional[Any]:
        """Extract Google credentials from execution context."""
        if not GOOGLE_API_AVAILABLE:
            return None
        
        token = context.permissions.oauth_tokens.get("google")
        if not token:
            return None
        
        # Create credentials from token
        try:
            credentials = Credentials(token=token)
            return credentials
        except Exception as e:
            logger.error(f"Failed to create credentials: {e}")
            return None
    
    def _get_service(self, credentials: Any, service_name: str, version: str) -> Any:
        """Get or create a Google API service."""
        key = f"{service_name}:{version}"
        if key not in self._services:
            self._services[key] = build(service_name, version, credentials=credentials)
        return self._services[key]
    
    # =========================================================================
    # Google Sheets Operations
    # =========================================================================
    
    async def _sheets_create(self, credentials: Any, inputs: Dict) -> AdapterResult:
        """Create a new Google Spreadsheet."""
        service = self._get_service(credentials, "sheets", "v4")
        
        spreadsheet_body = {
            "properties": {
                "title": inputs.get("title", "Untitled Spreadsheet")
            }
        }
        
        # Add sheets if specified
        sheets = inputs.get("sheets", [])
        if sheets:
            spreadsheet_body["sheets"] = [
                {"properties": {"title": name}} for name in sheets
            ]
        
        result = service.spreadsheets().create(body=spreadsheet_body).execute()
        
        spreadsheet_id = result.get("spreadsheetId")
        spreadsheet_url = result.get("spreadsheetUrl")
        
        return AdapterResult(
            success=True,
            data={
                "spreadsheet_id": spreadsheet_id,
                "spreadsheet_url": spreadsheet_url,
            },
            artifacts=[Artifact(
                type="spreadsheet",
                url=spreadsheet_url,
                metadata={"id": spreadsheet_id, "title": inputs.get("title")}
            )]
        )
    
    async def _sheets_read(self, credentials: Any, inputs: Dict) -> AdapterResult:
        """Read data from a Google Spreadsheet."""
        service = self._get_service(credentials, "sheets", "v4")
        
        spreadsheet_id = inputs["spreadsheet_id"]
        range_notation = inputs["range"]
        
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_notation
        ).execute()
        
        values = result.get("values", [])
        actual_range = result.get("range", range_notation)
        
        return AdapterResult(
            success=True,
            data={
                "values": values,
                "range": actual_range,
                "row_count": len(values),
            }
        )
    
    async def _sheets_append(self, credentials: Any, inputs: Dict) -> AdapterResult:
        """Append a row to a Google Spreadsheet."""
        service = self._get_service(credentials, "sheets", "v4")
        
        spreadsheet_id = inputs["spreadsheet_id"]
        sheet = inputs.get("sheet", "Sheet1")
        values = inputs["values"]
        
        body = {"values": [values]}
        
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet}!A:A",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()
        
        updates = result.get("updates", {})
        
        return AdapterResult(
            success=True,
            data={
                "updated_range": updates.get("updatedRange"),
                "updated_rows": updates.get("updatedRows", 1),
            }
        )
    
    async def _sheets_update(self, credentials: Any, inputs: Dict) -> AdapterResult:
        """Update cells in a Google Spreadsheet."""
        service = self._get_service(credentials, "sheets", "v4")
        
        spreadsheet_id = inputs["spreadsheet_id"]
        range_notation = inputs["range"]
        values = inputs["values"]
        
        body = {"values": values}
        
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_notation,
            valueInputOption="USER_ENTERED",
            body=body
        ).execute()
        
        return AdapterResult(
            success=True,
            data={
                "updated_range": result.get("updatedRange"),
                "updated_cells": result.get("updatedCells"),
            }
        )
    
    # =========================================================================
    # Google Slides Operations
    # =========================================================================
    
    async def _slides_create(self, credentials: Any, inputs: Dict) -> AdapterResult:
        """Create a new Google Slides presentation."""
        service = self._get_service(credentials, "slides", "v1")
        
        presentation_body = {
            "title": inputs.get("title", "Untitled Presentation")
        }
        
        result = service.presentations().create(body=presentation_body).execute()
        
        presentation_id = result.get("presentationId")
        # Construct URL (Slides API doesn't return it directly)
        presentation_url = f"https://docs.google.com/presentation/d/{presentation_id}/edit"
        
        return AdapterResult(
            success=True,
            data={
                "presentation_id": presentation_id,
                "presentation_url": presentation_url,
            },
            artifacts=[Artifact(
                type="presentation",
                url=presentation_url,
                metadata={"id": presentation_id, "title": inputs.get("title")}
            )]
        )
    
    async def _slides_add_slide(self, credentials: Any, inputs: Dict) -> AdapterResult:
        """Add a slide to a Google Slides presentation."""
        service = self._get_service(credentials, "slides", "v1")
        
        presentation_id = inputs["presentation_id"]
        layout = inputs.get("layout", "BLANK")
        
        # Create slide request
        requests = [
            {
                "createSlide": {
                    "slideLayoutReference": {
                        "predefinedLayout": layout
                    }
                }
            }
        ]
        
        # Add title/body if provided
        result = service.presentations().batchUpdate(
            presentationId=presentation_id,
            body={"requests": requests}
        ).execute()
        
        slide_id = result.get("replies", [{}])[0].get("createSlide", {}).get("objectId")
        
        # Add text if title/body provided
        if inputs.get("title") or inputs.get("body"):
            await self._add_slide_text(
                service, presentation_id, slide_id,
                inputs.get("title"), inputs.get("body")
            )
        
        return AdapterResult(
            success=True,
            data={
                "slide_id": slide_id,
                "presentation_id": presentation_id,
            }
        )
    
    async def _add_slide_text(
        self,
        service: Any,
        presentation_id: str,
        slide_id: str,
        title: Optional[str],
        body: Optional[str]
    ) -> None:
        """Add text to a slide (helper method)."""
        requests = []
        
        if title:
            # Add title text box
            requests.append({
                "createShape": {
                    "objectId": f"{slide_id}_title",
                    "shapeType": "TEXT_BOX",
                    "elementProperties": {
                        "pageObjectId": slide_id,
                        "size": {"width": {"magnitude": 600, "unit": "PT"},
                                 "height": {"magnitude": 50, "unit": "PT"}},
                        "transform": {"scaleX": 1, "scaleY": 1, "translateX": 50,
                                      "translateY": 50, "unit": "PT"}
                    }
                }
            })
            requests.append({
                "insertText": {
                    "objectId": f"{slide_id}_title",
                    "text": title
                }
            })
        
        if requests:
            service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={"requests": requests}
            ).execute()
    
    # =========================================================================
    # Google Drive Operations
    # =========================================================================
    
    async def _drive_share(self, credentials: Any, inputs: Dict) -> AdapterResult:
        """Share a Google Drive file."""
        service = self._get_service(credentials, "drive", "v3")
        
        file_id = inputs["file_id"]
        email = inputs["email"]
        role = inputs.get("role", "reader")
        
        permission = {
            "type": "user",
            "role": role,
            "emailAddress": email
        }
        
        result = service.permissions().create(
            fileId=file_id,
            body=permission,
            sendNotificationEmail=True
        ).execute()
        
        return AdapterResult(
            success=True,
            data={
                "permission_id": result.get("id"),
                "shared_with": email,
                "role": role,
            }
        )
    
    async def _drive_list(self, credentials: Any, inputs: Dict) -> AdapterResult:
        """List files in Google Drive."""
        service = self._get_service(credentials, "drive", "v3")
        
        query = inputs.get("query", "")
        page_size = inputs.get("page_size", 10)
        
        results = service.files().list(
            q=query if query else None,
            pageSize=page_size,
            fields="files(id, name, mimeType, modifiedTime, webViewLink)"
        ).execute()
        
        files = results.get("files", [])
        
        return AdapterResult(
            success=True,
            data={
                "files": files,
                "count": len(files),
            }
        )
    
    # =========================================================================
    # Mock Mode (for development/testing without credentials)
    # =========================================================================
    
    async def _mock_execute(
        self,
        action: ActionStep,
        context: ExecutionContext,
    ) -> AdapterResult:
        """Mock execution for testing without Google credentials."""
        tool_name = action.tool
        inputs = action.inputs
        
        logger.info(f"[MOCK] Executing {tool_name} with inputs: {inputs}")
        
        mock_responses = {
            "google_sheets_create": {
                "data": {
                    "spreadsheet_id": "mock_spreadsheet_id_12345",
                    "spreadsheet_url": "https://docs.google.com/spreadsheets/d/mock_id/edit"
                },
                "artifacts": [Artifact(
                    type="spreadsheet",
                    url="https://docs.google.com/spreadsheets/d/mock_id/edit",
                    metadata={"id": "mock_id", "title": inputs.get("title", "Mock Sheet")}
                )]
            },
            "google_sheets_read": {
                "data": {
                    "values": [["Header1", "Header2"], ["Data1", "Data2"]],
                    "range": inputs.get("range", "Sheet1!A1:B2"),
                    "row_count": 2
                }
            },
            "google_sheets_append_row": {
                "data": {
                    "updated_range": "Sheet1!A10:Z10",
                    "updated_rows": 1
                }
            },
            "google_slides_create": {
                "data": {
                    "presentation_id": "mock_presentation_id_12345",
                    "presentation_url": "https://docs.google.com/presentation/d/mock_id/edit"
                },
                "artifacts": [Artifact(
                    type="presentation",
                    url="https://docs.google.com/presentation/d/mock_id/edit",
                    metadata={"id": "mock_id", "title": inputs.get("title", "Mock Presentation")}
                )]
            },
            "google_drive_list": {
                "data": {
                    "files": [
                        {"id": "file1", "name": "Document.docx", "mimeType": "application/vnd.google-apps.document"},
                        {"id": "file2", "name": "Spreadsheet.xlsx", "mimeType": "application/vnd.google-apps.spreadsheet"}
                    ],
                    "count": 2
                }
            }
        }
        
        response = mock_responses.get(tool_name, {"data": {"mock": True}})
        
        return AdapterResult(
            success=True,
            data=response.get("data"),
            artifacts=response.get("artifacts", []),
            latency_ms=50  # Simulated latency
        )
