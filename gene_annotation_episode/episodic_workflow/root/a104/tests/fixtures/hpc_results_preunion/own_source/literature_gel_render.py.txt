"""Render only possessed gel numerical cells and source-backed meanings."""
from collections.abc import Mapping
from fractions import Fraction

from .literature_binding_interaction_render import overlaps_numbers as _shared_overlaps_numbers
from .literature_gel_native_contracts import FACT_VERSION, LANE_MEANINGS


def is_row(value):
    return isinstance(value,Mapping) and value.get('version')==FACT_VERSION


def rows_from_reports(reports):
    for report in reports:
        if isinstance(report,Mapping):
            for values in report.values():
                if isinstance(values,(list,tuple)):
                    yield from (v for v in values if is_row(v))


def overlaps_numbers(record,locations,witness_location=None):
    # A source can own both an original image and a text representation. Pixel
    # coordinates and authenticated UTF8 spans are different coordinate spaces;
    # a text condition is not a gel pixel operand just because its source agrees.
    anchor=record.get('anchor')
    text_span=(witness_location is not None and witness_location.get('kind')=='utf8_span'
        or isinstance(anchor,Mapping) and type(anchor.get('start')) is int and type(anchor.get('end')) is int)
    if text_span:locations=[loc for loc in locations if loc['kind']=='utf8_span']
    return _shared_overlaps_numbers(record,locations,witness_location)


def hidden_records(reports,records,*,bindings=None):
    rows=list(rows_from_reports(reports));locations=[loc for r in rows for loc in r['numeric_locations']]
    refs={r['sheet_ref'] for r in rows}
    refs.update(b['record_ref'] for r in rows for b in (bindings or {}).get(r['sheet_ref'],{}).values())
    # Source handles retain custody, but do not expand the underlying paper or
    # image in the automatic fact display. Disjoint separately admitted facts
    # keep their own record identities and remain independently renderable.
    refs.update(d['source_dependency']['source_ref'] for r in rows for d in r['numerical_dependencies'])
    refs.update(loc['source_ref'] for r in rows for loc in r['numeric_locations'])
    refs.update(record['source_ref'] for ref,record in records.items()
        if ref in refs and record.get('source_ref') is not None)
    return refs|{ref for ref,record in records.items() if overlaps_numbers(record,locations)}


def _number(exact):
    if exact is None:return None
    value=Fraction(int(exact['numerator']),int(exact['denominator']))
    try:return float(value)
    except OverflowError:return str(value)


def render_received(parts,rows,records,*,section,table,values,bindings=None):
    rows=list(rows)
    if not rows:return
    locations=[loc for r in rows for loc in r['numeric_locations']]
    assignments=[];sheets=[];lane_keys=[];band_keys={}
    for row in rows:
        if row['sheet_ref'] not in sheets:sheets.append(row['sheet_ref'])
        choice=(row['sheet_ref'],row['assignment_id'])
        if row['assignment_id'] is not None and choice not in assignments:assignments.append(choice)
        for lane in row['scientific_context']['lanes']:
            key=(row['sheet_ref'],lane['lane_id'])
            if key not in lane_keys:lane_keys.append(key)
        if row['band_id'] is not None:
            key=(row['sheet_ref'],row['lane_id'])
            bands=band_keys.setdefault(key,[])
            if row['band_id'] not in bands:bands.append(row['band_id'])
    # These names identify only the currently possessed display. They neither
    # expose original IDs nor invent a biological relation between lanes/bands.
    def lane_name(row,lane_id):
        return 'Lane '+str(lane_keys.index((row['sheet_ref'],lane_id))+1)
    def choice_name(row):
        return (str(assignments.index((row['sheet_ref'],row['assignment_id']))+1)
            if row['assignment_id'] is not None else 'Range '+str(sheets.index(row['sheet_ref'])+1))
    def region_name(row):
        if row['band_id'] is not None:
            number=band_keys[(row['sheet_ref'],row['lane_id'])].index(row['band_id'])+1
            return 'Band '+str(number)+' ('+row['band_role']+')'
        return {'background':'background','whole_lane':'whole lane'}.get(row['region_kind'],
            'lane component' if row['view']=='lane' else 'comparison lanes')
    def label(row,reference):
        if reference is None:return 'unknown'
        binding=(bindings or {}).get(row['sheet_ref'],{}).get(reference)
        record=records.get(reference)
        if binding is None or record is None:return 'source-bound meaning retained for scoped access'
        if any(overlaps_numbers(record,locations,location) for location in binding['canonical_witness_locations']):
            return 'source-bound meaning retained for scoped access'
        return record['label']+(' (source label preview)' if binding['label_preview'] else '')
    section(parts,'Requested gel display components',table(
        ('View','Reading choice','Lane','Region / band','Component','Value','Lower','Upper','Unit','Status','Unavailable reason'),
        ((r['view'],choice_name(r),lane_name(r,r['lane_id']) if r['lane_id'] is not None else 'see role map',region_name(r),
          r['component'].replace('_',' '),r['cell']['value'] if r['cell']['value'] is not None else _number(r['cell']['exact']),
          _number(r['cell']['lower']),_number(r['cell']['upper']),r['cell']['unit'],r['cell']['status'],
          r['cell']['unavailable_reason']) for r in rows)))
    section(parts,'Local display labels',
        'Lane and band numbers are local labels for this returned subset, not original gel numbering.')
    seen=set()
    for row in rows:
        context=row['scientific_context']
        for category,meaning in context['global'].items():
            key=(row['sheet_ref'],'global',category,str(meaning))
            if key in seen:continue
            seen.add(key)
            section(parts,'Gel experimental meaning',table(('Meaning','State','Source interpretation'),[
                (category.replace('_',' '),meaning['state'],label(row,meaning['value_ref']))]))
        for lane in context['lanes']:
            key=(row['sheet_ref'],'lane',lane['lane_id'])
            if key in seen:continue
            seen.add(key)
            section(parts,lane_name(row,lane['lane_id'])+' source meaning',table(('Meaning','State','Source interpretation'),
                ((name.replace('_',' '),lane[name]['state'],label(row,lane[name]['value_ref'])) for name in LANE_MEANINGS)))
        if context['comparison_roles'] is not None:
            key=(row['sheet_ref'],'comparison_roles',row['assignment_id'])
            if key not in seen:
                seen.add(key)
                section(parts,'Gel comparison lane roles',table(('Reading choice','Role','Lane'),
                    ((choice_name(row),role,lane_name(row,lane) if lane is not None else 'not selected')
                        for role,lane in context['comparison_roles'].items())))
        if context['interpretation'] is not None:
            section(parts,'Gel comparison qualifications',values(context['interpretation']))
        section(parts,'Display measurement qualifications',values({
            'origin':row['origin'],'meaning':context['intensity_meaning'],
            'qualifications':row['cell']['qualifications'],
            'sampling uncertainty':context['sampling_uncertainty']['status'],
            'detector response calibration':context['detector_response_calibration']['status'],
            'independent preparation count':context['independent_preparation_count'],
            'unimplemented quantities':context['unimplemented_quantities']}))
        methods=list(dict.fromkeys(m['background_method'] for m in row['roi_methods']))
        if methods:section(parts,'Applicable background statistic',values(methods))
        if row['cell']['sensitivity'] is not None:
            info=row['cell']['sensitivity']
            section(parts,'Reading-choice range meaning',values({
                'meaning':info['kind'],'status':info['status'],
                'available reading choices':len(info['included_assignment_ids']),
                'unavailable reading choices':len(info['unavailable_assignment_ids']),
                'bounds unavailable choices':info['bounds_unavailable_assignments'],
                'sampling confidence level':info['sampling_confidence_level']}))


def render_own_result(parts,content,*,section,table,values,records=None,bindings=None):
    if not isinstance(content,Mapping):return False
    if isinstance(content.get('result'),Mapping):content=content['result']
    rows=content.get('cells')
    if not isinstance(rows,(list,tuple)) or not all(is_row(r) for r in rows):return False
    if not rows and 'component_keys' not in content:return False
    render_received(parts,rows,records or {},section=section,table=table,values=values,bindings=bindings)
    return True


__all__=['is_row','rows_from_reports','hidden_records','render_received','render_own_result']
