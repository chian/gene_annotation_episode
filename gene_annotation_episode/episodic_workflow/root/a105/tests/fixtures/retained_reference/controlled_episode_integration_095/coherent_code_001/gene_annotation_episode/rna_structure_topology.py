"""Exact nested RNA topology from supplied dot-bracket text.

This module evaluates no thermodynamic model. Pair endpoints are zero-based
indices; exposed intervals are half open. Crossing pairs are recognized only
to report unsupported input, never reduced to a nested subset.
"""
from __future__ import annotations

from .rna_structure_contracts import COORDINATE_SYSTEM, issue


def parse_rna_topology(dot_bracket: str, *, coordinate_system: str) -> dict:
    """Return all immediate pair, maximal stem and exposed-region relationships.

    Scientific string errors are typed issues. Wrong Python/container types or
    coordinate conventions raise a fixed contract error. No input is trimmed,
    repaired or resized, including the original-to-analysis position identity.
    """
    if type(dot_bracket) is not str or coordinate_system != COORDINATE_SYSTEM:
        raise ValueError("rna_invalid_input_schema")
    result = {"schema": "rna_topology_v1", "coordinate_system": coordinate_system,
        "dot_bracket": dot_bracket, "length_nt": len(dot_bracket),
        "status": "invalid", "positions": None, "pairs": None, "stems": None,
        "regions": None, "issues": []}

    def failure(code, index=None, *, unsupported=False):
        result["status"] = "unsupported" if unsupported else "invalid"
        result["issues"] = [issue(code, stage="input", field="/dot_bracket", index=index)]
        return result

    if not dot_bracket:
        return failure("rna_empty_structure")
    matches = {")": "(", "]": "[", "}": "{"}
    stack, endpoints = [], []
    first_crossing = None
    for index, token in enumerate(dot_bracket):
        if token not in ".()[]{}":
            return failure("rna_invalid_structure_symbol", index)
        if token in "([{":
            stack.append((index, token))
        elif token in matches:
            if not stack:
                return failure("rna_unbalanced_structure", index)
            if stack[-1][1] == matches[token]:
                left, _ = stack.pop()
            else:
                # A matching opener below another open pair implies a crossing
                # only if the whole typed bracket string later balances.
                location = next((k for k in range(len(stack) - 1, -1, -1)
                    if stack[k][1] == matches[token]), None)
                if location is None:
                    return failure("rna_mismatched_bracket", index)
                left, _ = stack.pop(location)
                if first_crossing is None:
                    first_crossing = index
            endpoints.append((left, index))
    if stack:
        return failure("rna_unbalanced_structure", stack[-1][0])
    if first_crossing is not None:
        return failure("rna_crossing_pairs_unsupported", first_crossing, unsupported=True)

    pairs, nesting, by_key, stems, by_stem = [], [], {}, [], {}
    for left, right in sorted(endpoints):
        while nesting and nesting[-1]["j"] < left:
            nesting.pop()
        parent = nesting[-1] if nesting else None
        key = f"pair:{left}:{right}"
        adjacent = parent is not None and left == parent["i"] + 1 and right == parent["j"] - 1
        stem_key = parent["stem_key"] if adjacent else f"stem:{left}:{right}"
        pair = {"pair_key": key, "i": left, "j": right,
            "opening_token": dot_bracket[left], "closing_token": dot_bracket[right],
            "parent_pair_key": parent["pair_key"] if parent else None,
            "child_pair_keys": [], "stem_key": stem_key}
        if parent:
            parent["child_pair_keys"].append(key)
        if not adjacent:
            stem = {"stem_key": stem_key, "pair_keys": [],
                "outer_pair": [left, right], "inner_pair": [left, right]}
            stems.append(stem)
            by_stem[stem_key] = stem
        by_stem[stem_key]["pair_keys"].append(key)
        by_stem[stem_key]["inner_pair"] = [left, right]
        pairs.append(pair)
        by_key[key] = pair
        nesting.append(pair)

    regions = []

    def add_region(pair, children, kind):
        start, end = (pair["i"] + 1, pair["j"]) if pair else (0, len(dot_bracket))
        intervals = []
        cursor = start
        for child in children:
            if cursor < child["i"]:
                intervals.append([cursor, child["i"]])
            cursor = child["j"] + 1
        if cursor < end:
            intervals.append([cursor, end])
        sides = kind in ("bulge", "internal")
        regions.append({"region_key": f"region:{pair['i']}:{pair['j']}" if pair else "region:exterior",
            "kind": kind, "closing_pair_key": pair["pair_key"] if pair else None,
            "immediate_branch_pair_keys": [p["pair_key"] for p in children],
            "unpaired_intervals": intervals,
            "unpaired_indices": [i for a, b in intervals for i in range(a, b)],
            "five_prime_unpaired_indices": list(range(start, children[0]["i"])) if sides else None,
            "three_prime_unpaired_indices": list(range(children[0]["j"] + 1, end)) if sides else None})

    for pair in pairs:
        children = [by_key[key] for key in pair["child_pair_keys"]]
        if not children:
            kind = "hairpin"
        elif len(children) > 1:
            kind = "multibranch"
        else:
            five = children[0]["i"] - pair["i"] - 1
            three = pair["j"] - children[0]["j"] - 1
            if not five and not three:
                continue  # A stack edge has no exposed region of its own.
            kind = "internal" if five and three else "bulge"
        add_region(pair, children, kind)
    add_region(None, [p for p in pairs if p["parent_pair_key"] is None], "exterior")
    paired = {i: pair for pair in pairs for i in (pair["i"], pair["j"])}
    exposed = {i: region["region_key"] for region in regions for i in region["unpaired_indices"]}
    positions = []
    for index, bracket in enumerate(dot_bracket):
        pair = paired.get(index)
        positions.append({"index": index, "input_index": index, "bracket": bracket,
            "partner_index": (pair["j"] if index == pair["i"] else pair["i"]) if pair else None,
            "pair_key": pair["pair_key"] if pair else None,
            "stem_key": pair["stem_key"] if pair else None,
            "unpaired_region_key": exposed.get(index)})
    result.update(status="valid", positions=positions, pairs=pairs, stems=stems, regions=regions)
    return result
