"""Selected electrical cells from the retained original Fluc-Ec2 article.

The article is an original source. The small DNA problem below only supplies a
valid episode store; no target correspondence or annotation credit is inferred.
"""

import asyncio
from dataclasses import replace
from fractions import Fraction
import hashlib
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from gene_annotation_episode.communication import form_with_facts
from gene_annotation_episode.domain import validate_schema
from gene_annotation_episode.episode_bindings import BindingContext, EpisodeBindingRegistry
from gene_annotation_episode.episode_services import WorkflowServices
from gene_annotation_episode.literature_channel_storage import (
    LiteratureChannelRepository, channel_cells_schema,
)
from gene_annotation_episode.literature_episodes import LiteratureEpisodes
from gene_annotation_episode.state import Store
from gene_annotation_episode.tools import ToolRegistry


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "research/experimental_scoring_review_2026-10-23/a105_transport_channel_case_174/source/elife-01084-v1.xml"
SHA256 = "83867d6966a972f32899bdfe545c9952cb9d10393dc54d68dce29b6f4954b053"
REQUESTED = ["chord_conductance", "charge_equivalent_rate", "chord_conductance_variance"]
FORM = {"type": "object", "properties": {"electrical": channel_cells_schema()},
        "required": ["electrical"], "additionalProperties": False}


def _witness(raw, source, quote, *, occurrence=0):
    needle = quote.encode("utf-8")
    start = -1
    for _ in range(occurrence + 1):
        start = raw.find(needle, start + 1)
        assert start >= 0, quote
    return {"source_ref": source, "representation": "original", "start": start,
            "end": start + len(needle), "quote": quote}


def _number(raw, source, phrase, token):
    selected = _witness(raw, source, phrase)
    start = phrase.index(token)
    return {"witness": selected, "number_start": start, "number_end": start + len(token)}


def _measurement(raw, source, phrase, point, unit, *, spread=None, context=None):
    return {"number": _number(raw, source, phrase, point),
            "unit": _witness_in_phrase(raw, source, phrase, unit),
            "context": None if context is None else _witness(raw, source, context),
            "spread": None if spread is None else _number(raw, source, phrase, spread),
            "spread_kind": {"value": "unspecified" if spread is not None else "unknown",
                            "witnesses": [] if spread is None else [_witness(raw, source, phrase)]}}


def _witness_in_phrase(raw, source, phrase, token):
    parent = _witness(raw, source, phrase)
    offset = len(phrase[:phrase.index(token)].encode("utf-8"))
    return {"source_ref": source, "representation": "original",
            "start": parent["start"] + offset, "end": parent["start"] + offset + len(token.encode("utf-8")),
            "quote": token}


def _setup(path):
    raw = PAPER.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SHA256
    store = Store(path)
    store.create_problem(raw_sequence="ATGGCT", molecule="dna")
    artifact = store.artifact(raw, "application/xml")
    source = store.put("source", {"provider": "retained_original_elife", "accession": "e01084",
        "uri": None, "artifact_ref": artifact, "text_ref": artifact, "request_ref": None,
        "version": "original_xml_v1", "retrieved_at": None}, origin="caller")["id"]
    literals = {name: None for name in (
        "organism", "genotype", "molecule", "construct", "preparation", "experimental_system",
        "membrane", "ionic_conditions", "voltage_convention", "current_baseline",
        "conducting_unit", "endpoint", "intended_variable")}
    literals["molecule"] = _witness(raw, source, "Fluc-Ec2 reconstituted liposomes")
    literals["experimental_system"] = _witness(raw, source, "planar bilayers under salt-gradient conditions")
    literals["ionic_conditions"] = _witness(raw, source, "300 mM NaF//30 mM NaF")
    literals["current_baseline"] = _witness(raw, source,
        "zero current is defined as the mean level of the fully closed channel")
    literals["endpoint"] = _witness(raw, source, "first-insertion current histograms")
    current_phrase = "1.8 pA under these conditions, equivalent to 7 pS"
    voltage_phrase = "were recorded at −200 mV"
    reversal_phrase = "53 ± 1 mV"
    args = {"source_ref": source, "source_kind": "primary_source", "literals": literals,
        # One construct is named, but the original caption does not establish
        # how many independent protein preparations supplied these bilayers.
        "arrangement_kind": {"value": "unknown", "witnesses": []},
        "current_kind": {"value": "current_step_magnitude",
            "witnesses": [_witness(raw, source, "insertion-step amplitudes")]},
        "arrangement_relation": {"value": "same_electrical_arrangement_supported",
            "witnesses": [_witness(raw, source, "under salt-gradient conditions"),
                          _witness(raw, source, "salt gradient (300 mM NaF//30 mM NaF)")]},
        "measurements": {
            "current": _measurement(raw, source, current_phrase, "1.8", "pA",
                context="Most of these insertion-steps are 1.8 pA under these conditions"),
            "applied_voltage": _measurement(raw, source, voltage_phrase, "−200", "mV",
                context="current fluctuations (downward opening) were recorded at −200 mV"),
            "reversal_voltage": _measurement(raw, source, reversal_phrase, "53", "mV", spread="1",
                context="for salt-gradient and bi-ionic conditions, respectively"),
            "reported_conductance": _measurement(raw, source, current_phrase, "7", "pS",
                context="equivalent to 7 pS"),
        }, "covariance_source_ref": None, "variance_status": "unknown", "variance_witnesses": []}
    context = BindingContext("fluc-original-run", "fluc-child", "literature", (("literature", "fluc-child"),),
        store.validate_scope(), {"version": "literature_assignment_v1", "question_context_refs": [],
        "source_refs": [source], "requested_channel_components": REQUESTED}, {}, (source,))
    return store, context, args, raw


def _binding(store, context):
    host = SimpleNamespace(store=store, run_id=context.run_id, tools=ToolRegistry(store))
    binding = LiteratureEpisodes(WorkflowServices(host), rate_population=True, channel_population=True)
    host.episode_bindings = EpisodeBindingRegistry((binding,))
    return binding


def test_original_fluc_selected_channel_cells_and_typed_return(tmp_path):
    store, context, args, raw = _setup(tmp_path)
    with store:
        binding = _binding(store, context)
        assert "literature.channel.populate" in {item["name"] for item in binding.catalog(context)}
        outcome = asyncio.run(binding.execute(context, "literature.channel.populate", args, "fluc-selected"))
        assert outcome["status"] == "completed", outcome
        rows = outcome["result"]["cells"]
        validate_schema(rows, channel_cells_schema())
        assert [row["component"] for row in rows] == REQUESTED
        assert rows[0]["value"] == float(Fraction(1800, 253))
        assert rows[0]["unit"] == "pS"
        assert rows[0]["conditional_on"] == ["reversal_condition_applicable_to_current_voltage",
                                                "defined_chord_not_differential_conductance"]
        assert rows[1]["value"] == float(Fraction("1.8e-12") / Fraction("1.602176634e-19"))
        assert rows[1]["unit"] == "elementary_charge_equivalents_per_s"
        assert rows[2]["value"] is None
        assert rows[2]["unavailable_reason"] == "primitive_covariance_not_supplied"
        assert all(row["source_kind"] == "primary_source" for row in rows)
        assert all(row["variance_status"] == "unknown" for row in rows)
        assert all(row["replication_status"] == "not_evaluated_by_this_component" for row in rows)
        assert all(row["annotation_credit"] is None for row in rows)
        assert all(row["arrangement_relation"]["value"] == "same_electrical_arrangement_supported"
                   for row in rows)
        assert all(row["operands"][2]["spread_kind"]["value"] == "unspecified"
                   for row in rows if row["component"] != "charge_equivalent_rate")
        assert all(raw[w["start"]:w["end"]] == w["quote"].encode("utf-8")
                   for row in rows for op in row["operands"] for field in ("reading", "spread_reading")
                   if (reading := op[field]) is not None for w in [reading["number"]])
        saved = LiteratureChannelRepository(store, context.run_id).read(outcome["result"]["sheet_ref"])
        assert saved["extraction"]["measurements"]["reversal_voltage"]["spread"]["value"] == 1
        assert saved["sheet"]["cells"]["reported_conductance"]["value"] == 7
        assert len(set(saved["sheet"]["cells"]["chord_conductance"]["measurement_keys"])) == 3
        delivered = replace(context, received_record_refs=(*context.received_record_refs, *outcome["record_refs"]))
        form = form_with_facts({}, FORM, binding.facts(delivered, {"committed_record_refs": outcome["record_refs"]}))
        assert form["electrical"] == rows
        binding.validate_report(delivered, form, FORM)


def test_original_biionic_reversal_cannot_enter_salt_gradient_chord(tmp_path):
    store, context, args, raw = _setup(tmp_path)
    args["measurements"]["reversal_voltage"] = _measurement(raw, args["source_ref"],
        "119 ± 3 mV", "119", "mV", spread="3",
        context="for salt-gradient and bi-ionic conditions, respectively")
    args["arrangement_relation"] = {"value": "different_electrical_arrangements",
        "witnesses": [_witness(raw, args["source_ref"],
            "for salt-gradient and bi-ionic conditions, respectively")]}
    with store:
        result = asyncio.run(_binding(store, context).execute(
            context, "literature.channel.populate", args, "biionic-not-chord"))
        rows = {row["component"]: row for row in result["result"]["cells"]}
        assert rows["chord_conductance"]["value"] is None
        assert rows["chord_conductance"]["unavailable_reason"] == "different_electrical_arrangements"
        assert rows["charge_equivalent_rate"]["value"] == float(
            Fraction("1.8e-12") / Fraction("1.602176634e-19"))
        assert rows["chord_conductance_variance"]["value"] is None


def test_original_fluc_cold_saved_reconstruction_does_not_reparse_source(tmp_path, monkeypatch):
    store, context, args, _raw = _setup(tmp_path)
    binding = _binding(store, context)
    outcome = asyncio.run(binding.execute(context, "literature.channel.populate", args, "fluc-selected"))
    ref = outcome["result"]["sheet_ref"]
    saved = LiteratureChannelRepository(store, context.run_id).read(ref)
    store.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    store.close()
    before = {str(p.relative_to(tmp_path)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in tmp_path.rglob("*") if p.is_file()}

    def forbidden(*_args, **_kwargs):
        raise AssertionError("cold reconstruction invoked science")

    for module, names in {
        "literature_channel_storage": ("read_channel_inputs", "channel_calculation_inputs",
                                       "populate_channel_components"),
        "literature_channel_inputs": ("read_channel_inputs", "_number", "_read_unit"),
        "literature_channel_calculations": ("populate_channel_components",),
    }.items():
        for name in names:
            monkeypatch.setattr(f"gene_annotation_episode.{module}.{name}", forbidden)
    cold = Store.__new__(Store)
    cold.path = tmp_path
    cold._savepoint = 0
    cold.db = sqlite3.connect((tmp_path / "state.sqlite3").resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    cold.db.row_factory = sqlite3.Row
    cold.db.execute("PRAGMA query_only=ON")
    with cold:
        allowed = {value[field] for value in cold.list("source") if value["origin"] == "tool"
                   for field in ("artifact_ref", "request_ref")}
        original_get = cold.get_artifact

        def guarded(artifact):
            assert artifact in allowed
            return original_get(artifact)

        monkeypatch.setattr(cold, "get_artifact", guarded)
        repo = LiteratureChannelRepository(cold, context.run_id)
        assert repo.read(ref) == saved
        assert repo.populate(context, args, "fluc-selected") == outcome
        assert repo.project_cells([ref], permitted_record_refs=[ref]) == outcome["result"]["cells"]
        assert cold.db.total_changes == 0
    after = {str(p.relative_to(tmp_path)): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in tmp_path.rglob("*") if p.is_file()}
    assert after == before
