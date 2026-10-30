"""Save complete A1 examples and provenance, reusing259 native executions."""
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from test_hmmer_artifact_data import native_case, populate, payload, NATIVE, BUNDLE_ROLES
from gene_annotation_episode.hmmer_artifact_calculations import calculate_hmmer_artifact_components

HERE = Path.cwd() / "examples"
HERE.mkdir()


def write(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


names = (["hmmconvert_ascii", "hmmconvert_binary", "hmmconvert_legacy2", "hmmconvert_binary_to_ascii"]
    + ["hmmconvert_3"+r for r in "abcde"] + ["hmmconvert_annotated_3"+r for r in "abcdef"]
    + ["hmmfetch_single", "hmmfetch_unindexed_alias", "hmmfetch_indexed_alias", "hmmfetch_unindexed_missing",
       "hmmfetch_indexed_missing", "hmmfetch_duplicate", "hmmfetch_index", "hmmpress_success", "hmmpress_duplicate"])
provenance, summary = [], []
for name in names:
    args = native_case(name)
    operation, inputs, outputs, bindings = args
    sheet = populate(*args)
    result = calculate_hmmer_artifact_components(sheet)
    write(name + "_sheet.json", sheet)
    write(name + "_components.json", result)
    original_receipt = NATIVE / name / "receipt.json"
    receipt = json.loads(original_receipt.read_text())
    paths = {}
    if operation["program"] == "hmmconvert":
        paths["input/models/0"] = Path(receipt["argv"][-1])
        paths["output/converted_models/0"] = NATIVE / name / "stdout.log"
    elif operation["program"] == "hmmfetch" and operation["mode"] != "index":
        paths["input/models/0"] = Path(receipt["argv"][-2])
        paths["output/fetched_models/0"] = NATIVE / name / "stdout.log"
        if operation["mode"] == "key_file":
            paths["input/keys/0"] = Path(receipt["argv"][-1])
        if "ssi" in inputs:
            paths["input/ssi/0"] = NATIVE / "hmmfetch_index/models.hmm.ssi"
    else:
        paths["input/models/0"] = NATIVE / name / "models.hmm"
        if operation["program"] == "hmmfetch":
            paths["output/ssi/0"] = NATIVE / name / "models.hmm.ssi"
        elif name == "hmmpress_success":
            for role,suffix in zip(BUNDLE_ROLES,("h3m","h3i","h3f","h3p")):
                paths["output/"+role+"/0"] = NATIVE / name / ("models.hmm."+suffix)
    paths.update({"output/"+role+"/0":NATIVE / name / (role+".log") for role in ("stdout","stderr")})
    provenance.append({"name":name, "native_receipt":str(original_receipt.relative_to(ROOT)),
        "native_receipt_sha256":digest(original_receipt), "native_argv":receipt["argv"],
        "native_returncode":receipt["returncode"], "native_policy":receipt["policy"],
        "executable_sha256":digest(Path(receipt["argv"][0])),
        "supplied_bindings_qualification":"Supplied from retained259 associations; this pure port does not authenticate producer custody.",
        "occurrences":[{"occurrence_id":oid,"path":str(path.relative_to(ROOT)),"sha256":digest(path),"size_bytes":path.stat().st_size}
                       for oid,path in paths.items()]})
    populations = {r["direction"]:r["decoded_model_count"] for r in result["rows"] if r["kind"] == "population"}
    comparisons = [r for r in result["rows"] if r["kind"] == "model_comparison"]
    item = {"name":name,"native_returncode":receipt["returncode"],"decoded_populations":populations,
        "compared_cells":[r["compared_cell_count"] for r in comparisons],
        "maximum_differences":[r["max_absolute_probability_difference"] for r in comparisons],
        "optional_field_changes":[{key:r[key] for key in ("retained_optional_field_count","lost_optional_field_count",
                                                        "changed_optional_field_count","gained_optional_field_count")} for r in comparisons]}
    for kind in ("key_population","index_summary","bundle"):
        item[kind] = [r for r in result["rows"] if r["kind"] == kind]
    summary.append(item)

operation,inputs,outputs,bindings = native_case("hmmconvert_ascii")
changed = outputs["converted_models"][0]["content"].replace(b"0.40547",b"0.50547",1)
(HERE / "synthetic_changed_probability.hmm").write_bytes(changed)
outputs["converted_models"] = [payload(changed,"converted_models","output")]
outputs["stdout"] = [payload(changed,"stdout","output")]
sheet = populate(operation,inputs,outputs,bindings)
write("synthetic_changed_probability_sheet.json",sheet)
for label,parameters in (("strict",{"probability_tolerance":.001,"expected_revision":"3/f"}),
                         ("relaxed",{"probability_tolerance":.1,"expected_revision":"3/e"})):
    write("synthetic_changed_probability_"+label+"_components.json",calculate_hmmer_artifact_components(sheet,parameters=parameters))
with localcontext() as context:
    context.prec = 60
    delta = abs((-Decimal("0.50547")).exp()-(-Decimal("0.40547")).exp())
    independent = {"qualification":"Synthetic mutation of one supplied native probability token, not a new native execution.",
        "source_token":"0.40547","changed_token":"0.50547","formula":"abs(exp(-changed_token)-exp(-source_token))",
        "expected_max_absolute_difference":str(delta),"expected_mean_absolute_difference":str(delta/Decimal(611)),
        "compared_cell_denominator":611,"denominator_formula":"20 composition + 13*20 insert + 12*20 match + 13*7 transition cells"}
source_files = ["gene_annotation_episode/hmmer_artifact_data.py","gene_annotation_episode/hmmer_artifact_calculations.py",
    "gene_annotation_episode/hmmer_model_data.py","gene_annotation_episode/hmmer_model_calculations.py",
    "tests/test_hmmer_artifact_data.py","tests/test_hmmer_artifact_calculations.py",
    "resources/software/infernal-1.1.5/hmmer/src/hmmconvert.c","resources/software/infernal-1.1.5/hmmer/src/hmmfetch.c",
    "resources/software/infernal-1.1.5/hmmer/src/hmmpress.c","resources/software/infernal-1.1.5/hmmer/src/p7_hmmfile.c",
    "resources/software/infernal-1.1.5/hmmer/src/impl_sse/io.c","resources/software/infernal-1.1.5/easel/esl_ssi.c",
    "resources/software/infernal-1.1.5/easel/esl_fileparser.c"]
write("provenance.json",{"native_examples":provenance,"source_sha256":{path:digest(ROOT/path) for path in source_files}})
write("summary.json",{"native_cases":summary,"independent_changed_probability_expectation":independent})
print(json.dumps({"saved_native_examples":len(names),"directory":str(HERE),"synthetic_expectation":independent}))
