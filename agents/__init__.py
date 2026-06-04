"""
Agents Module
Each agent has a single responsibility and input/output contract.
"""


class AgentException(Exception):
    """Exception raised when an agent encounters an unrecoverable error."""

    def __init__(self, agent_name: str, error_type: str, message: str, context: dict = None):
        self.agent_name = agent_name
        self.error_type = error_type
        self.message = message
        self.context = context or {}
        super().__init__(f"[{agent_name}] {error_type}: {message}")
