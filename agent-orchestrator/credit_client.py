"""
Credit Client for interacting with the Backend Credit API.

This module provides credit balance checking and consumption functionality
for the agent orchestrator.
"""

import logging
from typing import Optional, Tuple
from dataclasses import dataclass
import httpx

from config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class CreditCheckResult:
    """Result of a credit balance check."""
    has_sufficient: bool
    current_balance: int
    required_credits: int
    error: Optional[str] = None


@dataclass
class CreditConsumeResult:
    """Result of credit consumption."""
    success: bool
    new_balance: int
    credits_consumed: int
    transaction_id: Optional[str] = None
    error: Optional[str] = None


class CreditClient:
    """
    Client for interacting with the Backend Credit API.
    
    Provides methods to:
    - Check if office has sufficient credits
    - Consume credits for task execution
    - Get current balance
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = f"{self.settings.backend_url}/api/v1"
        self._client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _internal_headers(self) -> dict:
        """Get headers for internal API calls."""
        return {
            "X-Internal-API-Key": self.settings.internal_api_key,
            "Content-Type": "application/json",
        }
    
    async def check_balance(self, office_id: str, required_credits: int) -> CreditCheckResult:
        """
        Check if an office has sufficient credits for a task.
        
        Args:
            office_id: The office ID to check
            required_credits: Number of credits required
            
        Returns:
            CreditCheckResult with balance info
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/internal/credits/check",
                json={
                    "office_id": office_id,
                    "required_credits": required_credits,
                },
                headers=self._internal_headers(),
            )
            
            if response.status_code == 200:
                data = response.json()
                return CreditCheckResult(
                    has_sufficient=data.get("has_sufficient", False),
                    current_balance=data.get("current_balance", 0),
                    required_credits=required_credits,
                )
            else:
                logger.warning(f"Credit check failed: {response.status_code} - {response.text}")
                return CreditCheckResult(
                    has_sufficient=False,
                    current_balance=0,
                    required_credits=required_credits,
                    error=f"API error: {response.status_code}",
                )
                
        except Exception as e:
            logger.error(f"Credit check error: {e}")
            return CreditCheckResult(
                has_sufficient=True,  # Fail open to not block on errors
                current_balance=0,
                required_credits=required_credits,
                error=str(e),
            )
    
    async def consume_credits(
        self,
        office_id: str,
        task_id: str,
        credits: int,
        model_name: str,
    ) -> CreditConsumeResult:
        """
        Consume credits for a completed task.
        
        Args:
            office_id: The office ID
            task_id: The task ID (for reference)
            credits: Number of credits to consume
            model_name: Model used (for description)
            
        Returns:
            CreditConsumeResult with transaction info
        """
        try:
            client = await self._get_client()
            response = await client.post(
                f"{self.base_url}/internal/credits/consume",
                json={
                    "office_id": office_id,
                    "task_id": task_id,
                    "credits": credits,
                    "description": f"Task execution using {model_name}",
                },
                headers=self._internal_headers(),
            )
            
            if response.status_code == 200:
                data = response.json()
                return CreditConsumeResult(
                    success=True,
                    new_balance=data.get("new_balance", 0),
                    credits_consumed=credits,
                    transaction_id=data.get("transaction_id"),
                )
            else:
                logger.warning(f"Credit consume failed: {response.status_code} - {response.text}")
                return CreditConsumeResult(
                    success=False,
                    new_balance=0,
                    credits_consumed=0,
                    error=f"API error: {response.status_code}",
                )
                
        except Exception as e:
            logger.error(f"Credit consume error: {e}")
            return CreditConsumeResult(
                success=False,
                new_balance=0,
                credits_consumed=0,
                error=str(e),
            )
    
    async def get_balance(self, office_id: str) -> Tuple[int, Optional[str]]:
        """
        Get current credit balance for an office.
        
        Returns:
            Tuple of (balance, error_message)
        """
        try:
            client = await self._get_client()
            response = await client.get(
                f"{self.base_url}/internal/credits/balance/{office_id}",
                headers=self._internal_headers(),
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("balance", 0), None
            else:
                return 0, f"API error: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Get balance error: {e}")
            return 0, str(e)


# Singleton instance
_credit_client: Optional[CreditClient] = None


def get_credit_client() -> CreditClient:
    """Get the credit client singleton."""
    global _credit_client
    if _credit_client is None:
        _credit_client = CreditClient()
    return _credit_client
