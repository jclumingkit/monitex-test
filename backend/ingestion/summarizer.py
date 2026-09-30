import os
import httpx

from models.detection_event import DetectionEvent


OPENROUTER_KEY = os.getenv("OPEN_ROUTER_API")

SUMMARY_MODEL = "deepseek/deepseek-v4.1-flash"

client = httpx.AsyncClient(
    timeout=15.0,
)


async def summarize_event(event: DetectionEvent) -> str:
    if not OPENROUTER_KEY:
        return fallback_summary(event)

    response = await client.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": SUMMARY_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You summarize security monitoring events for human operators. "
                        "Return exactly one concise sentence with a recommended action. "
                        "Maximum 30 words. "
                        "Only state facts present in the event. "
                        "Do not speculate or mention missing information."
                    ),
                },
                {
                    "role": "user",
                    "content": event.model_dump_json(),
                },
            ],
            "reasoning": {"effort": "none"},
            "temperature": 0.1,
            # "max_tokens": 120,
        },
    )

    response.raise_for_status()

    data = response.json()
    content = data["choices"][0]["message"]["content"]

    if not content:
        return fallback_summary(event)

    return content.strip()


def fallback_summary(event: DetectionEvent) -> str:
    event_type = event.type.value.replace("_", " ")

    return (
        f"{event_type.capitalize()} reported at {event.site_id} "
        f"in {event.zone} with {event.confidence:.0%} confidence."
    )
