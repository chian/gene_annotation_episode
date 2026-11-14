from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)
from gene_annotation_episode.episodic_workflow.root.scientific_process.published_evidence_assessment.family import member_for_role

class LiteraturePopulationDisplay:

    def _concentration_window_display_context(self, context):
        return {'literature_concentration_window_receipt_bindings': self._concentration_window_repository().receipt_bindings()}

    def _measurement_comparison_display_context(self, context):
        from gene_annotation_episode.episodic_workflow.root.library.literature_measurement_comparison_metadata import REQUESTED
        repo = self._measurement_comparison_repository()
        result = {'literature_measurement_comparison_receipt_bindings': repo.receipt_bindings()}
        return result

    def _summary_precision_display_context(self, context):
        from gene_annotation_episode.episodic_workflow.root.library.literature_kinetic_summary_precision_metadata import REQUESTED
        repo = self._summary_precision_repository()
        result = {'literature_summary_precision_receipt_bindings': repo.receipt_bindings()}
        return result

    def _endpoint_signal_display_context(self, context):
        repo = self._endpoint_signal_repository()
        result = {'literature_endpoint_receipt_bindings': repo.receipt_bindings()}
        return result

    def _controlled_response_bindings(self, context):
        """Host-only selected label locations, limited to this episode's possession."""
        from gene_annotation_episode.episodic_workflow.root.literature_controlled_response_storage import PROVIDER, COMPONENTS, VIEWS
        repository = self._controlled_response_repository()
        rows = list(repository.received_cells(context))
        for reference in context.received_record_refs:
            record = self.services.read_record(reference)
            if record.get("record_type") == "source" and record.get("provider") == PROVIDER:
                # Explicit host inspection of the owned/admitted roster is not
                # a default scientific return request. fact_cells enforces the
                # original owner or the receiver's exact admitted subset.
                keys = repository.requested_component_keys(reference, {
                    "requested_controlled_response_components": list(COMPONENTS),
                    "requested_controlled_response_views": list(VIEWS)})
                rows.extend(repository.fact_cells(context, [reference], components=keys))
        unique = {}
        for row in rows:
            key = (row["sheet_ref"], row["component_key"])
            if key in unique and unique[key] != row:
                raise ContractError("controlled_response_possession_conflict")
            unique[key] = row
        return repository.semantic_bindings(list(unique.values()))
    def _gel_bindings(self, context):
        """Host-only selected label locations, limited to this episode's possession."""
        from gene_annotation_episode.episodic_workflow.root.literature_gel_storage import PROVIDER, COMPONENTS, VIEWS
        repository = self._gel_repository()
        rows = list(repository.received_cells(context))
        for reference in context.received_record_refs:
            record = self.services.read_record(reference)
            if record.get("record_type") == "source" and record.get("provider") == PROVIDER:
                # Explicit host inspection of the owned/admitted roster is not
                # a default scientific return request. fact_cells enforces the
                # original owner or the receiver's exact admitted subset.
                keys = repository.requested_component_keys(reference, {
                    "requested_gel_components": list(COMPONENTS),
                    "requested_gel_views": list(VIEWS)})
                rows.extend(repository.fact_cells(context, [reference], components=keys))
        unique = {}
        for row in rows:
            key = (row["sheet_ref"], row["component_key"])
            if key in unique and unique[key] != row:
                raise ContractError("gel_possession_conflict")
            unique[key] = row
        return repository.semantic_bindings(list(unique.values()))

    def _gel_display_context(self, context):
        """Actual possessed meaning records, outside generic working-state pagination."""
        bindings = self._gel_bindings(context)
        records = {}
        for entries in bindings.values():
            for reference, binding in entries.items():
                if binding["category"] != "scientific_meaning":
                    continue
                if binding["record_ref"] != reference or reference not in context.received_record_refs:
                    raise ContractError("gel_semantic_display_record_not_received")
                record = self._require(reference, context.scope, "reference")
                if record.get("id") != reference or record.get("record_type") != "reference":
                    raise ContractError("gel_semantic_display_record_mismatch")
                records[reference] = record
        return {"literature_gel_return_bindings": bindings, "literature_gel_return_records": records}

    def _received_fact_display_context(self, context):
        """Possessed scientific metadata only, independent of working pagination.

        This map grants no source bytes or additional scientific references.
        The pure renderer selects the relevant dependency closure and applies
        existing operand maskers before presenting any of these records.
        """
        from gene_annotation_episode.episodic_workflow.root.library.literature_received_fact_render import KINDS
        records = {}
        for reference in context.received_record_refs:
            # Record kind is encoded by domain.identity. Reject other handles
            # before access; source/artifact metadata is not display content.
            kind = next((kind for kind in KINDS if reference.startswith(kind + "_")), None)
            if kind is None:
                continue
            record = self._require(reference, context.scope, kind)
            if record.get("id") != reference or record.get("record_type") != kind:
                raise ContractError("literature_received_fact_display_record_mismatch")
            records[reference] = record
        if self._enabled('a108_context_evidence', context) or self._enabled('a106_intervention', context) or self._enabled('assay_grading_population', context):
            from gene_annotation_episode.episodic_workflow.root.literature_completed_work_projection import source_metadata
            records.update(source_metadata(self.services.workflow.store, context.received_record_refs))
        return {"literature_received_fact_display": {"records": records,
            "received_refs": list(context.received_record_refs)}}

    def _native_rate_display_context(self, context):
        """Exact owned/admitted rate rows and possessed meaning-record metadata."""
        from gene_annotation_episode.episodic_workflow.root.literature_rate_storage import PROVIDER, NATIVE_RECORD_VERSION
        from gene_annotation_episode.episodic_workflow.root.library.literature_rate_return_schema import COMPONENTS
        from gene_annotation_episode.episodic_workflow.root.library.literature_rate_source_render import MEANING_FIELDS
        repository = self.services.literature_rate_repository().source_projection()
        rows = list(repository.received_cells(context))
        for reference in context.received_record_refs:
            record = self.services.read_record(reference)
            if (record.get("record_type") == "source" and record.get("provider") == PROVIDER
                    and record.get("version") == NATIVE_RECORD_VERSION):
                # fact_cells authenticates original ownership or the exact
                # receiver subset. A known sheet never expands parent custody.
                rows.extend(repository.fact_cells(context, [reference], components=COMPONENTS))
        unique = {}
        for row in rows:
            key = (row["sheet_ref"], row["component"])
            if key in unique and unique[key] != row:
                raise ContractError("literature_rate_source_display_possession_conflict")
            unique[key] = row
        records = {}
        for row in unique.values():
            for field, namespace in MEANING_FIELDS.items():
                reference = row[field]
                if reference is None:
                    continue
                if reference not in context.received_record_refs:
                    raise ContractError("literature_rate_source_display_record_not_received")
                record = self._require(reference, context.scope, namespace)
                if record.get("id") != reference or record.get("record_type") != namespace:
                    raise ContractError("literature_rate_source_display_record_mismatch")
                records[reference] = record
        return {"literature_rate_source_display": {"cells": list(unique.values()), "records": records}}

    def _native_rate_domain_display_context(self, context):
        """Exact owned/admitted rate rows and possessed meaning-record metadata."""
        from gene_annotation_episode.episodic_workflow.root.literature_rate_storage import PROVIDER, NATIVE_RECORD_VERSION
        from gene_annotation_episode.episodic_workflow.root.library.literature_rate_return_schema import COMPONENTS
        from gene_annotation_episode.episodic_workflow.root.library.literature_rate_source_render import MEANING_FIELDS
        repository = self.services.literature_rate_repository().source_domain_projection()
        rows = list(repository.received_cells(context))
        for reference in context.received_record_refs:
            record = self.services.read_record(reference)
            if (record.get("record_type") == "source" and record.get("provider") == PROVIDER
                    and record.get("version") == NATIVE_RECORD_VERSION):
                # fact_cells authenticates original ownership or the exact
                # receiver subset. A known sheet never expands parent custody.
                rows.extend(repository.fact_cells(context, [reference], components=COMPONENTS))
        unique = {}
        for row in rows:
            key = (row["sheet_ref"], row["component"])
            if key in unique and unique[key] != row:
                raise ContractError("literature_rate_source_domain_display_possession_conflict")
            unique[key] = row
        records = {}
        for row in unique.values():
            for field, namespace in MEANING_FIELDS.items():
                reference = row[field]
                if reference is None:
                    continue
                if reference not in context.received_record_refs:
                    raise ContractError("literature_rate_source_domain_display_record_not_received")
                record = self._require(reference, context.scope, namespace)
                if record.get("id") != reference or record.get("record_type") != namespace:
                    raise ContractError("literature_rate_source_domain_display_record_mismatch")
                records[reference] = record
        return {"literature_rate_source_domain_display": {"cells": list(unique.values()), "records": records}}

    def _native_rate_meaning_display_context(self, context):
        """Owned or exactly admitted meaning rows; known sheets grant no expansion."""
        from gene_annotation_episode.episodic_workflow.root.literature_rate_storage import PROVIDER, NATIVE_RECORD_VERSION
        from gene_annotation_episode.episodic_workflow.root.library.literature_rate_return_schema import COMPONENTS
        from gene_annotation_episode.episodic_workflow.root.library.literature_rate_source_render import MEANING_FIELDS
        repository = self._native_rate_meaning_repository()
        rows = list(repository.received_cells(context))
        for reference in context.received_record_refs:
            record = self.services.read_record(reference)
            if (record.get("record_type") == "source" and record.get("provider") == PROVIDER
                    and record.get("version") == NATIVE_RECORD_VERSION):
                rows.extend(repository.fact_cells(context, [reference], components=COMPONENTS))
        unique = {}
        for row in rows:
            key = (row["sheet_ref"], row["component"])
            if key in unique and unique[key] != row:
                raise ContractError("literature_rate_source_meaning_display_possession_conflict")
            unique[key] = row
        records = {}
        for row in unique.values():
            for field, namespace in MEANING_FIELDS.items():
                reference = row[field]
                if reference is None:
                    continue
                if reference not in context.received_record_refs:
                    raise ContractError("literature_rate_source_meaning_display_record_not_received")
                record = self._require(reference, context.scope, namespace)
                if record.get("id") != reference or record.get("record_type") != namespace:
                    raise ContractError("literature_rate_source_meaning_display_record_mismatch")
                records[reference] = record
        return {"literature_rate_source_meaning_display": {"cells": list(unique.values()), "records": records}}

