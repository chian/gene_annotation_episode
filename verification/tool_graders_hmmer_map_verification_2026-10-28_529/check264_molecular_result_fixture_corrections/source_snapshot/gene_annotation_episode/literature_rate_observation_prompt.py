"""Recurring investigation instructions; pure requested-cell scientific display."""
from collections.abc import Mapping

RATE_OBSERVATION_TASK = """Evaluate the source molecule’s reported activity entries and the explicitly selected functional comparison. Inspect the original workbook’s panel, subject, native unit, group labels and individual observation labels; select those source cells deliberately. The source cells supply the measured numbers. A requested group without matching source entries remains unobserved. This targeted reader supports selected publisher XLSX numeric cells; a formula’s cached result is not an accepted measured number.

Keep the source’s reported entries separate from physical experiments and independent preparations. This reader supports a contiguous block of row-labelled observations immediately below each selected group header; the number of rows is selected from the source and is not fixed. Each observation label and value share a row, the value column matches the selected subject header, and the observation-label column matches its group header. Keep missing, censored and nondetected cells in that selected block. Selecting the exact same source cells twice does not add an entry. Different labels with equal values remain distinct reported entries. Different cells with the same observation label within one group leave their association unresolved: preserve those representations, withhold full-group summaries and retain only descriptive summaries of points whose entry identities are known. Cell locations and Parallel labels establish neither physical independence nor pairing. Preserve shared original reference cells across comparisons. CV requires a positive reported mean; retain signed native means and differences when that prerequisite fails.

When preparation grouping is unknown, retain useful source-entry mean, descriptive sample SD and CV without inventing preparation IDs, independent n, standard errors or a sampling model. SD uses the selected distinct entry count minus one and describes those reported entries only. Missing, censored and nondetected entries stay in the selected roster; available-point summaries do not replace an incomplete full-set mean.

Preserve the source-native unit convention. A same-source reported-activity difference or ratio can remain useful while physical conversion is unknown. Do not define U from an unrelated assay. Keep experimental comparability outside the selected change separate from isolation of the measured effect. A common source, subject label or unit does not establish equal active enzyme, a matched blank, calibration, product identity or molecular attribution. Source-entry variability and an explicitly selected substrate contrast inform precision and functional distinction; they are not reliability, function probabilities or annotation credit. Return exactly the requested saved components and their actual source meanings, count basis and qualifications. Keep reported source values, calculated summaries and synthetic fixtures distinctly labelled."""

RATE_OBSERVATION_OPERATION_DESCRIPTION = "Read explicitly selected original XLSX activity-entry cells from an actually received scoped source, with witnessed panel, subject, source-native unit, group and observation labels. The finite layout requires contiguous labelled rows immediately below group headers, same-row labels/values and the selected subject column. Source numeric nonformula cells supply all measured points; formula caches remain unsupported. Select source_kind explicitly; synthetic fixtures retain synthetic input origin. Populate descriptive reported-entry mean/SD/CV and a specified same-source reported-convention difference/ratio. Preserve unknown grouping, physical conversion, method/blank/calibration/product attribution; do not infer preparation n, pairing, SE, corrected rate, assay reliability or annotation credit. Same-cell selections deduplicate; reused labels at different rows leave association and distinct-entry count unknown. Missing/censored/nondetected selected entries remain in the roster, with explicit partials. CV requires a positive mean."


def is_row(row):
    return isinstance(row,Mapping) and row.get('evaluation_scope') in ('source_reported_rate_observations','source_reported_curve_precision') and 'component' in row


def rows_from_values(value):
    if is_row(value):yield value
    elif isinstance(value,Mapping):
        for child in value.values():yield from rows_from_values(child)
    elif isinstance(value,(list,tuple)):
        for child in value:yield from rows_from_values(child)


def rows_from_reports(reports):
    for report in reports:
        if isinstance(report,Mapping):
            for value in report.values():
                if isinstance(value,(list,tuple)):yield from (r for r in value if is_row(r))


def render_received(parts,rows,*,section,table):
    rows=list(rows)
    render_grid_received(parts,[r for r in rows if is_grid_row(r)],section=section,table=table)
    rows=[r for r in rows if not is_grid_row(r)]
    comparisons={};entries={}
    for row in rows:
        comparisons.setdefault(row['sheet_ref'],[]).append(row)
        for group in row['groups'].values():
            for entry in (group['observed']['observation_labels'] if group['observed'] else ()):
                entries.setdefault(entry['record_identity'],len(entries)+1)
    for number,comparison in enumerate(comparisons.values(),1):
        first=comparison[0]
        section(parts,'Reported activity comparison '+str(number),table(
            ('Subject','Source panel / reported endpoint','Native source convention','Input origin'),
            [(first['subject'],first['panel'],first['source_native_unit'],', '.join(first['input_origins']))]))
        section(parts,'Requested reported-entry numerical components',table(
            ('Component','Value','Unit','Status','Unavailable reason'),
            [(row['component'],row['value'],row['unit'],row['status'],row['unavailable_reason']) for row in comparison]))
        section(parts,'Requested groups and actual count basis',table(
            ('Role','Requested group','Observed status','Distinct source entries','Selected rows','Known entries','Available points','Representations','Complete','Association unresolved'),
            [(role,g['requested_label'],g['status'],g['observed']['entry_count'] if g['observed'] else None,
              g['observed']['selected_row_count'] if g['observed'] else None,
              g['observed']['known_entry_count'] if g['observed'] else None,
              g['observed']['point_entry_count'] if g['observed'] else None,
              g['observed']['representation_count'] if g['observed'] else None,
              g['observed']['complete'] if g['observed'] else None,
              g['observed']['association_unresolved'] if g['observed'] else None) for role,g in first['groups'].items()]))
        section(parts,'Source-labelled entry identity and reuse',table(
            ('Role','Group','Source observation label','Local report-entry identity','Status','Conflict','Association unresolved','Limitation'),
            [(role,g['requested_label'],entry['label'],'source entry '+str(entries[entry['record_identity']]),
              entry['status'],entry['conflicting'],entry['association_unresolved'],entry['unavailable_reason'])
             for role,g in first['groups'].items() for entry in (g['observed']['observation_labels'] if g['observed'] else ())]))
        section(parts,'Scientific qualifications',table(('Meaning','Status'),
            [('Arithmetic','same-source reported convention only'),('Preparation grouping / independent n','unknown'),
             ('SD / CV basis','descriptive across distinct reported entries; denominator entry_count-1 for SD'),
             ('SE / pairing / between-preparation SD','unavailable; grouping and sampling design unknown'),
             ('Physical unit conversion / assay method / blank / calibration / product attribution','unknown'),
             ('Experimental comparability / effect isolation','not established by common source, subject or units')]))
        section(parts,'Requested calculation meanings',table(('Component','Calculation'),
            [(row['component'],row['formula']) for row in comparison]))


# The complete reviewed five-paragraph source-investigation TASK.
REPORTED_CURVE_TASK = "Evaluate what the reported rate curves establish about the studied molecule's activity and the precision of that inference. Identify the actual construct, preparation, experimental system, substrate, measured endpoint, unit and normalization. Establish which molecules replace one another and which reporter or coupling enzymes coexist. Start from supplied material; a candidate annotation is not required.\n\nRead the original source's concentration values, individual rate entries, reporting-column or replicate labels, blanks, calibration information and uncertainty descriptions together. Preserve absent, censored and nondetected entries in the selected roster. Distinguish a source reporting label from an actual sampling unit or independent protein preparation. A triplicate caption does not by itself establish biological independence, physical pairing or a parameter standard error. Preserve conflicts between source headers and Methods rather than silently choosing one endpoint meaning.\n\nSelect the numerical question and its exact estimator before assigning uncertainty. Keep per-concentration descriptive spread, variation among separately fitted curves, the mean of fitted parameter vectors and a fit to averaged observations distinct. Identify the fit model, weighting, selected data and applicable parameter units. A covariance belongs to its original estimator, model and source measurements; matching numbers or units do not authorize reuse on a published or differently fitted estimate. Preserve signed shared-measurement and shared-fit covariance rather than treating dependent parameters as independent experiments.\n\nAsk deterministic readers and calculators for the requested numerical components. Keep descriptive source variability separate from explicitly conditional sampling-model uncertainty. Use an IID-unit or paired-unit model only with its declared source-supported or stipulated meaning; unknown physical grouping remains unknown. A native amount-rate amplitude is not a molecular turnover rate without the applicable amount and active-fraction normalization. Preserve useful native results when a fit, normalization or uncertainty conversion is unimplemented or unsupported.\n\nExplain which weaknesses remain for the functional assertion. Reporter precision does not establish chemical product identity, recovery, assay accuracy or isolation of the molecule's contribution. Examine applicable no-molecule controls, quantitative matrix/coupling validation and complementary product or coproduct measurements. Different endpoints may address different weaknesses while sharing preparations or measurements; they do not automatically provide independent replication. Return exactly the requested numerical components and necessary qualifications in the parent's form, with missing source information distinct from unfinished implementation. Final annotation credit and continuation retain their existing owners.\n"
REPORTED_CURVE_SCOPE_TASK = 'For the reported-curve precision calculation, preserve that the selected reported concentration coordinates are treated as fixed. The resulting uncertainty describes the selected rate-curve estimator under its declared sampling scenario; it does not include concentration calibration uncertainty, blank or recovery uncertainty, active molecular amount uncertainty, or unresolved reporter-to-product meaning. Do not present it as total physical uncertainty or as the uncertainty of a published parameter estimate.'

RATE_OBSERVATION_UNION_OPERATION_DESCRIPTION = "Populate requested numerical components from actually received source XLSX cells. The original row-labelled branch retains reported-entry descriptive contrasts under its original layout and native convention. The explicit reported-curve branch reads concentration rows and reporting columns, authenticates selected unit/endpoint/sampling context, and supplies requested descriptive spread, fitted-estimator and conditional covariance scalars. Keep the mean of fitted parameter vectors separate from fitting point means. Source labels do not establish physical IID preparations. Preserve fixed concentration-coordinate scope, endpoint conflicts, source versus implementation limitations and available-only partials. Native amount-rate Vmax is not kcat; no overall reliability grade or annotation credit."


def is_grid_row(value):
    return is_row(value) and value.get('evaluation_scope')=='source_reported_curve_precision'


def grid_task_relevant(state):
    assignment=state.get('literature_assignment',{})
    if isinstance(assignment,Mapping) and assignment.get('requested_rate_grid_components'):return True
    if state.get('literature_rate_grid_work',{}).get('version')=='literature_reported_curve_task_v1':return True
    form=state.get('requested_form',{})
    if isinstance(form,Mapping) and any(isinstance(v,Mapping) and v.get('x-source')=='literature_rate_grid_cells'
            for v in form.get('properties',{}).values()):return True
    result=(state.get('last_local_outcome') or {}).get('result',{})
    if isinstance(result,Mapping) and result.get('view')=='reported_curve_precision_components':return True
    return any(is_grid_row(r) for r in rows_from_values((state.get('child_reports',()),state.get('current_report_update',{}))))


def legacy_task_relevant(state):
    assignment=state.get('literature_assignment',{})
    if isinstance(assignment,Mapping) and assignment.get('requested_rate_observation_components'):return True
    if state.get('literature_rate_grid_operation_lookup'):return True
    result=(state.get('last_local_outcome') or {}).get('result',{})
    if isinstance(result,Mapping) and result.get('view')=='reported_rate_observation_components':return True
    return any(not is_grid_row(r) for r in rows_from_values((state.get('child_reports',()),state.get('current_report_update',{}))))


def grid_state_view(state,lookup_results=()):
    """Detached presentation marker; original assignments/contracts are untouched."""
    from .literature_numerical_return_presentation import reported_curve_lookup
    if any(reported_curve_lookup(r) for r in lookup_results) or any(is_grid_row(r) for r in rows_from_values(lookup_results)):
        state={**state,'literature_rate_grid_work':{'version':'literature_reported_curve_task_v1'}}
    if any(isinstance(r,Mapping) and r.get('status')=='completed'
            and r.get('result',{}).get('information_kind')=='operation_contract_information_v1'
            and r['result'].get('operation')=='literature.rate.observations.populate' for r in lookup_results):
        state={**state,'literature_rate_grid_operation_lookup':True}
    return state


def hidden_grid_records(rows,records):
    """Do not hydrate numerical context through generic scientific aliases."""
    locations=[loc for row in rows if is_grid_row(row) for loc in row['host_custody']['context_locations']]
    workbook={loc['artifact_ref'] for row in rows if is_grid_row(row) for loc in row['host_custody']['selected_cell_locations']}
    hidden=set()
    for ref,record in records.items():
        if not isinstance(record,Mapping):continue
        anchor=record.get('anchor')
        if not isinstance(anchor,Mapping):continue
        if anchor.get('artifact_ref') in workbook or any(anchor.get('artifact_ref')==loc['artifact_ref']
                and type(anchor.get('start')) is int and type(anchor.get('end')) is int
                and anchor['start']<loc['end'] and loc['start']<anchor['end'] for loc in locations):hidden.add(ref)
    return hidden


def render_grid_received(parts,rows,*,section,table):
    grouped={};seen=set()
    for row in rows:
        import json
        key=json.dumps(row,sort_keys=True,allow_nan=False)
        if key in seen:continue
        seen.add(key);grouped.setdefault(row['sheet_ref'],[]).append(row)
    sets={};estimators={};models={}
    def local(mapping,key,name):
        if key is None:return 'not applicable'
        if key not in mapping:mapping[key]=name+' '+str(len(mapping)+1)
        return mapping[key]
    def exact(value):
        if value is None:return 'unknown'
        return value['numerator'] if value['denominator']=='1' else value['numerator']+'/'+value['denominator']
    for number,selected in enumerate(grouped.values(),1):
        first=selected[0]
        section(parts,'Reported curve precision '+str(number),table(('Aspect','Scientific meaning'),
            [(name,value['display_text']) for name,value in first['source_context'].items()]+
            [('Source kind',first['source_kind']),('Input origins',', '.join(first['input_origins']))]))
        section(parts,'Requested curve precision results',table(
            ('Question','Ordinary value','Conditional scenario','Unit','Status','Estimator'),
            [(row['selector']['scope']+': '+row['selector']['component'],row['value'],row['conditional_value'],
              row['unit'],row['status'],row['model_meaning']['estimator']) for row in selected]))
        coordinates=[(row['selector']['component'],c['role'],exact(c['exact_value']),c['unit'],c['status'],
            c['bound'],exact(c['exact_limit'])) for row in selected for c in row['coordinate_context']]
        if coordinates:section(parts,'Named source concentration coordinates',table(
            ('Component','Coordinate role','Reported point','Unit','Status','Bound','Reported limit'),coordinates))
        section(parts,'Numerical meanings and limitations',table(
            ('Component','Calculation','Numeric basis','Source point/count limits','Model or relationship limits','Implementation limits'),
            [(r['selector']['component'],r['formula_id'],r['numeric_basis'],', '.join(r['source_missing_reasons']),
              ', '.join(r['relationship_reasons']),', '.join(r['implementation_reasons'])) for r in selected]))
        section(parts,'Sampling and fixed-coordinate scope',table(('Aspect','Meaning'),
            list(first['sampling'].items())+list(first['scientific_scope'].items())+
            [('Count basis',first['count_basis'])]))
        section(parts,'Selected statistic reporting denominators',table(('Component','Reporting meaning','Count'),
            [(row['selector']['component'],key,value) for row in selected for key,value in row['reporting_counts'].items() if value is not None]))
        section(parts,'Shared source and estimator dependencies',table(('Component','Source quantities','Estimator identity','Sampling scenario','Variance status'),
            [(row['selector']['component'],local(sets,tuple(row['input_measurement_keys']),'shared source set'),
              local(estimators,row['estimator_key'],'selected estimator'),
              ', '.join(local(models,k,'declared scenario') for k in row['model_keys']) or 'not used',row['variance_status']) for row in selected]))
        section(parts,'Interpretation limits',table(('Meaning',),[
            ('Source sets and estimator labels identify reuse, not independent experiments.',),
            ('Reporting columns and entry counts do not establish physical preparations or biological n.',),
            ('Reporter precision does not establish product identity, recovery, molecular attribution or annotation credit.',),
            ('Only requested scalars and their named concentration context are returned; other source entries and fitted values stay scoped.',)]))
