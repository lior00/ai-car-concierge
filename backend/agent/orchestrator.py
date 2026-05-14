"""
Agent orchestrator using Anthropic tool-use API.
Routes between sql_tool, rag_tool, email_tool, and reservation_tool.
Policy enforcement runs inside each tool — not delegated to LLM instructions alone.
"""
import json
import logging
from pathlib import Path

import anthropic

from backend.config import ANTHROPIC_API_KEY, LLM_MODEL
from backend.agent.tools.sql_tool import query_inventory
from backend.agent.tools.rag_tool import search_knowledge_base
from backend.agent.tools.email_tool import send_purchase_email
from backend.agent.tools.reservation_tool import reserve_vehicle

logger = logging.getLogger(__name__)

_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

_SYSTEM_PROMPT = (
    Path(__file__).parent / "prompts" / "system_prompt.txt"
).read_text(encoding="utf-8")

# Tool definitions for Anthropic tool-use API
TOOLS: list[dict] = [
    {
        "name": "query_inventory",
        "description": (
            "Query the vehicle inventory database using natural language. "
            "Use this for any question about specific vehicles: price, availability, "
            "make, model, year, fuel type, color, specs, or stock count."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "natural_language": {
                    "type": "string",
                    "description": "The user's vehicle question in plain English.",
                }
            },
            "required": ["natural_language"],
        },
    },
    {
        "name": "search_knowledge_base",
        "description": (
            "Search the dealership's policy and documentation knowledge base. "
            "Use this for questions about: sales policy, refunds, test drive scheduling, "
            "maintenance schedules (EV vs gasoline), shipping and delivery, FAQs, or contact info."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The user's question about dealership policy or procedures.",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "send_purchase_email",
        "description": (
            "Send a purchase interest confirmation email to the customer. "
            "Only call this when: (1) the user clearly expresses purchase intent, "
            "(2) the vehicle year is 2022 or newer (SELLABLE), "
            "and (3) you have the customer's email address."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_email": {"type": "string", "description": "Customer's email address."},
                "customer_name": {"type": "string", "description": "Customer's name."},
                "vehicle_make": {"type": "string"},
                "vehicle_model": {"type": "string"},
                "vehicle_year": {"type": "integer"},
                "vehicle_id": {"type": "integer", "description": "Database ID of the vehicle."},
                "vehicle_price": {"type": "number"},
            },
            "required": [
                "customer_email", "customer_name", "vehicle_make",
                "vehicle_model", "vehicle_year", "vehicle_id", "vehicle_price",
            ],
        },
    },
    {
        "name": "reserve_vehicle",
        "description": (
            "Reserve a vehicle by decrementing its stock count in the database. "
            "Only call after explicit user confirmation ('yes, reserve it'). "
            "The vehicle must be from 2022 or newer."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "vehicle_id": {
                    "type": "integer",
                    "description": "The database ID of the vehicle to reserve.",
                }
            },
            "required": ["vehicle_id"],
        },
    },
]


def _dispatch_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool call and return its result as a JSON string."""
    try:
        if tool_name == "query_inventory":
            result = query_inventory(tool_input["natural_language"])
        elif tool_name == "search_knowledge_base":
            result = search_knowledge_base(tool_input["query"])
        elif tool_name == "send_purchase_email":
            result = send_purchase_email(**tool_input)
        elif tool_name == "reserve_vehicle":
            result = reserve_vehicle(tool_input["vehicle_id"])
        else:
            result = {"error": f"Unknown tool: {tool_name}"}
    except Exception as e:
        logger.exception(f"Tool {tool_name} raised an exception: {e}")
        result = {"error": str(e)}

    return json.dumps(result, ensure_ascii=False)


def chat(
    user_message: str,
    history: list[dict],
) -> tuple[str, list[dict]]:
    """
    Process one user turn and return (assistant_response, updated_history).

    Args:
        user_message: The current user input.
        history: List of previous messages [{"role": ..., "content": ...}].

    Returns:
        (response_text, updated_history)
    """
    messages = history + [{"role": "user", "content": user_message}]

    while True:
        response = _client.messages.create(
            model=LLM_MODEL,
            max_tokens=2048,
            system=_SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        # Serialize to dicts immediately — SDK objects are not re-serializable across turns
        messages.append({"role": "assistant", "content": [b.model_dump() for b in response.content]})

        if response.stop_reason == "end_turn":
            # Extract text from response content blocks
            text_parts = [
                block.text for block in response.content
                if hasattr(block, "text")
            ]
            return " ".join(text_parts).strip(), messages

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    logger.debug(f"Tool call: {block.name}({block.input})")
                    result_str = _dispatch_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_str,
                    })

            messages.append({"role": "user", "content": tool_results})
            # Loop continues — model will process tool results and respond
        else:
            # Unexpected stop reason
            logger.warning(f"Unexpected stop_reason: {response.stop_reason}")
            break

    return "I encountered an unexpected issue. Please try again.", messages
