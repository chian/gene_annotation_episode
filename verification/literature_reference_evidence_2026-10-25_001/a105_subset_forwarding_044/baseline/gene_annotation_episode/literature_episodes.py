"""Literature specializations of the application's ordinary Episode loop.

This binding supplies operands, available ordinary operations and source
custody. The shared source owns decisions, reasoning commits, commissioning,
waits, report updates and continuation. In particular, a reading selection is
information for an investigation, never a script that this binding executes.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
import hashlib
import inspect
import json
from pathlib import Path

from .communication import ReportBoundaryError, plain, validate_form
from .domain import ContractError, REF, identity, obj, validate_schema
from .episode_bindings import reference_in_context


VERSION = "literature_episode_binding_v1"
ROLES = ("literature", "literature_strategy", "literature_search",
         "literature_page", "literature_table", "literature_ordered",
         "literature_targeted")

_REFERENCES = {"type": "array", "items": REF, "uniqueItems": True}
_REPRESENTATION = {"type": "string", "enum": ["text", "original", "stdout", "stderr"]}
_NATURAL = {"type": "integer", "minimum": 0}
_POSITIVE = {"type": "integer", "minimum": 1}
_TEXT = {"type": "string", "minLength": 1}
_WINDOW = obj({"source_ref": REF, "representation": _REPRESENTATION,
               "offset": _NATURAL, "limit": _POSITIVE})
_TABLE = obj({"source_ref": REF, "sheet_key": _TEXT, "offset": _NATURAL,
    "limit": _NATURAL, "header_row": {"type": ["integer", "null"], "minimum": 1},
    "where": {**obj({"column": {"type": ["string", "null"], "pattern": "^[A-Z]+$"},
        "match": {"enum": ["equals", "contains"]}, "value": _TEXT,
        "case_sensitive": {"type": "boolean"}}), "type": ["object", "null"]}})
_PAGE = obj({"version": {"const": "page_assignment_v1"}, "source_ref": REF,
    "representation": _REPRESENTATION, "artifact_ref": REF,
    "question_context_refs": _REFERENCES, "prior_delivery_refs": _REFERENCES})

_CHILDREN = {"literature": ("literature_strategy",),
    "literature_strategy": ("literature_search",),
    "literature_search": ("literature_page",),
    "literature_page": ("literature_table", "literature_ordered", "literature_targeted"),
    "literature_table": (), "literature_ordered": (), "literature_targeted": ()}

_ACCESS_TOOLS = ("state.query", "source.read", "source.locate", "image.view", "source.archive.members",
    "source.archive.extract", "source.xlsx.sheets", "source.xlsx.rows",
    "source.pdf.info", "source.pdf.text", "source.pdf.page", "execution.estimate")
_ACQUISITION_TOOLS = ("public.literature.search", "public.literature.read",
    "public.ncbi.search", "public.pmc.versions", "public.pmc.files", "public.pmc.asset")
_READ_TOOLS = ("source.read", "source.locate", "source.xlsx.rows", "source.pdf.text", "image.view")

_ROLE_INSTRUCTIONS = {
    "literature": "Investigate which published evidence bears on the assigned scientific question. You can pursue ordinary searches and source reads directly, or assign a strategy investigation when that narrower question warrants iteration.",
    "literature_strategy": "Investigate which search approach is productive. Keep the information objective and evidence context separate from a literal provider query. Revise terms or source choices in light of actual search/read outcomes; a search child can investigate which returned sources deserve examination.",
    "literature_search": "Investigate which returned sources merit examination for the assigned question. Search results are source-discovery information. Examine original sources and their conditions before asserting biological evidence. A page child can investigate where and how to examine a selected source.",
    "literature_page": "Investigate where and how this exact source should be examined. Choose ordinary source operations or selected table, ordered-reading or targeted-passage investigations as useful. Paragraph projections omit some XML headings, tables and footnotes; retained original bytes remain addressable.",
    "literature_table": "Investigate the selected table/sheet and its scientific meaning. Select rows, headers, conditions and footnotes deliberately; revise row selection or reread when outcomes warrant it. XLSX cells/formulas/caches keep their native identity. Article XML tables are read through exact original-source windows.",
    "literature_ordered": "Investigate the source in document order as useful for the assigned question. Use returned UTF-8 byte continuations and retain representation identity. Decide whether to continue, reread, change the examined window or interpret obtained evidence from actual outcomes.",
    "literature_targeted": "Investigate the supplied source-bound passages for the assigned question. Read neighboring context, qualifications or alternative passages as needed and revise the interpretation from actual outcomes. Separate spans remain separate; never concatenate them into a fabricated quotation.",
}


def _population_catalog():
    """Actual child population operations, independent of episode identity."""
    result = []
    from .literature_rate_storage import rate_population_schema
    result.append({"name": "literature.rate.populate",
        "description": "Populate source-preparation rate cells from a selected already acquired CSV/TSV summary. Preserve actual subjects, conditions, units, uncertainty and missingness. This finite table route does not read arbitrary prose/figures or calculate target transfer/annotation credit. Select a statistical model only when supported; otherwise use none and unknown dependence.",
        "input_schema": rate_population_schema()})
    from .literature_quantity_storage import quantity_population_schema
    result.append({"name": "literature.quantity.populate",
        "description": "Read one literal specific activity or apparent Km from selected original JATS prose, or apparent Km from selected original HTML prose. Select quantity role and analyte, not numbers. HTML paragraphs without IDs use the explicit direct_paragraph:N selector within the selected section. Preserve untyped plus-minus spread. Subject-token presence does not establish experimental attribution; inspect the assay context separately. No comparison arms, conditions, product identity or missing correction score are invented.",
        "input_schema": quantity_population_schema()})
    from .literature_assay_inputs import assay_arguments_schema
    result.append({"name": "literature.assay.populate",
        "description": "Interpret the source assay's actual subject, conditions, endpoint and molecular arrangement with exact source witnesses. Select reported numerical spans only when they have the stated correction-operand meanings. Deterministically parse and correct the interpreted source endpoint, preserving full covariance, conditional assumptions and unknowns. Exact quotes validate custody, not interpretation; no target transfer or annotation probability.",
        "input_schema": assay_arguments_schema()})
    from .literature_ratio_storage import ratio_population_schema
    result.append({"name": "literature.ratio.populate",
        "description": "Read reported relative-signal percentages from selected JATS prose and optionally compare retained visual transcriptions with original image custody. Preserve the actual denominator/arrangement and conflicting candidate values. Signal is not calibrated molar amount or an isolated functional effect; no source reliability or target-transfer score is fabricated.",
        "input_schema": ratio_population_schema()})
    from .literature_binding_storage import binding_population_schema
    result.append({"name": "literature.binding.populate",
        "description": "Populate source binding-parameter components from an already received table or explicitly retained visual transcription. Keep IC50 distinct from reported Hill-fit Kd, actual protein/state/ligand identities, reported fit-spread basis and point/limit arithmetic. Original image custody is validated; no OCR, sampling confidence, intrinsic-affinity conversion or target credit is inferred.",
        "input_schema": binding_population_schema()})
    from .literature_binding_model_storage import binding_model_population_schema
    result.append({"name": "literature.binding.model.populate",
        "description": "Evaluate the ordered parameter contrast in an actually received committed binding sheet using an explicitly supplied source model. Preserve full log-covariance measurement ownership, known versus estimated variance, and the stated threshold-reporting mechanism. Missing model source retains usable native contrast and explicit unknown likelihood cells. No inference of covariance from fit spreads or counts, limit-as-point calculation, intrinsic-affinity conversion, target transfer or annotation credit.",
        "input_schema": binding_model_population_schema()})
    from .literature_transport_storage import transport_response_population_schema
    result.append({"name": "literature.transport.response.populate",
        "description": "Calculate a conditional source substrate-response correction from exact concentration spans and a received saved apparent-Km quantity. Preserve actual molecule, preparation, analyte, endpoint and fitted-curve contexts. Different or unknown curves leave the comparison unavailable. Full covariance retains physical owners and shared Km once; no sampling variance from untyped spread, target transfer or annotation credit is inferred.",
        "input_schema": transport_response_population_schema()})
    from .literature_perturbation_storage import perturbation_population_schema
    result.append({"name": "literature.perturbation.populate",
        "description": "Populate reference perturbation/restoration components from source-bound design interpretations and optional received quantitative data. Keep actual recipient, changed component, partner, endpoint calibration and real restoration arms distinct. Qualitative-only outcomes cannot supply numerical rates. Preserve nuisance comparability separately from effect isolation and leave missing inputs/uncertainty unknown. No target transfer, necessity inference from an unmeasured catalytic knockout, or final annotation credit.",
        "input_schema": perturbation_population_schema()})
    from .literature_structure_storage import structure_population_schema
    result.append({"name": "literature.structure.populate",
        "description": "Populate source-model geometry and local residue RSCC components from received coordinates and optional matching deposited validation. Select exact model/author atom groups and fixed physical criteria. Preserve missing endpoints, validation entry/revision mismatch and unreported coordinate uncertainty. The explicit scope is conditional deposited-model geometry; it does not establish population occupancy, causal mechanism, target correspondence or annotation credit.",
        "input_schema": structure_population_schema()})
    from .literature_reaction_storage import reaction_population_schema
    result.append({"name": "literature.reaction.populate",
        "description": "Populate reported reference reaction-ratio residuals, named-prediction comparisons and simple resource-budget components from an explicitly retained received dataset. Preserve unknown replication, missing alternatives and incomplete resource constraints. Product-pair ratios, supplied reagent budgets and usable capacity have distinct meanings. This route does not parse NMR spectra, establish measured oxygen coupling, apply missing corrections or calculate target transfer/annotation credit.",
        "input_schema": reaction_population_schema()})
    from .literature_context_storage import context_population_schema
    result.append({"name": "literature.context.populate",
        "description": "Populate biological context compatibility from source-bound retained observations and domain/route meanings. Keep organism capability distinct from fixed-sample coverage; preserve physical unit bases, missing local mapping, unexamined states, sample weights, pairing and conditional sampling design. Logical domain bounds are not confidence intervals or intuitive quality grades. Purified-enzyme assays are not automatically organism witnesses or habitat samples. No target correspondence or annotation credit is calculated.",
        "input_schema": context_population_schema()})
    from .literature_figure_storage import figure_population_schema
    result.append({"name": "literature.figure.populate",
        "description": "Read native experimental mean-bar ordinates from received original images using a retained linear-axis selection recipe. Preserve both subject/partner arms, endpoint and normalization meanings, source representation relationships, reported repeat/spread meanings and conditional digitization bounds. Return raw ordinates and a signed difference; pixel extraction does not supply SD, statistical significance, molar calibration, partner necessity or target credit.",
        "input_schema": figure_population_schema()})
    from .literature_partner_storage import partner_population_schema
    result.append({"name": "literature.partner.populate",
        "description": "Populate source experimental partner-removal and addback components from received retained measurements and exact source witnesses. Preserve directed molecule/partner roles, nitrogen and other nonpartner conditions, normalization identity, physical measurement identity and reported spread meanings. Incompatible or incomplete comparisons keep native values and explicit unknown components. Censor domains are not confidence intervals; chemical bypass and partner swaps do not establish universal partner necessity, genomic presence, target transfer or annotation credit.",
        "input_schema": partner_population_schema()})
    from .literature_partner_storage import partner_source_population_schema
    result.append({"name": "literature.partner.source.populate",
        "description": "Populate the same experimental partner components directly from selected literal source spans. Select complete rate/limit tokens, native units, spread meanings and source-bound entity/physical-measurement identities; do not supply scientific numbers or a prepared numeric JSON dataset. For source-defined activity units such as U/mg, select the endpoint-specific definition, quantity, molecular entity and time basis; no universal U conversion is assumed. Deterministic readers preserve original tokens, convert supported rate units and retain unknown normalization, conditions or observation identity. A repeated representation is not a new measurement. No sampling uncertainty, universal necessity, target correspondence or annotation credit is inferred.",
        "input_schema": partner_source_population_schema()})
    from .literature_rate_native_inputs import rate_source_population_schema
    result.append({"name": "literature.rate.source.populate",
        "description": "Populate the existing source-rate comparison sheet directly from selected literal paper spans, without a prepared CSV/TSV or model-authored scientific numbers. Request its closed literature_rate_source_cells return projection, which preserves each arm's subject, construct, preparation and approximation; literature_rate_cells is the separate legacy table projection. Select source-backed endpoint/basis relationships and statistical assumptions; different constructs may be the intended comparison. Source-defined U/mg requires its endpoint-specific definition. Missing meanings, unsupported units and censored values retain partial inputs. Exact witnesses verify custody, not causal isolation, target correspondence or annotation credit.",
        "input_schema": rate_source_population_schema()})
    from .literature_amount_inputs import amount_arguments_schema
    result.append({"name": "literature.amount.populate",
        "description": "Populate A105 source amount components from exact reported numerical/unit spans and witnessed experimental meanings. Keep target/total same-stock mass-fraction estimates separate from nominal molar amounts between arms. Preserve both quantity roles, preparations, methods, bases, bounds, approximation and source-owned covariance. Ratios above one and missing relationships remain explicit; no active fraction, universal activity correction, target transfer or annotation credit is inferred. The conditional mass-denominator factor is retained without applying it to a saved rate.",
        "input_schema": amount_arguments_schema()})
    from .literature_optical_inputs import optical_arguments_schema
    result.append({"name": "literature.optical.populate",
        "description": "Populate the existing net_rate and variance_net_rate input meanings from selected source-bound optical observations. Preserve NADH-depletion endpoint scope, actual subject/construct/preparation/conditions, qualified or missing inputs and source-owned covariance. Optical epsilon/path conversion is not recovery k, protein amount, product attribution or a complete activity score. Repeated representations create no independent evidence or annotation credit.",
        "input_schema": optical_arguments_schema()})
    return result


class LiteratureEpisodes:
    """C7 binding for C10 assignments; no model connection or private loop."""

    roles = ROLES
    entry_roles = ("literature",)

    def __init__(self, services, *, outcome_page_size=8, rate_population=False, reference_parent_sources=None):
        if type(outcome_page_size) is not int or outcome_page_size < 1:
            raise ValueError("positive_literature_outcome_page_size_required")
        self.services = services
        self.outcome_page_size = outcome_page_size
        if type(rate_population) is not bool:
            raise ValueError("boolean_rate_population_binding_required")
        self.rate_population = rate_population
        if reference_parent_sources is not None:
            if (not rate_population or not isinstance(reference_parent_sources, (list, tuple))
                    or not reference_parent_sources
                    or any(not isinstance(ref, str) or not ref for ref in reference_parent_sources)
                    or len(set(reference_parent_sources)) != len(reference_parent_sources)):
                raise ValueError("explicit_unique_reference_parent_sources_required")
            reference_parent_sources = tuple(reference_parent_sources)
        self.reference_parent_sources = reference_parent_sources

    def as_record(self):
        implementation = Path(__file__).read_bytes()
        implementation += Path(__file__).with_name("source_locations.py").read_bytes()
        configuration = {"outcome_page_size": self.outcome_page_size}
        if self.rate_population:
            configuration["rate_population"] = True
            for name in ("literature_experimental_contracts.py", "literature_rate_reader.py",
                         "literature_rate_native_inputs.py",
                         "literature_rate_calculations.py", "literature_rate_storage.py",
                         "literature_experimental_prompt.py", "literature_prose_reader.py",
                         "literature_html_quantity_reader.py",
                         "literature_activity_calculations.py", "literature_quantity_storage.py",
                         "literature_assay_inputs.py", "literature_assay_storage.py", "literature_assay_prompt.py",
                         "literature_reference_parent_prompt.py", "literature_ratio_reader.py",
                         "literature_ratio_calculations.py", "literature_ratio_storage.py",
                         "literature_binding_reader.py", "literature_binding_calculations.py",
                         "literature_binding_storage.py", "literature_binding_prompt.py",
                         "literature_binding_models.py", "literature_binding_model_inputs.py",
                         "literature_binding_model_storage.py", "literature_transport_calculations.py",
                         "literature_transport_inputs.py", "literature_transport_storage.py",
                         "literature_transport_prompt.py", "literature_perturbation_calculations.py",
                         "literature_perturbation_inputs.py", "literature_perturbation_storage.py",
                         "literature_perturbation_prompt.py", "literature_structure_inputs.py",
                         "literature_structure_calculations.py", "literature_structure_storage.py",
                         "literature_structure_prompt.py", "communication.py",
                         "literature_reaction_inputs.py", "literature_reaction_calculations.py",
                         "literature_reaction_storage.py", "literature_reaction_prompt.py",
                         "literature_context_inputs.py", "literature_context_calculations.py",
                         "literature_context_storage.py", "literature_context_prompt.py",
                         "literature_figure_measurements.py", "literature_figure_inputs.py",
                         "literature_figure_storage.py", "literature_figure_prompt.py",
                         "literature_partner_calculations.py", "literature_partner_inputs.py",
                         "literature_partner_storage.py", "literature_partner_prompt.py",
                         "literature_partner_source_fields.py", "literature_partner_native_inputs.py",
                         "literature_partner_defined_units.py", "literature_amount_inputs.py",
                         "literature_amount_calculations.py", "literature_amount_storage.py",
                         "literature_optical_inputs.py", "literature_optical_calculations.py",
                         "literature_optical_validation.py", "literature_optical_storage.py"):
                implementation += Path(__file__).with_name(name).read_bytes()
        if self.reference_parent_sources is not None:
            configuration["reference_parent_sources"] = list(self.reference_parent_sources)
        return {"version": VERSION, "binding_id": "literature",
            "implementation_sha256": hashlib.sha256(implementation).hexdigest(),
            "configuration": configuration}

    @staticmethod
    def _role(role):
        if role not in ROLES:
            raise ValueError("unsupported_literature_role:" + str(role))
        return role

    def credit_kind(self, role):
        self._role(role)
        return "scientific"

    def assignment_schema(self, role):
        self._role(role)
        if role == "literature_page":
            schema = _PAGE
        elif role in {"literature_table", "literature_ordered", "literature_targeted"}:
            selection = ({"anyOf": [_TABLE, _WINDOW]} if role == "literature_table" else _WINDOW if role == "literature_ordered"
                else obj({"spans": {"type": "array", "minItems": 1, "items": _WINDOW}}))
            schema = obj({"version": {"const": "reading_assignment_v1"},
                          "page": _PAGE, "selection": selection})
        else:
            version, field = {
                "literature": ("literature_assignment_v1", "source_refs"),
                "literature_strategy": ("strategy_assignment_v1", "prior_search_refs"),
                "literature_search": ("search_assignment_v1", "search_result_refs"),
            }[role]
            schema = obj({"version": {"const": version}, "question_context_refs": _REFERENCES,
                          field: _REFERENCES})
        schema = deepcopy(schema)
        if self.rate_population:
            from .literature_rate_storage import COMPONENTS
            schema["properties"]["requested_rate_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(COMPONENTS)}}
            from .literature_quantity_storage import COMPONENTS as QUANTITIES
            schema["properties"]["requested_quantity_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(QUANTITIES)}}
            from .literature_assay_storage import COMPONENTS as ASSAY_COMPONENTS
            schema["properties"]["requested_assay_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(ASSAY_COMPONENTS)}}
            from .literature_ratio_calculations import COMPONENTS as RATIO_COMPONENTS
            schema["properties"]["requested_ratio_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(RATIO_COMPONENTS)}}
            from .literature_binding_calculations import COMPONENTS as BINDING_COMPONENTS
            schema["properties"]["requested_binding_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(BINDING_COMPONENTS)}}
            from .literature_binding_models import COMPONENTS as BINDING_MODEL_COMPONENTS
            schema["properties"]["requested_binding_model_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(BINDING_MODEL_COMPONENTS)}}
            from .literature_transport_calculations import COMPONENTS as TRANSPORT_COMPONENTS
            schema["properties"]["requested_transport_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(TRANSPORT_COMPONENTS)}}
            from .literature_perturbation_calculations import COMPONENTS as PERTURBATION_COMPONENTS
            schema["properties"]["requested_perturbation_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(PERTURBATION_COMPONENTS)}}
            from .literature_structure_calculations import COMPONENTS as STRUCTURE_COMPONENTS
            schema["properties"]["requested_structure_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(STRUCTURE_COMPONENTS)}}
            from .literature_reaction_calculations import COMPONENTS as REACTION_COMPONENTS
            schema["properties"]["requested_reaction_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(REACTION_COMPONENTS)}}
            from .literature_context_calculations import COMPONENTS as CONTEXT_COMPONENTS
            schema["properties"]["requested_context_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(CONTEXT_COMPONENTS)}}
            from .literature_figure_storage import COMPONENTS as FIGURE_COMPONENTS
            schema["properties"]["requested_figure_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(FIGURE_COMPONENTS)}}
            from .literature_partner_calculations import COMPONENTS as PARTNER_COMPONENTS
            schema["properties"]["requested_partner_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(PARTNER_COMPONENTS)}}
            from .literature_amount_calculations import COMPONENTS as AMOUNT_COMPONENTS
            schema["properties"]["requested_amount_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(AMOUNT_COMPONENTS)}}
            from .literature_optical_storage import COMPONENTS as OPTICAL_COMPONENTS
            schema["properties"]["requested_optical_components"] = {
                "type": "array", "uniqueItems": True, "items": {"enum": list(OPTICAL_COMPONENTS)}}
        return schema

    def permitted_common_actions(self, context):
        self._role(context.role)
        return ("tool", "reason", "child", "wait", "redeliver_report")

    def allowed_children(self, parent, caller_capabilities):
        self._role(parent.role)
        # These are available branches, never automatically instantiated work.
        return _CHILDREN[parent.role]

    def child_roles(self, role):
        self._role(role)
        return _CHILDREN[role]

    def _require(self, reference, scope, namespace=None):
        if not self.services.reference_in_scope(reference, scope, namespace):
            raise ContractError("literature_reference_unavailable", detail={
                "reference": reference, "namespace": namespace})
        return self.services.read_record(reference)

    @staticmethod
    def _artifact(source, representation):
        if representation == "original":
            return source["artifact_ref"]
        if representation == "text":
            # Match the existing source.read fallback exactly.
            return source.get("text_ref") or source["artifact_ref"]
        return source.get(representation + "_ref")

    def _validate_page(self, page, scope):
        source = self._require(page["source_ref"], scope, "source")
        if self._artifact(source, page["representation"]) != page["artifact_ref"]:
            raise ContractError("literature_source_artifact_mismatch", detail={
                "reference": page["source_ref"], "artifact_ref": page["artifact_ref"],
                "representation": page["representation"]})
        self._require(page["artifact_ref"], scope, "artifact")
        for reference in (*page["question_context_refs"], *page["prior_delivery_refs"]):
            self._require(reference, scope)
        # prior_delivery_refs are provenance only. They do not assert reading
        # coverage, successful extraction or understanding.

    def _validate_assignment(self, role, assignment, scope):
        value = plain(assignment)
        json.dumps(value, allow_nan=False)
        validate_schema(value, self.assignment_schema(role))
        if role in {"literature_page",
                "literature_table", "literature_ordered", "literature_targeted"}:
            page = value if role == "literature_page" else value["page"]
            self._validate_page(page, scope)
            if role != "literature_page":
                selected = value["selection"]
                windows = selected["spans"] if role == "literature_targeted" else [selected]
                for window in windows:
                    if window["source_ref"] != page["source_ref"]:
                        raise ContractError("literature_reading_source_mismatch")
                    if "representation" in window and window["representation"] != page["representation"]:
                        raise ContractError("literature_reading_representation_mismatch")
                    if "representation" in window:
                        artifact = self.services.read_record(page["artifact_ref"])
                        if window["offset"] > artifact["size"]:
                            raise ContractError("source_offset_out_of_bounds")
        else:
            for field, references in value.items():
                if field.endswith("_refs"):
                    for reference in references:
                        self._require(reference, scope, None if field == "question_context_refs" else "source")
        return value

    def prepare_assignment(self, parent, role, selection, scope, operation_key):
        # Common composition validates scope containment, ownership, the
        # original form and the operation identity. Never replace them here.
        self._role(role)
        if not isinstance(operation_key, str) or not operation_key:
            raise ContractError("operation_key_required")
        value = self._validate_assignment(role, selection, scope)
        if parent.role == "literature_page" and role in _CHILDREN["literature_page"]:
            original = self._validate_assignment(parent.role, parent.assignment, parent.scope)
            if not self._within_source(value["page"]["source_ref"], original["source_ref"], scope):
                raise ContractError("literature_reading_outside_assigned_source")
        return value

    def instructions(self, context):
        self._role(context.role)
        return (_ROLE_INSTRUCTIONS[context.role] + "\n"
            "This is an iterative scientific investigation in the shared Episode loop. "
            "Earlier outcomes and admitted child forms inform later choices; no child order, "
            "reading quota or complete-document requirement is prescribed. A one-off search/read "
            "is an ordinary tool. A supplied reading selector is context, not an automatically "
            "executed action. Preserve the source's actual subject, experimental conditions, "
            "representation, version and UTF-8 byte anchors. Distinguish source claims from "
            "their applicability to the fixed target. Negative findings and qualifications can "
            "advance the investigation. Commit interpretations with the common reasoning action "
            "and update only the parent's declared typed form in that same work call. "
            "Navigation, byte coverage and repeated reading earn no scientific credit by themselves. "
            "The configured controller owns continuation; this binding has no stop rule.")

    def initial_decision_context(self, context):
        """Explicit caller source job for the existing annotation/root parent."""
        if (self.reference_parent_sources is None or context.role != "annotation"
                or len(context.path) != 1):
            return {}
        custody = []
        for reference in self.reference_parent_sources:
            if reference not in context.received_record_refs:
                raise ContractError("literature_parent_source_not_received")
            source = self._require(reference, context.scope, "source")
            custody.append({"source_ref": reference, **{name: source.get(name) for name in (
                "artifact_ref", "text_ref", "version", "parent_source_refs")}})
        return {"reference_evidence_parent": {"version": "reference_evidence_parent_v1",
                    "source_refs": list(self.reference_parent_sources), "source_custody": custody,
                    "child_population_operations": [
                        {name: entry[name] for name in ("name", "description")}
                        for entry in _population_catalog()]},
                "literature_experimental_work": {"version": "literature_experimental_task_v1",
                    "aspect": "reference_evidence_parent"}}

    def decision_context(self, context, current_view):
        assignment = self._validate_assignment(context.role, context.assignment, context.scope)
        page = (assignment if context.role == "literature_page" else assignment.get("page"))
        sources = ([page["source_ref"]] if page else assignment.get("source_refs", []))
        custody = []
        for reference in sources:
            source = self._require(reference, context.scope, "source")
            custody.append({"source_ref": reference, **{key: source.get(key) for key in
                ("version", "artifact_ref", "text_ref", "stdout_ref", "stderr_ref", "parent_source_refs")}})
        result = {"literature_assignment": assignment, "literature_source_custody": custody,
            "own_literature_outcomes": plain(self.services.own_outcomes(context.episode_id,
                tools=(*_ACQUISITION_TOOLS, *_READ_TOOLS), offset=0, limit=self.outcome_page_size)),
            "literature_history_meaning": "Own outcome metadata only. Read exact previous outcomes through episode.history. Source delivery does not establish understanding, absence or resolved science."}
        if self.rate_population:
            result["literature_experimental_work"] = {
                "version": "literature_experimental_task_v1", "aspect": "source_experimental_evidence"}
        return result

    def catalog(self, context):
        self._role(context.role)
        available = self.services.tool_catalog(context.scope)
        entries = ([{"name": name, **entry} for name, entry in available.items()]
                   if isinstance(available, Mapping) else list(available))
        allowed = set(_ACCESS_TOOLS)
        if context.role in {"literature", "literature_strategy", "literature_search"}:
            allowed.update(_ACQUISITION_TOOLS)
        result = []
        for entry in entries:
            if entry["name"] not in allowed:
                continue
            entry = deepcopy(plain(entry))
            if entry["name"] == "public.ncbi.search":
                entry["input_schema"]["properties"]["database"] = {"enum": ["pubmed"]}
            if entry["name"] == "execution.estimate":
                branches = [branch for branch in entry["input_schema"].get("anyOf", ())
                    if branch.get("properties", {}).get("tool", {}).get("const") in {
                        "source.xlsx.sheets", "source.xlsx.rows"}]
                if not branches:
                    continue
                entry["input_schema"] = {"anyOf": branches}
            result.append(entry)
        if self.rate_population:
            result.extend(_population_catalog())
        return result

    def _within_source(self, reference, root, scope):
        pending, seen = [reference], set()
        while pending:
            current = pending.pop()
            if current == root:
                return True
            if current in seen:
                continue
            seen.add(current)
            source = self._require(current, scope, "source")
            pending.extend(source.get("parent_source_refs", ()))
        return False

    def _tool_arguments(self, context, tool_name, arguments):
        assignment = self._validate_assignment(context.role, context.assignment, context.scope)
        entries = {entry["name"]: entry for entry in self.catalog(context)}
        if tool_name not in entries:
            raise ContractError("tool_not_available_to_literature_role")
        arguments = plain(arguments)
        validate_schema(arguments, entries[tool_name]["input_schema"])
        page = assignment if context.role == "literature_page" else assignment.get("page")
        if page:
            selected_arguments = arguments["arguments"] if tool_name == "execution.estimate" else arguments
            source_ref = selected_arguments.get("source_ref")
            if tool_name == "source.archive.extract":
                member = self._require(arguments["member_ref"], context.scope, "archive_member")
                source_ref = member["source_ref"]
            if source_ref is not None and not self._within_source(source_ref, page["source_ref"], context.scope):
                raise ContractError("literature_reading_outside_assigned_source")
            if (context.role == "literature_table" and tool_name == "source.xlsx.rows"
                    and "sheet_key" in assignment["selection"]):
                if arguments["sheet_key"] != assignment["selection"]["sheet_key"]:
                    raise ContractError("literature_table_sheet_mismatch")
            if tool_name in {"literature.rate.source.populate", "literature.assay.populate", "literature.ratio.populate", "literature.binding.populate", "literature.binding.model.populate", "literature.transport.response.populate", "literature.perturbation.populate", "literature.structure.populate", "literature.reaction.populate", "literature.context.populate", "literature.figure.populate", "literature.partner.populate", "literature.partner.source.populate", "literature.amount.populate", "literature.optical.populate"}:
                def sources(value):
                    if isinstance(value, dict):
                        for key, child in value.items():
                            if key in {"source_ref", "covariance_source_ref", "model_source_ref", "km_sheet_ref", "data_source_ref", "coordinate_source_ref", "validation_source_ref"} and isinstance(child, str):
                                yield child
                            else:
                                yield from sources(child)
                    elif isinstance(value, list):
                        for child in value:
                            yield from sources(child)
                    elif isinstance(value, str) and value in arguments.get("visual_source_refs", ()):
                        yield value
                if any(not self._within_source(ref, page["source_ref"], context.scope)
                       for ref in set(sources(arguments))):
                    raise ContractError("literature_reading_outside_assigned_source")
        return arguments

    async def execute(self, context, tool_name, arguments, operation_key):
        try:
            arguments = self._tool_arguments(context, tool_name, arguments)
        except ContractError as error:
            # The common source records this actual failed own attempt. It
            # supplies feedback for another selected action, never a completed
            # scientific observation or an automatic retry.
            return {"status": "invalid", "operation_ref": identity("operation", {
                "key": operation_key, "name": tool_name, "arguments": plain(arguments)}),
                "record_refs": [], "changed_record_refs": [], "result": None,
                "feedback": {"category": "arguments_or_reference", "code": str(error),
                    **({"detail": error.detail} if error.detail else {})}}
        if tool_name in {"literature.rate.populate", "literature.rate.source.populate", "literature.quantity.populate", "literature.assay.populate", "literature.ratio.populate", "literature.binding.populate", "literature.binding.model.populate", "literature.transport.response.populate", "literature.perturbation.populate", "literature.structure.populate", "literature.reaction.populate", "literature.context.populate", "literature.figure.populate", "literature.partner.populate", "literature.partner.source.populate", "literature.amount.populate", "literature.optical.populate"}:
            from .literature_experimental_contracts import ExperimentalContractError
            try:
                repo = {"literature.rate.populate": self.services.literature_rate_repository,
                        "literature.rate.source.populate": self.services.literature_rate_repository,
                        "literature.quantity.populate": self.services.literature_quantity_repository,
                        "literature.assay.populate": self.services.literature_assay_repository,
                        "literature.amount.populate": self.services.literature_amount_repository,
                        "literature.optical.populate": self.services.literature_optical_repository,
                        "literature.ratio.populate": self.services.literature_ratio_repository,
                        "literature.binding.populate": self.services.literature_binding_repository,
                        "literature.binding.model.populate": self.services.literature_binding_model_repository,
                        "literature.transport.response.populate": self.services.literature_transport_repository,
                        "literature.perturbation.populate": self.services.literature_perturbation_repository,
                        "literature.structure.populate": self.services.literature_structure_repository,
                        "literature.reaction.populate": self.services.literature_reaction_repository,
                        "literature.context.populate": self.services.literature_context_repository,
                        "literature.figure.populate": self.services.literature_figure_repository,
                        "literature.partner.populate": self.services.literature_partner_repository,
                        "literature.partner.source.populate": self.services.literature_partner_repository}[tool_name]()
                return (repo.populate_native(context, arguments, operation_key)
                        if tool_name == "literature.rate.source.populate" else repo.populate(context, arguments, operation_key))
            except (ContractError, ExperimentalContractError) as error:
                return {"status": "invalid", "operation_ref": identity("operation", {
                    "key": operation_key, "name": tool_name, "arguments": plain(arguments)}),
                    "record_refs": [], "changed_record_refs": [], "result": None,
                    "feedback": {"category": "arguments_or_reference", "code": str(error),
                                 "field": getattr(error, "field", None),
                                 **({"detail": deepcopy(error.detail)}
                                    if isinstance(error, ExperimentalContractError)
                                    and error.code == "source_quote_mismatch" and error.detail is not None
                                    else {})}}
        authorization = ({"permitted_record_refs": tuple(context.received_record_refs)}
                         if tool_name == "source.locate" else {})
        outcome = self.services.execute_tool(tool_name, arguments, scope=context.scope,
                                              operation_key=operation_key, **authorization)
        return await outcome if inspect.isawaitable(outcome) else outcome

    def fact_sources(self, role):
        self._role(role)
        # Common scientific facts already expose actual changed assessments,
        # observations, annotation accounts and report-basis references.
        return self._rate_fact_sources() if self.rate_population else {}

    def facts(self, context, completion_snapshot):
        self._role(context.role)
        if not self.rate_population:
            return {}
        return self._rate_facts(context, completion_snapshot["committed_record_refs"])

    @staticmethod
    def _rate_fact_sources():
        from .literature_rate_storage import rate_cells_schema, rate_source_cells_schema
        from .literature_quantity_storage import quantity_cells_schema
        from .literature_assay_storage import assay_cells_schema
        from .literature_ratio_storage import ratio_cells_schema
        from .literature_binding_storage import binding_cells_schema
        from .literature_binding_model_storage import binding_model_cells_schema
        from .literature_transport_storage import transport_response_cells_schema
        from .literature_perturbation_storage import perturbation_cells_schema
        from .literature_structure_storage import structure_cells_schema
        from .literature_reaction_storage import reaction_cells_schema
        from .literature_context_storage import context_cells_schema
        from .literature_figure_storage import figure_cells_schema
        from .literature_partner_storage import partner_cells_schema
        from .literature_amount_storage import amount_cells_schema
        from .literature_optical_storage import optical_cells_schema
        return {"literature_rate_cells": {"type": "array", "meaning":
            "Saved source-preparation rate cells with measured subject/experiment retained in the referenced sheet. Conditional statistics are not annotation probabilities or target-transfer scores; unavailable operands remain null with reasons.",
            "report_schema": rate_cells_schema()},
            "literature_rate_source_cells": {"type": "array", "meaning":
                "The same saved numerical rate components from native source spans, with each arm's actual subject/construct/preparation bindings and approximation retained. Source-supported conditional statistical assumptions do not establish causal isolation, target transfer or annotation credit. This closed native return view is distinct from the legacy table view, not a second scoring sheet.",
                "report_schema": rate_source_cells_schema()},
            "literature_quantity_cells": {"type": "array", "meaning":
                "Saved single reported source quantities, with quantity and analyte identity. Untyped spread remains untyped. Source conditions, attribution and correction scores remain unknown where unsupported.",
                "report_schema": quantity_cells_schema()},
            "literature_assay_cells": {"type": "array", "meaning":
                "Saved source-anchored assay interpretations and numerical operands/corrections. Endpoint and arrangement describe the episode's source interpretation. Known-normal indices remain conditional and are not function probabilities. Unknown operands remain null.",
                "report_schema": assay_cells_schema()},
            "literature_ratio_cells": {"type": "array", "meaning":
                "Reported comparative signal components with actual denominator/arrangement, received representation candidates and source origins. Conflicts are not sampling intervals. Calibration and functional response/uncertainty remain separate missing inputs.",
                "report_schema": ratio_cells_schema()},
            "literature_binding_cells": {"type": "array", "meaning":
                "Saved source binding-parameter components with actual protein/state/ligand comparison, uncertainty basis and reported-limit arithmetic. Limits are not confidence or true-parameter bounds; IC50 is not Kd. Missing inputs and unimplemented observation models remain explicit.",
                "report_schema": binding_cells_schema()},
            "literature_binding_model_cells": {"type": "array", "meaning":
                "Saved conditional source log-parameter contrast, full-covariance noise and signed likelihood/index components for test parameter exceeding reference. Known/estimated variance, actual censor mechanism and model origin stay explicit. Native reporting limits are not point observations or confidence bounds; these are not probabilities of function or target-transfer scores.",
                "report_schema": binding_model_cells_schema()},
            "literature_transport_cells": {"type": "array", "meaning":
                "Saved native concentrations and conditional same-curve kinetic-response components. condition_response is test substrate saturation divided by reference substrate saturation under the same fitted curve. Keep actual curve/preparation identities, Km uncertainty meaning and full covariance ownership. The response can divide an appropriate source effect once; it is not reliability or annotation credit. Missing or different curves remain unavailable.",
                "report_schema": transport_response_cells_schema()},
            "literature_perturbation_cells": {"type": "array", "meaning":
                "Saved reference-perturbation effects and proposed restoration components, retaining actual recipient/construct/partner and endpoint meanings. Calibrated same-endpoint contrasts, real restoration, nuisance comparability and effect isolation are distinct. Missing quantitative outcomes and uncertainty remain unknown. The proposed source index is not target correspondence or annotation credit.",
                "report_schema": perturbation_cells_schema()},
            "literature_structure_cells": {"type": "array", "meaning":
                "Saved conditional source-model geometry and local residue RSCC components with exact source bindings. Entry/revision validation, fixed required panels, proposed physical predicates and unreported coordinate/measurement uncertainty remain explicit. Conditional state/assignment identities do not establish population occupancy, causal isolation or target annotation credit.",
                "report_schema": structure_cells_schema()},
            "literature_reaction_cells": {"type": "array", "meaning":
                "Saved reported reference reaction-ratio residuals, fixed named-prediction comparisons and simple resource budgets. Source summary uncertainty and incomplete resources remain explicit unknowns. Product-pair ratios and supplied reagent coverage do not establish consumption, native capacity or measured coupling. Logical domain bounds are not confidence intervals; no target correspondence or annotation credit is calculated.",
                "report_schema": reaction_cells_schema()},
            "literature_context_cells": {"type": "array", "meaning":
                "Saved organism/sample compatibility bounds with the original capability-versus-coverage question, actual context frame, weights, pairing, mapping and domain qualifications. Unpaired fractions use bounds; unexamined biological situations remain unknown. Conditional Hoeffding sampling is separate from logical domains and requires the actual independent context design. Source assay observations are not additional biological samples, target-transfer weights or annotation credit.",
                "report_schema": context_cells_schema()},
            "literature_figure_cells": {"type": "array", "meaning":
                "Saved native experimental graph ordinates and signed differences with both molecule/partner arms, endpoint/normalization, source representation relationships and repeat/spread meanings. Bounds describe conditional pixel digitization, not SD or confidence intervals. Coupled product or partner-swap differences do not establish upstream-only activity, partner necessity, target correspondence or annotation credit.",
                "report_schema": figure_cells_schema()},
            "literature_partner_cells": {"type": "array", "meaning":
                "Saved experimental partner-removal and addback components with actual molecule/partner identities, nonpartner-condition comparisons, normalization, physical observation identity and reported spread meanings. Native rates survive unavailable controlled comparisons. Bounds condition on supplied censor domains and exact reported means; they are not sampling confidence. Directed condition-specific dependence does not establish universal necessity, genomic presence, coexpression, target correspondence or annotation credit.",
                "report_schema": partner_cells_schema()},
            "literature_amount_cells": {"type": "array", "meaning":
                "Saved A105 source amount components with both quantities' actual roles, preparation/stock, method, basis, qualification and covariance ownership. Target/total mass-fraction estimates differ from nominal molar arm comparisons. Conditional denominator conversion is not applied to a rate; uncertainty and unknown relationships remain explicit, without target correspondence or annotation credit.",
                "report_schema": amount_cells_schema()},
            "literature_optical_cells": {"type": "array", "meaning":
                "Saved projections of existing net_rate(q) and variance_net_rate(Vq) inputs for the source NADH-depletion endpoint, conditional on the selected optical relationships. Preserve actual subject/construct/preparation/conditions, source qualifications, local reuse and covariance ownership. This is not isolated product formation, recovery k, protein amount, corrected activity, target transfer, annotation credit or independent evidence from another rate representation.",
                "report_schema": optical_cells_schema()}}

    def _population_routes(self):
        from .literature_rate_storage import COMPONENTS, PROVIDER
        from .literature_quantity_storage import COMPONENTS as QUANTITIES, PROVIDER as QUANTITY_PROVIDER
        from .literature_assay_storage import COMPONENTS as ASSAY_COMPONENTS, PROVIDER as ASSAY_PROVIDER
        from .literature_ratio_calculations import COMPONENTS as RATIO_COMPONENTS
        from .literature_ratio_storage import PROVIDER as RATIO_PROVIDER
        from .literature_binding_calculations import COMPONENTS as BINDING_COMPONENTS
        from .literature_binding_storage import PROVIDER as BINDING_PROVIDER
        from .literature_binding_models import COMPONENTS as BINDING_MODEL_COMPONENTS
        from .literature_binding_model_storage import PROVIDER as BINDING_MODEL_PROVIDER
        from .literature_transport_storage import COMPONENTS as TRANSPORT_COMPONENTS, PROVIDER as TRANSPORT_PROVIDER
        from .literature_perturbation_storage import COMPONENTS as PERTURBATION_COMPONENTS, PROVIDER as PERTURBATION_PROVIDER
        from .literature_structure_storage import COMPONENTS as STRUCTURE_COMPONENTS, PROVIDER as STRUCTURE_PROVIDER
        from .literature_reaction_storage import COMPONENTS as REACTION_COMPONENTS, PROVIDER as REACTION_PROVIDER
        from .literature_context_storage import COMPONENTS as CONTEXT_COMPONENTS, PROVIDER as CONTEXT_PROVIDER
        from .literature_figure_storage import COMPONENTS as FIGURE_COMPONENTS, PROVIDER as FIGURE_PROVIDER
        from .literature_partner_storage import COMPONENTS as PARTNER_COMPONENTS, PROVIDER as PARTNER_PROVIDER
        from .literature_amount_storage import COMPONENTS as AMOUNT_COMPONENTS, PROVIDER as AMOUNT_PROVIDER
        from .literature_optical_storage import COMPONENTS as OPTICAL_COMPONENTS, PROVIDER as OPTICAL_PROVIDER
        return (("literature_rate_cells", "requested_rate_components", PROVIDER,
                 COMPONENTS, self.services.literature_rate_repository),
                ("literature_rate_source_cells", "requested_rate_components", PROVIDER,
                 COMPONENTS, self.services.literature_rate_repository().source_projection),
                ("literature_quantity_cells", "requested_quantity_components", QUANTITY_PROVIDER,
                 QUANTITIES, self.services.literature_quantity_repository),
                ("literature_assay_cells", "requested_assay_components", ASSAY_PROVIDER,
                 ASSAY_COMPONENTS, self.services.literature_assay_repository),
                ("literature_ratio_cells", "requested_ratio_components", RATIO_PROVIDER,
                 RATIO_COMPONENTS, self.services.literature_ratio_repository),
                ("literature_binding_cells", "requested_binding_components", BINDING_PROVIDER,
                 BINDING_COMPONENTS, self.services.literature_binding_repository),
                ("literature_binding_model_cells", "requested_binding_model_components", BINDING_MODEL_PROVIDER,
                 BINDING_MODEL_COMPONENTS, self.services.literature_binding_model_repository),
                ("literature_transport_cells", "requested_transport_components", TRANSPORT_PROVIDER,
                 TRANSPORT_COMPONENTS, self.services.literature_transport_repository),
                ("literature_perturbation_cells", "requested_perturbation_components", PERTURBATION_PROVIDER,
                 PERTURBATION_COMPONENTS, self.services.literature_perturbation_repository),
                ("literature_structure_cells", "requested_structure_components", STRUCTURE_PROVIDER,
                 STRUCTURE_COMPONENTS, self.services.literature_structure_repository),
                ("literature_reaction_cells", "requested_reaction_components", REACTION_PROVIDER,
                 REACTION_COMPONENTS, self.services.literature_reaction_repository),
                ("literature_context_cells", "requested_context_components", CONTEXT_PROVIDER,
                 CONTEXT_COMPONENTS, self.services.literature_context_repository),
                ("literature_figure_cells", "requested_figure_components", FIGURE_PROVIDER,
                 FIGURE_COMPONENTS, self.services.literature_figure_repository),
                ("literature_partner_cells", "requested_partner_components", PARTNER_PROVIDER,
                 PARTNER_COMPONENTS, self.services.literature_partner_repository),
                ("literature_amount_cells", "requested_amount_components", AMOUNT_PROVIDER,
                 AMOUNT_COMPONENTS, self.services.literature_amount_repository),
                ("literature_optical_cells", "requested_optical_components", OPTICAL_PROVIDER,
                 OPTICAL_COMPONENTS, self.services.literature_optical_repository))

    def _rate_facts(self, context, references):
        result = {}
        for namespace, requested_field, provider, defaults, repository in self._population_routes():
            selected = []
            adapter = repository()
            for reference in references:
                if reference not in context.received_record_refs:
                    continue
                row = self.services.read_record(reference)
                if row.get("record_type") == "source" and row.get("provider") == provider:
                    if namespace in {"literature_rate_cells", "literature_rate_source_cells"}:
                        if row.get("version") not in {"literature_rate_population_record_v1", "literature_rate_population_record_v2"}:
                            raise ContractError("literature_rate_projection_version_mismatch")
                        if row.get("version") != adapter.record_version:
                            continue
                    selected.append(reference)
            components = tuple(context.assignment.get(requested_field, defaults))
            result[namespace] = (adapter.fact_cells(context, selected, components=components)
                if namespace == "literature_optical_cells" else adapter.project_cells(selected,
                    permitted_record_refs=context.received_record_refs, components=components))
        return result

    def received_report_sources(self, role):
        return (self._rate_fact_sources() if self.rate_population and role not in ROLES else {})

    def received_report_facts(self, context):
        if not self.rate_population or context.role in ROLES:
            return {}
        result = {}
        for namespace, _, _, _, repository in self._population_routes():
            cells = repository().received_cells(context)
            if cells or namespace == "literature_rate_cells":
                result[namespace] = cells
        return result

    def received_form_references(self, context, form, schema, operation_key):
        if not self.rate_population:
            return []
        for namespace, _, _, _, repository in self._population_routes():
            cells = []
            for name, node in schema.get("properties", {}).items():
                if node.get("x-source") == namespace:
                    cells.extend(form[name])
            if cells:
                repository().receive_cells(context, cells, operation_key)
        return []

    def validate_received_report(self, context, form, schema):
        if not self.rate_population:
            return
        for namespace, requested_field, _, _, repository in self._population_routes():
            for name, node in schema.get("properties", {}).items():
                if node.get("x-source") != namespace:
                    continue
                rows = form[name]
                permitted = set(context.received_record_refs)
                if any(row["sheet_ref"] not in permitted for row in rows):
                    # Refresh only the exact child's later durable receipts.
                    selection = self.services.record_selection(context)
                    if (selection.get("run_id") != context.run_id
                            or selection.get("episode_id") != context.episode_id):
                        raise ReportBoundaryError("Literature return receiver differs",
                            code="literature_rate_receiver_mismatch", field=name)
                    permitted.update(selection["known_record_refs"])
                try:
                    if (namespace in {"literature_rate_cells", "literature_rate_source_cells"}
                            and not rows and context.assignment.get("requested_rate_components") not in ([], ())):
                        repository().validate_empty_return_family(context)
                    repository().validate_returned_values(rows, permitted_record_refs=permitted)
                    requested = context.assignment.get(requested_field)
                    if requested is not None and any(row["component"] not in requested for row in rows):
                        raise ContractError("unrequested_literature_rate_component")
                except ContractError as error:
                    raise ReportBoundaryError(str(error), code=str(error), field=name) from error

    def resolve(self, context, reference, namespace):
        self._role(context.role)
        return reference_in_context(self.services, context, reference, namespace)

    def validate_report(self, context, form, original_schema):
        self._validate_assignment(context.role, context.assignment, context.scope)
        validate_form(form, original_schema,
                      lambda reference, namespace: self.resolve(context, reference, namespace))
        self.validate_received_report(context, form, original_schema)

    def credit_view(self, context, receiver_selection):
        self._role(context.role)
        return self.services.scientific_credit(context, receiver_selection)


__all__ = ["LiteratureEpisodes", "ROLES", "VERSION"]
