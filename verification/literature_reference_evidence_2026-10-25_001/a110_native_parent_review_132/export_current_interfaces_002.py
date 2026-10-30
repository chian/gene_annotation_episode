"""Freeze actual current interfaces for later credit owners; no execution."""
from pathlib import Path
import hashlib,json
from gene_annotation_episode.literature_episodes import LiteratureEpisodes,_population_catalog,_ACCESS_TOOLS,_ACQUISITION_TOOLS
import gene_annotation_episode.literature_episodes as module
BASE=Path(__file__).resolve().parent
PIN=BASE/'pin_003'
assert Path(module.__file__).resolve().is_relative_to(PIN)
binding=LiteratureEpisodes(None,rate_population=True,ratio_source_population=True,controlled_response_population=True,gel_population=True)
facts=binding._rate_fact_sources()
base=_population_catalog();all_operations=_population_catalog(ratio_source_population=True,controlled_response_population=True,gel_population=True)
assert len(base)==19 and len(all_operations)==22
for filename,value in [('CURRENT_FACT_CONTRACTS_002.json',facts),('CURRENT_POPULATION_CONTRACTS_002.json',all_operations)]:
 (BASE/filename).write_text(json.dumps(value,indent=2)+'\n')
ordinary=list(dict.fromkeys([*_ACCESS_TOOLS,*_ACQUISITION_TOOLS]))
source_readers=[name for name in ordinary if name not in ('state.query','execution.estimate')]
report={'scope':'Declaredliteraturecapabilities withallthreeoptionalpopulationprofilesexplicitlyenabled; availabilitystillrequiresactualboundsource/service/scientificscope. Theseareoperationcounts, NOTassaygrader/sheet/experimentcounts.','default_population_operations':len(base),'optional_population_operations':len(all_operations)-len(base),'all_population_reader_calculator_operations':len(all_operations),'source_access_acquisition_reader_operations':len(source_readers),'support_operations':['state.query','execution.estimate'],'computational_biology_suite_operations_exposed':[],'complex_software_count':0,'source_reader_names':source_readers,'population_operation_names':[row['name'] for row in all_operations],'typed_return_views':len(facts),'actual_schemas_sha256':{filename:hashlib.sha256((BASE/filename).read_bytes()).hexdigest() for filename in ['CURRENT_FACT_CONTRACTS_002.json','CURRENT_POPULATION_CONTRACTS_002.json']}}
(BASE/'CURRENT_INTERFACE_INVENTORY_002.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('source_reader_names','population_operation_names','actual_schemas_sha256','scope')},indent=2))
