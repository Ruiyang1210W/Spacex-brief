"""Tool-using briefing agent. Live facts come from tools.py, not the model."""

from __future__ import annotations

import json
import os

from openai import OpenAI

from tools import get_apod, get_iss_passes, get_next_spacex_launches

SYSTEM_PROMPT = """You are Pad Brief, a live SpaceX/space briefing intern.

Rules:
- Never invent launch times, pads, payloads, ISS passes, or APOD titles.
- For anything about launches, ISS, satellites, or today's sky picture, call a tool first.
- After tools return, brief like a 60-second pad intern: short, concrete, no hype.
- Convert takeaways for a Hawthorne / Los Angeles audience (Pacific Time).
- If a tool errors, say the data source failed. Do not guess a replacement time.
- If the user asks something outside space/launch/ISS/APOD, answer briefly then steer back.
- Default language: match the user. Chinese in, Chinese out. English in, English out.
- End with one suggested follow-up question.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_next_spacex_launches",
            "description": "Get the next upcoming SpaceX launches with time, pad, rocket, and mission.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "How many upcoming launches to fetch (1-5).",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_iss_passes",
            "description": "Get current ISS position and upcoming naked-eye visible passes for a lat/lon.",
            "parameters": {
                "type": "object",
                "properties": {
                    "lat": {"type": "number"},
                    "lon": {"type": "number"},
                    "place": {"type": "string"},
                    "n": {"type": "integer"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_apod",
            "description": "Get NASA Astronomy Picture of the Day, optionally for a YYYY-MM-DD date.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Optional date YYYY-MM-DD. Omit for today.",
                    }
                },
            },
        },
    },
]

DISPATCH = {
    "get_next_spacex_launches": get_next_spacex_launches,
    "get_iss_passes": get_iss_passes,
    "get_apod": get_apod,
}


def _client() -> OpenAI:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key or key.startswith("sk-your-key"):
        raise RuntimeError(
            "Missing OPENAI_API_KEY. Copy .env.example to .env and paste your key."
        )
    return OpenAI(api_key=key)


def run_agent(messages: list[dict]) -> tuple[str, list[str]]:
    """Return (assistant_text, tool_names_called)."""
    client = _client()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    working = [{"role": "system", "content": SYSTEM_PROMPT}, *messages]
    used: list[str] = []

    for _ in range(4):
        resp = client.chat.completions.create(
            model=model,
            messages=working,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.3,
        )
        choice = resp.choices[0].message
        tool_calls = choice.tool_calls or []
        if not tool_calls:
            return (choice.content or "").strip(), used

        working.append(
            {
                "role": "assistant",
                "content": choice.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            }
        )
        for tc in tool_calls:
            name = tc.function.name
            used.append(name)
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            fn = DISPATCH.get(name)
            result = {"ok": False, "error": f"Unknown tool {name}"} if fn is None else fn(**args)
            working.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                }
            )

    return "Tool loop stopped after too many steps. Try asking a narrower question.", used
