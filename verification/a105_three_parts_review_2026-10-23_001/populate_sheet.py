"""Historical A105 evidence-record reader prototype, not a completed scoring sheet.

No grading policy, points, annotation credit, model call, Store write, or job.
The executable fixture is wholly synthetic. Literature input is already recorded
typed evidence, not prose for another model to paraphrase. The explicit manifest
selects an underlying assay, source claim, samples, conditions and observations;
this example does not discover equivalence between separate experiments.
The original recordkeeping sheet was rejected as the requested numerical
scoring sheet. This prototype does not implement its replacement or part 3.
"""
from __future__ import annotations

from copy import deepcopy
import csv
from decimal import Decimal
import hashlib
import io
import json


def ref(kind, label):
    """Stable synthetic fixture references, with existing domain REF syntax."""
    return kind + "_" + hashlib.sha256(label.encode()).hexdigest()[:24]


def number(value, unit_ref, **reported):
    return {"type": "number", "value": value, "unit_ref": unit_ref, **reported}


def metric(observation, name):
    values = [row["value"] for row in observation["measurements"] if row["name"] == name]
    if len(values) != 1:
        raise ValueError("one_selected_measurement_required:" + name)
    return deepcopy(values[0])


def _decimal(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError("finite_numeric_value_required")
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("finite_numeric_value_required")
    return result


def blank_corrected_rate(series, manifest):
    """Fit net product concentration versus time by ordinary least squares.

    The data are already calibrated concentrations. Do not infer a calibration,
    enzyme concentration, kcat, initial-rate regime, significance, or error model.
    Censored numbers remain native values but cannot be scalar fit operands.
    """
    selected = {row["sample_ref"]: row["rows"] for row in series}
    treated, blank = (selected[manifest[name]] for name in ("treated_sample_ref", "blank_sample_ref"))
    result = {"name": "net_product_formation_rate", "state": "unknown", "value": None,
        "uncertainty_status": "unknown", "unknown_reason": None,
        "derivation": {"operation": "ordinary_least_squares_of_blank_subtracted_concentration",
            "treated_sample_ref": manifest["treated_sample_ref"],
            "blank_sample_ref": manifest["blank_sample_ref"],
            "time_unit_ref": manifest["time_unit_ref"],
            "concentration_unit_ref": manifest["concentration_unit_ref"],
            "time_window": None, "net_product_concentrations": []}}
    if len(treated) < 2 or len(treated) != len(blank):
        result["unknown_reason"] = "insufficient_or_unpaired_timepoints"
        return result
    for row in treated + blank:
        for field, unit_field in (("time", "time_unit_ref"), ("product_concentration", "concentration_unit_ref")):
            atom = row[field]
            if atom["type"] != "number" or atom["unit_ref"] != manifest[unit_field]:
                raise ValueError("selected_quantity_or_unit_mismatch")
            _decimal(atom["value"])
            if "bound" in atom:
                result["unknown_reason"] = "censored_operand_cannot_supply_scalar_rate"
                return result
    times = [_decimal(row["time"]["value"]) for row in treated]
    if times != [_decimal(row["time"]["value"]) for row in blank] or any(
            right <= left for left, right in zip(times, times[1:])):
        raise ValueError("same_strictly_increasing_timepoints_required")
    net = [_decimal(t["product_concentration"]["value"]) - _decimal(b["product_concentration"]["value"])
        for t, b in zip(treated, blank)]
    mean_t, mean_y = sum(times) / len(times), sum(net) / len(net)
    slope = sum((t - mean_t) * (y - mean_y) for t, y in zip(times, net)) / sum(
        (t - mean_t) ** 2 for t in times)
    approximate = any(atom.get("qualifier") == "approximate" for row in treated + blank for atom in row.values())
    result.update(state="calculated", value=number(float(slope), manifest["rate_unit_ref"],
        **({"qualifier": "approximate"} if approximate else {})),
        unknown_reason="rate_uncertainty_not_established")
    result["derivation"].update(time_window={"start": deepcopy(treated[0]["time"]),
        "end": deepcopy(treated[-1]["time"])}, net_product_concentrations=[
            number(float(value), manifest["concentration_unit_ref"]) for value in net])
    # Input plus/minus magnitudes are preserved in the sheet. Their statistic is
    # unspecified in the existing atom schema; this reader cannot propagate them.
    return result


def _populate(records, manifest, input_kind):
    """Copy selected facts; calculate only the explicitly requested native rate."""
    question = records[manifest["target_question_ref"]]
    assay = records[manifest["experiment_ref"]]
    if assay["record_type"] != "reference" or assay["reference_type"] != "assay":
        raise ValueError("explicit_assay_reference_required")
    observations = [records[reference] for reference in manifest["observation_refs"]]
    series, links = [], []
    for sample in (manifest["treated_sample_ref"], manifest["blank_sample_ref"]):
        selected = [row for row in observations if metric(row, "sample_ref")["ref"] == sample]
        # Read order is retained. The fitter verifies its time alignment.
        series.append({"sample_ref": sample, "rows": [
            {"time": metric(row, "time"), "product_concentration": metric(row, "concentration")}
            for row in selected]})
        links.extend({"sample_ref": sample, "row_index": index, "observation_ref": row["id"],
            "source_ref": row["source_ref"], "subject_refs": deepcopy(row["subject_refs"]),
            "observation_kind": row["kind"],
            "source_subject_refs": deepcopy(row["source_subject_refs"]),
            "dependencies": deepcopy(row["dependencies"]), "anchor": deepcopy(row["anchor"])}
            for index, row in enumerate(selected))
    if len(links) != len(observations):
        raise ValueError("observation_outside_selected_samples")
    for row in observations:
        if manifest["experiment_ref"] not in row["dependencies"]:
            raise ValueError("observation_not_linked_to_selected_experiment")
        if metric(row, "product_ref")["ref"] != manifest["product_ref"]:
            raise ValueError("product_identity_mismatch")
    assessments = [deepcopy(records[reference]) for reference in manifest.get("assessment_refs", [])]
    for assessment in assessments:
        if assessment["hypothesis_ref"] != question["id"] or assessment["observation_ref"] not in manifest["observation_refs"]:
            raise ValueError("assessment_does_not_address_selected_question_and_observation")
    # The source claim comes from already recorded finding/assay metadata. It is
    # not inferred from product accumulation, and is not a target measurement.
    claim = deepcopy(manifest.get("source_claim"))
    if claim is not None and claim["subject_refs"] != manifest["assayed_subject_refs"]:
        raise ValueError("claim_must_name_actual_assayed_subject")
    # This is exact identity of the selected reference sets, not an assessment
    # of transfer or biological equivalence between distinct references. Partial
    # overlap (including a target assayed alongside another subject) is not exact
    # identity. An empty selection cannot establish identity either.
    assayed_subjects = set(manifest["assayed_subject_refs"])
    assayed_subject_is_target = bool(assayed_subjects) and assayed_subjects == set(question["subject_refs"])
    experiment = {"experiment_ref": assay["id"],
        "assayed_subject_refs": deepcopy(manifest["assayed_subject_refs"]),
        "source_claim": claim,
        "conditions": [deepcopy(records[reference]) for reference in manifest["condition_refs"]],
        "controls": [{"kind": "protein_free_blank", "sample_ref": manifest["blank_sample_ref"],
            "condition_refs": deepcopy(manifest["condition_refs"])}],
        "native_measurement_series": series,
        "derived_measurements": [blank_corrected_rate(series, manifest)],
        "target_correspondence": {
            "assayed_subject_is_target": assayed_subject_is_target,
            "interpretation_status": "recorded" if assessments else "unknown",
            "assessments": assessments},
        "provenance_views": [{"input_kind": input_kind, "row_links": links}]}
    return {"proposal_status": "unadopted_review", "fixture_status": "synthetic",
        "evidence_axis": "A105", "target_question": {"hypothesis_ref": question["id"],
            **{name: deepcopy(question[name]) for name in ("subject_refs", "predicate", "value", "context_refs")}},
        "experiments": [experiment]}


def populate_from_literature(records, finding_selection):
    """Read existing source-anchored observations; no second prose/model grader."""
    for reference in finding_selection["observation_refs"]:
        if records[reference]["anchor"] is None:
            raise ValueError("literature_observation_requires_retained_source_anchor")
    return _populate(records, finding_selection, "literature_finding")


def _observations_from_table(text, source, manifest, sample_labels, *, kind, origin):
    """Concrete CSV-table adapter with declared columns and calibrated units."""
    rows, offset, observations = text.splitlines(keepends=True), 0, []
    parsed = list(csv.DictReader(io.StringIO(text)))
    if len(parsed) != len(rows) - 1:
        raise ValueError("fixture_requires_one_csv_record_per_line")
    offset = len(rows[0].encode())
    for values, literal in zip(parsed, rows[1:]):
        sample = sample_labels[values["sample"]]
        start, end = offset, offset + len(literal.encode())
        offset = end
        protein = manifest["assayed_subject_refs"] if sample == manifest["treated_sample_ref"] else []
        observations.append({"id": ref("observation", source["id"] + ":" + str(start)),
            "record_type": "observation", "origin": origin, "kind": kind,
            "subject_refs": protein or [sample],
            "source_subject_refs": protein + [sample, manifest["product_ref"]],
            "source_ref": source["id"], "dependencies": [manifest["experiment_ref"], *manifest["condition_refs"]],
            "anchor": {"source_ref": source["id"], "artifact_ref": source["artifact_ref"],
                "start": start, "end": end, "quote": literal},
            "measurements": [
                {"name": "time", "value": number(float(Decimal(values["time_min"])), manifest["time_unit_ref"])},
                {"name": "concentration", "value": number(float(Decimal(values["product_uM"])), manifest["concentration_unit_ref"])},
                {"name": "sample_ref", "value": {"type": "reference", "ref": sample}},
                {"name": "product_ref", "value": {"type": "reference", "ref": manifest["product_ref"]}}]})
    return observations


def populate_from_dataset(csv_text, records, assay_selection, sample_labels):
    """Analyze this declared experimental CSV, preserving original row anchors."""
    selected = deepcopy(assay_selection)
    source = records[selected["dataset_source_ref"]]
    expected_artifact = "artifact_" + hashlib.sha256(csv_text.encode()).hexdigest()
    if source["artifact_ref"] != expected_artifact:
        raise ValueError("dataset_artifact_identity_mismatch")
    observations = _observations_from_table(csv_text, source, selected, sample_labels,
        kind="biochemical_assay", origin="tool")
    selected["observation_refs"] = [row["id"] for row in observations]
    return _populate({**records, **{row["id"]: row for row in observations}}, selected, "experimental_dataset")


def merge_same_experiment(left, right):
    """Retain two source views of one explicitly linked assay exactly once.

    Different assay identities are not deduplicated by equal numbers. Conflicting
    views of the same declared assay require repair; never average or overwrite.
    """
    if left["target_question"] != right["target_question"]:
        raise ValueError("different_target_questions")
    result = deepcopy(left)
    indexed = {row["experiment_ref"]: row for row in result["experiments"]}
    for incoming in right["experiments"]:
        previous = indexed.get(incoming["experiment_ref"])
        if previous is None:
            result["experiments"].append(deepcopy(incoming))
            indexed[incoming["experiment_ref"]] = result["experiments"][-1]
            continue
        for field in ("assayed_subject_refs", "source_claim", "conditions", "controls",
                "native_measurement_series", "derived_measurements", "target_correspondence"):
            if previous[field] != incoming[field]:
                raise ValueError("same_experiment_views_conflict:" + field)
        for view in incoming["provenance_views"]:
            if view not in previous["provenance_views"]:
                previous["provenance_views"].append(deepcopy(view))
    return result


def synthetic_fixture():
    """No real protein, publication, observation, or scientific finding."""
    ids = {name: ref(kind, "A105_SYNTHETIC:" + name) for name, kind in {
        "target": "reference", "protein": "reference", "substrate": "reference", "product": "reference",
        "assay": "reference", "treated": "reference", "blank": "reference", "condition": "context",
        "question": "hypothesis", "metadata": "source", "dataset": "source", "literature": "source",
        "min": "term", "uM": "term", "uM_min": "term", "celsius": "term"}.items()}
    csv_text = "sample,time_min,product_uM\nprotein,0,0\nprotein,1,2\nprotein,2,4\nblank,0,0\nblank,1,0.2\nblank,2,0.4\n"
    # A synthetic literature table reports the SAME assay, not a replication.
    literature_text = csv_text
    records = {}
    for name, text in (("metadata", "SYNTHETIC assay metadata: protein H converts substrate S to product P; 30 C; pH 7.5.\n"),
            ("dataset", csv_text), ("literature", literature_text)):
        records[ids[name]] = {"id": ids[name], "record_type": "source", "origin": "external",
            "provider": "synthetic_" + name, "accession": "SYNTHETIC_" + name,
            "uri": None, "artifact_ref": "artifact_" + hashlib.sha256(text.encode()).hexdigest(),
            "text_ref": None, "request_ref": None, "version": None, "retrieved_at": None}
    for name, label in (("target", "SYNTHETIC target T"), ("protein", "SYNTHETIC assayed protein H"),
            ("substrate", "SYNTHETIC substrate S"), ("product", "SYNTHETIC product P"),
            ("assay", "SYNTHETIC underlying assay 1"), ("treated", "SYNTHETIC protein-containing sample"),
            ("blank", "SYNTHETIC protein-free blank")):
        records[ids[name]] = {"id": ids[name], "record_type": "reference", "origin": "external",
            "reference_type": "assay" if name == "assay" else "chemical" if name in {"substrate", "product"}
                else "sample" if name in {"treated", "blank"} else "protein",
            "source_ref": ids["metadata"], "accession": "SYNTHETIC_" + name, "label": label,
            "sequence_ref": None, "molecule": "protein" if name in {"target", "protein"} else None,
            "length": None, "term_refs": [], "context_refs": []}
    for name, label in (("min", "min"), ("uM", "µM"), ("uM_min", "µM/min"), ("celsius", "C")):
        records[ids[name]] = {"id": ids[name], "record_type": "term", "origin": "external",
            "namespace": "synthetic_unit", "accession": name, "label": label,
            "term_type": "unit", "source_ref": ids["metadata"], "anchor": None}
    records[ids["condition"]] = {"id": ids["condition"], "record_type": "context", "origin": "external",
        "context_type": "assay_condition", "name": "SYNTHETIC assay: 30 C; pH 7.5",
        "source_ref": ids["metadata"], "related_refs": [ids["assay"], ids["treated"], ids["blank"]],
        "attributes": [{"name": "temperature", "value": number(30, ids["celsius"])},
            {"name": "ph", "value": number(7.5, None)}], "anchor": None}
    relation = {"type": "relation", "roles": [
        {"role": "substrate", "ref": ids["substrate"]}, {"role": "product", "ref": ids["product"]}]}
    records[ids["question"]] = {"id": ids["question"], "record_type": "hypothesis", "origin": "reasoning",
        "subject_refs": [ids["target"]], "predicate": "catalyzes", "value": relation, "context_refs": []}
    manifest = {"target_question_ref": ids["question"], "experiment_ref": ids["assay"],
        "assayed_subject_refs": [ids["protein"]], "product_ref": ids["product"],
        "treated_sample_ref": ids["treated"], "blank_sample_ref": ids["blank"],
        "condition_refs": [ids["condition"]], "time_unit_ref": ids["min"],
        "concentration_unit_ref": ids["uM"], "rate_unit_ref": ids["uM_min"],
        "dataset_source_ref": ids["dataset"], "assessment_refs": [],
        "source_claim": {"subject_refs": [ids["protein"]], "predicate": "catalyzes",
            "value": deepcopy(relation), "context_refs": [ids["condition"]]}}
    samples = {"protein": ids["treated"], "blank": ids["blank"]}
    # These are pre-existing typed literature findings in the review input.
    # A literature pipeline would supply them; no model is invoked here.
    observations = _observations_from_table(literature_text, records[ids["literature"]], manifest, samples,
        kind="assay_report", origin="extracted")
    records.update({row["id"]: row for row in observations})
    literature_selection = {**deepcopy(manifest), "observation_refs": [row["id"] for row in observations]}
    return {"ids": ids, "records": records, "dataset_csv": csv_text,
        "synthetic_literature_table": literature_text, "dataset_selection": manifest,
        "literature_selection": literature_selection, "sample_labels": samples}


def example():
    fixture = synthetic_fixture()
    dataset = populate_from_dataset(fixture["dataset_csv"], fixture["records"],
        fixture["dataset_selection"], fixture["sample_labels"])
    literature = populate_from_literature(fixture["records"], fixture["literature_selection"])
    return {"fixture_notice": "WHOLLY SYNTHETIC: no real scientific finding; unadopted review artifact.",
        "inputs": fixture, "python_reader_returns": {"dataset": dataset, "literature": literature,
            "merged_same_experiment": merge_same_experiment(dataset, literature)}}


if __name__ == "__main__":
    print(json.dumps(example(), ensure_ascii=False, indent=2, allow_nan=False))
