from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a103.homology_result_acquisition.contracts import ContractError, artifact_path

class AcquisitionPlanning:

    def prospective_execution_classes(self, store, scope):
        """Caller-resource configurations for actual eligible protein records.

        Reading this inventory does not translate a sequence, choose work,
        create an order, or launch anything. It is recomputed for later
        decisions so newly acquired protein records can become visible.
        """
        return list({value['execution_class'].ref: value['execution_class'] for value in self.prospective_execution_options(store, scope)}.values())

    def prospective_execution_options(self, store, scope):
        """Local selectable operands and their statistical class, never a choice.

        Query identity stays in the episode's local configuration inventory;
        it is not added to shared run statistics or credited as a finding.
        """
        if self.statistics is None:
            return []
        options = []
        offset = 0
        while True:
            page = store.query_records('subject', scope=scope, offset=offset, limit=100)
            for candidate in page['records']:
                try:
                    query = self._query(store, scope, candidate['id'])
                    symbols = artifact_path(store, query['sequence_ref']).read_text()
                except (ValueError, KeyError, OSError, ContractError):
                    continue
                for cpu in self.jobs.cpu_forecast_choices:
                    for mode in self.jobs.search_modes:
                        execution_class = self.statistics.execution_class_for_query(self.jobs, query_fasta='>query\n' + symbols + '\n', cpu=cpu, search_mode=mode)
                        options.append({'query_ref': query['id'], 'cpu': cpu, 'search_mode': mode, 'execution_class': execution_class})
            if page['next_offset'] is None:
                return options
            offset = page['next_offset']
