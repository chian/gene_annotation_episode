"""Closed typed parent forms, adapted from the supplied method_loop boundary.

Sources: episodic_workflow/method_loop/communication.py and the restricted
schema guard in orbital_workflow/orbital_workflow/communication.py. This module
adapts domain string types and reference validation; it never assesses science.
Recorded fields bind to facts instead of asking a second model to compose them.
"""
from __future__ import annotations

import ast
from collections.abc import Mapping
from functools import lru_cache
import json
import math
import re
from typing import Callable

from jsonschema import Draft202012Validator, SchemaError

from .form_reference_validation import form_reference_validation


class ReportBoundaryError(ValueError):
    def __init__(self, message: str, *, code="invalid_form", field=None):
        super().__init__(message)
        self.diagnostic = {"category": "report_format", "code": code, "field": field}


CODE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.:+/\-]{0,127}$")
UNITS = {"dimensionless", "fraction", "percent", "count", "nt", "aa", "bits", "seconds", "bytes"}
REFERENCE_FORMATS = {"reference", "identifier", "accession"}
FORMATS = REFERENCE_FORMATS | {"unit", "mathematical_expression", "dna_sequence", "protein_sequence",
    "alignment_symbol", "alignment_strand", "structure_identifier", "structure_residue_number",
    "structure_insertion_code"}
KEYWORDS = {"type", "properties", "required", "additionalProperties", "items", "minItems", "maxItems",
            "uniqueItems", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "enum", "const",
            "format", "description", "x-reference-namespace", "x-source"}


def plain(value):
    if isinstance(value, Mapping):
        return {k: plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def _finite(value, path="report"):
    if isinstance(value, float) and not math.isfinite(value):
        raise ReportBoundaryError("Non-finite report number", code="nonfinite_number", field=path)
    if isinstance(value, Mapping):
        for key, child in value.items():
            _finite(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for i, child in enumerate(value):
            _finite(child, f"{path}[{i}]")


def _expression(value):
    try:
        tree = ast.parse(value, mode="eval")
    except (SyntaxError, ValueError):
        return False
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Name, ast.Load, ast.Constant,
               ast.Call, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.USub, ast.UAdd)
    functions = {"sqrt", "sin", "cos", "exp", "log", "abs"}
    for node in ast.walk(tree):
        if not isinstance(node, allowed):
            return False
        if isinstance(node, ast.Constant) and (type(node.value) not in (int, float) or not math.isfinite(node.value)):
            return False
        if isinstance(node, ast.Call) and (not isinstance(node.func, ast.Name) or node.func.id not in functions or node.keywords):
            return False
    return True


def _schema_cacheable(value):
    """Only exact finite JSON content can use the compilation cache."""
    kind = type(value)
    if value is None or kind in (str, int, bool):
        return True
    if kind is float:
        return math.isfinite(value)
    if kind is dict:
        return all(type(key) is str and _schema_cacheable(child)
                   for key, child in value.items())
    if kind is list:
        return all(_schema_cacheable(child) for child in value)
    return False


@lru_cache(maxsize=128)
def _compiled_schema_content(content):
    # lru_cache retains successful calls only. This process-local grammar
    # verdict contains no payload, reference, possession or scientific fact.
    _compile_closed_schema(json.loads(content))


def validate_closed_schema(schema):
    """Compile a parent-chosen form and return its current detached tree."""
    schema = plain(schema)
    try:
        content = (json.dumps(schema, separators=(",", ":"), allow_nan=False).encode("utf-8")
                   if _schema_cacheable(schema) else None)
    except (ValueError, TypeError, OverflowError, RecursionError):
        content = None
    if content is None:
        return _compile_closed_schema(schema)
    try:
        _compiled_schema_content(content)
    except (ValueError, TypeError, OverflowError, RecursionError):
        # Preserve the original input's diagnostics, including unsupported
        # objects and failures that cannot be represented by the fast path.
        return _compile_closed_schema(schema)
    return schema


def _compile_closed_schema(schema):
    """Closed-form grammar plus exact registered facts; errors are never cached."""
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ReportBoundaryError(exc.message, code="invalid_schema") from exc

    native_blast_sources = None
    standard_blast_sources = None
    rna_structure_sources = None
    protein_structure_sources = None
    genomic_overlap_sources = None
    chromatin_sources = None
    atac_sources = None
    expression_nmf_sources = None
    flux_balance_sources = None
    fluorescence_sources = None
    masking_sources = None
    blast_utility_sources = None

    def check(node, path, depth=0):
        nonlocal native_blast_sources, standard_blast_sources, rna_structure_sources, protein_structure_sources, genomic_overlap_sources
        nonlocal chromatin_sources, atac_sources, expression_nmf_sources, fluorescence_sources
        nonlocal flux_balance_sources
        nonlocal masking_sources, blast_utility_sources
        source = node.get("x-source") if isinstance(node, dict) else None
        if source == "bvbrc_application_outcomes":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .bvbrc_application_returns import application_fact_sources
            expected = application_fact_sources()[source]["report_schema"]
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: application fact schema must match its registered source", code="invalid_schema")
            return
        if source == "somatic_variant_outcomes":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .somatic_variant_contracts import somatic_fact_sources
            expected = somatic_fact_sources()[source]["report_schema"]
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: somatic fact schema must match its registered source", code="invalid_schema")
            return
        if source == "esm_gene_embedding_outcomes":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .esm_gene_embedding_contracts import esm_gene_embedding_fact_sources
            expected = esm_gene_embedding_fact_sources()[source]["report_schema"]
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: ESM fact schema must match its registered source", code="invalid_schema")
            return
        if source == "protein_conservation_outcomes":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .protein_conservation_result_contracts import conservation_fact_sources
            expected = conservation_fact_sources()[source]["report_schema"]
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: conservation fact schema must match its registered source", code="invalid_schema")
            return
        if source == "protein_phylogeny_outcomes":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .protein_phylogeny_result_contracts import phylogeny_fact_sources
            expected = phylogeny_fact_sources()[source]["report_schema"]
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: phylogeny fact schema must match its registered source", code="invalid_schema")
            return
        if source == "primer_placement_outcomes":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .primer_placement_result_contracts import ordinary_primer_placement_fact_sources
            expected = ordinary_primer_placement_fact_sources()[source]["report_schema"]
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: primer placement fact schema must match its registered source", code="invalid_schema")
            return
        if source == "protein_disorder_outcomes":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .protein_disorder_result_contracts import ordinary_disorder_fact_sources
            expected = ordinary_disorder_fact_sources()[source]["report_schema"]
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: protein disorder fact schema must match its registered source", code="invalid_schema")
            return
        if source == "arsenic_speciation_outcomes":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .arsenic_speciation_result_contracts import ordinary_arsenic_fact_sources
            expected = ordinary_arsenic_fact_sources()[source]["report_schema"]
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: arsenic speciation fact schema must match its registered source", code="invalid_schema")
            return
        if source == "vcf_result_outcomes":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .vcf_result_tools import vcf_result_fact_sources
            expected = vcf_result_fact_sources()[source]["report_schema"]
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: VCF result fact schema must match its registered source", code="invalid_schema")
            return
        if source == "tf_binding_outcomes":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .tf_binding_result_contracts import tf_binding_fact_sources
            expected = tf_binding_fact_sources()[source]["report_schema"]
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: TF binding fact schema must match its registered source", code="invalid_schema")
            return
        if source == "protease_kinetics_outcomes":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .protease_kinetics_result_contracts import ordinary_protease_kinetics_fact_sources
            expected = ordinary_protease_kinetics_fact_sources()[source]["report_schema"]
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: protease kinetics fact schema must match its registered source", code="invalid_schema")
            return
        if source == "homer_motif_outcomes":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .homer_motif_result_contracts import homer_motif_fact_sources
            expected = homer_motif_fact_sources()[source]["report_schema"]
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: HOMER motif fact schema must match its registered source", code="invalid_schema")
            return
        if source == "macs2_peak_outcomes":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .macs2_peak_result_contracts import macs2_peak_fact_sources
            expected = macs2_peak_fact_sources()[source]["report_schema"]
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: MACS2 peak fact schema must match its registered source", code="invalid_schema")
            return
        if source == "reference_edit_outcomes":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .reference_edit_outcome_tools import reference_edit_outcome_fact_sources
            expected = reference_edit_outcome_fact_sources()[source]["report_schema"]
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: reference editing outcome fact schema must match its registered source", code="invalid_schema")
            return
        if source == "orf_measurements":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .molecular_sequence_result_contracts import ordinary_orf_fact_sources
            expected = ordinary_orf_fact_sources()[source]["report_schema"]
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: ORF fact schema must match its registered source", code="invalid_schema")
            return
        if source == "n_glycosylation_motif_outcomes":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .molecular_sequence_result_contracts import ordinary_molecular_sequence_fact_sources
            expected = ordinary_molecular_sequence_fact_sources("find_n_glycosylation_motifs")[source]["report_schema"]
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: N-glycosylation fact schema must match its registered source", code="invalid_schema")
            return
        if source == "o_glycosylation_hotspot_outcomes":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .molecular_sequence_result_contracts import ordinary_molecular_sequence_fact_sources
            expected = ordinary_molecular_sequence_fact_sources("predict_o_glycosylation_hotspots")[source]["report_schema"]
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: O-glycosylation fact schema must match its registered source", code="invalid_schema")
            return
        if isinstance(source, str) and source in {"protein_structure_action_views", "protein_structure_action_sequences",
                "protein_structure_action_saved_sheets"}:
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .protein_structure_action_records import protein_structure_action_fact_sources
            expected = protein_structure_action_fact_sources()[source]["report_schema"]
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: protein action fact schema must match its registered source", code="invalid_schema")
            return
        if source == "execution_addgene_sequence_facts":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .addgene_sequence_facts import ADDGENE_SEQUENCE_FACTS_SCHEMA
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(ADDGENE_SEQUENCE_FACTS_SCHEMA, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: Addgene fact schema must match its registered source", code="invalid_schema")
            return
        if source == "circular_dichroism_summaries":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .circular_dichroism_contracts import circular_dichroism_fact_sources
            expected = circular_dichroism_fact_sources()[source]["report_schema"]
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: CD fact schema must match its registered source", code="invalid_schema")
            return
        if source == "liftover_point_mappings":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .liftover_contracts import liftover_fact_sources
            expected = liftover_fact_sources()[source]["report_schema"]
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: liftover fact schema must match its registered source", code="invalid_schema")
            return
        if isinstance(source, str) and source in {"execution_enrichr_tables", "execution_enrichr_rows"}:
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .enrichr_contracts import enrichr_fact_sources
            expected = enrichr_fact_sources()[source]["report_schema"]
            # Literal native labels and numeric tokens belong to this exact
            # recorded contract. Payload, reference and custody validation
            # still apply; generic model-authored strings remain restricted.
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: Enrichr fact schema must match its registered source", code="invalid_schema")
            return
        if source == "execution_file_capture_outcomes":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .local_file_capture_results import OUTCOMES_SCHEMA
            # Native paths and status text are recorded custody facts. Only
            # this exact complete source-owned contract admits those strings;
            # Draft value and semantic-reference validation still run below.
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(OUTCOMES_SCHEMA, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: file capture fact schema must match its registered source", code="invalid_schema")
            return
        if isinstance(source, str) and source.startswith("execution.blast_utility_"):
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            if blast_utility_sources is None:
                from .blast_utility_result_views import blast_utility_fact_sources
                from .blast_utility_historical_fact_schemas import blast_utility_historical_fact_schemas
                historical = blast_utility_historical_fact_schemas()
                blast_utility_sources = {
                    key: (value["report_schema"], *historical.get(key, ()))
                    for key, value in blast_utility_fact_sources().items()}
            expected = blast_utility_sources.get(source, ())
            # Saved parents keep their exact registered contract. Older enum
            # populations are not inferred from a caller's narrower schema.
            if (not expected or not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    not in {json.dumps(tree, sort_keys=True, allow_nan=False) for tree in expected}):
                raise ReportBoundaryError(f"{path}: BLAST utility fact schema must match its registered source", code="invalid_schema")
            return
        if isinstance(source, str) and source.startswith("execution.masking_"):
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            if masking_sources is None:
                from .sequence_masking_result_views import masking_fact_sources
                masking_sources = masking_fact_sources()
            expected = masking_sources.get(source, {}).get("report_schema")
            if (expected is None or not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: masking fact schema must match its registered source", code="invalid_schema")
            return
        if source == "uniprot_selected_returns":
            if depth != 1:
                raise ReportBoundaryError("UniProt facts require a whole top-level field",
                    code="uniprot_original_schema_conflict", field=path)
            from .uniprot_return_contracts import requested_uniprot_selection, UniProtReturnValidationError
            try:
                requested_uniprot_selection(schema)
            except UniProtReturnValidationError as error:
                field = error.field or path
                if field.startswith("selection"):
                    field = path + ".x-uniprot-selection" + field[len("selection"):]
                elif field.startswith("properties."):
                    field = "report." + field[len("properties."):]
                raise ReportBoundaryError("Invalid selected UniProt fact schema",
                    code=error.code, field=field) from error
            return
        if source == "bvbrc_minhash_calculation_diagnostics":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .bvbrc_minhash_views import minhash_fact_sources
            expected = minhash_fact_sources()[source]["report_schema"]
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: MinHash diagnostic schema must match its registered source", code="invalid_schema")
            return
        if isinstance(source, str) and source.startswith("fluorescence_"):
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            if fluorescence_sources is None:
                from .fluorescence_return_views import fluorescence_fact_sources
                fluorescence_sources = fluorescence_fact_sources()
            expected = fluorescence_sources.get(source, {}).get("report_schema")
            if (expected is None or not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: fluorescence fact schema must match its registered source", code="invalid_schema")
            return
        if isinstance(source, str) and source.startswith("flux_balance_"):
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            if flux_balance_sources is None:
                from .flux_balance_return_views import fba_fact_sources
                flux_balance_sources = fba_fact_sources()
            expected = flux_balance_sources.get(source, {}).get("report_schema")
            if (expected is None or not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: FBA fact schema must match its registered source", code="invalid_schema")
            return
        if isinstance(source, str) and source.startswith("expression_nmf_"):
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            if expression_nmf_sources is None:
                from .expression_nmf_return_views import expression_nmf_fact_sources
                expression_nmf_sources = expression_nmf_fact_sources()
            expected = expression_nmf_sources.get(source, {}).get("report_schema")
            if (expected is None or not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: NMF fact schema must match its registered source", code="invalid_schema")
            return
        if isinstance(source, str) and source.startswith("atac_differential_"):
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            if atac_sources is None:
                from .atac_differential_return_views import atac_fact_sources
                atac_sources = atac_fact_sources()
            expected = atac_sources.get(source, {}).get("report_schema")
            if (expected is None or not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: ATAC fact schema must match its registered source", code="invalid_schema")
            return
        if isinstance(source, str) and source.startswith("chromatin_interaction_"):
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            if chromatin_sources is None:
                from .chromatin_interaction_return_views import FACT_SOURCES, chromatin_fact_schema_alternatives
                chromatin_sources = {key: chromatin_fact_schema_alternatives(key) for key in FACT_SOURCES}
            expected = chromatin_sources.get(source, ())
            if (not expected or not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    not in {json.dumps(tree, sort_keys=True, allow_nan=False) for tree in expected}):
                raise ReportBoundaryError(f"{path}: chromatin fact schema must match its registered source", code="invalid_schema")
            return
        if source == 'literature_concentration_window_cells':
            if depth != 1:
                raise ReportBoundaryError(f'{path}: fact bindings apply to whole top-level fields', code='invalid_schema')
            from .literature_concentration_window_storage import CONCENTRATION_WINDOW_CELLS_SCHEMA_V1
            if (not _schema_cacheable(node) or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(CONCENTRATION_WINDOW_CELLS_SCHEMA_V1, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f'{path}: concentration-window schema must match its registered source', code='invalid_schema')
            return
        if source == 'literature_measurement_comparison_cells':
            if depth != 1:
                raise ReportBoundaryError(f'{path}: fact bindings apply to whole top-level fields', code='invalid_schema')
            from .literature_measurement_comparison_storage import MEASUREMENT_COMPARISON_CELLS_SCHEMA_V2
            if (not _schema_cacheable(node) or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(MEASUREMENT_COMPARISON_CELLS_SCHEMA_V2, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f'{path}: comparison schema must match its registered source', code='invalid_schema')
            return
        if source == 'literature_kinetic_summary_precision_cells':
            if depth != 1:
                raise ReportBoundaryError(f'{path}: fact bindings apply to whole top-level fields', code='invalid_schema')
            from .literature_kinetic_summary_precision_storage import SUMMARY_PRECISION_CELLS_SCHEMA_V1
            if (not _schema_cacheable(node) or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(SUMMARY_PRECISION_CELLS_SCHEMA_V1, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f'{path}: summary precision schema must match its registered source', code='invalid_schema')
            return
        if source == "literature_endpoint_signal_cells":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .literature_endpoint_signal_storage import ENDPOINT_SIGNAL_CELLS_SCHEMA_V1
            if (not _schema_cacheable(node) or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(ENDPOINT_SIGNAL_CELLS_SCHEMA_V1, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: endpoint schema must match its registered source", code="invalid_schema")
            return
        if source == "literature_product_coupling_cells":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .literature_product_coupling_storage import product_coupling_cells_schema
            expected = product_coupling_cells_schema()
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: product coupling schema must match its registered source", code="invalid_schema")
            return
        if source == 'literature_parent_depletion_cells':
            if depth != 1:
                raise ReportBoundaryError(f'{path}: fact bindings apply to whole top-level fields', code='invalid_schema')
            from .literature_parent_depletion_storage import parent_depletion_cells_schema
            expected = parent_depletion_cells_schema()
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f'{path}: parent depletion schema must match its registered source', code='invalid_schema')
            return
        if source == 'literature_stoichiometric_balance_cells':
            if depth != 1:
                raise ReportBoundaryError(f'{path}: fact bindings apply to whole top-level fields', code='invalid_schema')
            from .literature_stoichiometric_balance_storage import stoichiometric_balance_cells_schema
            expected = stoichiometric_balance_cells_schema()
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f'{path}: stoichiometric balance schema must match its registered source', code='invalid_schema')
            return
        if source == "literature_measurement_validation_cells":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .literature_measurement_validation_storage import measurement_validation_cells_schema
            expected = measurement_validation_cells_schema()
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: measurement validation schema must match its registered source", code="invalid_schema")
            return
        if source == "literature_ion_discrimination_cells":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .literature_ion_discrimination_storage import ion_discrimination_cells_schema
            expected = ion_discrimination_cells_schema()
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: ion fact schema must match its registered source", code="invalid_schema")
            return
        if source == "literature_channel_cells":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .literature_channel_storage import channel_cells_schema
            expected = channel_cells_schema()
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: channel fact schema must match its registered source", code="invalid_schema")
            return
        if source in {"literature_compiled_assay_cells", "literature_compiled_assay_v2_cells", "literature_compiled_assay_v3_cells"}:
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .literature_compiled_assay_storage import compiled_assay_cells_schema
            expected = compiled_assay_cells_schema(3 if source == 'literature_compiled_assay_v3_cells'
                else 2 if source == "literature_compiled_assay_v2_cells" else 1)
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: compiled assay schema must match its registered source", code="invalid_schema")
            return
        if source == "literature_calibration_recovery_cells":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .literature_calibration_recovery_storage import calibration_recovery_cells_schema
            expected = calibration_recovery_cells_schema()
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: recovery fact schema must match its registered source", code="invalid_schema")
            return
        if source == "literature_rate_grid_cells":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .literature_rate_observation_storage import rate_grid_cells_schema
            expected = rate_grid_cells_schema()
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: reported curve fact schema must match its registered source", code="invalid_schema")
            return
        if source == "literature_rate_observation_cells":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .literature_rate_observation_storage import rate_observation_cells_schema
            expected = rate_observation_cells_schema()
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: reported observation fact schema must match its registered source", code="invalid_schema")
            return
        if source == "literature_rate_replicate_cells":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .literature_rate_replicate_storage import rate_replicate_cells_schema
            expected = rate_replicate_cells_schema()
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: raw replicate fact schema must match its registered source", code="invalid_schema")
            return
        if source in {"literature_intervention_grading_cells", "literature_a106_subscore_cells"}:
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .literature_intervention_storage import intervention_cells_schema
            from .literature_a106_subscore import cells_schema as subscore_schema
            registered = intervention_cells_schema if source == "literature_intervention_grading_cells" else subscore_schema
            if (not _schema_cacheable(node) or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(registered(), sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: intervention grading fact schema must match its registered source", code="invalid_schema")
            return
        if source in {'literature_source_lead_dispositions', 'literature_screening_answers'}:
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code='invalid_schema')
            from .literature_task_credit import LEADS, lead_return_schema, screening_schema
            expected = lead_return_schema() if source == LEADS else screening_schema()
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: literature task fact schema must match its registered source", code='invalid_schema')
            return
        if source == "literature_assay_grading_cells":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .literature_assay_grading_storage import assay_grading_cells_schema, legacy_assay_grading_cells_schema
            expected = (assay_grading_cells_schema(), legacy_assay_grading_cells_schema())
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    not in {json.dumps(item, sort_keys=True, allow_nan=False) for item in expected}):
                raise ReportBoundaryError(f"{path}: assay grading fact schema must match its registered source", code="invalid_schema")
            return
        if source in {'literature_a108_grading_cells', 'literature_a108_aggregation_cells'}:
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code='invalid_schema')
            from .literature_a108_grading_storage import grading_cells_schema
            from .literature_a108_aggregation_storage import aggregation_cells_schema
            registered = grading_cells_schema if source == 'literature_a108_grading_cells' else aggregation_cells_schema
            if (not _schema_cacheable(node) or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(registered(), sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: A108 numerical fact schema must match its registered source", code='invalid_schema')
            return
        if source == 'literature_a105_aggregation_cells':
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code='invalid_schema')
            from .literature_a105_aggregation_storage import aggregation_cells_schema
            if (not _schema_cacheable(node) or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(aggregation_cells_schema(), sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: A105 aggregation fact schema must match its registered source", code='invalid_schema')
            return
        if source == "literature_completion_time_cells":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .literature_completion_time_storage import completion_time_cells_schema
            expected = completion_time_cells_schema()
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: completion time fact schema must match its registered source", code="invalid_schema")
            return
        if source == "literature_active_site_cells":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .literature_active_site_storage import active_site_cells_schema
            expected = active_site_cells_schema()
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: active site fact schema must match its registered source", code="invalid_schema")
            return
        if source == "literature_rate_source_meaning_cells":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .literature_rate_meaning_delivery import rate_source_meaning_cells_schema
            expected = rate_source_meaning_cells_schema()
            # Exact recorded witnesses are permitted only in this complete
            # registered fact view. Generic model-authored strings retain the
            # original closed-form grammar and saved-value custody checks.
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: rate meaning fact schema must match its registered source", code="invalid_schema")
            return
        if isinstance(source, str) and source.startswith("genomic_overlap_"):
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            if genomic_overlap_sources is None:
                from .genomic_overlap_return_views import genomic_overlap_fact_sources
                genomic_overlap_sources = genomic_overlap_fact_sources()
            expected = genomic_overlap_sources.get(source, {}).get("report_schema")
            if (expected is None or not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: overlap fact schema must match its registered source", code="invalid_schema")
            return
        if source == "literature_perturbation_operand_cells":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .literature_perturbation_operands import cells_schema
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(cells_schema(), sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: perturbation operand fact schema must match its registered source", code="invalid_schema")
            return
        if source == "literature_perturbation_summary_cells":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .literature_perturbation_summary_storage import perturbation_summary_cells_schema
            # Only these complete registered fact contracts permit their
            # optional premise metadata. Generic object/keyword rules remain
            # unchanged. Actual saved-value checks prevent dropping a basis
            # supplied by the source-bound measurement recipe.
            expected = (perturbation_summary_cells_schema(),
                perturbation_summary_cells_schema(include_covariance_interpretations=False),
                perturbation_summary_cells_schema(include_interpretation_basis=False))
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    not in {json.dumps(item, sort_keys=True, allow_nan=False) for item in expected}):
                raise ReportBoundaryError(f"{path}: perturbation summary fact schema must match its registered source", code="invalid_schema")
            return
        if source == "literature_controlled_response_component_cells":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .literature_controlled_response_storage import controlled_response_cells_schema
            expected = controlled_response_cells_schema()
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: controlled response fact schema must match its registered source", code="invalid_schema")
            return
        if source == "literature_gel_component_cells":
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            from .literature_gel_storage import gel_cells_schema
            expected = gel_cells_schema()
            if (not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: gel fact schema must match its registered source", code="invalid_schema")
            return
        if isinstance(source, str) and source.startswith("execution_protein_structure_"):
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            if protein_structure_sources is None:
                from .protein_structure_result_views import protein_structure_fact_sources
                protein_structure_sources = protein_structure_fact_sources()
            original = protein_structure_sources.get(source, {}).get("report_schema")
            expected = None if original is None else {**original, "x-source": source}
            if (expected is None or not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: protein fact schema must match its registered source", code="invalid_schema")
            return
        if isinstance(source, str) and source.startswith("execution_rna_structure_"):
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            if rna_structure_sources is None:
                from .rna_structure_result_views import rna_structure_fact_sources
                from .rna_structure_comparison_views import rna_comparison_fact_sources
                rna_structure_sources = rna_structure_fact_sources()
                rna_structure_sources.update(rna_comparison_fact_sources())
            expected = rna_structure_sources.get(source, {}).get("report_schema")
            # Recorded RNA fields have exact units, nullable associations and
            # native labels. They do not grant a free-form model schema.
            if (expected is None or not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: RNA fact schema must match its registered source", code="invalid_schema")
            return
        if isinstance(source, str) and source.startswith("execution_blast_standard_database_"):
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            if standard_blast_sources is None:
                from .native_blast_standard_database_result_views import standard_blast_database_fact_sources
                standard_blast_sources = standard_blast_database_fact_sources()
            expected = standard_blast_sources.get(source, {}).get("report_schema")
            # These recorded contracts contain native strings, tagged identities,
            # tuples and numerical relationships outside the generic grammar.
            # Match the complete detached JSON tree, including scalar types;
            # Python equality alone would treat True, 1 and 1.0 as equal.
            if (expected is None or not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: native BLAST fact schema must match its registered source", code="invalid_schema")
            return
        if isinstance(source, str) and source.startswith("execution_blast_database_"):
            if depth != 1:
                raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
            if native_blast_sources is None:
                from .native_blast_database_result_views import native_blast_database_fact_sources
                native_blast_sources = native_blast_database_fact_sources()
            expected = native_blast_sources.get(source, {}).get("report_schema")
            # These recorded contracts contain native strings, tagged identities,
            # tuples and numerical relationships outside the generic grammar.
            # Match the complete detached JSON tree, including scalar types;
            # Python equality alone would treat True, 1 and 1.0 as equal.
            if (expected is None or not _schema_cacheable(node)
                    or json.dumps(node, sort_keys=True, allow_nan=False)
                    != json.dumps(expected, sort_keys=True, allow_nan=False)):
                raise ReportBoundaryError(f"{path}: native BLAST fact schema must match its registered source", code="invalid_schema")
            return
        if not isinstance(node, dict) or set(node) - KEYWORDS:
            raise ReportBoundaryError(f"{path}: unsupported schema keyword", code="invalid_schema")
        declared = node.get("type")
        kinds = set(declared) if isinstance(declared, list) else {declared}
        if not kinds or len(kinds - {"null"}) > 1 or not kinds <= {"object", "array", "number", "integer", "boolean", "null", "string"}:
            raise ReportBoundaryError(f"{path}: explicit single type required", code="invalid_schema")
        if "object" in kinds:
            props = node.get("properties")
            if not isinstance(props, dict) or node.get("additionalProperties") is not False or set(node.get("required", [])) != set(props):
                raise ReportBoundaryError(f"{path}: fields must be explicit, required and closed", code="open_object")
            for name, child in props.items():
                if not CODE.fullmatch(name):
                    raise ReportBoundaryError(f"{path}: invalid field name", code="invalid_schema")
                check(child, path + "." + name, depth + 1)
        elif "array" in kinds:
            if "items" not in node:
                raise ReportBoundaryError(f"{path}: arrays need item types", code="open_array")
            check(node["items"], path + "[]", depth + 1)
        elif "string" in kinds:
            literals = node.get("enum", [node["const"]] if "const" in node else None)
            if literals is not None:
                if not literals or any(v is not None and (not isinstance(v, str) or not CODE.fullmatch(v)) for v in literals):
                    raise ReportBoundaryError(f"{path}: string literals must be declared codes", code="unrestricted_string")
            elif node.get("format") not in FORMATS:
                raise ReportBoundaryError(f"{path}: strings need a declared semantic type", code="unrestricted_string")
        elif "format" in node:
            raise ReportBoundaryError(f"{path}: format only applies to strings", code="invalid_schema")
        for literal in node.get("enum", [node["const"]] if "const" in node else []):
            if isinstance(literal, (dict, list)):
                raise ReportBoundaryError(f"{path}: composite constants cannot bypass fields", code="invalid_schema")
        if "x-reference-namespace" in node and node.get("format") not in REFERENCE_FORMATS:
            raise ReportBoundaryError(f"{path}: reference namespace needs reference type", code="invalid_schema")
        if "x-source" in node and (not isinstance(node["x-source"], str) or not CODE.fullmatch(node["x-source"])):
            raise ReportBoundaryError(f"{path}: fact source must be a registered key", code="invalid_schema")
        if "x-source" in node and (path.count(".") != 1 or "[]" in path):
            raise ReportBoundaryError(f"{path}: fact bindings apply to whole top-level fields", code="invalid_schema")
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise ReportBoundaryError("Report must be a closed object", code="invalid_schema")
    check(schema, "report")
    _finite(schema)
    return schema


def validate_form(payload, schema, reference_resolver: Callable | None = None):
    with form_reference_validation():
        return _validate_form(payload, schema, reference_resolver)


def _validate_form(payload, schema, reference_resolver):
    schema = validate_closed_schema(schema)
    payload = plain(payload)
    for name, node in schema["properties"].items():
        if (node.get("x-source") == "somatic_variant_outcomes"
                and isinstance(payload, dict) and name in payload):
            from .somatic_variant_contracts import validate_somatic_return
            try:
                if type(payload[name]) is not list:
                    raise ValueError("somatic_variant_return_array_required")
                for value in payload[name]:
                    validate_somatic_return(value)
            except ValueError as error:
                raise ReportBoundaryError("Invalid retained somatic variant facts",
                    code=str(error), field=name) from error
        if (node.get("x-source") == "esm_gene_embedding_outcomes"
                and isinstance(payload, dict) and name in payload):
            from .esm_gene_embedding_contracts import validate_esm_embedding_return
            try:
                if type(payload[name]) is not list:
                    raise ValueError("esm_gene_embedding_return_array_required")
                for value in payload[name]:
                    validate_esm_embedding_return(value)
            except ValueError as error:
                raise ReportBoundaryError("Invalid retained ESM representation facts",
                    code=str(error), field=name) from error
        if (node.get("x-source") == "bvbrc_application_outcomes"
                and isinstance(payload, dict) and name in payload):
            from .bvbrc_application_returns import validate_application_rows
            try:
                validate_application_rows(payload[name])
            except (ValueError, TypeError, OverflowError, RecursionError) as error:
                raise ReportBoundaryError("Invalid retained application facts",
                    code=str(error), field=name) from error
        if (node.get("x-source") == "protein_conservation_outcomes"
                and isinstance(payload, dict) and name in payload):
            from .protein_conservation_result_contracts import validate_conservation_return
            try:
                if type(payload[name]) is not list:
                    raise ValueError("protein_conservation_return_array_required")
                for value in payload[name]:
                    validate_conservation_return(value)
            except ValueError as error:
                raise ReportBoundaryError("Invalid retained conservation facts",
                    code=str(error), field=name) from error
        if (node.get("x-source") == "protein_phylogeny_outcomes"
                and isinstance(payload, dict) and name in payload):
            from .protein_phylogeny_result_contracts import validate_phylogeny_return
            try:
                if type(payload[name]) is not list:
                    raise ValueError("protein_phylogeny_return_array_required")
                for value in payload[name]:
                    validate_phylogeny_return(value)
            except ValueError as error:
                raise ReportBoundaryError("Invalid retained phylogeny facts",
                    code=str(error), field=name) from error
        if (node.get("x-source") == "primer_placement_outcomes"
                and isinstance(payload, dict) and name in payload):
            from .primer_placement_result_contracts import validate_ordinary_primer_placement_return
            try:
                if type(payload[name]) is not list:
                    raise ValueError("primer_placement_return_array_required")
                for value in payload[name]:
                    validate_ordinary_primer_placement_return(value)
            except ValueError as error:
                raise ReportBoundaryError("Invalid retained primer placement facts",
                    code=str(error), field=name) from error
        if (node.get("x-source") == "protein_disorder_outcomes"
                and isinstance(payload, dict) and name in payload):
            from .protein_disorder_result_contracts import validate_ordinary_disorder_return
            try:
                if type(payload[name]) is not list:
                    raise ValueError("protein_disorder_return_array_required")
                for value in payload[name]:
                    validate_ordinary_disorder_return(value)
            except ValueError as error:
                raise ReportBoundaryError("Invalid retained protein disorder measurement facts",
                    code=str(error), field=name) from error
        if (node.get("x-source") == "arsenic_speciation_outcomes"
                and isinstance(payload, dict) and name in payload):
            from .arsenic_speciation_result_contracts import validate_ordinary_arsenic_return
            try:
                if type(payload[name]) is not list:
                    raise ValueError("arsenic_speciation_return_array_required")
                for value in payload[name]:
                    validate_ordinary_arsenic_return(value)
            except ValueError as error:
                raise ReportBoundaryError("Invalid retained arsenic speciation measurement facts",
                    code=str(error), field=name) from error
        if (node.get("x-source") == "vcf_result_outcomes"
                and isinstance(payload, dict) and name in payload):
            from .vcf_result_measurements import validate_vcf_return
            try:
                if type(payload[name]) is not list:
                    raise ValueError("vcf_result_return_array_required")
                for value in payload[name]:
                    validate_vcf_return(value)
            except ValueError as error:
                raise ReportBoundaryError("Invalid retained VCF result facts",
                    code=str(error), field=name) from error
        if (node.get("x-source") == "tf_binding_outcomes"
                and isinstance(payload, dict) and name in payload):
            from .tf_binding_result_contracts import validate_tf_binding_return
            try:
                if type(payload[name]) is not list:
                    raise ValueError("tf_binding_return_array_required")
                for value in payload[name]:
                    validate_tf_binding_return(value)
            except ValueError as error:
                raise ReportBoundaryError("Invalid retained native TF score facts",
                    code=str(error), field=name) from error
        if (node.get("x-source") == "protease_kinetics_outcomes"
                and isinstance(payload, dict) and name in payload):
            from .protease_kinetics_result_contracts import validate_ordinary_protease_kinetics_return
            try:
                if type(payload[name]) is not list:
                    raise ValueError("protease_kinetics_return_array_required")
                for value in payload[name]:
                    validate_ordinary_protease_kinetics_return(value)
            except ValueError as error:
                raise ReportBoundaryError("Invalid retained protease kinetics measurement facts",
                    code=str(error), field=name) from error
        if (node.get("x-source") == "homer_motif_outcomes"
                and isinstance(payload, dict) and name in payload):
            from .homer_motif_result_contracts import validate_homer_motif_return
            try:
                if type(payload[name]) is not list:
                    raise ValueError("homer_motif_return_array_required")
                for value in payload[name]:
                    validate_homer_motif_return(value)
            except ValueError as error:
                raise ReportBoundaryError("Invalid retained native HOMER motif facts",
                    code=str(error), field=name) from error
        if (node.get("x-source") == "macs2_peak_outcomes"
                and isinstance(payload, dict) and name in payload):
            from .macs2_peak_result_contracts import validate_macs2_peak_return
            try:
                if type(payload[name]) is not list:
                    raise ValueError("macs2_peak_return_array_required")
                for value in payload[name]:
                    validate_macs2_peak_return(value)
            except ValueError as error:
                raise ReportBoundaryError("Invalid retained native MACS2 peak facts",
                    code=str(error), field=name) from error
        if (node.get("x-source") == "reference_edit_outcomes"
                and isinstance(payload, dict) and name in payload):
            from .reference_edit_outcomes import validate_reference_edit_outcome_return
            try:
                if type(payload[name]) is not list:
                    raise ValueError("reference_edit_outcome_return_array_required")
                for value in payload[name]:
                    validate_reference_edit_outcome_return(value)
            except ValueError as error:
                raise ReportBoundaryError("Invalid retained reference editing outcome facts",
                    code=str(error), field=name) from error
        if (node.get("x-source") == "orf_measurements"
                and isinstance(payload, dict) and name in payload):
            from .molecular_sequence_result_contracts import validate_ordinary_orf_return
            try:
                if type(payload[name]) is not list:
                    raise ValueError("ordinary_orf_return_array_required")
                for value in payload[name]:
                    validate_ordinary_orf_return(value)
            except ValueError as error:
                raise ReportBoundaryError("Invalid retained ORF measurement facts",
                    code=str(error), field=name) from error
        if (node.get("x-source") == "n_glycosylation_motif_outcomes"
                and isinstance(payload, dict) and name in payload):
            from .molecular_sequence_result_contracts import validate_ordinary_molecular_sequence_return
            try:
                if type(payload[name]) is not list:
                    raise ValueError("ordinary_n_glycosylation_return_array_required")
                for value in payload[name]:
                    validate_ordinary_molecular_sequence_return(value, operation="find_n_glycosylation_motifs")
            except ValueError as error:
                raise ReportBoundaryError("Invalid retained N-glycosylation motif facts",
                    code=str(error), field=name) from error
        if (node.get("x-source") == "o_glycosylation_hotspot_outcomes"
                and isinstance(payload, dict) and name in payload):
            from .molecular_sequence_result_contracts import validate_ordinary_molecular_sequence_return
            try:
                if type(payload[name]) is not list:
                    raise ValueError("ordinary_o_glycosylation_return_array_required")
                for value in payload[name]:
                    validate_ordinary_molecular_sequence_return(value, operation="predict_o_glycosylation_hotspots")
            except ValueError as error:
                raise ReportBoundaryError("Invalid retained O-glycosylation hotspot facts",
                    code=str(error), field=name) from error
        if (node.get("x-source") == "execution_addgene_sequence_facts"
                and isinstance(payload, dict) and name in payload):
            from .addgene_sequence_facts import validate_addgene_sequence_fact
            try:
                if type(payload[name]) is not list:
                    raise ValueError("addgene_sequence_fact_array_required")
                for value in payload[name]:
                    validate_addgene_sequence_fact(value)
            except ValueError as error:
                raise ReportBoundaryError("Invalid retained Addgene sequence facts",
                    code=str(error), field=name) from error
        if (node.get("x-source") == "circular_dichroism_summaries"
                and isinstance(payload, dict) and name in payload):
            from .circular_dichroism_contracts import validate_circular_dichroism_return
            try:
                if type(payload[name]) is not list:
                    raise ValueError("circular_dichroism_return_array_required")
                for value in payload[name]:
                    validate_circular_dichroism_return(value)
            except ValueError as error:
                raise ReportBoundaryError("Invalid retained CD summary facts",
                    code=str(error), field=name) from error
        if (node.get("x-source") == "uniprot_selected_returns"
                and isinstance(payload, dict) and name in payload):
            from .uniprot_return_contracts import validate_uniprot_selected_values, UniProtReturnValidationError
            try:
                validate_uniprot_selected_values(payload[name], selection=node["x-uniprot-selection"])
            except UniProtReturnValidationError as error:
                field = name + (error.field[len("value"):] if error.field and error.field.startswith("value") else "")
                raise ReportBoundaryError("Invalid selected UniProt facts",
                    code=error.code, field=field) from error
    _finite(payload)
    # A registered native field is a complete original schema document. Its
    # local #/$defs references belong to that document, not the enclosing form.
    # Validate its actual payload first; only the validation copy of the parent
    # uses a placeholder. Original contracts and returned rows remain exact.
    parent_schema = schema
    native = {name: node for name, node in schema["properties"].items()
        if node.get("x-source") in {"literature_concentration_window_cells", "literature_measurement_comparison_cells", "literature_kinetic_summary_precision_cells", "literature_controlled_response_component_cells", "literature_gel_component_cells", "literature_ion_discrimination_cells",
            "protein_structure_action_views", "protein_structure_action_sequences", "protein_structure_action_saved_sheets",
            "macs2_peak_outcomes", "homer_motif_outcomes", "tf_binding_outcomes", "vcf_result_outcomes", "protease_kinetics_outcomes", "arsenic_speciation_outcomes", "protein_disorder_outcomes", "primer_placement_outcomes", "protein_conservation_outcomes", "protein_phylogeny_outcomes", "bvbrc_application_outcomes", "esm_gene_embedding_outcomes", "somatic_variant_outcomes"}
        or str(node.get("x-source", "")).startswith(("execution.blast_utility_", "execution.masking_", "execution_protein_structure_", "genomic_overlap_", "chromatin_interaction_", "atac_differential_", "expression_nmf_", "fluorescence_", "flux_balance_"))}
    if native:
        parent_schema = {**schema, "properties": dict(schema["properties"])}
        for name, node in native.items():
            if isinstance(payload, dict) and name in payload:
                if str(node.get("x-source", "")).startswith("execution.blast_utility_"):
                    from .blast_utility_result_views import validate_blast_utility_fact_values
                    try:
                        validate_blast_utility_fact_values(node["x-source"], payload[name])
                    except (ValueError, TypeError, OverflowError, RecursionError) as error:
                        raise ReportBoundaryError("Invalid recorded BLAST utility fact", code="invalid_form", field=name) from error
                elif str(node.get("x-source", "")).startswith("execution.masking_"):
                    from .sequence_masking_result_views import validate_masking_fact_values
                    try:
                        validate_masking_fact_values(node["x-source"], payload[name])
                    except (ValueError, TypeError, OverflowError, RecursionError) as error:
                        raise ReportBoundaryError("Invalid recorded masking fact", code="invalid_form", field=name) from error
                elif (str(node.get("x-source", "")).startswith("execution_protein_structure_")
                        or node.get("x-source") in {"protein_structure_action_views",
                            "protein_structure_action_sequences", "protein_structure_action_saved_sheets"}):
                    _validate_protein_structure_fact_rows(payload[name], node["x-source"], name)
                elif str(node.get("x-source", "")).startswith("genomic_overlap_"):
                    from .genomic_overlap_return_views import validate_genomic_overlap_fact_values
                    try:
                        validate_genomic_overlap_fact_values(node["x-source"], payload[name])
                    except (ValueError, TypeError, OverflowError, RecursionError) as error:
                        raise ReportBoundaryError("Invalid recorded overlap fact", code="invalid_form", field=name) from error
                elif str(node.get("x-source", "")).startswith("chromatin_interaction_"):
                    from .chromatin_interaction_return_views import validate_chromatin_fact_values
                    try:
                        validate_chromatin_fact_values(node["x-source"], payload[name])
                    except (ValueError, TypeError, OverflowError, RecursionError) as error:
                        raise ReportBoundaryError("Invalid recorded chromatin fact", code="invalid_form", field=name) from error
                elif str(node.get("x-source", "")).startswith("fluorescence_"):
                    from .fluorescence_return_views import validate_fluorescence_fact_values
                    try:
                        validate_fluorescence_fact_values(node["x-source"], payload[name])
                    except (ValueError, TypeError, OverflowError, RecursionError) as error:
                        raise ReportBoundaryError("Invalid recorded fluorescence fact", code="invalid_form", field=name) from error
                elif str(node.get("x-source", "")).startswith("flux_balance_"):
                    from .flux_balance_return_views import validate_fba_fact_values
                    try:
                        validate_fba_fact_values(node["x-source"], payload[name])
                    except (ValueError, TypeError, OverflowError, RecursionError) as error:
                        raise ReportBoundaryError("Invalid recorded FBA fact", code="invalid_form", field=name) from error
                elif str(node.get("x-source", "")).startswith("expression_nmf_"):
                    from .expression_nmf_return_views import validate_expression_nmf_fact_values
                    try:
                        validate_expression_nmf_fact_values(node["x-source"], payload[name])
                    except (ValueError, TypeError, OverflowError, RecursionError) as error:
                        raise ReportBoundaryError("Invalid recorded NMF fact", code="invalid_form", field=name) from error
                elif str(node.get("x-source", "")).startswith("atac_differential_"):
                    from .atac_differential_return_views import validate_atac_fact_values
                    try:
                        validate_atac_fact_values(node["x-source"], payload[name])
                    except (ValueError, TypeError, OverflowError, RecursionError) as error:
                        raise ReportBoundaryError("Invalid recorded ATAC fact", code="invalid_form", field=name) from error
                errors = list(Draft202012Validator(node).iter_errors(payload[name]))
                if errors:
                    error = errors[0]
                    field = ".".join((name, *map(str, error.absolute_path)))
                    raise ReportBoundaryError(error.message, code=error.validator, field=field)
            parent_schema["properties"][name] = {}
    errors = list(Draft202012Validator(parent_schema).iter_errors(payload))
    if errors:
        error = errors[0]
        raise ReportBoundaryError(error.message, code=error.validator, field=".".join(map(str, error.absolute_path)))

    _validate_form_semantics(payload, schema, reference_resolver)
    return payload


def _validate_protein_structure_fact_rows(rows, source, field):
    """Strict native shapes, distinct from actual receipt and operand authority."""
    from .protein_structure_contracts import (validate_saved_sheet_descriptor, validate_structure_sequence_descriptor,
        validate_saved_sheet_descriptor_v2, validate_structure_sequence_descriptor_v2)
    from .protein_structure_action_records import validate_protein_structure_action_view
    from .protein_structure_result_views import (
        validate_protein_structure_projection_result, validate_protein_structure_failure_return,
    )
    validators = {
        "execution_protein_structure_projections": validate_protein_structure_projection_result,
        "execution_protein_structure_saved_sheets": validate_saved_sheet_descriptor,
        "execution_protein_structure_sequences": validate_structure_sequence_descriptor,
        "execution_protein_structure_failures": validate_protein_structure_failure_return,
        "protein_structure_action_views": validate_protein_structure_action_view,
        "protein_structure_action_sequences": validate_structure_sequence_descriptor_v2,
        "protein_structure_action_saved_sheets": validate_saved_sheet_descriptor_v2,
    }
    if type(rows) is not list:
        raise ReportBoundaryError("Protein facts must be an array", code="type", field=field)
    for index, row in enumerate(rows):
        try:
            validators[source](row)
        except (ValueError, TypeError, OverflowError, RecursionError) as error:
            raise ReportBoundaryError("Invalid recorded protein fact", code="invalid_form",
                field=f"{field}[{index}]") from error


def _validate_form_semantics(payload, schema, reference_resolver, *, path="report", resource=None):
    """Visit semantic annotations after Draft validation, within a local resource."""
    def visit(value, node, path, resource=None):
        if value is None or not isinstance(node, dict):
            return
        if (node.get("x-source") in {"literature_concentration_window_cells", "literature_measurement_comparison_cells", "literature_kinetic_summary_precision_cells", "literature_controlled_response_component_cells", "literature_gel_component_cells", "literature_ion_discrimination_cells",
                "protein_structure_action_views", "protein_structure_action_sequences", "protein_structure_action_saved_sheets",
                "macs2_peak_outcomes", "homer_motif_outcomes", "tf_binding_outcomes", "vcf_result_outcomes", "protease_kinetics_outcomes", "arsenic_speciation_outcomes", "protein_disorder_outcomes", "primer_placement_outcomes", "protein_conservation_outcomes", "protein_phylogeny_outcomes", "bvbrc_application_outcomes", "esm_gene_embedding_outcomes", "somatic_variant_outcomes"}
                or str(node.get("x-source", "")).startswith(("execution.blast_utility_", "execution.masking_", "execution_protein_structure_", "genomic_overlap_", "chromatin_interaction_", "atac_differential_", "expression_nmf_", "fluorescence_", "flux_balance_"))):
            resource = node
        if resource is not None and "$ref" in node:
            pointer = node["$ref"]
            if not isinstance(pointer, str) or not pointer.startswith("#/$defs/"):
                raise ReportBoundaryError(f"{path}: external native schema reference", code="invalid_schema", field=path)
            target = resource
            try:
                for token in pointer[2:].split("/"):
                    target = target[token.replace("~1", "/").replace("~0", "~")]
            except (KeyError, TypeError) as error:
                raise ReportBoundaryError(f"{path}: unresolved native schema reference", code="invalid_schema", field=path) from error
            visit(value, target, path, resource)
        def applies(branch):
            validator = (Draft202012Validator(resource).evolve(schema=branch)
                if resource is not None else Draft202012Validator(branch))
            return validator.is_valid(value)
        # The full Draft validator has already checked the payload. Semantic
        # annotations still need every applicable branch as well as base fields;
        # a nullable/tagged branch must not bypass its actual reference resolver.
        for keyword in ("anyOf", "oneOf"):
            for branch in node.get(keyword, []):
                if applies(branch):
                    visit(value, branch, path, resource)
        for branch in node.get("allOf", []):
            visit(value, branch, path, resource)
        if "if" in node:
            selected = "then" if applies(node["if"]) else "else"
            if selected in node:
                visit(value, node[selected], path, resource)
        if isinstance(value, dict):
            properties = node.get("properties", {})
            for key, child in value.items():
                if key in properties:
                    visit(child, properties[key], f"{path}.{key}", resource)
        elif isinstance(value, list):
            if "x-unique-by" in node:
                seen = set()
                for i, child in enumerate(value):
                    identity = tuple(child[key] for key in node["x-unique-by"])
                    if identity in seen:
                        raise ReportBoundaryError(f"{path}[{i}]: duplicate recorded identity", code="duplicate_identity", field=f"{path}[{i}]")
                    seen.add(identity)
            prefix = node.get("prefixItems", [])
            for i, child in enumerate(value):
                if i < len(prefix):
                    visit(child, prefix[i], f"{path}[{i}]", resource)
                elif "items" in node:
                    visit(child, node["items"], f"{path}[{i}]", resource)
        elif isinstance(value, str):
            kind = node.get("format")
            if kind in REFERENCE_FORMATS:
                if reference_resolver is None or not reference_resolver(value, node.get("x-reference-namespace")):
                    raise ReportBoundaryError(f"{path}: reference is unavailable at this boundary", code="unknown_reference", field=path)
            elif kind == "unit" and value not in UNITS:
                raise ReportBoundaryError(f"{path}: unknown unit", code="unknown_unit", field=path)
            elif kind == "mathematical_expression" and not _expression(value):
                raise ReportBoundaryError(f"{path}: invalid expression", code="invalid_expression", field=path)
            elif kind == "dna_sequence" and not re.fullmatch(r"[ACGTRYSWKMBDHVNacgtryswkmbdhvn]+", value):
                raise ReportBoundaryError(f"{path}: invalid DNA sequence", code="invalid_sequence", field=path)
            elif kind == "protein_sequence" and not re.fullmatch(r"[ACDEFGHIKLMNPQRSTVWYBXZJUO*]+", value):
                raise ReportBoundaryError(f"{path}: invalid protein sequence", code="invalid_sequence", field=path)
            elif kind == "alignment_symbol" and not re.fullmatch(r"[!-~]", value):
                raise ReportBoundaryError(f"{path}: invalid alignment symbol", code="invalid_alignment_symbol", field=path)
            elif kind == "alignment_strand" and value not in {"+", "-", "unknown"}:
                raise ReportBoundaryError(f"{path}: invalid alignment strand", code="invalid_alignment_strand", field=path)
            elif kind == "structure_identifier" and not re.fullmatch(r"[!-~]+", value):
                raise ReportBoundaryError(f"{path}: invalid structure identifier", code="invalid_structure_identifier", field=path)
            elif kind == "structure_residue_number" and not re.fullmatch(r"-?[0-9]+", value):
                raise ReportBoundaryError(f"{path}: invalid structure residue number", code="invalid_structure_residue_number", field=path)
            elif kind == "structure_insertion_code" and value != "" and not re.fullmatch(r"[!-~]+", value):
                raise ReportBoundaryError(f"{path}: invalid structure insertion code", code="invalid_structure_insertion_code", field=path)
    visit(payload, schema, path, resource)


def interpretation_schema(schema):
    """Recorded fields are not requested from a model."""
    schema = validate_closed_schema(schema)
    props = {name: node for name, node in schema["properties"].items() if "x-source" not in node}
    return {"type": "object", "additionalProperties": False, "properties": props, "required": list(props)}


def generation_schema(schema):
    schema = validate_closed_schema(schema)
    def translate(node):
        if not isinstance(node, dict):
            return node
        node = dict(node)
        if "properties" in node:
            node["properties"] = {name: translate(child) for name, child in node["properties"].items()}
        for keyword in ("anyOf", "oneOf", "allOf", "prefixItems"):
            if keyword in node:
                node[keyword] = [translate(child) for child in node[keyword]]
        for keyword in ("items", "not", "if", "then", "else"):
            if keyword in node:
                node[keyword] = translate(node[keyword])
        kind = node.pop("format", None)
        node.pop("x-reference-namespace", None)
        node.pop("x-source", None)
        node.pop("x-unique-by", None)
        node.pop("uniqueItems", None)
        if kind == "unit" and "enum" not in node:
            node["enum"] = sorted(UNITS) + ([None] if "null" in node.get("type", []) else [])
        if "const" in node:
            node["enum"] = [node.pop("const")]
        return node
    return translate(schema)


def form_with_facts(interpretations, schema, facts):
    schema = validate_closed_schema(schema)
    allowed = set(interpretation_schema(schema)["properties"])
    if not isinstance(interpretations, Mapping) or set(interpretations) != allowed:
        raise ReportBoundaryError("Interpretations must fill exactly the non-recorded fields", code="interpretation_fields")
    result = dict(interpretations)
    for name, node in schema["properties"].items():
        if "x-source" in node:
            key = node["x-source"]
            if key not in facts:
                raise ReportBoundaryError("Recorded fact source unavailable", code="unknown_fact", field=name)
            result[name] = plain(facts[key])
    return result


def reference_resolver(registry):
    """Create a resolver from live namespace -> actual semantic references."""
    def resolve(value, namespace=None):
        if namespace is not None:
            return value in registry.get(namespace, ())
        return any(value in values for values in registry.values())
    return resolve
