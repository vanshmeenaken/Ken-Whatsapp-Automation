"""
Unit Tests — Message Builder Agent
Run: pytest tests/ -v
"""

import pytest
from agents.message_builder import MessageBuilder
from agents import AgentException


@pytest.fixture
def builder():
    return MessageBuilder()


def test_basic_substitution(builder):
    result = builder.run({
        "template": "Hi {{first_name}}, {{company}} would benefit from our service.",
        "variables": {"first_name": "Rohan", "company": "Candesis"}
    })
    assert result["success"] is True
    assert "Rohan" in result["personalized_message"]
    assert "Candesis" in result["personalized_message"]
    assert "{{" not in result["personalized_message"]


def test_missing_variable_raises_error(builder):
    with pytest.raises(AgentException):
        builder.run({
            "template": "Hi {{first_name}}, welcome to {{company}}",
            "variables": {"first_name": "Rohan"}  # company missing
        })


def test_empty_template_raises_error(builder):
    with pytest.raises(AgentException):
        builder.run({"template": "", "variables": {}})


def test_no_variables_passthrough(builder):
    result = builder.run({
        "template": "Hi there, check out our services!",
        "variables": {}
    })
    assert result["success"] is True
    assert result["personalized_message"] == "Hi there, check out our services!"


def test_message_too_long(builder):
    with pytest.raises(AgentException):
        builder.run({
            "template": "a" * 5000,
            "variables": {}
        })


def test_default_values_used(builder):
    result = builder.run({
        "template": "Hi {{first_name}}, from {{company}}",
        "variables": {"first_name": "", "company": ""}
    })
    # Empty strings are substituted (validation is upstream)
    assert "{{" not in result["personalized_message"]
