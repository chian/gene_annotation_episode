"""A103 private strict parser for retained native JSON source bytes."""
import json
import math
from typing import Any


class ModelOutputError(ValueError):
    """Original response and parser diagnosis, available to the calling audit."""

    def __init__(self, message, *, category, raw_response, **details):
        super().__init__(message)
        self.raw_response = raw_response
        self.diagnostic = {"category": category, "why": message, **details}


def parse_json_value(text: str) -> Any:
    """Parse one finite, unambiguous JSON value without enforcing an envelope."""
    def reject(message, category, **details):
        raise ModelOutputError(message, category=category, raw_response=text, **details)

    def constant(value):
        reject(f"Non-JSON numeric token: {value}", "nonfinite_json_number", token=value)

    def floating(value):
        parsed = float(value)
        if not math.isfinite(parsed):
            reject("JSON number exceeds finite numeric range", "nonfinite_json_number", token=value)
        return parsed

    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                reject("Duplicate JSON object key", "duplicate_json_key", key=key)
            result[key] = value
        return result

    if not isinstance(text, str):
        reject("LLM output must be text", "non_text_model_output")
    try:
        parsed = json.loads(text, parse_constant=constant, parse_float=floating,
                            object_pairs_hook=object_pairs)
    except json.JSONDecodeError as exc:
        raise ModelOutputError(
            f"LLM output was not valid JSON: {exc.msg} at line {exc.lineno}, column {exc.colno}",
            category="malformed_json", raw_response=text, parser_message=exc.msg,
            line=exc.lineno, column=exc.colno, position=exc.pos,
        ) from exc
    return parsed

