from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.library.root_literature_contracts import (Mapping, deepcopy, replace, hashlib, inspect, json, Path, ReportBoundaryError, plain, validate_form, CONTRACT_INFORMATION_PROFILE, ContractError, REF, identity, obj, source_location_inputs, validate_schema, reference_in_context, VERSION, ROLES, _REFERENCES, _REPRESENTATION, _NATURAL, _POSITIVE, _TEXT, _WINDOW, _TABLE, _PAGE, _CHILDREN, EXPERIMENT_DATABASE_TOOLS, _ACCESS_TOOLS, _ACQUISITION_TOOLS, _A108_ACCESS_TOOLS, _A108_ACQUISITION_TOOLS, _A108_NAMESPACES, _READ_TOOLS, _ROLE_INSTRUCTIONS, _a108_population_catalog, _population_catalog)

class LiteratureTaskOperations:
    def _required_grading_repository(self, context=None):
        if self._enabled('a108_context_evidence', context):
            return self._a108_grading_repository()
        if self._enabled('assay_grading_population', context) and not self._enabled('a106_intervention', context):
            return self._assay_grading_repository()
        return None

    def reasoning_action_schema(self, context, commit_schema):
        repository = self._required_grading_repository(context)
        leads = context.assignment.get('literature_task', {}).get('kind') == 'verified_source_leads'
        if repository is None and not leads:
            return None
        from gene_annotation_episode.episodic_workflow.root.literature_required_grading import action_schema
        schema = (obj({'kind': {'const': 'reason'}, 'commit': deepcopy(commit_schema)}) if repository is None else
            action_schema(commit_schema, source_location_inputs(repository.population_schema())))
        if leads:
            from gene_annotation_episode.episodic_workflow.root.library.literature_task_answer_schemas import lead_schema
            schema['properties']['source_lead'] = lead_schema()
        return source_location_inputs(schema)

    def reasoning_has_task_content(self, context, selection):
        from .commission_contract import commissioned_task
        from gene_annotation_episode.episodic_workflow.root.library.literature_task_answer_schemas import lead_schema
        if 'source_lead' not in selection:
            return False
        task, _ = commissioned_task(context)
        if task['kind'] != 'verified_source_leads':
            return False
        validate_schema(plain(selection['source_lead']), source_location_inputs(lead_schema()))
        return True

    def execute_reasoning(self, context, selection, operation_key):
        repository = self._required_grading_repository(context)
        if 'source_lead' in selection:
            from .task_answers import validate_lead
            from gene_annotation_episode.episodic_workflow.root.library.literature_experimental_contracts import ExperimentalContractError
            from gene_annotation_episode.episodic_workflow.root.literature_required_grading import execute
            store = self.services.workflow.store
            try:
                witness = selection['source_lead']['witness']
                self._tool_arguments(context, 'source.read', {'source_ref': witness['source_ref'],
                    'representation': witness['representation'], 'offset': witness['start'],
                    'limit': witness['end'] - witness['start']})
                with store.transaction():
                    native = {key: value for key, value in plain(selection).items() if key != 'source_lead'}
                    ownership = ({'account_owner': (context.run_id, context.episode_id)}
                        if native['commit'].get('interpretation_accounts') else {})
                    result = (store.commit_reasoning(native['commit'], plain(context.scope), operation_key, **ownership)
                        if repository is None else execute(context, native, operation_key, repository,
                            authorize_source_access=lambda ref, representation: self._tool_arguments(
                                context, 'source.read', {'source_ref': ref, 'representation': representation})))
                    if result['status'] not in ('completed', 'partial'):
                        return result
                    return {**result, 'literature_source_lead': validate_lead(store, context, selection['source_lead'], result)}
            except (ContractError, ExperimentalContractError) as error:
                return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [], 'result': None,
                    'feedback': {'category': 'source_lead', 'code': getattr(error, 'code', str(error))}}
        if repository is None:
            return None
        from gene_annotation_episode.episodic_workflow.root.literature_required_grading import execute
        return execute(context, selection, operation_key, repository,
            authorize_source_access=lambda ref, representation: self._tool_arguments(
                context, 'source.read', {'source_ref': ref, 'representation': representation}))

    def catalog(self, context):
        self._role(context.role)
        available = self.services.tool_catalog(context.scope)
        entries = ([{"name": name, **entry} for name, entry in available.items()]
                   if isinstance(available, Mapping) else list(available))
        allowed = set(_A108_ACCESS_TOOLS if self._enabled('a108_context_evidence', context) else _ACCESS_TOOLS)
        allowed.update(_A108_ACQUISITION_TOOLS if self._enabled('a108_context_evidence', context) else _ACQUISITION_TOOLS)
        if self._enabled('a106_intervention', context):
            allowed.update(("public.ncbi.entrez", "public.ncbi.sequence"))
        if self._enabled('a106_intervention', context):
            allowed.update(("public.ncbi.geo", "public.ncbi.sra.file"))
        result = []
        for entry in entries:
            if entry["name"] not in allowed:
                continue
            entry = deepcopy(plain(entry))
            if entry["name"] == "public.ncbi.search":
                entry["input_schema"]["properties"]["database"] = {'enum':
                    ['pubmed', 'protein', 'nuccore', 'taxonomy', 'biosample', 'bioproject']
                    if self._enabled('a108_context_evidence', context) else ['pubmed']}
            if entry["name"] == "execution.estimate":
                branches = [branch for branch in entry["input_schema"].get("anyOf", ())
                    if branch.get("properties", {}).get("tool", {}).get("const") in {
                        "source.xlsx.sheets", "source.xlsx.rows"}]
                if not branches:
                    continue
                entry["input_schema"] = {"anyOf": branches}
            result.append(entry)
        if self.rate_population or self._enabled('a108_context_evidence', context):
            populations = (_a108_population_catalog() if self._enabled('a108_context_evidence', context) else _population_catalog(a106_intervention=self._enabled('a106_intervention', context), assay_grading_population=self._enabled('assay_grading_population', context),
                            ratio_source_population=self.ratio_source_population,
                            controlled_response_population=self.controlled_response_population, gel_population=self.gel_population,
                            completion_time_population=self.completion_time_population,
                            active_site_population=self.active_site_population,
                            parent_depletion_population=self.parent_depletion_population,
                            stoichiometric_balance_population=self.stoichiometric_balance_population,
                            product_partition_population=self.product_partition_population,
                            compiled_assay_population=self.compiled_assay_population,
                            channel_population=self.channel_population,
                            ion_discrimination_population=self.ion_discrimination_population))
            if self._contract_information_profile is not None:
                from gene_annotation_episode.episodic_workflow.root.composition_information import CONTRACT_ARGUMENT_TRANSPORT
                populations = [{**row, 'argument_transport': CONTRACT_ARGUMENT_TRANSPORT} for row in populations]
            result.extend(populations)
        if self._enabled('a106_intervention', context):
            from gene_annotation_episode.episodic_workflow.root.legacy_annotation.published_evidence_assessment.analysis_contract import contract_catalog
            result.extend(contract_catalog(self.services))
        # Publish location-only input contracts to the model.
        return [{**entry, 'input_schema': source_location_inputs(entry['input_schema'])}
                for entry in result]

