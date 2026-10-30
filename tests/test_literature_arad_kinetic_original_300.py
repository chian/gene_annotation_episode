"""A selected A105 kinetic return from Fan et al. Table 2, with PDF custody.

The PDF extraction flattens superscripts. A pinned XML glyph receipt verifies
their geometry before a narrow, explicitly derived numerical transcription is
passed to the existing literal reader. The original PDF is retained in the
source ancestry. This does not claim direct PDF-typography parsing.
"""
import asyncio
from copy import deepcopy
from functools import partial
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from gene_annotation_episode.communication import validate_form
from gene_annotation_episode.domain import obj
from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_kinetic_storage import LiteratureKineticRepository, kinetic_cells_schema
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "verification/a105_arad3529_primary_case_299/source/P274-JACS-Pterin_Deaminase-2013.pdf"
LAYOUT = ROOT / "verification/a105_arad3529_primary_case_299/source/P274-JACS-Pterin_Deaminase-2013.layout.txt"
GEOMETRY = ROOT / "verification/a105_arad_kinetic_selected_300/source/arad3529.xml"
PINS = {
    PAPER: "620b47080c971b74e30c2c107d704ab24759433fc80326668dc647b4e26b1ae3",
    LAYOUT: "121c98af0d85d16cac70717a48567f6257c526e9901aa5f9ff2508de2b044511",
    GEOMETRY: "54c1f63ffc672e71a83ff63f2911e2c6e6747f77faa936bf93eea5da76b3cb25",
}
FORM = obj({"numbers": kinetic_cells_schema()})
REQUESTED = ["numerator_parameter", "denominator_parameter", "parameter_ratio", "log_parameter_contrast"]


def _geometry_exponent(xml_bytes, label, mantissa_spread, exponent):
    root = ET.fromstring(xml_bytes)
    matches = []
    for page in root.findall("page"):
        nodes = list(page.findall("text"))
        for index, node in enumerate(nodes):
            if "".join(node.itertext()) != label:
                continue
            nearby = nodes[index + 1:index + 5]
            if ["".join(item.itertext()) for item in nearby] != [mantissa_spread, "×", "10", exponent]:
                continue
            mantissa, multiplication, base, power = nearby
            if (int(power.attrib["top"]) < int(base.attrib["top"])
                    and int(power.attrib["height"]) < int(base.attrib["height"])
                    and int(power.attrib["left"]) >= int(base.attrib["left"]) + int(base.attrib["width"])
                    and int(multiplication.attrib["left"]) >= int(mantissa.attrib["left"]) + int(mantissa.attrib["width"])):
                matches.append((page.attrib["number"], dict(base.attrib), dict(power.attrib)))
    assert len(matches) == 1, (label, matches)
    return matches[0]


def _transcription():
    raw = {path: path.read_bytes() for path in PINS}
    assert {path: hashlib.sha256(value).hexdigest() for path, value in raw.items()} == PINS
    assert _geometry_exponent(raw[GEOMETRY], "biopterin", "1.0 (0.1)", "6")[0] == "6"
    assert _geometry_exponent(raw[GEOMETRY], "7,8-dihydrobiopterin", "9.3 (0.5)", "2")[0] == "6"
    original = raw[LAYOUT].decode("utf-8")
    changes = (
        ("biopterin                                1.0 (0.1) × 106",
         "biopterin                                1.0e6 (0.1e6)"),
        ("7,8-dihydrobiopterin                     9.3 (0.5) × 102",
         "7,8-dihydrobiopterin                     9.3e2 (0.5e2)"),
    )
    derived = original
    for before, after in changes:
        assert original.count(before) == 1
        derived = derived.replace(before, after, 1)
    assert derived != original and "× 106" in original and "× 102" in original
    return raw[PAPER], raw[GEOMETRY], derived.encode("utf-8")


class Spans:
    def __init__(self, content, source_ref):
        self.content, self.source_ref = content, source_ref

    def witness(self, quote, occurrence=0):
        token = quote.encode("utf-8")
        start = 0
        for _ in range(occurrence + 1):
            start = self.content.index(token, start)
            end = start + len(token)
            if _ < occurrence:
                start = end
        return {"source_ref": self.source_ref, "representation": "original",
                "start": start, "end": end, "quote": quote}

    def witness_after(self, marker, quote):
        start = self.content.index(quote.encode("utf-8"), self.content.index(marker.encode("utf-8")))
        return {"source_ref": self.source_ref, "representation": "original",
                "start": start, "end": start + len(quote.encode("utf-8")), "quote": quote}

    def number(self, token):
        return {"witness": self.witness(token), "number_start": 0, "number_end": len(token)}


def _selection(spans):
    table_title = "Table 2. Catalytic Constants for Substrates of Arad3529"
    title = spans.witness(table_title)
    header = spans.witness_after(table_title, "kcat/Km")
    unit = spans.witness_after(table_title, "M−1 s−1")
    construct = spans.witness("CHS30")
    organism = spans.witness("Agrobacterium radiobacter Strain K84")
    molecule = spans.witness("Arad3529")
    condition = spans.witness("at pH 7.7")
    def meaning(value, *witnesses):
        return {"value": value, "witnesses": list(witnesses)}
    def operand(label, value, spread):
        row = spans.witness(label + " " * (41 - len(label)) + value + " (" + spread + ")")
        return {"parameter_kind": meaning("catalytic_efficiency", header),
            "subject": {"organism": organism, "genotype": None, "molecule": molecule, "construct": construct},
            "context": {"substrate": spans.witness_after(table_title, label),
                "preparation": None, "experiment": title, "experimental_system": None,
                "conditions": condition, "endpoint": header, "normalization": None},
            "measurement_identity": row,
            "measurement": {"number": spans.number(value), "unit": unit},
            "qualification": meaning("reported_point", row),
            "uncertainty": {"statistic": meaning("unspecified", row), "magnitude": spans.number(spread),
                "interval": None, "unit": None, "unit_relationship": meaning("same_as_parameter", header),
                "confidence_level": None, "count": None,
                "repetition_basis": meaning("unspecified"), "estimate_basis": meaning("unknown")}}
    return {"version": "a105_kinetic_source_selection_v1", "source_ref": spans.source_ref,
        "source_kind": "primary_source", "numerator": operand("biopterin", "1.0e6", "0.1e6"),
        "denominator": operand("7,8-dihydrobiopterin", "9.3e2", "0.5e2"),
        "comparison": {
            "subject_relationship": meaning("same_molecule_and_construct", title, construct),
            "parameter_definition_relationship": meaning("same", header),
            "substrate_arrangement": meaning("separate_assays", title,
                spans.witness("biopterin                                1.0e6"),
                spans.witness("7,8-dihydrobiopterin                     9.3e2")),
            "comparison_scope": meaning("reported_protocols", title),
            "nonintended_conditions_relationship": meaning("unknown")}}


def _source(store, provider, content, parents=()):
    artifact = store.artifact(content, "application/pdf" if provider == "author_pdf" else "text/plain")
    return store.put("source", {"provider": provider, "accession": "10.1021/ja309680b",
        "uri": None, "artifact_ref": artifact, "text_ref": artifact if provider != "author_pdf" else None,
        "request_ref": None, "version": None, "retrieved_at": None,
        "parent_source_refs": list(parents)}, origin="caller")["id"]


def _reason(store, source_ref):
    source = store.get(source_ref)
    raw = store.get_artifact(source["artifact_ref"])
    quote = b"Arad3529"
    start = raw.index(quote)
    commit = {key: [] for key in store.reasoning_schema()["required"]}
    commit["source_subjects"] = [{"alias": "reported_assayed_molecule", "reference_type": "assay",
        "source_ref": source_ref, "label": quote.decode(), "anchor": {"source_ref": source_ref,
            "artifact_ref": source["artifact_ref"], "start": start, "end": start + len(quote), "quote": quote.decode()}}]
    return {"selection": {"kind": "reason", "commit": commit}, "report_update": {}}


def test_selected_arad3529_table2_kinetics_typed_return_and_first_cold_reconstruction(tmp_path, monkeypatch):
    pdf, xml, transcription = _transcription()
    path = tmp_path / "state"
    store = Store(path)
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    pdf_ref = _source(store, "author_pdf", pdf)
    xml_ref = _source(store, "pdf_glyph_geometry", xml, (pdf_ref,))
    source_ref = _source(store, "geometry_checked_kinetic_transcription", transcription, (xml_ref,))
    args = _selection(Spans(transcription, source_ref))
    returned = []
    def commission(role, assignment):
        return {"selection": {"kind": "episode_child", "role": role, "assignment": assignment,
            "goal": "Extract the reported Arad3529 Table 2 kinetic contrast",
            "scope": store.validate_scope(), "purpose": "Return the requested source-bound kinetic cells",
            "schema_json": json.dumps(FORM), "initial_report_json": "{}"}, "report_update": {}}
    def receive(inputs):
        form, = inputs["child_reports"]
        validate_form(form, FORM, lambda *_: True)
        rows = form["numbers"]
        assert [row["component"] for row in rows] == REQUESTED
        assert rows[0]["value"] == pytest.approx(60)
        assert rows[1]["value"] == pytest.approx(.0558)
        assert rows[2]["value"] == pytest.approx(100000 / 93)
        assert rows[3]["value"] == pytest.approx(6.980325971817)
        assert all(row["evaluation_scope"] == "source_kinetic_parameter_contrast" for row in rows)
        assert all(row["comparison"]["comparison_scope"]["value"] == "reported_protocols" for row in rows)
        assert all(row["comparison"]["nonintended_conditions_relationship"]["value"] == "unknown" for row in rows)
        assert all(row["numerator"]["uncertainty"]["statistic"] == "unspecified" for row in rows)
        assert all(row["denominator"]["uncertainty"]["statistic"] == "unspecified" for row in rows)
        assert rows[0]["numerator"]["uncertainty_values"]["magnitude"] == pytest.approx(6)
        assert rows[1]["denominator"]["uncertainty_values"]["magnitude"] == pytest.approx(.003)
        assert rows[0]["numerator"]["physical_observation_ref"] != rows[0]["denominator"]["physical_observation_ref"]
        assert all(row[role]["context"]["preparation"] is None for row in rows for role in ("numerator", "denominator"))
        assert all(row["model_input_status"] == "not_supplied_by_native_operation" for row in rows)
        returned.append(deepcopy(form))
        return _reason(store, source_ref)
    provider = ScriptedProvider([commission("literature", {"version": "literature_assignment_v1",
        "question_context_refs": [], "source_refs": [source_ref], "requested_kinetic_components": REQUESTED}),
        commission("literature_strategy", {"version": "strategy_assignment_v1", "question_context_refs": [],
            "prior_search_refs": [source_ref], "requested_kinetic_components": REQUESTED}),
        {"selection": {"kind": "tool", "tool": "literature.kinetic.populate", "arguments": args}, "report_update": {}},
        receive, receive])
    scorer = ScientificFindingProgress(FindingProgressPolicy(1))
    def controller(path, initial):
        return FixtureController(str(path), initial, 1 if len(path) == 3 else 2)
    try:
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path / "run", controller_factory=controller, project_credit=scorer,
            initial_known_record_refs=[source_ref, xml_ref, pdf_ref],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=[source_ref]),), binding_definitions={"credit": scorer.as_record()}))
        assert summary["credit"] == 0 and returned[0] == returned[1]
        assert len(provider.contexts) == 5
        assert not store.list("assessment") and not store.list("observation")
        assert store.db.execute("SELECT count(*) FROM literature_kinetic_operations").fetchone()[0] == 1
        assert store.db.execute("SELECT count(*) FROM literature_kinetic_received").fetchone()[0] == 2
        run_id, sheet_ref = store.db.execute("SELECT run_id,outcome FROM literature_kinetic_operations").fetchone()
        sheet_ref = json.loads(sheet_ref)["result"]["sheet_ref"]
        repo = LiteratureKineticRepository(store, run_id)
        saved = repo.read(sheet_ref)
        assert saved["input_source_refs"] == [source_ref, xml_ref, pdf_ref]
        assert saved["extraction"]["operands"]["numerator"]["number"]["value"] == 1.0e6
        assert saved["extraction"]["operands"]["denominator"]["number"]["value"] == 9.3e2
        assert saved["extraction"]["operands"]["numerator"]["uncertainty"]["magnitude"]["value"] == 1.0e5
        assert saved["extraction"]["operands"]["denominator"]["uncertainty"]["magnitude"]["value"] == 5.0e1
        assert saved["calculation"]["cells"]["log_contrast_variance"]["value"] is None
        assert saved["calculation"]["cells"]["source_profile_log_ratio"]["value"] is None
        assert saved["calculation"]["cells"]["log_contrast_variance"]["unavailable_reason"] == "kinetic_log_model_unreported"
        before = list(store.db.iterdump())
        source_artifacts = {store.get(ref)["artifact_ref"] for ref in (source_ref, xml_ref, pdf_ref)}
    finally:
        store.close()
    def forbidden(*_args, **_kwargs):
        raise AssertionError("cold reconstruction must use saved operation and binding records only")
    monkeypatch.setattr("gene_annotation_episode.literature_kinetic_storage.read_kinetic_inputs", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_kinetic_storage.populate_kinetic_contrast", forbidden)
    with Store(path) as reopened:
        original_get = reopened.get_artifact
        monkeypatch.setattr(reopened, "get_artifact", lambda ref: forbidden() if ref in source_artifacts else original_get(ref))
        reopened.db.execute("PRAGMA query_only=ON")
        restored = LiteratureKineticRepository(reopened, run_id)
        assert restored.read(sheet_ref) == saved
        rows = restored.project_cells([sheet_ref], permitted_record_refs=(sheet_ref,), components=REQUESTED)
        assert {row["component"]: row["value"] for row in rows} == {row["component"]: row["value"] for row in returned[0]["numbers"]}
        assert list(reopened.db.iterdump()) == before
