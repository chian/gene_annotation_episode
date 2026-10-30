"""Freeze old results once; compare the complete current result/error without rewriting them."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from gene_annotation_episode.blast_pssm_calculators import calculate_blast_pssm_components
from gene_annotation_episode.blast_pssm_inputs import read_blast_pssm
from tests.test_blast_pssm_calculators import model

BASE = Path(__file__).resolve().parent
SOURCES = ROOT / "verification/tool_graders_blast_pssm_2026-10-26_306/sources"
BASELINE = BASE / "calculator_baseline.json"


def read(text):
    return read_blast_pssm(text.encode(), format="scoremat_asn_text",
                          artifact_key="synthetic:comparison", source_ref="synthetic:319")


def cases():
    out = []
    def add(name, sheet, origin="synthetic"):
        out.append(dict(name=name, origin=origin, sheet=sheet))
    for name in ("pssm_freq_ratios.asn", "pssm_zero_fratios.asn"):
        add(name, read_blast_pssm((SOURCES / name).read_bytes(), format="scoremat_asn_text",
            artifact_key="retained:" + name, source_ref="pinned-primary-source"), "retained_upstream_native_input")
    add("default", read(model()))
    for encoding in ('iupacaa "ACD"', 'ncbieaa "ACD"', "ncbistdaa '010304'H",
                     'ncbieaa "A-D"', "ncbistdaa '010004'H", 'ncbieaa "UOJ*"',
                     "ncbistdaa '0103FF'H", "ncbistdaa '0103F'H", "ncbistdaa '010304'B",
                     "ncbi8aa '010304'H", 'iupacaa "AcD"', 'iupacaa "A-D"'):
        add("encoding:" + encoding, read(model(f"query seq {{ inst {{ length 3, seq-data {encoding} }} }}, ", query=False)))
    for query in ('seq { inst { seq-data iupacaa "ACD" } }',
                  'seq { inst { length 4, seq-data iupacaa "ACD" } }',
                  'seq { inst { length -1, seq-data iupacaa "ACD" } }',
                  'seq { inst { length 3, length 3, seq-data iupacaa "ACD" } }',
                  'seq { inst { repr delta, length 3, seq-data iupacaa "ACD" } }',
                  'seq { inst { mol dna, length 3, seq-data iupacaa "ACD" } }',
                  'seq { inst { length 3, seq-data { iupacaa "ACD", ncbieaa "ACD" } } }',
                  'set { seq-set { seq { inst { length 3, seq-data iupacaa "ACD" } } } }',
                  'seq { inst 1 }', 'seq { }', 'other { }'):
        add("query:" + query, read(model("query " + query + ", ", query=False)))
    for body in ("isProtein FALSE, ", "isProtein 1, ", "byRow TRUE, ", "byRow 1, "):
        add("body:" + body, read(model(body)))
    for replacement in ("numColumns 4", "numColumns 0", "numColumns FALSE", "numColumns 3, numColumns 3"):
        add("columns:" + replacement, read(model().replace("numColumns 3", replacement)))
    for name, text in (("missing-master", model(query=False)), ("empty", ""),
                       ("truncated", model()[:-3]), ("multiple", model() + "\n" + model(query=False)),
                       ("no-arrays", model(data="")),
                       ("bad-array", model(data="finalData { scores { 1 }, lambda 1e-1000, kappa 1, h 0 }"))):
        add(name, read(text))
    for format, raw in (("ascii_pssm", b"unsupported text"), ("scoremat_asn_binary", b"\xff")):
        add(format, read_blast_pssm(raw, format=format, artifact_key="unsupported", source_ref="synthetic:319"))
    mutations = {
        "sheet-schema": lambda s: s.update(schema="wrong"),
        "sheet-field": lambda s: s.update(extra=None),
        "records-type": lambda s: s.update(pssms={}),
        "record-field": lambda s: s["pssms"][0].update(extra=None),
        "record-native": lambda s: s["pssms"][0].update(native_pssm=[]),
        "record-tree": lambda s: s["pssms"][0].update(native_record=[]),
        "record-params": lambda s: s["pssms"][0].update(native_params=[]),
        "record-ordinal": lambda s: s["pssms"][0].update(record_ordinal=True),
        "record-key": lambda s: s["pssms"][0].update(pssm_key="wrong"),
        "record-issues": lambda s: s["pssms"][0].update(issues=[{"code": "wrong"}]),
        "record-duplicate": lambda s: s["pssms"].append(deepcopy(s["pssms"][0])),
    }
    for name, change in mutations.items():
        sheet = read(model())
        change(sheet)
        add(name, sheet)
    return out


def observe(sheet):
    before = deepcopy(sheet)
    try:
        answer = {"result": calculate_blast_pssm_components(sheet)}
    except Exception as error:
        answer = {"error_type": type(error).__name__, "error_args": list(error.args)}
    assert sheet == before, "calculator mutated input"
    return answer


def identity(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))


calculator = ROOT / "gene_annotation_episode/blast_pssm_calculators.py"
if sys.argv[1] == "baseline":
    records = [{**case, "expected": observe(case["sheet"])} for case in cases()]
    with BASELINE.open("x") as handle:
        json.dump(dict(calculator_source=identity(calculator), cases=records), handle, indent=2, allow_nan=False)
        handle.write("\n")
    paths = [calculator, ROOT / "gene_annotation_episode/blast_pssm_inputs.py",
        ROOT / "gene_annotation_episode/blast_iteration_inputs.py", ROOT / "gene_annotation_episode/blast_iteration_calculators.py",
        ROOT / "verification/tool_graders_native_blast_database_result_contract_2026-10-26_314/CONTRACT_ADDENDUM_002.md",
        Path("/home/chia/.codex/attachments/e94d8875-9d86-482e-9bb3-8887aa457b88/pasted-text-1.txt")]
    paths.extend(SOURCES / name for name in ("pssm_freq_ratios.asn", "pssm_zero_fratios.asn", "scoremat.asn", "seqport_util.cpp", "MANIFEST.json", "MANIFEST_002.json"))
    with (BASE / "source_hashes_before.json").open("x") as handle:
        json.dump([identity(path) for path in paths], handle, indent=2)
        handle.write("\n")
    print(json.dumps(dict(baseline=str(BASELINE), case_count=len(records), baseline_identity=identity(BASELINE))))
else:
    baseline = json.loads(BASELINE.read_text())
    mismatches = [case["name"] for case in baseline["cases"] if observe(case["sheet"]) != case["expected"]]
    result = dict(case_count=len(baseline["cases"]), mismatches=mismatches,
        old_calculator_source=baseline["calculator_source"], new_calculator_source=identity(calculator),
        baseline_identity=identity(BASELINE))
    with (BASE / "calculator_comparison.json").open("x") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps(result))
    raise SystemExit(bool(mismatches))
