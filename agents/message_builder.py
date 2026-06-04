"""
Agent 1: Message Builder
Personalizes message templates by replacing {{variable}} placeholders with actual values.
No external API calls. Pure string manipulation.
"""

import re
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from config.settings import settings


class MessageBuilder(BaseAgent):
    """
    Responsible for:
    1. Taking a message template with {{placeholder}} syntax
    2. Replacing placeholders with actual contact data
    3. Validating the final message
    4. Returning personalized, send-ready message text
    """

    def __init__(self):
        super().__init__("MessageBuilder")
        self.placeholder_pattern = re.compile(r"\{\{(\w+)\}\}")
        self.max_length = settings.MESSAGE_MAX_LENGTH

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Input:
        {
            "template": "Hi {{first_name}}, {{company}} would benefit from...",
            "variables": {
                "first_name": "Rohan",
                "company": "Candesis"
            }
        }

        Output:
        {
            "success": True,
            "personalized_message": "Hi Rohan, Candesis would benefit from...",
            "original_template": "...",
            "variables_used": {
                "first_name": "Rohan",
                "company": "Candesis"
            }
        }
        """
        template = input_data.get("template")
        variables = input_data.get("variables", {})

        if not template:
            self.raise_error("ValidationError", "No template provided", input_data)

        # Personalize the template
        personalized = self._personalize(template, variables)

        # Validate the result
        self._validate_message(personalized)

        return {
            "success": True,
            "personalized_message": personalized,
            "original_template": template,
            "variables_used": variables,
            "character_count": len(personalized)
        }

    def _personalize(self, template: str, variables: Dict[str, str]) -> str:
        """Replace all {{placeholder}} with actual values."""
        message = template

        # Replace each variable
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            message = message.replace(placeholder, str(value))

        return message

    def _validate_message(self, message: str):
        """Validate the personalized message."""
        if not message or len(message.strip()) < 3:
            self.raise_error(
                "ValidationError",
                "Personalized message is empty or too short",
                {"message": message}
            )

        if len(message) > self.max_length:
            self.raise_error(
                "ValidationError",
                f"Message exceeds max length ({self.max_length} chars)",
                {"length": len(message), "max": self.max_length}
            )

        # Check for remaining unfilled placeholders
        remaining = self.placeholder_pattern.findall(message)
        if remaining:
            self.raise_error(
                "ValidationError",
                f"Unfilled placeholders in message: {remaining}",
                {"message": message, "unfilled": remaining}
            )

        self.log_debug(f"Message validated: {len(message)} chars")
