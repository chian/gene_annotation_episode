"""Bounded source-verification probe; not a production grader or fixture result."""
from pathlib import Path
import importlib
import importlib.metadata
import json
import sys
import traceback

root = Path.cwd()
records = []

def record(kind, **data):
    value = {"kind": kind, **data}
    records.append(value)
    print(json.dumps(value, sort_keys=True, allow_nan=False), flush=True)

record("interpreter", executable=sys.executable, version=sys.version)
for package in ("ViennaRNA", "biomni"):
    try:
        record("distribution", package=package, version=importlib.metadata.version(package))
    except Exception as exc:
        record("distribution", package=package, error_type=type(exc).__name__, error=str(exc))

for module_name in ("RNA", "biomni.tool.microbiology", "biomni.tool.biochemistry"):
    try:
        module = importlib.import_module(module_name)
        record("import", module=module_name, path=getattr(module, "__file__", None),
               version=getattr(module, "__version__", None), status="success")
    except Exception as exc:
        record("import", module=module_name, status="failed", error_type=type(exc).__name__, error=str(exc))
        continue
    if module_name == "RNA":
        for sequence in ("GGGAAACCC", "GCGCUUCGCC"):
            try:
                structure, energy = module.fold(sequence)
                record("native_fold", sequence=sequence, dot_bracket=structure,
                       mfe_kcal_mol=energy, uncertainty="not_produced_by_RNA.fold")
            except Exception as exc:
                record("native_fold", sequence=sequence, error_type=type(exc).__name__, error=str(exc))
        try:
            md = module.md()
            record("model_defaults", values={key: getattr(md, key, None) for key in
                ("temperature", "dangles", "noLP", "noGU", "noGUclosure", "special_hp",
                 "logML", "circ", "min_loop_size", "max_bp_span", "gquad", "sfact", "betaScale")})
        except Exception as exc:
            record("model_defaults", error_type=type(exc).__name__, error=str(exc))
    elif module_name == "biomni.tool.microbiology":
        for label, sequence in (("valid", "GGGAAACCC"), ("empty", ""), ("dna", "GGGTTTCCC")):
            try:
                output = module.predict_rna_secondary_structure(sequence, str(root / ("prediction_" + label)))
                record("upstream_predict", label=label, sequence=sequence, complete_return=output)
            except Exception as exc:
                record("upstream_predict", label=label, sequence=sequence,
                       error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
    else:
        cases = [
            ("hairpin", "(((...)))", "GGGAAACCC"),
            ("external_gap", "((...))..((...))", None),
            ("internal_loop", "((..((...))..))", None),
            ("unpaired", "....", "AAAA"),
            ("empty", "", None),
            ("mixed_nested", "[{...}]", None),
            ("crossing", "([..)]", None),
            ("mismatch", "(....]", None),
            ("unbalanced", "(((...))", None),
            ("length_mismatch", "(((...)))", "GGGAAA"),
            ("lowercase", "(((...)))", "gggaaaccc"),
            ("unknown_bases", "(((...)))", "NNNAAANNN"),
            ("empty_sequence", "(((...)))", ""),
        ]
        for label, structure, sequence in cases:
            try:
                output = module.analyze_rna_secondary_structure_features(structure, sequence)
                record("upstream_features", label=label, dot_bracket=structure,
                       sequence=sequence, complete_return=output)
            except Exception as exc:
                record("upstream_features", label=label, dot_bracket=structure, sequence=sequence,
                       error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())

(root / "probe_records.json").write_text(json.dumps(records, indent=2, sort_keys=True, allow_nan=False) + "\n")
