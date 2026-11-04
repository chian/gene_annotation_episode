"""Strict JSON parsing copied from episodic_workflow's model boundary.

Source: task_executors/evidence_extraction/argo.py, parse_json_object and
ModelOutputError. The exception inherits ValueError here instead of the source
repository's HTTP-provider exception. No runtime dependency on that checkout.
"""

import json
import math
from collections.abc import Mapping
from itertools import islice
from typing import Any

from jsonschema import Draft202012Validator


def schema_failure_diagnostic(error):
    """Describe the failed constraint, without rendering a schema or instance.

    jsonschema's exception string pretty-prints the whole anyOf schema. An
    action catalog can make that string larger than the next model request is
    allowed to be. Select the branch identified by the action's existing const
    tags for diagnosis only; admission still uses the complete host schema.
    Exact proposals and contracts remain in the decision journal.
    """
    def bounded(value):
        if isinstance(value, str):
            return value[:160]
        if isinstance(value, (list, tuple)):
            return [bounded(item) for item in value[:8]]
        if isinstance(value, Mapping):
            return {str(key)[:160]: bounded(item)
                    for key, item in islice(value.items(), 8)}
        return value

    def leaves(item):
        if item.validator in ('anyOf', 'oneOf') and item.context:
            branches = item.schema[item.validator]
            matching = []
            if isinstance(item.instance, Mapping):
                for index, branch in enumerate(branches):
                    tags = {key: field for key, field in branch.get('properties', {}).items()
                            if 'const' in field or len(field.get('enum', [])) == 1}
                    if tags and all(key in item.instance and
                            Draft202012Validator(field).is_valid(item.instance[key])
                            for key, field in tags.items()):
                        matching.append(index)
            if len(matching) == 1:
                for child in item.context:
                    path = list(child.schema_path)
                    if path and path[0] == matching[0]:
                        yield from leaves(child)
                return
        yield item

    failures = list(islice(leaves(error), 9))
    issues = []
    for failure in failures[:8]:
        rule = failure.validator
        issue = {'path': bounded(list(failure.absolute_path)), 'rule': rule}
        if rule in ('type', 'pattern', 'format', 'enum', 'const', 'required',
                    'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum',
                    'minLength', 'maxLength', 'minItems', 'maxItems',
                    'uniqueItems', 'additionalProperties'):
            issue['expected'] = bounded(failure.validator_value)
        issues.append(issue)
    return {'code': 'schema_validation', 'issues': issues,
            'more_issues': len(failures) > 8}


class ModelOutputError(ValueError):
    """Original response and parser diagnosis, available to the calling audit."""

    def __init__(self, message, *, category, raw_response, **details):
        super().__init__(message)
        self.raw_response = raw_response
        self.diagnostic = {"category": category, "why": message, **details}


def parse_json_object(text: str) -> dict[str, Any]:
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
    if not isinstance(parsed, dict):
        reject("LLM output must be a JSON object", "non_object_json",
               received_type=type(parsed).__name__)
    return parsed
