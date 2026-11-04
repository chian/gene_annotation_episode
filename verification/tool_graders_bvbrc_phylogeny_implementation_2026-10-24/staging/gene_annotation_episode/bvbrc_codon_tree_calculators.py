"""Pure CodonTree arithmetic on saved documents and explicit populations.

These functions reproduce the named native formulas, without family selection,
alignment parsing, source acquisition or annotation-confidence conversion.
Provider assembly validates source custody and historical-stage provenance;
these checks validate the supplied operands and relationships they consume.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import math
import re

from . import phylogeny_calculation_contracts as c
from .phylogeny_format_contracts import validate_alignment_document


_REASONS = {
    "codon_alignment_population_incomplete": ("output_bytes", "alignment"),
    "genome_population_required": ("input_metadata", "main_genome_population"),
    "family_population_required": ("input_metadata", "family_population"),
    "family_membership_required": ("scientific_metadata", "family_genome_membership"),
    "evaluated_family_population_required": ("input_metadata", "pretrim_family_population"),
    "pretrim_sequence_population_required": ("input_metadata", "pretrim_sequence_population"),
    "pretrim_sequence_measurement_required": ("output_bytes", "pretrim_sequence_statistics"),
}
_SHEET_KEYS = {
    "schema_version", "tool", "mode", "inputs", "artifact_refs", "observed_run", "documents", "joins",
    "populations", "genomes", "families", "models", "native_measurements", "support_observations",
    "dependence_groups", "qualifications", "missing_requirements", "assembly", "read_outcomes",
}
_FAMILY_KEYS = {
    "family_id", "namespace", "matrix", "matrix_completeness", "memberships", "inclusion",
    "native_statistic_observation_ids", "final_block_indices",
}
_QUANTITY_KEYS = {
    "value", "state", "unit", "origin", "numerator", "denominator", "population_ref", "method",
    "evidence", "requirement_ids",
}
_GENOME_STAGES = (
    "requested_main", "requested_optional", "actually_forwarded_optional", "returned_family_records",
    "used_final_alignment", "used_final_tree",
)
_FAMILY_STAGES = ("returned", "eligible", "evaluated_pretrim", "selected")
_ADJUSTMENT = 0.00001


def _require(ok, code):
    c.require(ok, "codon_" + code)


def _scope_requirement(reason, *segments):
    return c.scope(*segments) + "/" + reason


def _state(*states):
    """Keep unavailable causes distinct, with incompatibility taking priority."""
    for state in ("incompatible", "failed", "truncated", "missing", "not_measured"):
        if state in states:
            return state
    return "missing"


def _sum(values):
    try:
        result = math.fsum(values)
    except (ValueError, OverflowError):
        c.fail("codon_arithmetic_nonfinite")
    _require(math.isfinite(result), "arithmetic_nonfinite")
    return result


def _quantity(value, pid, unit, method, *, requirements=(), state="missing", numerator=None, denominator=None):
    return c.quantity(value, population=pid, unit=unit, method=method, requirements=sorted(set(requirements)),
                      state=state, numerator=numerator, denominator=denominator)


def native_codon_literal_statistics(alignment: dict, *, population: dict) -> dict:
    """Literal c/n arithmetic, including gaps only in per-row log frequencies.

    Site sums exclude '-' and include every other literal symbol. Their sum
    divides L for the mean and sqrt(L) for the native family ranking statistic.
    Row means divide the sum of log2(c/n), including the row's gap states, by L.
    An empty matrix has actual zero counts and undefined statistics. A partial
    population never supplies a complete matrix denominator.
    """
    alignment = validate_alignment_document(alignment)
    c.alignment_population(population, alignment)
    pid = population["population_id"]
    selected, columns = population["row_indices"], population["columns_0based"]
    n, length = len(selected), len(columns)
    complete = alignment["completeness"] == population["completeness"] == "complete"
    state = "truncated" if "truncated" in (alignment["completeness"], population["completeness"]) else "missing"
    reqs = [] if complete else [_scope_requirement("codon_alignment_population_incomplete", pid)]
    sequences = {r["row_index"]: r["sequence"] for r in alignment["rows"]}
    counts = [Counter(sequences[i][j] for i in selected if j < len(sequences[i])) for j in columns]
    usable = complete and n > 0 and length > 0
    squared = [_sum((count / n) ** 2 for symbol, count in site.items() if symbol != "-")
               if usable else None for site in counts]
    total = _sum(squared) if usable else None
    gaps = sum(site["-"] for site in counts) if complete else None

    def q(value, unit, method, **kwargs):
        return _quantity(value, pid, unit, method, requirements=reqs, state=state, **kwargs)

    rows = []
    for i in selected:
        log_sum = _sum(math.log2(site[sequences[i][j]] / n) for j, site in zip(columns, counts)) if usable else None
        rows.append({"row_index": i, "mean_log2_literal_frequency": q(
            log_sum / length if usable else None, "bits_per_column", "row_mean_log2_literal_frequency",
            numerator=log_sum, denominator=length if complete else None)})
    return {
        "population_id": pid,
        "n_rows": q(n if complete else None, "rows", "selected_row_count"),
        "n_columns": q(length if complete else None, "columns", "selected_column_count"),
        "gaps": q(gaps, "characters", "literal_gap_count"),
        "gap_fraction": q(gaps / (n * length) if usable else None, "fraction", "literal_gap_fraction",
                          numerator=gaps, denominator=n * length if complete else None),
        "literal_nongap_sum_squared_frequency": q(total, "column_summed_squared_fraction", "literal_nongap_sum_squared_frequency"),
        "literal_nongap_mean_squared_frequency": q(total / length if usable else None,
            "mean_squared_fraction", "literal_nongap_mean_squared_frequency", numerator=total,
            denominator=length if complete else None),
        "native_family_ranking_score": q(total / math.sqrt(length) if usable else None,
            "square_root_columns", "native_family_ranking_score", numerator=total,
            denominator=math.sqrt(length) if complete else None),
        "sites": [{"column_0based": j, "sum_squared_frequency": q(value,
            "mean_squared_fraction", "literal_site_nongap_sum_squared_frequency", numerator=
            sum(v * v for s, v in site.items() if s != "-") if complete else None,
            denominator=n * n if complete else None)} for j, site, value in zip(columns, counts, squared)],
        "rows": rows,
    }


def _population(value, kind):
    member_key = "family_ids" if kind == "family" else "genome_ids"
    c.shape(value, {"population_id", member_key, "stage", "completeness", "evidence"},
            "codon_" + kind + "_population_shape_invalid")
    c.text(value["population_id"])
    c.strings(value[member_key])
    _require(value["stage"] in (_FAMILY_STAGES if kind == "family" else _GENOME_STAGES), "population_stage_invalid")
    _require(value["completeness"] in c.COMPLETENESS, "population_completeness_invalid")
    c.evidence(value["evidence"])


def _population_index(rows, kind):
    c.sequence(rows, stored=True)
    result = {}
    for row in rows:
        _population(row, kind)
        _require(row["population_id"] not in result, "duplicate_population_id")
        result[row["population_id"]] = row
    return result


def _family_matrix(family):
    """Validate every matrix row, including explicitly unselected genomes.

    Representation records do not add votes. Their feature/genome lists are
    validated independently; they are never zipped into an inferred mapping.
    Full source-table joins and inclusion provenance belong to provider assembly.
    """
    c.shape(family, _FAMILY_KEYS, "codon_family_shape_invalid")
    c.text(family["family_id"])
    _require(family["namespace"] in ("PGFam", "PLFam"), "family_namespace_invalid")
    _require(family["matrix_completeness"] in c.COMPLETENESS, "matrix_completeness_invalid")
    c.sequence(family["matrix"], stored=True)
    c.sequence(family["memberships"], stored=True)
    c.sequence(family["inclusion"], stored=True)
    c.strings(family["native_statistic_observation_ids"])
    c.unique_indices(family["final_block_indices"])
    matrix, feature_genomes = {}, {}
    for row in family["matrix"]:
        c.shape(row, {"genome_id", "feature_ids"}, "codon_matrix_row_shape_invalid")
        c.text(row["genome_id"])
        c.strings(row["feature_ids"])
        genome = row["genome_id"]
        _require(genome not in matrix, "duplicate_matrix_genome")
        for feature in row["feature_ids"]:
            _require(feature not in feature_genomes, "feature_genome_membership_conflict")
            feature_genomes[feature] = genome
        matrix[genome] = row["feature_ids"]
    membership_records = set()
    for row in family["memberships"]:
        c.shape(row, {"representation", "feature_ids", "genome_ids", "deleted_feature_ids",
                      "missing_codon_feature_ids", "source_table_id", "source_row_index"},
                "codon_representation_membership_shape_invalid")
        _require(row["representation"] in ("protein", "coding_nucleotide"), "representation_invalid")
        for key in ("feature_ids", "genome_ids", "deleted_feature_ids", "missing_codon_feature_ids"):
            c.strings(row[key])
        c.text(row["source_table_id"])
        c.integer(row["source_row_index"])
        identity = (row["source_table_id"], row["source_row_index"])
        _require(identity not in membership_records, "duplicate_representation_record")
        membership_records.add(identity)
        _require(not set(row["feature_ids"]) & set(row["deleted_feature_ids"]), "included_deleted_feature_conflict")
        if family["matrix_completeness"] == "complete":
            _require(all(f in feature_genomes for f in row["feature_ids"] + row["deleted_feature_ids"] +
                         row["missing_codon_feature_ids"]), "representation_feature_outside_matrix")
            _require(set(row["genome_ids"]) <= matrix.keys(), "representation_genome_outside_matrix")
            if row["genome_ids"]:
                _require(all(feature_genomes[f] in row["genome_ids"] for f in row["feature_ids"]),
                         "representation_genome_membership_conflict")
    return matrix


def codon_family_population_components(sheet: dict, *, family_population_id: str,
                                       genome_population_id: str) -> dict:
    """Count explicit feature copies against the caller's two populations.

    present=#genomes with >=1 feature; missing=N-present;
    extra=sum(max(copies-1,0)); presence=present/N; native rank=present-extra.
    A missing genome matrix row is unknown, even if other rows are complete.
    """
    c.shape(sheet, _SHEET_KEYS, "codon_sheet_shape_invalid")
    _require((sheet["schema_version"], sheet["tool"], sheet["mode"]) ==
             ("bvbrc_codon_tree_sheet_v1", "C-L193-CodonTree", "core_genome_codon_protein"), "sheet_identity_conflict")
    c.text(family_population_id)
    c.text(genome_population_id)
    c.shape(sheet["populations"], {"alignments", "leaves", "composition", "taxonomy", "genomes", "families",
                                 "bootstraps", "native"}, "codon_populations_shape_invalid")
    families = _population_index(sheet["populations"]["families"], "family")
    genomes = _population_index(sheet["populations"]["genomes"], "genome")
    _require(not families.keys() & genomes.keys(), "population_id_kind_conflict")
    fp, gp = families.get(family_population_id), genomes.get(genome_population_id)
    c.sequence(sheet["families"], stored=True)
    records = {}
    for family in sheet["families"]:
        c.shape(family, _FAMILY_KEYS, "codon_family_shape_invalid")
        c.text(family["family_id"])
        _require(family["family_id"] not in records, "duplicate_family_id")
        records[family["family_id"]] = family
    fp_complete = fp is not None and fp["completeness"] == "complete"
    gp_complete = gp is not None and gp["completeness"] == "complete"
    fr = [] if fp_complete else [_scope_requirement("family_population_required", family_population_id)]
    gr = [] if gp_complete else [_scope_requirement("genome_population_required", genome_population_id)]
    fstate = c.unavailable_state(fp["completeness"]) if fp else "missing"
    gstate = c.unavailable_state(gp["completeness"]) if gp else "missing"
    num_genomes = len(gp["genome_ids"]) if gp_complete else None
    result_rows = []
    for fid in fp["family_ids"] if fp else ():
        family = records.get(fid)
        matrix = _family_matrix(family) if family else None
        matrix_complete = family is not None and family["matrix_completeness"] == "complete"
        covered = matrix is not None and (gp is None or set(gp["genome_ids"]) <= matrix.keys())
        # A complete empty selected genome set needs no membership facts for
        # its empty sums. Supplied records above still undergo validation.
        mr = [] if num_genomes == 0 or matrix_complete and covered else [_scope_requirement(
            "family_membership_required", family_population_id, "family", fid, "genome_population", genome_population_id)]
        # A missing other family changes the family-count denominator, not the
        # supplied genome denominator for this individually identified family.
        reqs = gr + mr
        known = not reqs
        state = _state(gstate if not gp_complete else "available",
                       c.unavailable_state(family["matrix_completeness"]) if family else "missing")
        copies = [len(matrix[g]) for g in gp["genome_ids"]] if known else []
        present = sum(count > 0 for count in copies) if known else None
        extra = sum(max(count - 1, 0) for count in copies) if known else None

        def q(value, unit, method, **kwargs):
            return _quantity(value, genome_population_id, unit, method, requirements=reqs, state=state, **kwargs)

        result_rows.append({"family_id": fid,
            "present_genomes": q(present, "genomes", "family_present_genomes"),
            "missing_genomes": q(num_genomes - present if known else None, "genomes", "family_missing_genomes"),
            "extra_copies": q(extra, "features", "family_extra_copies"),
            "presence_fraction": q(present / num_genomes if known and num_genomes else None,
                "fraction", "family_presence_fraction", numerator=present, denominator=num_genomes),
            "native_initial_family_rank": q(present - extra if known else None, "count", "native_initial_family_rank",
                                            numerator=present - extra if known else None)})
    return {"family_population_id": family_population_id, "genome_population_id": genome_population_id,
        "population_genomes": _quantity(num_genomes, genome_population_id, "genomes", "selected_genome_count",
                                         requirements=gr, state=gstate),
        "population_families": _quantity(len(fp["family_ids"]) if fp_complete else None, family_population_id,
            "families", "selected_family_count", requirements=fr, state=fstate), "rows": result_rows}


def _mean_quantity(value):
    c.shape(value, _QUANTITY_KEYS, "codon_pretrim_quantity_shape_invalid")
    _require(value["unit"] == "bits_per_column", "pretrim_quantity_unit_conflict")
    _require(value["origin"] in ("native_observed", "derived"), "pretrim_quantity_origin_conflict")
    _require(value["state"] in c.STATES, "pretrim_quantity_state_invalid")
    for key in ("value", "numerator", "denominator"):
        c.number(value[key], nullable=True)
    _require((value["value"] is not None) == (value["state"] == "available"), "pretrim_quantity_value_state_conflict")
    c.text(value["population_ref"])
    c.text(value["method"])
    c.evidence(value["evidence"])
    c.strings(value["requirement_ids"])
    for rid in value["requirement_ids"]:
        _requirement(rid)
    # Source population_ref may identify the family's native alignment. It is
    # not rewritten to the evaluated-family denominator's population identity.


def native_codon_worst_sequence_ratios(*, pretrim_sequence_rows: tuple[dict, ...],
                                      evaluated_family_population: dict) -> dict:
    """Historical row/(same-genome mean - 1e-5), without selecting survivors.

    Expected feature identities define the denominator. An absent row has an
    unknown genome and can affect every mean. A present row with a missing value
    affects its stated genome only. Positive log frequencies produce incompatible
    derived quantities; their original signed values remain in input/numerators.
    """
    ep = evaluated_family_population
    c.shape(ep, {"population", "expected_sequence_memberships", "completeness"}, "codon_evaluated_population_shape_invalid")
    fp = ep["population"]
    _population(fp, "family")
    _require(fp["stage"] == "evaluated_pretrim", "historical_pretrim_stage_required")
    _require(ep["completeness"] in c.COMPLETENESS, "evaluated_completeness_invalid")
    c.sequence(ep["expected_sequence_memberships"], stored=True)
    pid, family_ids = fp["population_id"], fp["family_ids"]
    expected, feature_family = {}, {}
    for row in ep["expected_sequence_memberships"]:
        c.shape(row, {"family_id", "feature_ids"}, "codon_expected_membership_shape_invalid")
        c.text(row["family_id"])
        c.strings(row["feature_ids"])
        fid = row["family_id"]
        _require(fid in family_ids, "expected_family_outside_population")
        _require(fid not in expected, "duplicate_expected_family")
        expected[fid] = row["feature_ids"]
        for feature in row["feature_ids"]:
            _require(feature not in feature_family, "feature_family_membership_conflict")
            feature_family[feature] = fid
    c.sequence(pretrim_sequence_rows)
    rows, by_genome, seen_features = {}, defaultdict(list), set()
    for row in pretrim_sequence_rows:
        c.shape(row, {"family_id", "feature_id", "genome_id", "value"}, "codon_pretrim_row_shape_invalid")
        for key in ("family_id", "feature_id", "genome_id"):
            c.text(row[key])
        fid, feature = row["family_id"], row["feature_id"]
        _require(fid in family_ids, "pretrim_family_outside_population")
        _require(fid not in expected or feature in expected[fid], "pretrim_feature_outside_population")
        _require(feature not in feature_family or feature_family[feature] == fid, "feature_family_membership_conflict")
        _require(feature not in seen_features, "duplicate_pretrim_feature")
        seen_features.add(feature)
        _mean_quantity(row["value"])
        rows[(fid, feature)] = row
        by_genome[row["genome_id"]].append(row)
    global_reqs, global_states = [], []
    if fp["completeness"] != "complete":
        global_reqs.append(_scope_requirement("evaluated_family_population_required", pid))
        global_states.append(c.unavailable_state(fp["completeness"]))
    if ep["completeness"] != "complete" or set(expected) != set(family_ids):
        global_reqs.append(_scope_requirement("pretrim_sequence_population_required", pid))
        global_states.append(c.unavailable_state(ep["completeness"]))
    for fid, features in expected.items():
        for feature in features:
            if (fid, feature) not in rows:
                global_reqs.append(_scope_requirement("pretrim_sequence_population_required", pid, "family", fid, "feature", feature))
                global_states.append("missing")
    means, genome_requirements, genome_states = {}, {}, {}
    output_means = []
    for genome, records in by_genome.items():
        reqs, states = list(global_reqs), list(global_states)
        values = [row["value"]["value"] for row in records]
        for row in records:
            value = row["value"]
            reqs.extend(value["requirement_ids"])
            if value["value"] is None:
                if value["state"] != "incompatible":
                    reqs.append(_scope_requirement("pretrim_sequence_measurement_required", pid, "family", row["family_id"],
                                                   "genome", genome, "feature", row["feature_id"]))
                states.append(value["state"])
            elif value["value"] > 0:
                states.append("incompatible")
        identity_complete = not global_reqs
        numerator = _sum(values) if identity_complete and all(v is not None for v in values) else None
        denominator = len(records) if identity_complete else None
        mean = numerator / denominator if numerator is not None and not states else None
        means[genome] = mean
        genome_requirements[genome] = reqs
        genome_states[genome] = _state(*states)
        output_means.append({"genome_id": genome, "sequence_observations": sum(v is not None for v in values),
            "mean": _quantity(mean, pid, "bits_per_column", "pretrim_same_genome_mean_log2_frequency",
                requirements=reqs, state=genome_states[genome], numerator=numerator, denominator=denominator)})
    output_rows, family_rows = [], defaultdict(list)
    for (fid, feature), row in rows.items():
        genome, numerator = row["genome_id"], row["value"]["value"]
        denominator = means[genome] - _ADJUSTMENT if means[genome] is not None else None
        ratio = numerator / denominator if numerator is not None and denominator is not None else None
        # A positive value makes the genome mean incompatible, so no ratio is
        # emitted from it. No clamping, >8 gate or alternative population exists.
        q = _quantity(ratio, pid, "ratio", "native_worst_sequence_ratio", numerator=numerator, denominator=denominator,
                      requirements=genome_requirements[genome], state=genome_states[genome])
        output_rows.append({"family_id": fid, "feature_id": feature, "genome_id": genome, "ratio": q})
        family_rows[fid].append(q)
    maxima = []
    for fid in family_ids:
        quantities = family_rows[fid]
        reqs = global_reqs + [rid for q in quantities for rid in q["requirement_ids"]]
        states = global_states + [q["state"] for q in quantities if q["value"] is None]
        complete = not reqs and not states and fid in expected and len(quantities) == len(expected[fid])
        maximum = max(q["value"] for q in quantities) if complete and quantities else None
        maxima.append({"family_id": fid, "maximum": _quantity(maximum, pid, "ratio",
            "native_family_maximum_worst_sequence_ratio", requirements=reqs, state=_state(*states))})
    missing = set(global_reqs)
    for reqs in genome_requirements.values():
        missing.update(reqs)
    return {"family_population_id": pid, "genome_means": output_means, "rows": output_rows,
            "family_maxima": maxima, "denominator_adjustment": _ADJUSTMENT,
            "missing_requirements": [_requirement(rid) for rid in sorted(missing)]}


def _requirement(rid):
    prefix, separator, reason = rid.rpartition("/")
    _require(bool(separator) and prefix.startswith("phylogeny/") and reason in _REASONS, "requirement_reason_unknown")
    segments = prefix.split("/")[1:]
    _require(bool(segments) and all(segments) and all(re.search(r"%(?!25|2F)", s) is None for s in segments),
             "requirement_scope_invalid")
    kind, role = _REASONS[reason]
    return {"requirement_id": rid, "kind": kind, "role": role, "source_refs": [], "reason_code": reason}


def codon_calculation_requirements(component: dict) -> list[dict]:
    """Resolve only the seven frozen Codon missing-input reasons, without I/O.

    Explicit definitions preserve supplied source refs; conflicting meanings or
    unknown reasons fail. Providers merge these with shared requirements after
    calling each helper on its own component family.
    """
    _require(type(component) is dict, "component_shape_invalid")
    emitted, explicit, stack = set(), {}, [component]
    while stack:
        node = stack.pop()
        if type(node) is dict:
            if "requirement_ids" in node:
                c.strings(node["requirement_ids"])
                emitted.update(node["requirement_ids"])
            if "missing_requirements" in node:
                c.sequence(node["missing_requirements"], stored=True)
                for req in node["missing_requirements"]:
                    c.shape(req, {"requirement_id", "kind", "role", "source_refs", "reason_code"}, "codon_requirement_shape_invalid")
                    c.text(req["requirement_id"])
                    c.strings(req["source_refs"])
                    definition = _requirement(req["requirement_id"])
                    _require(all(req[k] == definition[k] for k in ("kind", "role", "reason_code")), "requirement_meaning_conflict")
                    rid = req["requirement_id"]
                    _require(rid not in explicit or explicit[rid] == req, "requirement_meaning_conflict")
                    explicit[rid] = req
            stack.extend(node.values())
        elif type(node) in (list, tuple):
            stack.extend(node)
    return [deepcopy(explicit[rid]) if rid in explicit else _requirement(rid) for rid in sorted(emitted | explicit.keys())]


__all__ = ["native_codon_literal_statistics", "codon_family_population_components",
           "native_codon_worst_sequence_ratios", "codon_calculation_requirements"]
