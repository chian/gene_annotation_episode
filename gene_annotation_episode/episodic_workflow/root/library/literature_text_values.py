"""Original supplied-state literature text values; no runtime ownership selection."""
import json
from collections.abc import Mapping

_TRACKING = frozenset({
    "run_id", "episode_id", "goal_id", "parent_goal_id", "problem_ref", "record_type",
    "sha256", "digest", "content_sha256", "entry_sha256", "section_sha256",
    "initial_selection_sha256", "operation_ref", "operation_key",
    "base_revision", "revision", "removed_fields", "created_at", "updated_at",
    "recorded_at", "parser_version", "parse_key", "controller_binding", "credit_binding",
    "parent_history", "parent_yields", "private_history", "history", "private_reasoning",
    "own_completed_action_history", "local_return_history", "restored_episode_history",
    "restored_public_exchanges", "restored_pending_decision_index", "diagnostics",
    "scientific_child_credit_binding", "scientific_process", "scoring_rubric",
    "axis_judgment_contract", "calculation_implementation",
    "curve_keys", "measurement_keys", "primitive_measurement_keys",
    "report_contract_declaration", "contract_information_profile",
    "requested_controlled_response_component_keys", "literature_controlled_response_return_bindings",
    "requested_gel_component_keys", "literature_gel_return_bindings", "literature_gel_return_records",
    "literature_rate_source_display", "literature_rate_source_domain_display",
    "literature_rate_source_meaning_display", "literature_endpoint_receipt_bindings",
    "literature_summary_precision_receipt_bindings", "literature_measurement_comparison_receipt_bindings", "literature_concentration_window_receipt_bindings",
})


def _safe(value):
    if isinstance(value, Mapping):
        return {key: _safe(child) for key, child in value.items()
                if key not in _TRACKING and not key.startswith("private_")
                and not key.endswith("_sha256")
                and not (key == "accession" and isinstance(child, str)
                    and child.startswith(("transport_curve_", "transport_quantity_", "native_rate_", "amount_")))}
    if isinstance(value, (list, tuple)):
        return [_safe(child) for child in value]
    return value


def _scalar(value):
    if value is None:
        return "unknown"
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


def _rows(value, path=""):
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield from _rows(child, f"{path}.{key}" if path else key)
    elif isinstance(value, (list, tuple)):
        if not value:
            yield path or "value", "none supplied"
        for index, child in enumerate(value):
            yield from _rows(child, f"{path}[{index}]")
    elif value is None and path.rsplit(".", 1)[-1] in (
            "next_offset", "next_query", "next_continuation_token"):
        # Null navigation controls mean no supplied continuation, not unknown evidence.
        yield path, "null (no continuation supplied)"
    elif isinstance(value, str) and path.rsplit(".", 1)[-1] == "quote":
        # Delimit exact source text independently of Markdown cell padding.
        # JSON escapes preserve whitespace and keep source markup literal.
        literal = json.dumps(value, ensure_ascii=True)
        for character, escaped in (("<", "\\u003c"), (">", "\\u003e"),
                                   ("&", "\\u0026"), ("|", "\\u007c")):
            literal = literal.replace(character, escaped)
        yield path, literal
    else:
        yield path or "value", _scalar(value)


def _table(headers, rows):
    rows = list(rows)
    if not rows:
        return "None supplied."
    def cell(value):
        return _scalar(value).replace("|", "\\|").replace("\r", "").replace("\n", "<br>")
    return "\n".join(["| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
        *("| " + " | ".join(cell(value) for value in row) + " |" for row in rows)])


def _complete_feedback(value):
    """Return complete recorded diagnostics without semantic field filtering."""
    return '```json\n' + json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n```'


def _values(value):
    if isinstance(value, Mapping) and value.get('feedback') is not None:
        ordinary = {key: child for key, child in value.items() if key != 'feedback'}
        parts = [_table(("Field", "Supplied value"), _rows(_safe(ordinary)))] if ordinary else []
        parts.extend(['Complete returned feedback', _complete_feedback(value['feedback'])])
        return '\n\n'.join(parts)
    return _table(("Field", "Supplied value"), _rows(_safe(value)))


def _section(parts, title, content):
    if content is not None:
        parts.extend(["", title, "", content])


def _pick(value, fields):
    return {name: value[name] for name in fields if name in value} if isinstance(value, Mapping) else {}


def _references(value):
    if isinstance(value, Mapping):
        for name, child in value.items():
            if (name == "id" or name == "ref" or name.endswith("_ref")) and isinstance(child, str):
                yield child
            elif (name.endswith("_refs") or name == "dependencies") and isinstance(child, (list, tuple)):
                yield from (ref for ref in child if isinstance(ref, str))
            yield from _references(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _references(child)


