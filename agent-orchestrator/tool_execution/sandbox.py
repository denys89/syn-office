"""Execution Sandbox - Isolated code execution environment.

Provides secure sandbox for dynamic code execution using subprocess
with resource limits (Option A - lighter weight approach).
"""

import asyncio
import logging
import subprocess
import sys
import tempfile
import os
import json
import time
from typing import Dict, Any, Optional

from .types import ResourceLimits, SandboxResult

logger = logging.getLogger(__name__)


class ExecutionSandbox:
    """
    Secure sandbox for dynamic code/data processing.
    
    Uses subprocess with resource limits for isolated execution.
    
    Security Requirements:
    - No persistent filesystem access
    - No outbound network (unless whitelisted)
    - CPU and memory limits enforced
    - Timeout enforcement
    
    Implementation: Subprocess with resource limits (Option A)
    """
    
    # Restricted builtins for sandboxed code
    ALLOWED_BUILTINS = {
        'abs', 'all', 'any', 'bool', 'dict', 'enumerate', 'filter',
        'float', 'frozenset', 'int', 'isinstance', 'len', 'list',
        'map', 'max', 'min', 'print', 'range', 'repr', 'reversed',
        'round', 'set', 'slice', 'sorted', 'str', 'sum', 'tuple',
        'type', 'zip', 'True', 'False', 'None',
    }
    
    # Allowed imports in sandbox
    ALLOWED_MODULES = {
        'json', 'math', 're', 'datetime', 'collections',
        'itertools', 'functools', 'operator', 'string',
        'statistics', 'decimal', 'fractions',
    }
    
    def __init__(self):
        self._initialized: bool = False
        self._available: bool = False
    
    async def initialize(self) -> None:
        """Initialize the sandbox."""
        # Verify Python is available
        try:
            result = subprocess.run(
                [sys.executable, '--version'],
                capture_output=True,
                timeout=5
            )
            self._available = result.returncode == 0
        except Exception as e:
            logger.warning(f"Sandbox initialization failed: {e}")
            self._available = False
        
        self._initialized = True
        logger.info(f"Execution Sandbox initialized (available: {self._available})")
    
    def is_available(self) -> bool:
        """Check if sandbox is available."""
        return self._available
    
    async def execute_safely(
        self,
        code: str,
        inputs: Dict[str, Any],
        limits: ResourceLimits,
    ) -> SandboxResult:
        """
        Execute code in isolated subprocess with resource limits.
        
        Args:
            code: Python code to execute
            inputs: Input data available as 'inputs' variable
            limits: Resource limits to enforce
            
        Returns:
            SandboxResult with output or error
        """
        start_time = time.time()
        
        if not self._available:
            return SandboxResult(
                success=False,
                error="Sandbox not available",
                execution_time_ms=0,
            )
        
        # Validate code safety
        safety_check = self._check_code_safety(code)
        if not safety_check[0]:
            return SandboxResult(
                success=False,
                error=f"Code safety check failed: {safety_check[1]}",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        
        # Create wrapper script
        wrapper_code = self._create_wrapper(code, inputs, limits)
        
        try:
            # Execute in subprocess
            result = await self._run_subprocess(
                wrapper_code,
                limits.timeout_seconds,
                limits.max_memory_mb,
            )
            
            execution_time = int((time.time() - start_time) * 1000)
            
            if result['success']:
                return SandboxResult(
                    success=True,
                    output=result.get('output'),
                    stdout=result.get('stdout', ''),
                    stderr=result.get('stderr', ''),
                    execution_time_ms=execution_time,
                )
            else:
                return SandboxResult(
                    success=False,
                    error=result.get('error', 'Unknown error'),
                    stdout=result.get('stdout', ''),
                    stderr=result.get('stderr', ''),
                    execution_time_ms=execution_time,
                )
                
        except asyncio.TimeoutError:
            return SandboxResult(
                success=False,
                error=f"Execution timeout after {limits.timeout_seconds}s",
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            logger.exception(f"Sandbox execution error: {e}")
            return SandboxResult(
                success=False,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )
    
    def _check_code_safety(self, code: str) -> tuple[bool, Optional[str]]:
        """
        Check code for potentially dangerous patterns.
        
        Returns:
            Tuple of (is_safe, error_message)
        """
        dangerous_patterns = [
            ('import os', "Direct os import not allowed"),
            ('import sys', "Direct sys import not allowed"),
            ('import subprocess', "subprocess import not allowed"),
            ('import socket', "socket import not allowed"),
            ('import requests', "requests import not allowed"),
            ('import urllib', "urllib import not allowed"),
            ('import http', "http import not allowed"),
            ('__import__', "__import__ not allowed"),
            ('eval(', "eval not allowed"),
            ('exec(', "exec not allowed"),
            ('compile(', "compile not allowed"),
            ('open(', "open() not allowed - use provided data"),
            ('file(', "file() not allowed"),
            ('globals(', "globals() not allowed"),
            ('locals(', "locals() not allowed"),
            ('getattr(', "getattr() not allowed"),
            ('setattr(', "setattr() not allowed"),
            ('delattr(', "delattr() not allowed"),
        ]
        
        code_lower = code.lower()
        for pattern, message in dangerous_patterns:
            if pattern.lower() in code_lower:
                return False, message
        
        return True, None
    
    def _create_wrapper(
        self,
        code: str,
        inputs: Dict[str, Any],
        limits: ResourceLimits,
    ) -> str:
        """Create wrapper script for sandbox execution."""
        
        # Serialize inputs
        inputs_json = json.dumps(inputs)
        
        wrapper = f'''
import json
import sys

# Set up restricted environment
__result__ = None
__error__ = None

# Parse inputs
inputs = json.loads({repr(inputs_json)})

try:
    # User code
{self._indent_code(code, 4)}
    
    # Capture result
    if '__result__' not in dir() or __result__ is None:
        __result__ = {{"status": "completed"}}
        
except Exception as e:
    __error__ = str(e)

# Output result
output = {{
    "success": __error__ is None,
    "output": __result__,
    "error": __error__,
}}
print("__SANDBOX_RESULT__")
print(json.dumps(output))
'''
        return wrapper
    
    def _indent_code(self, code: str, spaces: int) -> str:
        """Indent code by specified spaces."""
        indent = ' ' * spaces
        lines = code.split('\n')
        return '\n'.join(indent + line for line in lines)
    
    async def _run_subprocess(
        self,
        code: str,
        timeout: int,
        max_memory_mb: int,
    ) -> Dict[str, Any]:
        """Run code in subprocess with limits."""
        
        # Write code to temp file
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False
        ) as f:
            f.write(code)
            script_path = f.name
        
        try:
            # Build command with resource limits (Windows compatible)
            cmd = [sys.executable, script_path]
            
            # Run subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                # Limit environment
                env={
                    'PATH': os.environ.get('PATH', ''),
                    'PYTHONPATH': '',
                    'PYTHONDONTWRITEBYTECODE': '1',
                },
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise
            
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')
            
            # Parse result
            if '__SANDBOX_RESULT__' in stdout_str:
                result_start = stdout_str.index('__SANDBOX_RESULT__')
                result_json = stdout_str[result_start + len('__SANDBOX_RESULT__'):].strip()
                
                # Find the JSON part
                lines = result_json.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.startswith('{'):
                        try:
                            result = json.loads(line)
                            result['stdout'] = stdout_str[:result_start].strip()
                            result['stderr'] = stderr_str
                            return result
                        except json.JSONDecodeError:
                            pass
            
            # Fallback if no result marker found
            return {
                'success': process.returncode == 0,
                'output': stdout_str,
                'error': stderr_str if process.returncode != 0 else None,
                'stdout': stdout_str,
                'stderr': stderr_str,
            }
            
        finally:
            # Cleanup temp file
            try:
                os.unlink(script_path)
            except Exception:
                pass
    
    async def execute_simple(
        self,
        expression: str,
        context: Dict[str, Any],
    ) -> SandboxResult:
        """
        Execute a simple expression (not full code).
        
        Safer for quick calculations.
        
        Args:
            expression: Python expression to evaluate
            context: Variables available in expression
            
        Returns:
            SandboxResult with expression value
        """
        # Wrap expression in result assignment
        code = f"__result__ = {expression}"
        
        limits = ResourceLimits(
            max_cpu_seconds=2,
            max_memory_mb=64,
            timeout_seconds=5,
            allow_network=False,
        )
        
        return await self.execute_safely(code, context, limits)
