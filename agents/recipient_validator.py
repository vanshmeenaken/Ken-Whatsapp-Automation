"""
Agent 2: Recipient Validator
Validates phone numbers against format rules.
Does NOT verify if numbers are real/active - just format validation.
"""

import re
from typing import Dict, Any, List
from agents.base_agent import BaseAgent
from config.settings import settings


class RecipientValidator(BaseAgent):
    """
    Responsible for:
    1. Validating phone number format (E.164 compliance)
    2. Checking for duplicates
    3. Returning valid and invalid phone lists with reasons
    """

    def __init__(self):
        super().__init__("RecipientValidator")
        self.phone_regex = re.compile(settings.PHONE_REGEX_PATTERN)

    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Input:
        {
            "phone_numbers": ["+919876543210", "invalid123", "+919123456789"],
            "allow_duplicates": False
        }

        Output:
        {
            "valid_phones": ["+919876543210", "+919123456789"],
            "invalid_phones": [
                {
                    "phone_number": "invalid123",
                    "reason": "Invalid format. Expected E.164 format: +[country_code][number]"
                }
            ],
            "duplicates": ["+919876543210"]  # if allow_duplicates=False
        }
        """
        phones = input_data.get("phone_numbers", [])
        allow_duplicates = input_data.get("allow_duplicates", False)

        if not phones:
            self.raise_error("ValidationError", "No phone numbers provided", input_data)

        valid = []
        invalid = []
        seen = set()

        for phone in phones:
            phone = str(phone).strip() if phone else ""

            # Check format
            if not self._is_valid_format(phone):
                invalid.append({
                    "phone_number": phone,
                    "reason": "Invalid format. Expected E.164 format: +[country_code][number]"
                })
                continue

            # Check duplicates
            if phone in seen and not allow_duplicates:
                continue  # Skip duplicate

            valid.append(phone)
            seen.add(phone)

        self.log_info(f"Validated {len(valid)} phones, {len(invalid)} invalid")

        return {
            "valid_phones": valid,
            "invalid_phones": invalid,
            "valid_count": len(valid),
            "invalid_count": len(invalid),
            "duplicate_count": len(set(phones)) - len(set(valid + [i["phone_number"] for i in invalid]))
        }

    def _is_valid_format(self, phone: str) -> bool:
        """Check if phone matches E.164 format."""
        if not phone:
            return False
        return bool(self.phone_regex.match(phone))
