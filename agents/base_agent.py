"""
Base Agent Class
All agents inherit from this class for common functionality like logging and error handling.
"""

import logging
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Dict, Any
from agents import AgentException


class BaseAgent(ABC):
    """
    Base class for all agents.
    Each agent processes input and returns output following a contract.
    """

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.logger = logging.getLogger(agent_name)

    @abstractmethod
    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point for the agent.
        Subclasses must implement this.

        Args:
            input_data: Dict with agent-specific input

        Returns:
            Dict with agent-specific output

        Raises:
            AgentException: If agent encounters an error
        """
        pass

    def log_info(self, message: str):
        """Log info level message."""
        self.logger.info(f"[{self.agent_name}] {message}")

    def log_warning(self, message: str):
        """Log warning level message."""
        self.logger.warning(f"[{self.agent_name}] {message}")

    def log_error(self, message: str):
        """Log error level message."""
        self.logger.error(f"[{self.agent_name}] {message}")

    def log_debug(self, message: str):
        """Log debug level message."""
        self.logger.debug(f"[{self.agent_name}] {message}")

    def raise_error(self, error_type: str, message: str, context: dict = None):
        """Raise an AgentException with context."""
        self.log_error(f"{error_type}: {message}")
        raise AgentException(self.agent_name, error_type, message, context)

    def get_timestamp(self) -> str:
        """Get current UTC timestamp in ISO format."""
        return datetime.utcnow().isoformat()
