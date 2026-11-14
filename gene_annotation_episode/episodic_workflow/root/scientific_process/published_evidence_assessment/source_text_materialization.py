from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)
from gene_annotation_episode.episodic_workflow.root.scientific_process.published_evidence_assessment.family import member_for_role


class LiteratureSourceTextMaterialization:

    def _materialize_text_arguments(self, context, arguments, repository):
        from gene_annotation_episode.episodic_workflow.root.literature_assay_inputs import materialize_text_witness_inputs
        def read_source(ref, representation):
            source = repository._native_source(context, ref)
            self._tool_arguments(context, 'source.read', {
                'source_ref': ref, 'representation': representation})
            artifact = source.get('artifact_ref' if representation == 'original' else 'text_ref')
            if artifact is None:
                raise ContractError('literature_source_representation_unavailable')
            return {'artifact_ref': artifact, 'content': repository.store.get_artifact(artifact)}
        return materialize_text_witness_inputs(arguments, read_source=read_source)

