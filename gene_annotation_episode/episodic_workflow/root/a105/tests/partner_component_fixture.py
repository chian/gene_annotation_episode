"""Original synthetic partner input, produced by its actual A107 owner.

Used only to check A105 consumption of source-qualified partner components.
No partner scientific implementation is copied into A105 application code.
"""
import json
from gene_annotation_episode.episodic_workflow.root.a107.state import Store
from gene_annotation_episode.episodic_workflow.root.a107.episode_bindings import BindingContext
from gene_annotation_episode.episodic_workflow.root.a107.literature_partner_storage import BINDINGS

def source(store, content, *, parents=(), text=False):
    artifact = store.artifact(content)
    return store.put("source", {"provider": "synthetic_partner_fixture", "accession": None,
        "uri": None, "artifact_ref": artifact, "text_ref": artifact if text else None,
        "request_ref": None, "version": None, "retrieved_at": None,
        "parent_source_refs": list(parents)}, origin="caller")

def arm(role, value):
    return {"subject_ref": "synthetic_subject", "partner_ref": "synthetic_partner",
        "partner_state": "absent" if role == "omitted" else "present",
        "endpoint_ref": "synthetic_product", "normalization_ref": "per_mg_subject",
        "unit": "pmol/min/mg", "conditions": {"coverage": "complete", "factors": [
            {"factor": "nitrogen_source", "level": "glutamine", "unit": "identity"},
            {"factor": "temperature", "level": 37, "unit": "degC"}]},
        "measurement": {"measurement_id": "synthetic_measurement_" + role,
            "status": "observed", "value": value, "origin": "synthetic",
            "spread": {"kind": "unreported", "magnitude": None}}}

def fixture(path, *, page=False, mode="matched"):
    store = Store(path)
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    records = {"ancestor": source(store, "Synthetic provenance.")}
    records["root"] = source(store, b"\xff\x00Synthetic binary paper.", parents=[records["ancestor"]["id"]])
    root = records["root"]["id"]
    text = "Subject|Partner|Experiment|Endpoint|Normalization|Reference condition|Omission condition|Addback condition|Function"
    records["literal"] = source(store, text, parents=[root], text=True)
    quote = "Synthetic condition and measurement interpretations."
    records["interpretation"] = source(store, quote, parents=[root])
    document = {"version": "literature_partner_selection_v1", "inputs": {
        "version": "literature_partner_inputs_v1", "arms": {
            role: arm(role, value) for role, value in (("reference", 100), ("omitted", 20), ("addback", 90))}}}
    arms = document["inputs"]["arms"]
    if mode == "censored":
        arms["omitted"]["measurement"].update(status="upper_bound", value=5)
    elif mode == "crossed":
        arms["reference"]["measurement"].update(value=774, spread={"kind": "unspecified", "magnitude": 58})
        arms["omitted"]["measurement"].update(value=284, spread={"kind": "unspecified", "magnitude": 33})
        for role in ("reference", "omitted"):
            arms[role]["normalization_ref"] = None
            arms[role]["conditions"]["coverage"] = "partial"
        arms["omitted"]["conditions"]["factors"][0]["level"] = "ammonium_sulfate"
        arms["addback"] = None
    elif mode == "missing":
        arms["addback"] = None
    elif mode == "all_missing":
        document["inputs"]["arms"] = dict.fromkeys(("reference", "omitted", "addback"))
    records["recipe"] = source(store, json.dumps(document), parents=[root])
    literals, offset = {}, 0
    for (literal, _), text_quote in zip(BINDINGS.values(), text.split("|")):
        literals[literal] = {"source_ref": records["literal"]["id"], "representation": "text",
            "start": offset, "end": offset + len(text_quote), "quote": text_quote}
        offset += len(text_quote) + 1
    args = {"source_ref": root, "data_source_ref": records["recipe"]["id"],
        "source_kind": "synthetic_fixture", "literals": literals,
        "interpretation_witnesses": [{"source_ref": records["interpretation"]["id"],
            "representation": "original", "start": 0, "end": len(quote), "quote": quote}]}
    context = BindingContext("synthetic-partner-run", "partner-child", "literature",
        (("literature", "fixture"),), store.validate_scope(),
        {"page": {"source_ref": root}} if page else {}, {},
        tuple(row["id"] for key, row in records.items() if key != "ancestor"))
    return store, context, args, records, document
