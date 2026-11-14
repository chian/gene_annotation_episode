"""Exact original engineered amount source and actual Store setup."""
from copy import deepcopy
from ..state import Store
from gene_annotation_episode.episodic_workflow.root.receiving_context import BindingContext
from gene_annotation_episode.episodic_workflow.root.a106.library.literature_amount_inputs import LITERAL_FIELDS

SOURCE = "source_" + "1" * 24

ARTIFACT = "artifact_" + "1" * 24

TEXT = ("The same unnamed stock: target estimated by band intensity at an approximate concentration of 5 mg/ml; "
        "total protein estimated by Bradford analysis at 7 mg/ml. Separate nominal arms use 8.4 uM HFP and 8.8 uM IMP.")

def witness(text, quote, *, reference=SOURCE, occurrence=0):
    start = -1
    for _ in range(occurrence + 1):
        start = text.index(quote, start + 1)
    return {"source_ref": reference, "representation": "original", "start": len(text[:start].encode()),
        "end": len(text[:start + len(quote)].encode()), "quote": quote}

def meaning(value, text=TEXT, quote="same unnamed stock"):
    return {"value": value, "witnesses": [] if value in ("unknown", "unreported") else [witness(text, quote)]}

def selected(text, quote, number, unit, role, *, qualification="reported_point"):
    return {**dict.fromkeys(LITERAL_FIELDS),
        "measurement": {"number": {"witness": witness(text, quote), "number_start": quote.index(number),
            "number_end": quote.index(number) + len(number)},
            "unit": witness(text, unit, occurrence=text[:text.index(quote)].count(unit)) if unit else None},
        "amount_role": meaning(role, text, quote), "amount_kind": meaning("estimated", text, quote),
        "qualification": meaning(qualification, text, quote), "basis_status": meaning("supported", text, quote),
        "reported_uncertainty": {"kind": meaning("unreported"), "statement": None}}

def fixture(text=TEXT, first="5 mg/ml", second="7 mg/ml", n="5", d="7", nunit="mg/ml", dunit="mg/ml"):
    args = {"source_ref": SOURCE, "source_kind": "synthetic_fixture", "experiment": None, "intended_change": None,
        "comparison_kind": meaning("stock_target_mass_estimate_over_total_mass_estimate", text, first),
        "pair_relationship": meaning("supported", text, first), "stock_relationship": meaning("same", text, first),
        "quantities": {
            "numerator": selected(text, first, n, nunit, "target_mass_estimate"),
            "denominator": selected(text, second, d, dunit, "total_protein_mass_estimate")},
        "covariance_source_ref": None}
    sources = {SOURCE: {"artifact_ref": ARTIFACT, "content": text.encode()}}
    def reader(reference, representation):
        assert representation in ("original", "text")
        return deepcopy(sources[reference])
    return args, sources, reader

def setup(path, *, text=TEXT, arguments=None):
    store = Store(path)
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    artifact = store.artifact(text, "text/plain")
    source = store.put("source", {"provider": "synthetic_amount_fixture", "accession": None, "uri": None,
        "artifact_ref": artifact, "text_ref": artifact, "request_ref": None,
        "version": None, "retrieved_at": None}, origin="caller")["id"]
    args = deepcopy(arguments) if arguments is not None else fixture()[0]
    def replace_source(value):
        if isinstance(value, dict):
            return {key: replace_source(child) for key, child in value.items()}
        if isinstance(value, list):
            return [replace_source(child) for child in value]
        return source if value == SOURCE else value
    args = replace_source(args)
    context = BindingContext("amount-run", "amount-child", "literature", (("literature", "case"),),
        store.validate_scope(), {"version": "literature_assignment_v1", "question_context_refs": [],
            "source_refs": [source]}, {}, [source])
    return store, context, args
