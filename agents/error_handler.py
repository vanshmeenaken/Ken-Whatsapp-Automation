"""
Agent 5: Error Handler
Catches exceptions from other agents, logs to database, and optionally calls Claude CLI for analysis.
"""

import json
import subprocess
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from agents.base_agent import BaseAgent
from agents import AgentException
from config.settings import settings


class ErrorHandler(BaseAgent):
    """
    Responsible for:
    1. Capturing exceptions from all agents
    2. Logging errors with context to database
    3. Optionally invoking Claude CLI for error analysis (dev mode only)
    4. Returning structured error report
    """

    def __init__(self):
        super().__init__("ErrorHandler")

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def handle(self, exception: AgentException, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Handle an AgentException.

        Args:
            exception: The AgentException to handle
            context: Additional context about where error occurred

        Returns:
            Structured error report
        """
        context = context or {}
        
        self.log_error(f"{exception.agent_name}: {exception.error_type} - {exception.message}")

        # Log to database (in v2 with SQLite)
        error_id = self._log_error(exception, context)

        # Optionally invoke Claude CLI (dev only)
        claude_analysis = None
        if settings.CLAUDE_CLI_ENABLED and settings.API_ENV == "development":
            claude_analysis = self._invoke_claude_cli(exception, context)

        return {
            "error_id": error_id,
            "agent": exception.agent_name,
            "error_type": exception.error_type,
            "message": exception.message,
            "context": exception.context,
            "claude_analysis": claude_analysis,
            "timestamp": self.get_timestamp()
        }

    def _log_error(self, exception: AgentException, context: Dict) -> str:
        """
        Log error to persistent storage.
        TODO: Implement SQLite logging in v2
        For now, just log to file/console.
        """
        error_id = f"err_{datetime.utcnow().timestamp()}"
        
        error_data = {
            "error_id": error_id,
            "agent": exception.agent_name,
            "error_type": exception.error_type,
            "message": exception.message,
            "context": exception.context,
            "additional_context": context,
            "timestamp": self.get_timestamp()
        }

        self.log_info(f"Error logged: {error_id}")
        
        # TODO: Write to SQLite database
        # db.execute("INSERT INTO error_logs (...) VALUES (...)")
        
        return error_id

    def _invoke_claude_cli(self, exception: AgentException, context: Dict) -> Optional[str]:
        """
        Invoke Claude CLI to analyze the error.
        Only runs in development mode.

        Claude CLI must be installed:
        pip install anthropic-cli  (or similar, depending on Anthropic's package)
        """
        if not settings.CLAUDE_CLI_ENABLED:
            return None

        try:
            prompt = f"""
You are debugging a WhatsApp outreach automation system built with Python and FastAPI.

An error occurred in the following agent:
Agent: {exception.agent_name}
Error Type: {exception.error_type}
Error Message: {exception.message}

Agent Context:
{json.dumps(exception.context, indent=2)}

Additional Context:
{json.dumps(context, indent=2)}

Please provide:
1. Root cause analysis (1-2 sentences)
2. Recommended fix (specific and actionable)
3. Should this be retried or skipped? (retry | skip | investigate)
4. Is this a code bug or a data issue? (code | data | config)

Respond in plain text, no markdown.
"""

            result = subprocess.run(
                ["claude", "-p", prompt],
                capture_output=True,
                text=True,
                timeout=settings.CLAUDE_CLI_TIMEOUT
            )

            if result.returncode == 0:
                analysis = result.stdout.strip()
                self.log_info("Claude CLI analysis completed")
                return analysis
            else:
                self.log_warning(f"Claude CLI error: {result.stderr}")
                return None

        except subprocess.TimeoutExpired:
            self.log_warning("Claude CLI timed out")
            return "Claude CLI timed out"
        except FileNotFoundError:
            self.log_warning("Claude CLI not installed or not in PATH")
            return "Claude CLI not installed"
        except Exception as e:
            self.log_warning(f"Claude CLI failed: {str(e)}")
            return f"Claude CLI error: {str(e)}"
