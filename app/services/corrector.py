import json
from anthropic import Anthropic
from app.config import settings
from app.models.schemas import CaptionLine

client = Anthropic(api_key=settings.anthropic_api_key)
SYSTEM_PROMPT = """You correct caption lines into clean, natural {language}.
Rules:
- Return exactly one string for every input line, in the same order.
- Preserve meaning and do not merge, split, omit, number, or explain lines.
- Fix grammar, spelling, transliteration, and word choice.
- Translate English/mixed speech into {language}, except proper nouns/brands may remain unchanged.
- Return ONLY a JSON array of strings."""


def correct_lines(lines: list[CaptionLine], target_language: str) -> list[CaptionLine]:
    raw_texts = [line.text for line in lines]
    message = client.messages.create(
        model="claude-sonnet-4-6", max_tokens=max(4000, len(raw_texts) * 40),
        system=SYSTEM_PROMPT.format(language=target_language),
        messages=[{"role": "user", "content": json.dumps(raw_texts, ensure_ascii=False)}],
    )
    try:
        corrected_texts = json.loads(message.content[0].text)
    except (json.JSONDecodeError, IndexError, AttributeError) as e:
        raise RuntimeError("Caption correction returned invalid JSON") from e
    if not isinstance(corrected_texts, list) or len(corrected_texts) != len(lines):
        raise RuntimeError("Caption correction changed the number of lines")
    if not all(isinstance(x, str) for x in corrected_texts):
        raise RuntimeError("Caption correction returned invalid line data")
    return [CaptionLine(index=line.index, start_seconds=line.start_seconds,
                        end_seconds=line.end_seconds, text=text.strip())
            for line, text in zip(lines, corrected_texts)]
