from pathlib import Path
base=Path('gene_annotation_episode')
def change(name,old,new):
 p=base/name;s=p.read_text();assert old in s,(name,old);p.write_text(s.replace(old,new))
change('bvbrc_appservice_adapters.py','    from . import bvbrc_proteome_bundle_adapter_v2 as proteome_v2','    from . import bvbrc_proteome_bundle_adapter_v2 as proteome_v2\n    from . import bvbrc_comparative_systems_bundle_adapter as comparative_systems')
change('bvbrc_appservice_adapters.py','genome_alignment, proteome, proteome_v2)}','genome_alignment, proteome, proteome_v2, comparative_systems)}')
change('api_service_execution.py','        self.proteome_returns = BVBRCProteomeReturns(self)','        self.proteome_returns = BVBRCProteomeReturns(self)\n        from .bvbrc_comparative_systems_returns import BVBRCComparativeSystemsReturns\n        self.comparative_systems_returns = BVBRCComparativeSystemsReturns(self)')
change('api_service_execution.py','            service.validate_request(assignment[\'request\'], plain(scope) if scope is not None else None)','            service.validate_request(assignment[\'request\'], plain(scope) if scope is not None else None)\n            if service.service == \'bvbrc_appservice\' and assignment[\'request\'].get(\'required_application_id\') == \'ComparativeSystems\':\n                from .bvbrc_comparative_systems_tool_info import validate_comparative_request\n                validate_comparative_request(assignment[\'request\'])')
change('api_service_execution.py','            resolved = self.appservice.resolve(context, reference, namespace)', '''            from .bvbrc_comparative_systems_returns import IDENTIFIER_NAMESPACES as COMPARATIVE_NAMESPACES
            if namespace in COMPARATIVE_NAMESPACES:
                return (self.comparative_systems_returns.resolve_own(context, reference, namespace)
                    if context.role == 'results' else
                    self.comparative_systems_returns.resolve_received(context, reference, namespace))
            resolved = self.appservice.resolve(context, reference, namespace)''')
change('bvbrc_appservice_host.py','self.api.alignment_returns, self.api.genome_alignment_returns, self.api.proteome_returns):','self.api.alignment_returns, self.api.genome_alignment_returns, self.api.proteome_returns,\n                self.api.comparative_systems_returns):')
change('bvbrc_appservice_publication.py','        result = implementation.consume_bundle(bundle, artifact_bytes=raw, supplied_values=values,', '''        if (inputs['adapter']['adapter_id'], inputs['adapter']['adapter_version']) == ('bvbrc_comparative_systems', '1'):
            from .bvbrc_comparative_systems_host_inputs import collect_comparative_systems_inputs
            data, producers, supplied = collect_comparative_systems_inputs(self, context, inputs, bundle,
                current_acquisition=current_acquisition)
            for reference, content in supplied.items():
                _require(reference not in raw or raw[reference] == content,
                    'appservice_supplied_content_bytes_conflict')
                raw[reference] = content
            extra.update(qualified_data_inputs=data, qualified_producer_evidence=producers)
        result = implementation.consume_bundle(bundle, artifact_bytes=raw, supplied_values=values,''')
change('bvbrc_appservice_publication.py',"        value = {key: deepcopy(result[key]) for key in\n",'''        if (result['adapter_id'], result['adapter_version']) == ('bvbrc_comparative_systems', '1'):
            from .bvbrc_comparative_systems_publication import encode_comparative_publication_result
            result = encode_comparative_publication_result(result)
        value = {key: deepcopy(result[key]) for key in
''')
change('bvbrc_appservice_publication.py',"('bvbrc_proteome', '1'), ('bvbrc_proteome', '2')}","('bvbrc_proteome', '1'), ('bvbrc_proteome', '2'), ('bvbrc_comparative_systems', '1')}")
change('bvbrc_appservice_publication.py',"                for name in ('sheet', 'components'):\n                    content = adapter[name + '_content']\n                    if content is not None:\n                        self._content(content, origin, name, stamp)",'''                contents = {}
                for name in ('sheet', 'components'):
                    content = adapter[name + '_content']
                    contents[name] = None if content is None else self._content(content, origin, name, stamp)
                if (adapter['adapter_id'], adapter['adapter_version']) == ('bvbrc_comparative_systems', '1'):
                    from .bvbrc_comparative_systems_publication import decode_comparative_publication_result
                    from .bvbrc_comparative_systems_bundle_projection import validate_saved_comparative_systems_projection
                    native = decode_comparative_publication_result(adapter, **contents)
                    validate_saved_comparative_systems_projection(native['sheet'], native['components'],
                        **{key: native[key] for key in ('facts', 'status', 'missing_requirements', 'diagnostics')},
                        requested_form=inputs['selector']['requested_schema'], parameters=inputs['adapter']['parameters'],
                        original_task=bundle['original_task'], bundle=bundle)''')
change('bvbrc_appservice_publication.py',"if selected is not None and (selected['adapter_id'], selected['adapter_version']) == ('bvbrc_proteome', '2'):","if selected is not None and (selected['adapter_id'], selected['adapter_version']) in {('bvbrc_proteome', '2'), ('bvbrc_comparative_systems', '1')}:")
change('execution_episodes.py',"                    proteome_versions = tuple(version for version in ('1', '2')",'''                    if ('bvbrc_comparative_systems', '1') in service.scientific_adapters:
                        from .bvbrc_comparative_systems_tool_info import comparative_systems_tool_contracts
                        for entry in comparative_systems_tool_contracts(resource_id=resource_id,
                                assignment_schema=self.api_execution.assignment_schema(resource_id)):
                            key = entry['name'], kind
                            if key not in contracts:
                                contracts[key] = entry
                            else:
                                prior = contracts[key]
                                prior['input_schema'] = {'anyOf': [prior['input_schema'], entry['input_schema']]}
                                prior['invocation_route']['routes'].extend(entry['invocation_route']['routes'])
                    proteome_versions = tuple(version for version in ('1', '2')''')
change('execution_episodes.py','            result.update(proteome)','''            result.update(proteome)
            comparative = self.api_execution.comparative_systems_returns.received_facts(context, schema)
            if set(result).intersection(comparative):
                raise ValueError('received_report_fact_conflict')
            result.update(comparative)''')
change('execution_episodes.py','            resolved = self.api_execution.appservice.resolve(context, reference, namespace)', '''            from .bvbrc_comparative_systems_returns import IDENTIFIER_NAMESPACES as COMPARATIVE_NAMESPACES
            if namespace in COMPARATIVE_NAMESPACES:
                if context.role == 'results':
                    return None
                return self.api_execution.comparative_systems_returns.resolve_received(context, reference, namespace)
            resolved = self.api_execution.appservice.resolve(context, reference, namespace)''')
# The text replacement above is intentionally restricted by indentation below.
p=base/'execution_episodes.py';s=p.read_text()
# Restore the distinct own resolver's indentation and ownership after the matched fragment.
needle="                from .bvbrc_comparative_systems_returns import IDENTIFIER_NAMESPACES as COMPARATIVE_NAMESPACES\n            if namespace in COMPARATIVE_NAMESPACES:\n                if context.role == 'results':\n                    return None\n                return self.api_execution.comparative_systems_returns.resolve_received(context, reference, namespace)\n            resolved = self.api_execution.appservice.resolve(context, reference, namespace)"
replacement="""                from .bvbrc_comparative_systems_returns import IDENTIFIER_NAMESPACES as COMPARATIVE_NAMESPACES
                if namespace in COMPARATIVE_NAMESPACES:
                    return (self.api_execution.comparative_systems_returns.resolve_own(context, reference, namespace)
                        if context.role == 'results' else
                        self.api_execution.comparative_systems_returns.resolve_received(context, reference, namespace))
                resolved = self.api_execution.appservice.resolve(context, reference, namespace)"""
assert needle in s;s=s.replace(needle,replacement);p.write_text(s)
change('execution_episodes.py','            self.api_execution.proteome_returns.validate_received_report(context, form, schema)','            self.api_execution.proteome_returns.validate_received_report(context, form, schema)\n            self.api_execution.comparative_systems_returns.validate_received_report(context, form, schema)')
change('execution_episodes.py','        from .bvbrc_proteome_returns import proteome_fact_sources','        from .bvbrc_proteome_returns import proteome_fact_sources\n        from .bvbrc_comparative_systems_returns import comparative_systems_fact_sources')
change('execution_episodes.py',"**genome_alignment_fact_sources(), **proteome_fact_sources(), 'bvbrc_appservice_support_refs'", "**genome_alignment_fact_sources(), **proteome_fact_sources(), **comparative_systems_fact_sources(), 'bvbrc_appservice_support_refs'")
change('execution_episodes.py','            references.extend(self.api_execution.proteome_returns.record_admission(context, form, schema, operation_key))','            references.extend(self.api_execution.proteome_returns.record_admission(context, form, schema, operation_key))\n            references.extend(self.api_execution.comparative_systems_returns.record_admission(context, form, schema, operation_key))')
