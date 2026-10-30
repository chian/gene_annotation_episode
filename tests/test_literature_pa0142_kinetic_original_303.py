"""Selected Pa0142 A105 kinetics from Hall et al., JACS 2010, DOI 10.1021/ja909817d.

The PDF font mapping flattens superscripts and reads its ± glyph as `(`.
Pinned PDF/XML page geometry and a page image inspection support the narrow,
explicitly normalized transcription used by the existing literal reader.
"""
import asyncio
from copy import deepcopy
from functools import partial
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from gene_annotation_episode.investigation_progress import FindingProgressPolicy, ScientificFindingProgress
from gene_annotation_episode.literature_a105_worksheet import a105_worksheet_template, NATIVE, VERSION
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.literature_kinetic_calculations import populate_kinetic_contrast
from gene_annotation_episode.literature_kinetic_inputs import read_kinetic_inputs
from gene_annotation_episode.literature_kinetic_storage import LiteratureKineticRepository
from gene_annotation_episode.runtime import run_workflow
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry
from test_runtime import FixtureController, ScriptedProvider


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "verification/a105_pa0142_primary_case_301/source"
PDF = SOURCE / "Pa0142_JACS_original.pdf"
LAYOUT = SOURCE / "Pa0142_JACS_original.layout.txt"
SI = SOURCE / "ja909817d_si_001.pdf"
XML = ROOT / "verification/a105_pa0142_kinetic_selected_303/source/pa0142.xml"
PINS = {
    PDF: "e134cf00255ff58a3a229c615df45b031b6418ab5a2ef1b18de8f811247e3c4f",
    LAYOUT: "6f4085272b673ba209580a08855c90869f98c67f981328662000c3b3c58e3db2",
    SI: "1f0a0dd8ff50c6ba91b5b28bf4f02525d1cfb9beb5e7c2c0f2e929cdb457d5a3",
    XML: "b98ea93f8cfc5ad178018af7bb1070859325f203c510e68d5f9e137c973ae468",
}
REQUESTED = ["numerator_parameter", "denominator_parameter", "parameter_ratio", "log_parameter_contrast"]
TEMPLATE = a105_worksheet_template([{"field": "kinetics", "source": NATIVE, "components": REQUESTED}])
FORM = TEMPLATE["submitted_form"]
EMPTY = {"version": VERSION, "assertion_refs": [], "quantity_links": [], "assertion_links": []}


def _transcription():
    raw = {path: path.read_bytes() for path in PINS}
    assert {path: hashlib.sha256(value).hexdigest() for path, value in raw.items()} == PINS
    xml = raw[XML]
    root = ET.fromstring(xml)
    nodes = list(root.findall("page")[1].findall("text"))
    for mantissa, power in (("0.1)", "4"), ("0.4)", "3"), ("0.1)", "3")):
        candidates = []
        for i, node in enumerate(nodes):
            if "".join(node.itertext()) != mantissa:
                continue
            following = nodes[i + 1:i + 4]
            if ["".join(n.itertext()) for n in following] == ["×", "10", power]:
                candidates.append(following)
        assert candidates, (mantissa, power)
        assert any(int(group[2].attrib["height"]) < int(group[1].attrib["height"])
                   and int(group[2].attrib["top"]) < int(group[1].attrib["top"])
                   for group in candidates)
    original = raw[LAYOUT].decode()
    # The quoted clauses and their order are source-witnessed. Numerical tokens
    # below transcribe the visually checked ± and 10 superscripts for the V3
    # scalar reader; they are not literal pdftotext output or raw new data.
    for token in (
        "Pa0142 from Pseudomonas aeruginosa PA01", "Formation of ammonia was",
        "detected with 8-oxoG (1), guanine (2), isocytosine (3)",
        "For 2, the values of", "respectively. For 3, the corresponding values",
        "The maximal rate constant for the deamination of 8-oxoG",
    ):
        assert token in original
    assert "at pH 8.0" in original and "is less than 5 × 10-3 s-1" in original
    assert "(2.0 ( 0.1) × 104" in original and "(2.2 ( 0.1) × 103" in original
    transcription = """Pa0142 from Pseudomonas aeruginosa PA01 was expressed and purified to homogeneity.
Pa0142 was assayed against a library of more than 50 compounds. Formation of ammonia was monitored by a coupled enzyme assay using glutamate dehydrogenase, NADH, and alpha-ketoglutarate at pH 8.0. Product formation in each case was confirmed by mass spectrometry and UV spectroscopy.
Activity was detected with 8-oxoG (1), guanine (2), isocytosine (3), and ammeline (4) (Scheme 1).
The limited solubility of 8-oxoG prevented an accurate measurement of kcat and Km, but the kcat/Km value of (2.0e4 ± 0.1e4) M-1 s-1 is an order of magnitude larger than that for the next best compound tested.
For 2, the values of kcat, Km, and kcat/Km are 3.3 ± 0.6 s-1, 2.6 ± 0.6 mM, and (1.3e3 ± 0.4e3) M-1 s-1, respectively.
For 3, the corresponding values are 3.9 ± 0.1 s-1, 1.8 ± 0.1 mM, and (2.2e3 ± 0.1e3) M-1 s-1.
Two putative guanine deaminases were cloned, purified, and characterized: Pa0134 from P. aeruginosa and b2883 from Escherichia coli K12. The maximal rate constant for the deamination of 8-oxoG is less than 5e-3 s-1.
"""
    return raw[PDF], raw[SI], xml, transcription.encode()


class Spans:
    def __init__(self, content, source_ref):
        self.content, self.source_ref = content, source_ref

    def witness(self, quote, occurrence=0):
        token = quote.encode()
        start = 0
        for index in range(occurrence + 1):
            start = self.content.index(token, start)
            if index < occurrence:
                start += len(token)
        return {"source_ref": self.source_ref, "representation": "original",
                "start": start, "end": start + len(token), "quote": quote}

    def witness_after(self, marker, quote):
        token = quote.encode()
        start = self.content.index(token, self.content.index(marker.encode()))
        return {"source_ref": self.source_ref, "representation": "original",
                "start": start, "end": start + len(token), "quote": quote}

    def number(self, token):
        return {"witness": self.witness(token), "number_start": 0, "number_end": len(token)}


def _selection(spans, alternative):
    assert alternative in ("guanine", "isocytosine")
    marker, label, number, spread = (("For 2", "guanine (2)", "1.3e3", "0.4e3")
        if alternative == "guanine" else ("For 3", "isocytosine (3)", "2.2e3", "0.1e3"))
    def meaning(value, *witnesses):
        return {"value": value, "witnesses": list(witnesses)}
    common = {"organism": spans.witness("Pseudomonas aeruginosa PA01"), "genotype": None,
              "molecule": spans.witness("Pa0142"),
              "construct": spans.witness("Pa0142 from Pseudomonas aeruginosa PA01 was expressed and purified to homogeneity")}
    endpoint = spans.witness("kcat/Km")
    unit = spans.witness("M-1 s-1")
    condition = spans.witness("at pH 8.0")
    system = spans.witness("coupled enzyme assay using glutamate dehydrogenase, NADH, and alpha-ketoglutarate")
    def operand(substrate, row, value, uncertainty):
        return {"parameter_kind": meaning("catalytic_efficiency", endpoint),
            "subject": deepcopy(common),
            "context": {"substrate": substrate, "preparation": None,
                "experiment": spans.witness("Pa0142 was assayed against a library of more than 50 compounds"),
                "experimental_system": system, "conditions": condition,
                "endpoint": endpoint, "normalization": None},
            "measurement_identity": row,
            "measurement": {"number": spans.number(value), "unit": unit},
            "qualification": meaning("reported_point", row),
            "uncertainty": {"statistic": meaning("unspecified", row), "magnitude": spans.number(uncertainty),
                "interval": None, "unit": None, "unit_relationship": meaning("same_as_parameter", endpoint),
                "confidence_level": None, "count": None,
                "repetition_basis": meaning("unspecified"), "estimate_basis": meaning("unknown")}}
    numerator = operand(spans.witness("8-oxoG (1)"),
        spans.witness("(2.0e4 ± 0.1e4) M-1 s-1"), "2.0e4", "0.1e4")
    denominator = operand(spans.witness(label),
        spans.witness("(" + number + " ± " + spread + ") M-1 s-1"), number, spread)
    ordered_values = spans.witness("respectively") if alternative == "guanine" else spans.witness("corresponding values")
    return {"version": "a105_kinetic_source_selection_v1", "source_ref": spans.source_ref,
        "source_kind": "primary_source", "numerator": numerator, "denominator": denominator,
        "comparison": {
            "subject_relationship": meaning("same_molecule_and_construct", common["construct"]),
            "parameter_definition_relationship": meaning("same", endpoint, ordered_values),
            "substrate_arrangement": meaning("separate_assays", spans.witness(marker),
                spans.witness("8-oxoG (1)"), spans.witness(label)),
            "comparison_scope": meaning("reported_protocols", spans.witness(marker),
                spans.witness("at pH 8.0")),
            "nonintended_conditions_relationship": meaning("unknown")}}


def _source(store, provider, content, parents=()):
    artifact = store.artifact(content, "application/pdf" if provider in ("author_pdf", "author_si_pdf") else "text/plain")
    return store.put("source", {"provider": provider, "accession": "10.1021/ja909817d",
        "uri": None, "artifact_ref": artifact, "text_ref": artifact if provider == "geometry_checked_transcription" else None,
        "request_ref": None, "version": None, "retrieved_at": None,
        "parent_source_refs": list(parents)}, origin="caller")["id"]


def _reason(store, source_ref):
    source = store.get(source_ref)
    raw = store.get_artifact(source["artifact_ref"])
    quote = b"Pa0142"
    start = raw.index(quote)
    commit = {key: [] for key in store.reasoning_schema()["required"]}
    commit["source_subjects"] = [{"alias": "assayed_pa0142", "reference_type": "assay",
        "source_ref": source_ref, "label": quote.decode(), "anchor": {"source_ref": source_ref,
            "artifact_ref": source["artifact_ref"], "start": start, "end": start + len(quote),
            "quote": quote.decode()}}]
    return {"selection": {"kind": "reason", "commit": commit}, "report_update": {"assessment_context": EMPTY}}


def test_pa0142_two_selected_kinetic_contrasts_typed_worksheet_and_cold_reconstruction(tmp_path, monkeypatch):
    pdf, si, xml, transcription = _transcription()
    path = tmp_path / "state"
    store = Store(path)
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    pdf_ref = _source(store, "author_pdf", pdf)
    si_ref = _source(store, "author_si_pdf", si, (pdf_ref,))
    xml_ref = _source(store, "pdf_glyph_geometry", xml, (pdf_ref,))
    source_ref = _source(store, "geometry_checked_transcription", transcription, (pdf_ref, si_ref, xml_ref))
    spans = Spans(transcription, source_ref)
    guanine = _selection(spans, "guanine")
    isocytosine = _selection(spans, "isocytosine")
    captured = []
    def commission(role, assignment):
        return {"selection": {"kind": "episode_child", "role": role, "assignment": assignment,
            "goal": "Evaluate Pa0142 8-oxoG catalytic efficiency versus guanine and isocytosine",
            "scope": store.validate_scope(), "purpose": "Return both requested A105 numerical sections and their source limitations",
            "schema_json": json.dumps(FORM), "initial_report_json": json.dumps({"assessment_context": EMPTY})},
            "report_update": {"assessment_context": EMPTY}}
    def receive(inputs):
        form, = inputs["child_reports"]
        rows = form["kinetics"]
        assert len(rows) == 2 * len(REQUESTED)
        by_sheet = {}
        for row in rows:
            by_sheet.setdefault(row["sheet_ref"], {})[row["component"]] = row
        assert len(by_sheet) == 2
        for comparison in by_sheet.values():
            assert set(comparison) == set(REQUESTED)
            assert comparison["numerator_parameter"]["value"] == pytest.approx(1.2)
            assert comparison["numerator_parameter"]["numerator"]["uncertainty"]["statistic"] == "unspecified"
            assert comparison["parameter_ratio"]["comparison"]["comparison_scope"]["value"] == "reported_protocols"
            assert comparison["parameter_ratio"]["comparison"]["nonintended_conditions_relationship"]["value"] == "unknown"
            assert comparison["parameter_ratio"]["model_input_status"] == "not_supplied_by_native_operation"
            assert comparison["numerator_parameter"]["numerator"]["context"]["conditions"] is not None
            assert comparison["numerator_parameter"]["numerator"]["context"]["experimental_system"] is not None
        ratios = sorted(c["parameter_ratio"]["value"] for c in by_sheet.values())
        assert ratios == pytest.approx(sorted([100 / 11, 200 / 13]))
        numerator_ids = {c["numerator_parameter"]["numerator"]["physical_observation_ref"] for c in by_sheet.values()}
        denominator_ids = {c["denominator_parameter"]["denominator"]["physical_observation_ref"] for c in by_sheet.values()}
        assert len(numerator_ids) == 1 and len(denominator_ids) == 2
        assert numerator_ids.isdisjoint(denominator_ids)
        assert form["assessment_context"] == EMPTY
        captured.append(deepcopy(form))
        return _reason(store, source_ref)
    strategy_assignment = {"version": "strategy_assignment_v1", "question_context_refs": [],
        "prior_search_refs": [source_ref], **TEMPLATE["assignment_rosters"]}
    literature_assignment = {"version": "literature_assignment_v1", "question_context_refs": [],
        "source_refs": [source_ref], **TEMPLATE["assignment_rosters"]}
    provider = ScriptedProvider([commission("literature", literature_assignment),
        commission("literature_strategy", strategy_assignment),
        {"selection": {"kind": "tool", "tool": "literature.kinetic.populate", "arguments": guanine},
            "report_update": {"assessment_context": EMPTY}},
        {"selection": {"kind": "tool", "tool": "literature.kinetic.populate", "arguments": isocytosine},
            "report_update": {"assessment_context": EMPTY}}, receive, receive])
    scorer = ScientificFindingProgress(FindingProgressPolicy(1))
    try:
        summary = asyncio.run(run_workflow(store, ToolRegistry(store), provider=provider,
            run_dir=tmp_path / "run", controller_factory=lambda p, initial: FixtureController(str(p), initial, 2),
            project_credit=scorer, initial_known_record_refs=[source_ref, xml_ref, si_ref, pdf_ref],
            episode_binding_factories=(partial(LiteratureEpisodes, rate_population=True,
                reference_parent_sources=[source_ref]),), binding_definitions={"credit": scorer.as_record()}))
        assert summary["credit"] == 0 and captured[0] == captured[1]
        assert len(provider.contexts) == 6
        assert not store.list("assessment") and not store.list("observation")
        assert store.db.execute("SELECT count(*) FROM runtime_actions").fetchone()[0] == 6
        assert store.db.execute("SELECT count(*) FROM runtime_observations").fetchone()[0] == 6
        operations = store.db.execute("SELECT run_id,outcome FROM literature_kinetic_operations ORDER BY rowid").fetchall()
        assert len(operations) == 2
        run_id = operations[0]["run_id"]
        assert all(row["run_id"] == run_id for row in operations)
        sheet_refs = [json.loads(row["outcome"])["result"]["sheet_ref"] for row in operations]
        repo = LiteratureKineticRepository(store, run_id)
        saved = [repo.read(ref) for ref in sheet_refs]
        assert all(packet["input_source_refs"] == [source_ref, pdf_ref, si_ref, xml_ref] or
                   set(packet["input_source_refs"]) == {source_ref, pdf_ref, si_ref, xml_ref} for packet in saved)
        assert saved[0]["calculation"]["cells"]["parameter_ratio"]["value"] == pytest.approx(200 / 13)
        assert saved[1]["calculation"]["cells"]["parameter_ratio"]["value"] == pytest.approx(100 / 11)
        assert saved[0]["calculation"]["cells"]["log_parameter_contrast"]["value"] == pytest.approx(2.7333680090865)
        assert saved[1]["calculation"]["cells"]["log_parameter_contrast"]["value"] == pytest.approx(2.2072749131897)
        assert saved[0]["calculation"]["cells"]["denominator_parameter"]["value"] == pytest.approx(.078)
        assert saved[1]["calculation"]["cells"]["denominator_parameter"]["value"] == pytest.approx(.132)
        assert [packet["extraction"]["operands"]["denominator"]["uncertainty"]["canonical"]["magnitude"]
                for packet in saved] == pytest.approx([.024, .006])
        assert saved[0]["calculation"]["physical_measurement_ids"]["numerator"] == saved[1]["calculation"]["physical_measurement_ids"]["numerator"]
        assert saved[0]["calculation"]["physical_measurement_ids"]["denominator"] != saved[1]["calculation"]["physical_measurement_ids"]["denominator"]
        for packet in saved:
            cells = packet["calculation"]["cells"]
            assert packet["calculation"]["inputs"]["numerator"]["context"]["conditions"] == "at pH 8.0"
            assert "coupled enzyme assay" in packet["calculation"]["inputs"]["numerator"]["context"]["experimental_system"]
            for name in ("log_contrast_variance", "source_profile_log_ratio", "source_signed_index"):
                assert cells[name]["value"] is None
            assert cells["log_contrast_variance"]["unavailable_reason"] == "kinetic_log_model_unreported"
            assert packet["extraction"]["operands"]["numerator"]["uncertainty"]["canonical"]["statistic"] == "unspecified"
        before = list(store.db.iterdump())
        source_artifacts = {store.get(ref)["artifact_ref"] for ref in (source_ref, pdf_ref, si_ref, xml_ref)}
    finally:
        store.close()
    def forbidden(*_args, **_kwargs):
        raise AssertionError("cold reconstruction may use saved operation and binding records only")
    monkeypatch.setattr("gene_annotation_episode.literature_kinetic_storage.read_kinetic_inputs", forbidden)
    monkeypatch.setattr("gene_annotation_episode.literature_kinetic_storage.populate_kinetic_contrast", forbidden)
    with Store(path) as reopened:
        original_get = reopened.get_artifact
        monkeypatch.setattr(reopened, "get_artifact", lambda ref: forbidden() if ref in source_artifacts else original_get(ref))
        reopened.db.execute("PRAGMA query_only=ON")
        restored = LiteratureKineticRepository(reopened, run_id)
        assert [restored.read(ref) for ref in sheet_refs] == saved
        rows = restored.project_cells(sheet_refs, permitted_record_refs=sheet_refs, components=REQUESTED)
        assert {(row["sheet_ref"], row["component"], row["value"]) for row in rows} == {
            (row["sheet_ref"], row["component"], row["value"]) for row in captured[0]["kinetics"]}
        assert list(reopened.db.iterdump()) == before


def test_pa0142_sources_do_not_supply_the_other_enzymes_as_a_denominator(tmp_path):
    pdf, si, xml, transcription = _transcription()
    with Store(tmp_path / "state") as store:
        pdf_ref = _source(store, "author_pdf", pdf)
        si_ref = _source(store, "author_si_pdf", si, (pdf_ref,))
        xml_ref = _source(store, "pdf_glyph_geometry", xml, (pdf_ref,))
        source_ref = _source(store, "geometry_checked_transcription", transcription, (pdf_ref, si_ref, xml_ref))
        selected = _selection(Spans(transcription, source_ref), "guanine")
        read = read_kinetic_inputs(selected, read_source=lambda ref, representation: {
            "artifact_ref": store.get(ref)["artifact_ref"],
            "content": store.get_artifact(store.get(ref)["artifact_ref"])})
        assert read["calculation_inputs"]["numerator"]["parameter_kind"] == "catalytic_efficiency"
        assert read["calculation_inputs"]["denominator"]["parameter_kind"] == "catalytic_efficiency"
        assert read["calculation_inputs"]["denominator"]["context"]["substrate"] == "guanine (2)"
        assert populate_kinetic_contrast(read["calculation_inputs"])["cells"]["parameter_ratio"]["value"] == pytest.approx(200 / 13)
        assert b"Pa0134" in transcription and b"b2883" in transcription and b"less than 5e-3 s-1" in transcription
        # Read the source's censored, separately situated kcat as a deliberate
        # wrong denominator; it is not individually assigned to either enzyme.
        spans = Spans(transcription, source_ref)
        wrong = deepcopy(selected)
        den = wrong["denominator"]
        den["parameter_kind"] = {"value": "kcat", "witnesses": [spans.witness("maximal rate constant")]}
        den["subject"]["molecule"] = None
        den["context"]["substrate"] = spans.witness_after("Two putative guanine deaminases", "8-oxoG")
        den["context"]["endpoint"] = spans.witness("maximal rate constant")
        den["measurement_identity"] = spans.witness("less than 5e-3 s-1")
        den["measurement"] = {"number": spans.number("5e-3"), "unit": spans.witness_after("less than", "s-1")}
        den["qualification"] = {"value": "reported_point", "witnesses": [spans.witness("less than 5e-3 s-1")]}
        den["uncertainty"] = {"statistic": {"value": "unreported", "witnesses": []},
            "magnitude": None, "interval": None, "unit": None,
            "unit_relationship": {"value": "same_as_parameter", "witnesses": [spans.witness_after("less than", "s-1")]},
            "confidence_level": None, "count": None,
            "repetition_basis": {"value": "unspecified", "witnesses": []},
            "estimate_basis": {"value": "unknown", "witnesses": []}}
        wrong["comparison"]["subject_relationship"] = {"value": "different",
            "witnesses": [spans.witness("Two putative guanine deaminases were cloned, purified, and characterized") ]}
        wrong["comparison"]["parameter_definition_relationship"] = {"value": "different",
            "witnesses": [spans.witness("maximal rate constant"), spans.witness("kcat/Km")]}
        other_enzyme = read_kinetic_inputs(wrong, read_source=lambda ref, representation: {
            "artifact_ref": store.get(ref)["artifact_ref"],
            "content": store.get_artifact(store.get(ref)["artifact_ref"])})["calculation_inputs"]
        assert other_enzyme["denominator"]["status"] == "censored"
        assert other_enzyme["denominator"]["value"] == pytest.approx(.3)
        rejected = populate_kinetic_contrast(other_enzyme)["cells"]["parameter_ratio"]
        assert rejected["value"] is None and rejected["unavailable_reason"] == "censored_measurement"
