"""Mechanical lexical guard diagnosis; does not interpret new paper context."""
import hashlib
import json
from pathlib import Path
import re

from gene_annotation_episode.literature_assay_inputs import _Sources
from gene_annotation_episode.literature_amount_inputs import LEXICAL_DEPENDENCY, _amount_number
from gene_annotation_episode.literature_rate_native_inputs import _field_contexts
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.state import Store


OUT = Path(__file__).resolve().parent
PATTERNS = [
    r"\b(?:between|from|range|interval|CI|confidence\s+interval)\s*[:=]?\s*[\[(]?\s*$",
    r"\bbetween\b[^;\n]*\band\s*$",
    r"\d\s*(?:[–—−-]|\bto)\s*$",
    r"\s*(?:[–—−-]|\bto\b)\s*[+−-]?(?:\d|\.\d)",
]


def main():
    report = json.loads((OUT / "CASE025_POPULATED_001.json").read_text())
    selected = report["outputs"]["nominal_arms"]["selection"]
    results = []
    with Store(OUT / "case025_replay_state_001") as store:
        def read(reference, representation):
            source = store.get(reference)
            artifact = source["artifact_ref"] if representation == "original" else source["text_ref"]
            return {"artifact_ref": artifact, "content": store.get_artifact(artifact)}
        sources = _Sources(read)
        for role, quantity in selected["quantities"].items():
            selector = quantity["measurement"]["number"]
            witness = sources.witness(selector["witness"], role)
            prefix, suffix = _field_contexts(sources, witness, selector["number_start"], selector["number_end"])
            try:
                number = _amount_number(selector, sources)
                error = None
            except ExperimentalContractError as exc:
                number, error = None, {"code": exc.code, "field": exc.field}
            matches = []
            for index, pattern in enumerate(PATTERNS):
                context = suffix if index == 3 else prefix
                match = re.match(pattern, context) if index == 3 else re.search(pattern, context, re.I)
                if match:
                    matches.append({"pattern_index": index, "pattern": pattern,
                        "context": "suffix" if index == 3 else "prefix", "match_start": match.start(), "match_end": match.end()})
            results.append({"role": role, "witness": witness, "number_start": selector["number_start"],
                "number_end": selector["number_end"], "parsed": number, "error": error, "matching_interval_guards": matches,
                "private_full_field_context": {"prefix": prefix, "suffix": suffix},
                "context_sha256": hashlib.sha256((prefix + "\0" + suffix).encode()).hexdigest()})
    artifact = {"version": "amount027_nominal_guard_diagnostic_001", "lexical_dependency": LEXICAL_DEPENDENCY,
        "source_sha256": report["source_sha256"], "scientific_classification": "unclassified_pending_required_reset_if_new_context_is_interpreted",
        "source_context_emitted_to_conversation": False, "new_scientific_interpretation": False,
        "guard_owner": "literature_partner_source_fields._relation called by released native _number",
        "results": results}
    (OUT / "NOMINAL_GUARD_DIAGNOSTIC_001.json").write_text(json.dumps(artifact, indent=2) + "\n")
    print(json.dumps([{key: row[key] for key in ("role", "error", "matching_interval_guards", "context_sha256")} for row in results], indent=2))


if __name__ == "__main__":
    main()
