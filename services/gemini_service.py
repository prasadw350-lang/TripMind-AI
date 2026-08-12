"""Gemini AI service for AI Travel Planner."""

import json
import re

from google import genai
from google.genai import types

from config import config


class GeminiError(Exception):
    pass


# ---------------------------------------------------------
# Gemini client
# ---------------------------------------------------------

if not config.GEMINI_API_KEY:
    client = None
else:
    client = genai.Client(api_key=config.GEMINI_API_KEY)


# ---------------------------------------------------------
# JSON extraction
# ---------------------------------------------------------

def _extract_json(text: str):
    if not text:
        raise GeminiError("Gemini returned an empty response.")

    text = text.strip()

    # Remove markdown code fences
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try to extract a JSON object
    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]

        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    raise GeminiError(
        "The AI response could not be read as valid JSON."
    )


# ---------------------------------------------------------
# Gemini call
# ---------------------------------------------------------

def _call(prompt: str):
    if client is None:
        raise GeminiError(
            "Gemini is not configured. "
            "Add GEMINI_API_KEY to your .env file and restart the server."
        )

    model = getattr(
        config,
        "GEMINI_MODEL",
        "gemini-3.5-flash"
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

    except Exception as exc:
        print("GEMINI ERROR:", repr(exc))

        message = str(exc)

        if "429" in message:
            raise GeminiError(
                "Gemini rate limit reached. Please wait and try again."
            )

        if "401" in message or "403" in message:
            raise GeminiError(
                "Gemini API key was rejected. Check GEMINI_API_KEY."
            )

        if "404" in message:
            raise GeminiError(
                f"Gemini model '{model}' is unavailable. "
                "Check GEMINI_MODEL in your .env file."
            )

        if "503" in message:
            raise GeminiError(
                "Gemini is temporarily unavailable. Please try again."
            )

        raise GeminiError(
            "Gemini service error: " + message
        )

    text = getattr(response, "text", None)

    if not text:
        raise GeminiError(
            "Gemini returned an empty response."
        )

    return _extract_json(text)


# ---------------------------------------------------------
# Shared context
# ---------------------------------------------------------

def _context_block(ctx: dict) -> str:

    interests = ctx.get("interests") or []

    if isinstance(interests, str):
        interests = [interests]

    return (
        f"Destination: {ctx.get('destination', '')}\n"
        f"Country: {ctx.get('country', '')}\n"
        f"Traveller starts from: "
        f"{ctx.get('start_location') or 'not specified'}\n"
        f"Total trip budget: "
        f"INR {int(ctx.get('budget_inr', 0)):,} "
        f"for the WHOLE trip, NOT per day\n"
        f"Trip length: {ctx.get('days', 1)} days\n"
        f"Travel type: "
        f"{ctx.get('travel_type') or 'not specified'}\n"
        f"Season: "
        f"{ctx.get('season') or 'not specified'}\n"
        f"Interests: "
        f"{', '.join(interests) if interests else 'general'}\n"
    )


# ---------------------------------------------------------
# Global rules
# ---------------------------------------------------------

RULES = """
IMPORTANT RULES:

1. The budget is the TOTAL budget for the entire trip.
2. NEVER treat the budget as a daily budget.
3. All monetary values must be in Indian Rupees (INR).
4. Use realistic INR amounts.
5. The complete estimated trip cost must stay within the user's total budget.
6. Do not invent impossible prices.
7. Keep the destination exactly as requested.
8. Do not recommend a different destination.
9. Hotels, restaurants and attractions must be specific to the destination.
10. Consider the traveller's starting location.
11. Consider trip duration.
12. Consider season.
13. Consider travel type.
14. Consider all selected interests.
15. Return ONLY valid JSON.
16. Do not use Markdown.
17. Do not put JSON inside ``` code fences.
"""


# ---------------------------------------------------------
# AI Recommendation / Destination briefing
# ---------------------------------------------------------

def generate_insight(ctx: dict) -> dict:

    prompt = f"""
You are an expert Indian travel advisor.

Create a personalized destination briefing using the following traveller information:

{_context_block(ctx)}

{RULES}

Return exactly this JSON structure:

{{
    "summary": "3-4 sentence destination overview specifically tailored to the traveller",

    "why_it_fits": [
        "reason 1",
        "reason 2",
        "reason 3",
        "reason 4"
    ],

    "highlights": [
        {{
            "title": "real attraction or experience",
            "detail": "short useful explanation"
        }}
    ],

    "best_time": "best season or months and why",

    "getting_there": "realistic way to travel from the starting location with approximate INR cost",

    "local_food": [
        "dish 1",
        "dish 2",
        "dish 3",
        "dish 4"
    ],

    "culture_notes": [
        "note 1",
        "note 2",
        "note 3"
    ],

    "budget_fit": "Explain whether the TOTAL INR budget is realistic for the complete trip."
}}
"""

    return _call(prompt)


# ---------------------------------------------------------
# AI Trip Planner
# ---------------------------------------------------------

def generate_plan(ctx: dict) -> dict:

    days = int(ctx.get("days", 1))

    if days < 1:
        days = 1

    prompt = f"""
You are an expert Indian travel planner.

Create a complete and realistic {days}-day itinerary.

Traveller information:

{_context_block(ctx)}

{RULES}

The itinerary MUST contain exactly {days} day entries.

The total estimated cost must NOT exceed the user's total budget.

Flight/train transportation from the starting location should be considered.

Return exactly this JSON structure:

{{
    "overview": "3-4 sentence overview of the complete trip",

    "itinerary": [
        {{
            "day": 1,
            "title": "Day title",
            "morning": "morning plan",
            "afternoon": "afternoon plan",
            "evening": "evening plan",
            "estimated_cost_inr": 0
        }}
    ],

    "hotels": [
        {{
            "name": "real hotel",
            "area": "real area",
            "price_per_night_inr": 0,
            "why": "why this hotel fits"
        }}
    ],

    "restaurants": [
        {{
            "name": "real restaurant",
            "cuisine": "cuisine type",
            "must_try": "dish",
            "avg_cost_inr": 0
        }}
    ],

    "activities": [
        {{
            "name": "real activity",
            "detail": "short explanation",
            "cost_inr": 0
        }}
    ],

    "tips": [
        "tip 1",
        "tip 2",
        "tip 3",
        "tip 4",
        "tip 5"
    ],

    "packing": [
        "item 1",
        "item 2",
        "item 3",
        "item 4",
        "item 5",
        "item 6"
    ],

    "safety": [
        "safety note 1",
        "safety note 2",
        "safety note 3",
        "safety note 4"
    ],

    "budget_breakdown": [
        {{
            "category": "Flights / Transport",
            "amount_inr": 0
        }},
        {{
            "category": "Hotels",
            "amount_inr": 0
        }},
        {{
            "category": "Food",
            "amount_inr": 0
        }},
        {{
            "category": "Activities",
            "amount_inr": 0
        }},
        {{
            "category": "Local Transport",
            "amount_inr": 0
        }}
    ],

    "total_estimated_inr": 0
}}
"""

    result = _call(prompt)

    # Ensure itinerary length is correct
    itinerary = result.get("itinerary", [])

    if len(itinerary) != days:
        raise GeminiError(
            f"Gemini returned {len(itinerary)} days instead of {days}."
        )

    return result