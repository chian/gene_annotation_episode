"""Original source-bound product-partition number reader."""
from copy import deepcopy
from fractions import Fraction
import math
import re
from gene_annotation_episode.episodic_workflow.root.literature_assay_inputs import _fail, _index
from gene_annotation_episode.episodic_workflow.root.library.literature_partner_source_fields import _NUMBER, _relation
from gene_annotation_episode.episodic_workflow.root.library.literature_rate_native_inputs import _field_contexts, _APPROX, _UPPER, _LOWER

def _number(selection, sources):
    """Fraction scalar syntax; shared lexical guards, with explicit percent units.

    The older rate scalar deliberately rejects percentages. This reader retains
    that dimension and its bounds rather than relabeling it as a rate.
    """
    witness = sources.witness(selection["witness"], "number.witness")
    start, end = selection["number_start"], selection["number_end"]
    _index(start, "number_start"); _index(end, "number_end")
    if not 0 <= start < end <= len(witness["quote"]):
        _fail("source_number_span_order_invalid", "number")
    token = witness["quote"][start:end]
    if not _NUMBER.fullmatch(token):
        _fail("literal_source_number_required", "number")
    prefix, suffix = _field_contexts(sources, witness, start, end)
    operator = r"(?:[/×⋅·*+^]|\btimes\b|\bx\b)"
    if (re.search(r"\d\s*" + operator + r"\s*$", prefix, re.I) or
            re.match(r"\s*" + operator + r"\s*[+−-]?(?:\d|\.\d)", suffix, re.I)):
        _fail("source_arithmetic_expression_unsupported", "number")
    remaining, relations, approximate = prefix, [], False
    while True:
        approx, upper, lower = _APPROX.search(remaining), _UPPER.search(remaining), _LOWER.search(remaining)
        if approx:
            approximate = True; remaining = remaining[:approx.start()]
        elif upper or lower:
            match = upper or lower
            marker = re.sub(r"\s+", " ", match.group(1).lower())
            inclusive = marker in ("<=", "≤", "at most", "no more than", ">=", "≥", "at least", "no less than") or "equal" in marker
            relations.append(("l" if upper else "g") + ("e" if inclusive else "t"))
            remaining = remaining[:match.start()]
        else:
            break
    if len(set(relations)) > 1:
        _fail("composite_source_comparator_unsupported", "number")
    if re.search(r"\bnot\s*(?:(?:significantly|substantially|clearly)\s*)?$", remaining, re.I):
        _fail("negated_source_comparator_unsupported", "number")
    if re.search(r"(?:±|\+\s*/\s*-)\s*$", remaining) or re.search(r"\b(?:SD|SEM|standard deviation|standard error)\s*[:=]?\s*$", remaining, re.I):
        _fail("uncertainty_is_not_fraction_point", "number")
    relation = _relation(remaining, suffix, role="condition")
    before, after = prefix[-1:], suffix[:1]
    stop = after == "." and (len(suffix) == 1 or suffix[1].isspace() or suffix[1] in ")]};:")
    if (before and (before.isalnum() or before in ".eE+−-_") or
            after and (after in ".eE+−-" or after.isdigit()) and not stop):
        _fail("partial_source_numeric_token", "number")
    if re.search(r"\d,\s*$", prefix) or re.match(r",\s*\d", suffix):
        _fail("comma_source_number_unsupported", "number")
    value = float(token.replace("−", "-"))
    if not math.isfinite(value) or value == 0 and Fraction(token.replace("−", "-")) != 0:
        _fail("numerical_model_range", "number")
    return {"selector": {**deepcopy(selection), "witness": witness}, "raw_number": token,
            "value": value, "relation": relations[0] if relations else relation, "approximate": approximate}


