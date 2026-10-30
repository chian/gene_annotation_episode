"""Additive check: canonical clauses, absorption, and noninflated coverage.

Complements check_reducer_arithmetic_001.py. The first checker computes coverage
from distinct referenced leaves; the proposal's final coverage definition uses
the absorbed normal form below. No earlier result is rewritten.
"""

import itertools
import json
from pathlib import Path


def canonical_routes(node, aliases=None):
    aliases = aliases or {}
    if isinstance(node, str):
        return frozenset({frozenset({aliases.get(node, node)})})
    assert len(node) == 1
    op, children = next(iter(node.items()))
    assert children and op in {"all_of", "any_of"}
    child_routes = [canonical_routes(c, aliases) for c in children]
    if op == "any_of":
        routes = set().union(*child_routes)
    else:
        routes = {frozenset().union(*r) for r in itertools.product(*child_routes)}
    return frozenset(r for r in routes if not any(s < r for s in routes))


def evaluate(routes, bounds):
    lows = [min(bounds[x][0] for x in route) for route in routes]
    highs = [min(bounds[x][1] for x in route) for route in routes]
    return [max(lows), max(highs)]


forms = {
    "A": "A",
    "duplicate": {"any_of": ["A", "A"]},
    "synonym": {"all_of": ["A", "A_alias"]},
    "absorption_or": {"any_of": ["A", {"all_of": ["A", "B"]}]},
    "absorption_and": {"all_of": ["A", {"any_of": ["A", "B"]}]},
    "distributed": {"any_of": [{"all_of": ["A", "B"]}, {"all_of": ["A", "C"]}]},
    "factored": {"all_of": ["A", {"any_of": ["B", "C"]}]},
}
routes = {name: canonical_routes(form, {"A_alias": "A"}) for name, form in forms.items()}
for name in ("duplicate", "synonym", "absorption_or", "absorption_and"):
    assert routes[name] == routes["A"]
    assert set().union(*routes[name]) == {"A"}
assert routes["distributed"] == routes["factored"]

checks = 0
for a, b, c in itertools.product([-1.0, -0.4, 0.0, 0.72, 1.0], repeat=3):
    bounds = {"A": [a, a], "B": [b, b], "C": [c, c]}
    for name in ("duplicate", "synonym", "absorption_or", "absorption_and"):
        assert evaluate(routes[name], bounds) == [a, a]
        checks += 1
    assert evaluate(routes["distributed"], bounds) == evaluate(routes["factored"], bounds)
    checks += 1

# An unknown absorbed statement does not lower coverage or cause unavailable output.
unknown = {"A": [0.72, 0.72], "B": [-1.0, 1.0]}
assert evaluate(routes["absorption_or"], unknown) == [0.72, 0.72]
assert evaluate(routes["absorption_and"], unknown) == [0.72, 0.72]

result = {
    "status": "passed_synthetic_only",
    "equivalence_comparisons": checks,
    "canonical_routes": {k: sorted(sorted(r) for r in v) for k, v in routes.items()},
    "absorption_example": {
        "A": 0.72,
        "B": None,
        "A_OR_A_AND_B": 0.72,
        "A_AND_A_OR_B": 0.72,
        "unique_essential_statement_count": 1,
        "complete_essential_statement_count": 1,
        "coverage_fraction": 1.0,
    },
}
(Path(__file__).resolve().parent / "semantic_arithmetic_002.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result))
