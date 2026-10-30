.venv/bin/python - <<'PY'
import json
from pathlib import Path
root=Path('research/slotted_process_library')
cases={c['case_group']:c for c in json.loads((root/'case_records.json').read_text())}
a=json.loads((root/'annotation_options.json').read_text())['options']
p=json.loads((root/'thought_options.json').read_text())['options']
t=json.loads((root/'tool_options.json').read_text())['options']
actual=set(json.loads(Path('/tmp/slot-source-tool-names.json').read_text()))
def cell(value): return str(value).replace('|','\\|').replace('\n',' ')
def source(e, ident, ordinal):
 record=next(r['index_reference'] for r in cases[e['case_group']]['records'] if r['index_reference']['case_id']==e['case_id'])
 path=Path('corpus')/Path(record['record_path']).relative_to('/tmp/episode-published-cases')
 pointer=('line '+str(record['line'])) if 'line' in record else 'JSON pointer `'+(record.get('json_pointer') or '/')+'`'
 return f"[E-{ident}-{ordinal:02d}]({e['source_url']}) · [{e['case_id']}]({path.as_posix()}) ({pointer})"
def example(o):
 n=1 if o['id']=='P13' else 0
 e=o['evidence'][n]
 return cell(f"**E-{o['id']}-{n+1:02d}:** {e['observation']} **Limit:** {e['limit']}")
lines=['# Current slot options and their existing sources','',
'Current contract, 2026-10-21: a bioinformatics child is constructed from an **annotation-credit focus (A)**, a **thought pattern (P)** and **a set of actual tools retrieved for the parent’s requested investigation**. The common mother supplies the iterative episode machinery; the library supplies the selected process content. No complete episode is a library option, and no T01–T13 bundle is selected to fill the tools slot.','',
'| Slot | Input to child construction | Source of allowed content |','| --- | --- | --- |',
'| Annotation-credit focus | One pinned A option describing the annotation distinction being investigated | The existing A01–A10 entries below; parent-owned declared form fields and values still determine what is reported |',
'| Thought pattern | One pinned P option constraining plausible explanations and informative contrasts | The existing P01–P19 process entries below; their choices and result contingencies guide the child’s iterative investigation |',
'| Tools | Zero or more unique actual callable names, with their real descriptions and input schemas available to the child | A retriever selects relevant operations from the complete caller-provided actual tool map for this investigation; neither A nor P installs a fixed list |','',
'The runtime correction is being implemented and has not been verified by this documentation change. Its agreed interface is:','',
'```text',
'process.tools({investigation: <parent’s desired investigation>})',
'    -> {investigation, tools: [<actual callable name>, ...], catalog: [<actual tool record>, ...]}','',
'selection = {',
'    version: "scientific_process_selection_v2",',
'    annotation_ref: <pinned A option>,',
'    thought_ref: <pinned P option>,',
'    tools: <result.tools from retrieval>',
'}',
'```','',
'`ScientificToolLibrary` freezes the complete actual caller catalog under the run’s `scientific-tool-library` directory. The test retriever matches the requested investigation against those actual names and descriptions. It returns a variable-size set; it does not generate tools or consult historical T bundle specifications as available operations. A missing implementation remains missing. A catalog definition establishes an implemented API identity; caller enablement, credentials, service reachability and native dependency availability still come from the actual run configuration and outcomes.','',
'The parent separately supplies the job, scope, constraints, evidence and typed return form. `process.revise({thought_ref, tools})` prepares a different selection for a separately commissioned child; it does not change the current episode’s selection, merge the two children’s histories or create another credit score. This source table does not claim that the new runtime interfaces have passed connected tests.','',
'## Preserved research and what this table establishes','',
'The [maintained Follow-up Lane table](corpus/follow_up_lanes.md) keeps F01–F05 and their original names and order. The A rows below show the lane IDs already recorded in each option; no new lane assignments are inferred here. The original sequence, structure, context, cellular and organismal collections remain source provenance. They do not define fixed episode levels or restrict which tools a retriever may combine.','',
'The preserved corpus contains **142 distinct case groups and 149 retained records**, including seven records retained within already-counted groups. Its existing inspection register reports **134 groups with relevant primary sections inspected and eight with abstract/summary inspection**. These are retrospective case analyses with published outcomes known. They do not establish biological replication, blind discovery or prospective episode performance.','',
'The current A/P table preserves all **29 option identities and 135 existing option/source relationships**: 59 A links and 76 P links. Each source link below names the evidence ID, links its already-recorded publication URL and points to its preserved case ID and exact record line or JSON pointer. Full per-source observations, publication locators and inspection limits remain in [OPTION_SOURCES.md](OPTION_SOURCES.md) and [option_sources.json](option_sources.json); the representative observation column does not replace them. [CASE_COVERAGE.md](CASE_COVERAGE.md) retains contextual and limited-inspection mappings for all 142 groups. Repeated use of one case does not create independent evidence.','',
'An A option describes distinctions the structured credit form may need to represent. Its `example_structured_values` are illustrative. This corpus has **no adopted mapping from these ten A identities to numerical credit axes, weights or new runtime form fields**. Those bindings must be stated explicitly before claiming they exist. Selecting any A or P option earns no credit.','',
'## Annotation-credit focus options','',
'| Existing option | Distinction contributed to the child’s decision problem | Existing Follow-up Lane IDs | One source-grounded example and its limit | All existing source links |',
'| --- | --- | --- | --- | --- |']
for o in a:
 lines.append('| '+' | '.join([f"[{o['id']}](entries/{o['id']}.json): **{cell(o['name'])}**",cell(o['description']),', '.join(f'[{x}](corpus/follow_up_lanes.md)' for x in o['follow_up_lane_ids']),example(o),'<br>'.join(source(e,o['id'],i) for i,e in enumerate(o['evidence'],1))])+' |')
lines+=['','## Thought-pattern options','',
'These entries are reusable ways to choose between explanations. Their full definitions include use conditions, live alternatives, decision guidance, result-contingent choices and boundaries. Their source cases do not prescribe a task sequence or authorize new biological experiments. A published assay can be evidence available to an investigation without being an executable tool.','',
'| Existing option | Thought contributed to the child’s decision problem | One source-grounded example and its limit | All existing source links |','| --- | --- | --- | --- |']
for o in p:
 lines.append('| '+' | '.join([f"[{o['id']}](entries/{o['id']}.json): **{cell(o['name'])}**",cell(o['description']),example(o),'<br>'.join(source(e,o['id'],i) for i,e in enumerate(o['evidence'],1))])+' |')
lines+=['','## Historical T material versus actual callable operations','',
'T01–T13 are preserved research groupings of evidence operations. Their source links can explain why an operation would be useful, and their recorded limitations can inform tool documentation. They are **not runtime tool entries, tool bundles to select, or instructions to fabricate missing operations**. `research_script_only` means a particular research script was used or described; it does not register that operation in an episode. `capability_specification` means the requested implementation is absent from the inspected ordinary tool catalog. Published author experiments remain source evidence.','',
'The table below compares that historical material with definitions actually present in [`ToolRegistry.catalog`](../../gene_annotation_episode/tools.py). Callable names are recorded individually so their descriptions and exact input schemas can be used by the actual tool map. This is a source-inspection comparison, not a T-to-tool runtime mapping and not proof that any service or native operation was executed in this correction. Source-reading operations may supply published evidence for many investigations; listing them does not create the specialized analyses described in a T proposal.','',
'| Historical research grouping and example source | Existing material that can inform process/tool information | Actual ordinary callable overlap | Exact missing specialized implementation or limit |','| --- | --- | --- | --- |']
rows={
'T01': ('Retained article/supplement inspection, including selected OarX and YeaG workbook rows; these reads were not all performed through the repository registry.', ['public.literature.search','public.literature.read','public.pmc.versions','public.pmc.files','public.pmc.asset','source.read','source.pdf.info','source.pdf.text','source.pdf.page','image.view','source.archive.members','source.archive.extract','source.xlsx.sheets','source.xlsx.rows'], 'No dedicated scientific passage-ranking or XML-table API in this catalog. Existing source windows and readers have their actual representation limits.'),
'T02': ('HemK/PrmB sequence retrieval, pairwise comparisons and motif observations; author specificity assays are evidence.', ['public.uniprot.search','public.uniprot.record','public.ncbi.search','public.ncbi.sequence','sequence.align','sequence.sites','public.hmmer.databases','public.hmmer.search','public.hmmer.collect','public.hmmer.page','public.blast.search','public.blast.collect'], 'No general registered multiple-sequence alignment, phylogenetic-tree builder, learned specificity classifier or arbitrary local motif-rule executor. Registered pairwise/site APIs retain their own narrower schemas.'),
'T03': ('Published component profiles, selected OarX neighborhoods and fusion/distribution observations; retained counting scripts do not create a comparative-genomics service.', ['public.ncbi.sequence','reference.neighborhood','material.annotations'], 'No general component-profile assembler, fusion detector or gene-tree builder in this catalog. A neighborhood read returns actual source features, not orthology or a cross-genome presence/absence inference.'),
'T04': ('Retained PDBe record reads and declared coordinate measurements, including Cas2 donor-DNA contacts and the QueH 7LC5 probe.', [], 'No ordinary PDB/PDBe acquisition, structure-geometry/contact or coordinate-distance callable. Research scripts and stored coordinates remain research artifacts.'),
'T05': ('Authors’ fold, loop-model and docking results; no fresh fold search or docking was run in the recorded 142-group work.', [], 'No ordinary DALI/Foldseek, structure superposition, receptor modeling or ligand-docking callable. Every operation in this historical grouping is a proposed capability.'),
'T06': ('Bounded Bcd redox arithmetic and BioZ/ThyX route ledgers, with explicit accounting boundaries.', ['public.rhea.search','public.rhea.reaction','public.chebi.search','public.chebi.compound'], 'Chemical/reaction lookup does not calculate a general stoichiometric ledger, thermodynamic model, isotope propagation or native flux. Those specialized calculators are absent from this catalog.'),
'T07': ('Selected published kinetic/affinity ratios and censoring bounds; supplied estimates remain distinct from raw curves.', ['source.read','source.xlsx.sheets','source.xlsx.rows'], 'Source readers do not implement general assay comparison, ratio arithmetic, kinetic fitting or uncertainty estimation. Historical arithmetic scripts are not registered tools.'),
'T08': ('Published genotype/construct/component controls and selected EnvC table rows; no new perturbation experiments.', ['source.read','source.xlsx.sheets','source.xlsx.rows'], 'No general genotype/outcome matrix constructor, control-rule engine, epistasis analysis or complex-attribution operation. Literal XLSX row filtering does not supply those analyses.'),
'T09': ('Selected deposited Rend-seq track windows and GcsR study metadata; no raw-read reconstruction or formal replication analysis.', ['public.ncbi.search','public.ncbi.sequence','reference.neighborhood','reads.map'], 'No dedicated GEO acquisition, bedGraph-window summarizer, RNA-seq/Rend-seq processing or differential analysis callable. Generic native reads.map is a mapping operation, not one of those complete RNA pipelines.'),
'T10': ('Selected YeaG workbook site rows and reported analyte/product identities; author spectra were not reprocessed.', ['source.read','source.xlsx.sheets','source.xlsx.rows'], 'No raw spectral identification, peptide/modification search, isotope fitting, occupancy correction, metabolite identification or general quantitative table transformation callable. Reading a site row does not establish direct phosphorylation.'),
'T11': ('Published growth, CFU, reporter and competition outcomes retain time and condition; bounded research comparisons did not fit new trajectories.', ['source.read','source.xlsx.sheets','source.xlsx.rows','image.view'], 'No growth-curve digitizer/fitter, flow-event analysis, lineage tracking or animal/ecological reanalysis callable. image.view exposes selected pixels; it does not run those analyses.'),
'T12': ('Published IscR oligo comparisons and regulatory contrasts retain binding, molecular input/state and transcriptional output separately.', ['public.ncbi.sequence','reference.neighborhood','sequence.align','sequence.sites'], 'No FIMO/PWM scanning, general regulatory-record join or regulon reconstruction callable. Pairwise/site comparison does not infer regulatory sign or direct sensing.'),
'T13': ('Published leader-rule panels and access/processing/assembly contrasts; no fresh topology predictor or full FlaFind evaluation.', ['public.uniprot.record','material.annotations','sequence.align','sequence.sites'], 'No SignalP/TMHMM/DeepTMHMM/FlaFind, topology/export predictor or general membrane-access table constructor. Source annotations and selected residue differences are not new predictions.')}
for o in t:
 info,names,gap=rows[o['id']]
 assert set(names)<=actual,(o['id'],set(names)-actual)
 first=f"[{o['id']}](entries/{o['id']}.json): {cell(o['name'])}<br>"+source(o['evidence'][0],o['id'],1)
 lines.append('| '+' | '.join([first,cell(info),'<br>'.join(f'`{n}`' for n in names) if names else '**None in the inspected ordinary catalog.**',cell(gap)])+' |')
lines+=['',
'Only T01/T02/T03/T06 contain operations explicitly recorded as `repository_catalog_defined`; their other operations retain their separate historical status. The ordinary readers listed for T07/T08/T10/T11 and the general sequence primitives listed for T09/T12/T13 are overlapping existing APIs, not implementations of those specialized T descriptions. Separately bound resource/monitor operations belong to their actual registered execution contexts; a manual naming them does not make them ordinary scientific-child operations. The retriever’s complete input map must come from the caller’s actual catalog, rather than this inspection table.','',
'Existing publication/source manual entries can be inspected in [`knowledge/index.json`](../../gene_annotation_episode/knowledge/index.json). Those manuals explain actual operations; they do not fill the thought-pattern slot. Their named detached homology operations are separately bound and are not definitions in the ordinary `ToolRegistry` map inspected here.','',
'## Provenance and regeneration boundary','',
'The JSON catalogs, stable entry files, [case records](case_records.json), [validation record](validation.json), [corpus snapshot manifest](corpus_snapshot_manifest.json) and historical verification artifacts are preserved. The historical `build_catalog.py` still renders the original A/P/T research catalog, including its fixed T illustrations; it does not build the corrected runtime tool map. It also overwrites generated `OPTIONS.md`. This current table is maintained separately so historical regeneration cannot silently turn those T proposals back into executable tools.','',
'No new publication inspection, biological experiment, tool execution or scoring change was performed for this correction. The delivered checks verify existing source identities/pointers and preservation of the recorded corpus; runtime retrieval and child execution require their own connected implementation checks.']
(root/'CURRENT_SLOT_SOURCES.md').write_text('\n'.join(lines)+'\n')
updates={
'README.md': '''**Current contract (2026-10-21):** select one existing annotation-credit focus
(A), one existing thought pattern (P), and a variable-size set of actual tools
retrieved from the complete caller-provided tool map for the requested
investigation. No complete episodes or T01–T13 bundles are selectable construction
entries. [CURRENT_SLOT_SOURCES.md](CURRENT_SLOT_SOURCES.md) preserves all 29 A/P
identities and 135 source relationships, retains the existing F01–F05 lane IDs,
and states which historical T operations lack actual implementations. The
runtime correction is in progress; this documentation does not verify it.

The remainder of this README records the original version-1 research catalog.
Its 42-entry counts, one-T-per-selection descriptions and capability contracts
are historical curation, superseded by the current contract above. The case
corpus and historical manifests remain preserved.

''',
'RUNTIME_INTEGRATION.md': '''**Current correction (2026-10-21):** the active construction contract is one
pinned A option, one pinned P option, and `tools: [<actual callable name>, ...]` in
`scientific_process_selection_v2`. `process.tools({investigation})` retrieves
relevant names and their real catalog records from the complete caller-provided
tool map; the parent passes `result.tools` into the tools slot. `process.revise`
prepares a separately commissioned child with `{thought_ref, tools}`. There are
no complete episode entries or selected T bundles. This implementation is in
progress and is not verified by this documentation change. See the
[current source table and exact contract](CURRENT_SLOT_SOURCES.md).

Everything below is the retained earlier integration account, including its
single `tool_ref`, explicit T-operation mappings and historical test evidence.
Those interfaces are superseded; their passing tests do not validate the
current correction. Literature episode relationships are separate from this
bioinformatics mix-and-match construction change.

''',
'OPTIONS.md': '''**Current selectable content (2026-10-21):** A01–A10 and P01–P19 retain their
identities and source evidence. The tools slot is filled by a retriever with
multiple relevant actual callable names, chosen from the complete actual tool
map for the requested investigation. T01–T13 below are preserved historical
research groupings, ineligible as runtime tool entries. Complete episodes are
not selectable library entries. The [current source table](CURRENT_SLOT_SOURCES.md)
shows every A/P source relationship and the actual implementation gaps in the
historical T material. Runtime wiring is in progress, not verified here.

The remaining generated table is the original curation display. Historical
`build_catalog.py` regeneration overwrites this status paragraph; it does not
construct the corrected runtime tool map.

'''}
for name,note in updates.items():
 file=root/name
 content=file.read_text()
 title,body=content.split('\n',1)
 file.write_text(title+'\n\n'+note+body.lstrip('\n'))
print('Wrote current table and three allowed status paragraphs.')
print('A/P source relationships:',sum(len(o['evidence']) for o in a+p))
print('Actual callable names compared:',len(set(n for _,names,_ in rows.values() for n in names)))
PY