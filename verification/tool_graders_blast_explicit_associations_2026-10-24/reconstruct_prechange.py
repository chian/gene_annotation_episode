"""Reconstruct pre-H1 bytes and require the hash captured before any edits.

This writes only the verification copy. The production module is never replaced.
The exact original hash is also retained in legacy_prechange.json.
"""
import hashlib
import json
from pathlib import Path

directory = Path(__file__).resolve().parent
source = directory.parents[1] / "gene_annotation_episode/blast_database_grader.py"
text = source.read_text()


def replace(old, new=""):
    global text
    if text.count(old) != 1:
        raise ValueError("Expected one exact additive-edit marker: " + old[:80])
    text = text.replace(old, new, 1)


def remove_between(start, end):
    global text
    begin = text.index(start)
    finish = text.index(end, begin)
    text = text[:begin] + text[finish:]


replace('import re\n\nfrom .blast_search import PROGRAM_UNITS\n')
remove_between('\n_DESCRIPTION_BINDING_FIELDS = ', '\n\n\ndef _number')
remove_between('\n\ndef _index(', '\n\ndef _union_length(')
replace('    return _summarize_sequence_groups(hits, groups.values(), tokens_per_hit)\n\n\ndef _summarize_sequence_groups(hits, membership, tokens_per_hit):\n    """Keep the existing once-per-sequence numerical summaries for both paths."""\n')
replace('enumerate(sorted(membership, key=lambda values: min(values)))',
        'enumerate(sorted(groups.values(), key=lambda values: min(values)))')
remove_between('\n\ndef _explicit_sequence_groups(', '\n\ndef _taxonomy_summary(')
replace('                         database_profile: dict | None = None,\n                         description_bindings: list[dict] | None = None,\n                         sequence_identity_bindings: list[dict] | None = None) -> dict:',
        '                         database_profile: dict | None = None) -> dict:')
replace('\n    Both binding arguments omitted preserves the legacy matcher and grouping.\n    Supplying both lists selects exact original-ordinal metadata links and only\n    supplied full-sequence identities for cross-hit grouping. These functions\n    check the supplied relationships; the caller owns artifact/episode custody\n    and validating each full-sequence record\'s relation to the actual operand.\n')
replace('    if (description_bindings is None) != (sequence_identity_bindings is None):\n        raise ValueError("blast_explicit_binding_pair_required")\n    explicit = description_bindings is not None\n')
replace('    if explicit:\n        report, indexed_hits, descriptions, description_bindings, sequence_identity_bindings = _explicit_inputs(\n            normalized, description_bindings, sequence_identity_bindings, issues)\n        description_links = _description_links(description_bindings, metadata, report, indexed_hits, descriptions, issues)\n        sequence_links = _sequence_links(sequence_identity_bindings, normalized, report, indexed_hits, issues)\n')
replace('        associations = (_attach_explicit_metadata(native_hit, metadata, descriptions, description_links, matched, issues)\n                        if explicit else _attach_metadata(native_hit, metadata, matched, issues))\n',
        '        associations = _attach_metadata(native_hit, metadata, matched, issues)\n')
replace('        if explicit:\n            hits[-1]["source_locator"] = deepcopy(native_hit.get("source_locator"))\n    groups = _explicit_sequence_groups(hits, sequence_links, issues) if explicit else _sequence_groups(hits, issues)\n',
        '    groups = _sequence_groups(hits, issues)\n')
replace('    if explicit:\n        output.update(association_mode="explicit_bindings_v1",\n                      description_bindings=description_bindings,\n                      sequence_identity_bindings=sequence_identity_bindings)\n')
replace('    if (sheet.get("association_mode") == "explicit_bindings_v1"\n            and sheet.get("dependence", {}).get("unknown_cross_hit_sequence_identity") is True):\n        result["assumptions"].append(\n            "Unresolved returned native-hit groups are counted as separate model components; "\n            "this modeling choice is not measured sequence identity or evidence of independent experiments.")\n')
expected = json.loads((directory / "legacy_prechange.json").read_text())["provenance"]["module_sha256"]
actual = hashlib.sha256(text.encode()).hexdigest()
if actual != expected:
    raise ValueError(f"Reconstructed bytes do not match the recorded original: {actual} != {expected}")
output = directory / "blast_database_grader.prechange.py"
output.write_text(text)
print(json.dumps({"verified_prechange_sha256": actual, "bytes": output.stat().st_size}))
