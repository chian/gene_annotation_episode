"""Read published model-table values without inventing experimental operands."""
from copy import deepcopy
from dataclasses import replace
import hashlib
from pathlib import Path
import re

import pytest

from gene_annotation_episode.domain import ContractError, validate_schema
from gene_annotation_episode.literature_assay_grading_inputs import _literal
from gene_annotation_episode.literature_assay_inputs import _Sources
from gene_annotation_episode.literature_experimental_contracts import ExperimentalContractError
from gene_annotation_episode.literature_intervention_inputs import _intervention_unit, intervention_population_schema
from gene_annotation_episode.literature_intervention_storage import LiteratureInterventionRepository
from gene_annotation_episode.literature_intervention_table import associate_table_unit
from gene_annotation_episode.state import Store
from test_literature_intervention_storage import intervention_fixture
from test_literature_perturbation_integration import source, witness


TABLE = Path(__file__).parent / "fixtures/a106_source_tables/gawand_2015_table2.xml"
REF = "source_" + "a" * 24


def selected(raw, ref=REF, model="MOMA"):
    row_label = '<italic toggle="yes">E. coli</italic> Δ<italic toggle="yes">pgi</italic>'
    row = next(row for row in re.finditer(rb"<tr>.*?</tr>", raw, re.S)
        if (row_label + "</td>").encode() in row.group())
    cells = list(re.finditer(rb"<td\b[^>]*>(.*?)</td>", row.group(), re.S))
    cell = cells[5 if model == "MOMA" else 6]
    quote = cell.group(1).decode()
    value = "0.65" if model == "MOMA" else "0.18"
    start = row.start() + cell.start(1)
    number_witness = dict(source_ref=ref, representation="original", start=start,
        end=start + len(cell.group(1)), quote=quote)
    # The second repeated model heading belongs to the growth-rate group.
    header = list(re.finditer((">" + model + "</th>").encode(), raw))[1]
    model_witness = dict(source_ref=ref, representation="original", start=header.start() + 1,
        end=header.start() + 1 + len(model), quote=model)
    return dict(kind="source_table_number", origin="reported",
        number=dict(witness=number_witness, number_start=quote.index(value),
            number_end=quote.index(value) + len(value)),
        unit=witness(ref, raw, "h<sup>−1</sup>"), row_label=witness(ref, raw, row_label),
        column_labels=[witness(ref, raw, '<italic toggle="yes">µ</italic>'), model_witness])


def read(raw, selection):
    sources = _Sources(lambda *_: dict(content=raw,
        artifact_ref="artifact_" + hashlib.sha256(raw).hexdigest()))
    return _literal(selection, sources, unit_reader=_intervention_unit,
        unit_association=associate_table_unit)


@pytest.mark.parametrize("model,expected", [("MOMA", .65), ("RELATCH", .18)])
def test_published_grouped_table_retains_native_growth_prediction(model, expected):
    raw = TABLE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == "45ad34acfdd72e84b9e6bd954120261fa6ae8053fd6949516783ec02b8708a72"
    selection = selected(raw, model=model)
    before = deepcopy(selection)
    operand = read(raw, selection)
    assert operand["value"] == expected
    assert operand["unit"] == "per_h" and operand["status"] == "point"
    assert operand["origin"] == "reported" and operand["measurement_keys"]
    assert selection == before


def test_reacquired_table_preserves_physical_number_identity():
    raw = TABLE.read_bytes()
    first = read(raw, selected(raw))
    second = read(raw, selected(raw, ref="source_" + "b" * 24))
    assert first["measurement_keys"] == second["measurement_keys"]
    assert first["source_refs"] != second["source_refs"]


@pytest.mark.parametrize("change,error", [
    ("other_model_column", "source_quantity_column_mismatch"),
    ("other_row", "intervention_table_row_mismatch"),
    ("group_only", "intervention_table_column_ambiguous"),
    ("attribute", "source_markup_is_not_statistic"),
])
def test_table_labels_cannot_be_borrowed_or_ambiguous(change, error):
    raw = TABLE.read_bytes()
    selection = selected(raw)
    if change == "other_model_column":
        selection["column_labels"][-1] = witness(REF, raw, "MOMA")
    elif change == "other_row":
        selection["row_label"] = witness(REF, raw, '<italic toggle="yes">E. coli</italic> wild-type')
    elif change == "group_only":
        selection["column_labels"].pop()
    else:
        quote = witness(REF, raw, 'colspan="3"')
        selection["number"] = dict(witness=quote, number_start=9, number_end=10)
    with pytest.raises((ContractError, ExperimentalContractError), match=error):
        read(raw, selection)


def test_scalar_shortcut_still_rejects_a_nonadjacent_table_unit():
    raw = TABLE.read_bytes()
    selection = selected(raw)
    selection = {key: value for key, value in selection.items() if key not in ("row_label", "column_labels")}
    selection["kind"] = "source_number"
    sources = _Sources(lambda *_: dict(content=raw, artifact_ref="artifact_" + hashlib.sha256(raw).hexdigest()))
    with pytest.raises(ContractError, match="assay_grading_unit_not_adjacent_to_number"):
        _literal(selection, sources, unit_reader=_intervention_unit)


def test_table_adapter_preserves_scalar_censoring():
    # An engineered variant checks the inherited scalar semantics.
    raw = TABLE.read_bytes().replace(b">0.65</td>", b">&lt;0.65</td>", 1)
    operand = read(raw, selected(raw))
    assert operand["value"] is None and operand["status"] == "bounded"
    assert operand["bound"] == dict(relation="lt", lower=None, upper=.65)


def test_published_predictions_enter_saved_a106_inputs_without_manufacturing_a_score(tmp_path):
    raw = TABLE.read_bytes()
    with Store(tmp_path) as store:
        store.create_problem(raw_sequence="ATGGCT", molecule="dna")
        context, args = intervention_fixture(store)
        ref = source(store, raw)["id"]
        context = replace(context, received_record_refs=(*context.received_record_refs, ref))
        args.update(source_ref=ref, source_kind="primary_source", quantity_kind="native_endpoint",
            prediction_model=None, interpretations={})
        args["quantities"] = dict.fromkeys(args["quantities"])
        args["quantities"].update(assertion_prediction=selected(raw, ref, "RELATCH"),
            alternative_prediction=selected(raw, ref, "MOMA"))
        validate_schema(args, intervention_population_schema())
        repo = LiteratureInterventionRepository(store, context.run_id)
        outcome = repo.populate(context, args, "published-table-reader")
        saved = repo.read(outcome["result"]["sheet_ref"])
        quantities = saved["extraction"]["quantities"]
        assert quantities["assertion_prediction"]["value"] == .18
        assert quantities["alternative_prediction"]["value"] == .65
        assert quantities["effect"] is None and quantities["effect_variance"] is None
        assert saved["selection"]["quantities"] == args["quantities"]
        assert saved["sheet"]["cells"]["source_log_evidence_ratio"]["value"] is None


def test_saved_a106_binding_detects_table_reader_implementation_changes(monkeypatch):
    from gene_annotation_episode.literature_episodes import LiteratureEpisodes

    binding = LiteratureEpisodes(None, rate_population=True, a106_intervention=True)
    before = binding.as_record()
    original_read = Path.read_bytes

    def changed_read(path):
        body = original_read(path)
        return body + b"\n# changed table association implementation\n" if path.name == "literature_intervention_table.py" else body

    monkeypatch.setattr(Path, "read_bytes", changed_read)
    after = binding.as_record()
    assert before["configuration"] == after["configuration"]
    assert before["implementation_sha256"] != after["implementation_sha256"]
