from pathlib import Path
p=Path('gene_annotation_episode/literature_episodes.py');s=p.read_text()
a=s.index('        if self.compiled_assay_population and self._compiled_assay_repository().has_work(context):',s.index('def initial_decision_context'))
b=s.index('        if self.ratio_source_population:',a);s=s[:a]+s[b:]
a=s.index('            if self._rate_grid_repository().has_work(context):',s.index('def initial_decision_context'))
b=s.index('            result.update(self._native_rate_display_context(context))',a);s=s[:a]+s[b:]
a=s.index('            if assignment.get("requested_rate_grid_components")',s.index('def decision_context'))
b=s.index('        if self.ratio_source_population:',a);s=s[:a]+s[b:]
for name,version in [('ratio_source','literature_ratio_source_task_v1'),('controlled_response','literature_controlled_response_task_v1'),('gel','literature_gel_task_v1')]:
 s=s.replace(f'            result["literature_{name}_work"] = {{"version": "{version}"}}\n','')
for method,key in [('_measurement_comparison_display_context','REQUESTED in context.assignment or repo.has_work(context)'),('_summary_precision_display_context','context.assignment.get(REQUESTED) or repo.has_work(context)'),('_endpoint_signal_display_context',"context.assignment.get('requested_endpoint_signal_components') or repo.has_work(context)")]:
 a=s.index('    def '+method);b=s.index('    def ',a+8);part=s[a:b]
 start=part.index('        if '+key+':');end=part.index('        return result',start)
 part=part[:start]+part[end:];s=s[:a]+part+s[b:]
p.write_text(s)
p=Path('tests/test_literature_task_selection_274.py');s=p.read_text().replace("case='unknown_units'","case='both_units_missing'");p.write_text(s)
