"""SAMStat2.5.0 textual measurements and the BV-BRC caller's failure HTML.

Scripts are inert. SVG geometry and plot ticks are never numerical inputs.
The original byte binding and exact half-open byte locators retain provenance.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from html import unescape
from html.parser import HTMLParser
import math
import re

from .bvbrc_fastqutils_contracts import FastqUtilsContractError, checked_bytes, validate_contract
from .bvbrc_fastqutils_fastqc_reader import _Report, _NONE
from .bvbrc_fastqutils_identity import native_ref
from .bvbrc_fastqutils_metric_specs import metric_spec

_COUNT = rb'(?:0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+)'
_LENGTH = rb'~?[0-9][0-9,]*(?:\.[0-9]+)? (?:bp|kb|Mb)'
_FAILURE = b'Your samstat job had a segfault error. The results could not be displayed.'
_VOID = frozenset(('area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'))
_BINS = [('MAPQ >= 30','samstat_mapq_ge30',30,255), ('MAPQ 10-29','samstat_mapq_10_29',10,29),
         ('MAPQ < 10','samstat_mapq_0_9',0,9), ('Unmapped','samstat_unmapped',None,None)]


class _Element:
    def __init__(self, tag, attrs, start, inner, parent=None):
        self.tag, self.attrs, self.start, self.inner, self.parent = tag, dict(attrs), start, inner, parent
        self.stop = self.end = None
        self.children = []
        self.bad = len(self.attrs) != len(attrs)

    def descendants(self, tag=None):
        pending = list(reversed(self.children))
        while pending:
            node = pending.pop()
            if tag is None or node.tag == tag:
                yield node
            if node.tag not in ('script','style'):
                pending.extend(reversed(node.children))


class _HTML(HTMLParser):
    """Inert tokenizer with original UTF-8 byte positions, including entities."""
    def __init__(self, raw):
        super().__init__(convert_charrefs=False)
        self.raw = raw
        self.text = raw.decode('utf-8', errors='strict')
        self.line_chars = [0]
        self.byte_at = [0]
        for i, character in enumerate(self.text):
            self.byte_at.append(self.byte_at[-1] + len(character.encode('utf-8')))
            if character == '\n':
                self.line_chars.append(i+1)
        self.root = _Element('', [], 0, 0)
        self.root.stop = self.root.end = len(raw)
        self.stack = [self.root]
        self.nodes = []
        self.feed(self.text)
        self.close()

    def byte_position(self):
        line, column = self.getpos()
        return self.byte_at[self.line_chars[line-1]+column]

    def handle_starttag(self, tag, attrs):
        start = self.byte_position()
        end = start + len(self.get_starttag_text().encode('utf-8'))
        node = _Element(tag, attrs, start, end, self.stack[-1])
        self.stack[-1].children.append(node)
        self.nodes.append(node)
        if tag in _VOID:
            node.stop = node.end = end
        else:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if self.stack[-1].tag == tag:
            node = self.stack.pop()
            node.stop = node.end = node.inner

    def handle_endtag(self, tag):
        match = next((i for i in range(len(self.stack)-1,0,-1) if self.stack[i].tag == tag), None)
        if match is None:
            return
        node = self.stack[match]
        if match != len(self.stack)-1:
            node.bad = True
        node.stop = self.byte_position()
        end = self.raw.find(b'>',node.stop)
        node.end = end+1 if end >= 0 else None
        del self.stack[match:]

    def content(self, node):
        return self.raw[node.inner:node.stop if node.stop is not None else len(self.raw)]

    def plain(self, node):
        # Used for bounded labels and table headers, never script or SVG paths.
        return unescape(re.sub(r'<[^>]*>', '', self.content(node).decode('utf-8'))).strip()

    def direct(self, node):
        stop = min((n.start for n in node.children), default=node.stop if node.stop is not None else len(self.raw))
        a, b = node.inner, stop
        while a < b and self.raw[a:a+1].isspace(): a += 1
        while b > a and self.raw[b-1:b].isspace(): b -= 1
        return self.raw[a:b].decode('utf-8'), a, b


class _Current:
    """Private leaf implementation; public handoff is only NativeDocument."""
    def __init__(self, raw, context, actual, producer):
        self.raw, self.context = raw, context
        self.r = _Report(raw, context, context['declared_format'], producer)
        self.r.doc['artifact']['actual_format'] = actual
        self.html = None
        self.pops = {}
        self.prefix = False
        self.mode = None
        self.table_groups = []

    def section(self, key, node, *, state=None, block=None, kind='table'):
        state = state or ('complete' if node.end is not None and not node.bad else 'partial')
        s = self.r.section(key, start=node.start, end=node.end, state=state)
        s['locator']['block'] = block or node.attrs.get('id') or node.tag
        self.r.raw(s, name=block or node.attrs.get('id') or node.tag, kind=kind,
                   state=state if state in ('complete','partial','unsupported','malformed') else 'unsupported')
        if state in ('partial','malformed'):
            self.r.partial(s)
        return s

    def loc(self, section, field, start, end, row=None):
        return dict(self.r.loc(section, field, start=start, end=end, row=row), block=section['locator']['block'])

    def label(self, section, node, kind='native_label', field=None):
        if node.stop is None:
            return
        value = self.html.plain(node)
        self.r.label(section, kind, value, self.loc(section, field or node.tag, node.inner, node.stop))

    def population(self, section, ordinal=0, key=None):
        key = key or ('samstat_report_records' if self.mode in ('SAM','BAM') else 'samstat_report_sequences')
        identity = key, ordinal
        if identity not in self.pops:
            pop = self.r.population(section,key,ordinal,scope='partial' if self.prefix else 'unknown')
            self.pops[identity] = pop
            if ordinal in (1,2) and (key,0) in self.pops:
                pop['parent_population_refs'] = [self.pops[key,0]['id']]
            if (key,3-ordinal) in self.pops and ordinal in (1,2):
                other = self.pops[key,3-ordinal]
                pop['disjoint_from_refs'].append(other['id'])
                other['disjoint_from_refs'].append(pop['id'])
        return self.pops[identity]

    def emit(self, section, metric, token, start, end, *, population=None, axis=None,
             field='dd', row=None, unit=None, precision=None, state=None, value=None, codes=()):
        spec = metric_spec(metric)
        diagnostics = list(codes)
        if state is None:
            decoded = unescape(token).strip()
            if decoded.lower() in ('n/a','na'):
                state, value = 'not_measured', None
            else:
                # Only known finite native decimal/count tokens are accepted.
                number = decoded.rstrip('%').strip()
                if unit in ('bp','kbp','Mbp'):
                    match = re.fullmatch(r'~?([0-9][0-9,]*(?:\.[0-9]+)?) (bp|kb|Mb)', number)
                    number = match[1] if match else ''
                elif metric == 'samstat_total_base_count' and number.endswith(' bp'):
                    number = number[:-3]
                domain = spec['value_domain']
                integer = domain in ('nonnegative_integer','integer_0_100')
                pattern = _COUNT.decode() if integer else r'(?:0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+)(?:\.[0-9]+)?'
                if not re.fullmatch(pattern,number):
                    state, value = 'malformed', None
                    diagnostics.append('malformed_native')
                else:
                    try:
                        decimal = Decimal(number.replace(',',''))
                        value = int(decimal) if integer else float(decimal)
                        state = 'available'
                        if type(value) is float and not math.isfinite(value) or value < 0 or domain in ('number_0_100','integer_0_100') and value > 100 or domain == 'number_0_1' and value > 1:
                            state, value = 'malformed', None
                            diagnostics.append('malformed_native')
                    except (InvalidOperation, ValueError, OverflowError):
                        state, value = 'malformed', None
                        diagnostics.append('malformed_native')
        precision = precision or spec['precision']
        if precision == 'native_rounded' and 'rounded_native_value' not in diagnostics:
            diagnostics.append('rounded_native_value')
        if precision == 'native_estimator' and 'native_estimator' not in diagnostics:
            diagnostics.append('native_estimator')
        if state == 'not_measured':
            diagnostics.append('missing_requested_value')
        cell = dict(id=native_ref('cell',self.context,len(self.r.doc['cells'])),artifact_ref=self.r.ref,
            locator=self.loc(section,field,start,end,row),metric=metric,axis=deepcopy(axis or _NONE),
            population_ref=population['id'] if population else None,association_ref=None,state=state,
            value=value,native_token=token,unit=unit or spec['units'][0],meaning=spec['meaning'],
            precision=precision,diagnostic_codes=list(dict.fromkeys(diagnostics)),
            section_key=section['key'],section_ordinal=section['ordinal'])
        self.r.doc['cells'].append(cell)
        section['cell_refs'].append(cell['id'])
        if state in ('malformed','truncated','incompatible'):
            self.r.partial(section,'malformed_native' if state != 'incompatible' else 'count_inconsistent','requested_measurement')
        if state == 'not_measured':
            self.r.issue('missing_requested_value',affected=[cell['id']],required='requested_measurement')
        return cell

    def length(self, section, metric, token, a, b, population, field):
        decoded = unescape(token)
        unit = 'kbp' if decoded.endswith(' kb') else ('Mbp' if decoded.endswith(' Mb') else 'bp')
        precision = ('native_estimator' if decoded.startswith('~') else
                     'native_rounded' if unit != 'bp' else 'exact_for_retained_population')
        return self.emit(section,metric,token,a,b,population=population,unit=unit,precision=precision,field=field)

    def match_emit(self, section, node, pattern, group, metric, *, population=None, field=None, **kwargs):
        match = re.search(pattern,self.html.content(node))
        if match:
            a,b = node.inner+match.start(group),node.inner+match.end(group)
            token = self.raw[a:b].decode('utf-8')
            if kwargs.pop('length',False):
                return self.length(section,metric,token,a,b,population,field or node.tag)
            return self.emit(section,metric,token,a,b,population=population,field=field or node.tag,**kwargs)

    def incompatible(self, cells):
        for cell in cells:
            cell['state'], cell['value'] = 'incompatible', None
            if 'count_inconsistent' not in cell['diagnostic_codes']:
                cell['diagnostic_codes'].append('count_inconsistent')
        self.r.issue('count_inconsistent',affected=[c['id'] for c in cells],required='requested_measurement')
        self.r.doc['parse_scope'] = 'partial'

    def finish(self):
        # Readers traverse semantic sections; native IDs still follow byte order.
        replacements = {}
        for collection, kind in (('cells','cell'),('labels','label')):
            rows = sorted(self.r.doc[collection],key=lambda r:(r['locator']['byte_start'] is None,r['locator']['byte_start'] or 0))
            for i,row in enumerate(rows):
                replacements[row['id']] = native_ref(kind,self.context,i)
            self.r.doc[collection] = rows
        def update(value):
            if isinstance(value,dict):
                for key,child in value.items():
                    if isinstance(child,str) and child in replacements: value[key]=replacements[child]
                    else: update(child)
            elif isinstance(value,list):
                for i,child in enumerate(value):
                    if isinstance(child,str) and child in replacements: value[i]=replacements[child]
                    else: update(child)
        update(self.r.doc)
        return self.r.finish()


def _prepare(raw,context,actual,producer):
    context = validate_contract('ParseContext',context)
    checked_bytes(raw,content=context['content'])
    if context['declared_format'] not in {'samstat_html','samstat_html_2_2_3','samstat_html_2_5_0','samstat_bvbrc_error_html'}:
        raise FastqUtilsContractError('shape_invalid','/declared_format')
    reader = _Current(raw,context,actual,producer)
    try:
        reader.html = _HTML(raw)
    except (UnicodeError,ValueError,RecursionError):
        section = reader.r.section('samstat_header',start=0,end=len(raw),state='malformed')
        reader.r.raw(section,name='invalid HTML bytes',state='malformed')
        reader.r.partial(section)
    return reader


def _headers(reader):
    h = reader.html
    headers = [n for n in h.nodes if n.tag=='header']
    version_nodes = [n for n in h.nodes if n.tag=='p' and (n.attrs.get('class')=='meta' or n.parent.tag=='footer')]
    versions = []
    for node in version_nodes:
        if node.stop is not None:
            for m in re.finditer(rb'SAMStat ([0-9]+\.[0-9]+\.[0-9]+)(?![0-9A-Za-z])',h.content(node)):
                versions.append((m[1].decode(),node.inner+m.start(1),node.inner+m.end(1)))
    if len(headers)!=1 or len({v[0] for v in versions})!=1 or not versions or versions[0][0]!='2.5.0' or reader.context['producer_version'] not in (None,'2.5.0') or reader.context['declared_format'] not in ('samstat_html','samstat_html_2_5_0'):
        reader.r.doc['artifact']['actual_format']='unknown'
        section = reader.r.section('samstat_header',start=0,end=len(reader.raw),state='unsupported')
        reader.r.raw(section,name='unrecognized/conflicting2.5.0 header')
        for version,a,b in versions:
            reader.r.label(section,'producer_version',version,reader.r.loc(section,'native_version',start=a,end=b))
        if reader.context['producer_version'] is not None:
            reader.r.label(section,'producer_version',reader.context['producer_version'],reader.r.loc(section,'supplied_version'))
        reader.r.issue('unsupported_version',affected=[reader.r.ref],required='native_version')
        if len({v[0] for v in versions})>1 or reader.context['producer_version'] not in (None,'2.5.0'):
            reader.r.issue('native_header_conflict',affected=[reader.r.ref],required='native_version')
        reader.r.doc['parse_scope']='unsupported'
        return False
    reader.r.doc['artifact']['producer_version']='2.5.0'
    section = reader.section('samstat_header',headers[0],kind='header')
    for version,a,b in versions:
        reader.r.label(section,'producer_version',version,reader.loc(section,'native_version',a,b))
    meta = [n for n in headers[0].descendants('p') if n.attrs.get('class')=='meta']
    if len(meta)!=1 or meta[0].stop is None:
        reader.r.partial(section,'native_header_conflict','native_version')
        return False
    mode_match = re.match(rb'(SAM|BAM|FASTA|FASTQ)(?:, gzip)?(?: &middot;|\s)',h.content(meta[0]))
    if not mode_match:
        empty = any(n.tag=='p' and n.attrs.get('class')=='banner' and n.stop is not None
                    and h.plain(n)=='This file contains no reads.' for n in h.nodes)
        if not empty or not h.content(meta[0]).startswith(b'SAMStat 2.5.0'):
            reader.r.partial(section,'native_header_conflict','requested_measurement')
            return False
        # No sequence/alignment population is established by the absent label.
        reader.mode = 'unknown'
        reader.r.label(section,'native_label','unknown',reader.r.loc(section,'input_format_not_reported'))
        reader.r.issue('source_row_absent',affected=[reader.r.ref],required='native_execution_evidence')
    else:
        reader.mode = mode_match[1].decode()
        reader.r.label(section,'native_label',reader.mode,reader.loc(section,'input_format',meta[0].inner,meta[0].inner+len(mode_match[1])))
    reader.label(section,meta[0],field='meta')
    for node in headers[0].descendants('h1'):
        reader.label(section,node,'filename')
    prefix_nodes = [n for n in headers[0].descendants('span') if n.attrs.get('class')=='partial']
    reader.prefix = any(re.search(rb'partial: first '+_COUNT+rb' reads only \(-p\); not a random sample',h.content(n)) for n in prefix_nodes)
    if reader.prefix:
        reader.r.issue('samstat_native_prefix',affected=[reader.r.ref])
    for node in prefix_nodes:
        reader.label(section,node,field='native_prefix')
    reader.r.issue('samstat_input_scope_unproven',affected=[reader.r.ref])
    match = re.search(rb'reads \(median ('+_LENGTH+rb')\)',h.content(meta[0]))
    if match:
        reader.length(section,'samstat_median_length',match[1].decode(),meta[0].inner+match.start(1),meta[0].inner+match.end(1),reader.population(section),'meta.median')
    return True


def _summary(reader,node):
    h = reader.html
    section = reader.section('samstat_summary',node)
    population = reader.population(section)
    seen = defaultdict(list)
    metrics = {'Reads':'samstat_alignment_total_count' if reader.mode in ('SAM','BAM') else 'samstat_sequence_total_count',
        'Reads (R1+R2)':'samstat_alignment_total_count', 'Bases':'samstat_total_base_count',
        'N50':'samstat_n50_length','Mean Q':'samstat_error_probability_mean_phred',
        '% mapped':'samstat_reported_mapped_percent','% MAPQ >= 30':'samstat_reported_ge30_percent',
        '% bases clipped':'samstat_soft_clipped_base_percent','Median identity':'samstat_gap_compressed_median_identity_percent'}
    for div in node.children:
        if div.tag!='div': continue
        names = [n for n in div.children if n.tag=='dt']
        values = [n for n in div.children if n.tag=='dd']
        if len(names)!=1 or len(values)!=1 or names[0].stop is None or values[0].stop is None:
            reader.r.partial(section)
            continue
        label = h.plain(names[0])
        dd = values[0]
        token,a,b = h.direct(dd)
        reader.label(section,names[0],field='dt')
        reader.r.label(section,'native_label',token,reader.loc(section,'dd.main_display',a,b))
        subs = [n for n in dd.children if n.tag=='span' and n.attrs.get('class')=='sub']
        for sub in subs: reader.label(section,sub,field='dd.sub')
        metric = metrics.get(label)
        if metric is None:
            reader.r.issue('unsupported_report_section',required='supported_parser')
            continue
        if metric=='samstat_n50_length':
            cell = reader.length(section,metric,token,a,b,population,'dd.N50')
        else:
            if label in ('Reads','Reads (R1+R2)','Bases') and token!='n/a':
                exact = [n for n in subs if n.stop is not None and re.fullmatch(_COUNT,h.content(n))]
                if len(exact)==1:
                    token,a,b = h.direct(exact[0])
                elif len(exact)>1 or not re.fullmatch(_COUNT+(rb' bp' if label=='Bases' else b''),token.encode()):
                    cell=reader.emit(section,metric,token,a,b,population=population,state='malformed',field='dd.exact_count')
                    seen[label].append(cell)
                    continue
            codes = ('samstat_mapq255_merged',) if label=='% MAPQ >= 30' else ()
            cell = reader.emit(section,metric,token,a,b,population=population,field='dd.'+label,codes=codes)
        seen[label].append(cell)
    for cells in seen.values():
        if len(cells)>1: reader.incompatible(cells)


def _notes(reader,node,section=None):
    section = section or reader.section('samstat_notes',node)
    h = reader.html
    nodes = [node] if node.tag in ('li','p','desc') else list(node.descendants('li'))
    for note in nodes:
        if note.stop is None: continue
        reader.label(section,note)
        population = reader.population(section)
        for prefix,metric in [(rb'Mismatch profile excludes ','samstat_mismatch_unavailable_record_count'),
                              (rb'Identity unavailable for ','samstat_identity_unavailable_record_count')]:
            pattern=prefix+rb'('+_COUNT+rb') of ('+_COUNT+rb') mapped reads'
            reader.match_emit(section,note,pattern,1,metric,population=population,field='unavailable_records')
            reader.match_emit(section,note,pattern,2,'samstat_mapped_note_record_count',population=population,field='mapped_denominator')
        for pattern in (rb'fewer than ('+_COUNT+rb') reads',rb'needs at least ('+_COUNT+rb')'):
            reader.match_emit(section,note,pattern,1,'samstat_position_minimum_records',field='position_threshold')
        match=re.search(rb'(&lt;)?([0-9]+\.[0-9]+)% of bases lie beyond position 1000',h.content(note))
        if match:
            a,b=note.inner+match.start(1 if match[1] else 2),note.inner+match.end(2)
            token=reader.raw[a:b].decode()
            metric='samstat_beyond_axis_percent_upper_bound' if match[1] else 'samstat_beyond_axis_percent'
            reader.emit(section,metric,token,a,b,population=population,field='beyond_axis_percent',
                        state='available',value=float(match[2]))


def _mapping(reader,node):
    h=reader.html
    section=reader.section('samstat_mapping',node)
    if reader.mode not in ('SAM','BAM'):
        reader.r.partial(section,'incompatible_population','requested_measurement')
        return
    tables=list(node.descendants('table'))
    if len(tables)!=1:
        reader.r.partial(section,'native_header_conflict','requested_measurement')
        return
    table=tables[0]
    heads=list(table.descendants('thead'))
    header=[h.plain(n) for n in heads[0].descendants('th')] if len(heads)==1 else []
    expected=['Line in plots','Class','Reads','% of reads']
    if header not in (expected,expected+['Read 1','Read 2']):
        reader.r.partial(section,'native_header_conflict','supported_parser')
        return
    populations=[reader.population(section,i) for i in (range(3) if len(header)==6 else [0])]
    rows=[n for n in table.descendants('tr') if n.parent.tag=='tbody']
    seen=defaultdict(list)
    group=[]
    for index,row in enumerate(rows):
        columns=[n for n in row.children if n.tag in ('td','th')]
        if row.stop is None or len(columns)!=len(header) or any(n.stop is None for n in columns):
            reader.r.partial(section)
            continue
        label=h.plain(columns[1])
        reader.label(section,columns[1],field='Class')
        bin_info=next((v for v in _BINS if v[0]==label),None)
        if bin_info is None:
            reader.r.partial(section,'native_header_conflict','requested_measurement')
            continue
        _,_,lower,upper=bin_info
        axis=dict(kind='mapq' if lower is not None else 'native_label',label=label,lower=lower,upper=upper)
        values=[]
        for column,population in [(2,populations[0])]+([(4,populations[1]),(5,populations[2])] if len(populations)==3 else []):
            token,a,b=h.direct(columns[column])
            cell=reader.emit(section,'samstat_alignment_bin_count',token,a,b,population=population,axis=axis,
                field=header[column],row=index,codes=('samstat_mapq255_merged',) if lower==30 else ())
            values.append(cell)
            seen[label,population['population_ordinal']].append(cell)
            group.append(cell)
        token,a,b=h.direct(columns[3])
        reader.emit(section,'samstat_reported_bin_percent',token,a,b,population=populations[0],axis=axis,field='% of reads',row=index)
        if len(values)==3 and all(v['state']=='available' for v in values) and values[0]['value']!=sum(v['value'] for v in values[1:]):
            reader.incompatible(values)
    for cells in seen.values():
        if len(cells)>1: reader.incompatible(cells)
    if len(rows)!=4 or {label for label,_ in seen}!={v[0] for v in _BINS}:
        reader.r.partial(section,'source_row_absent','complete_native_bytes')
    reader.table_groups.append(group)
    if table.stop is None: reader.r.partial(section)
    for svg in table.descendants('svg'):
        reader.r.raw(section,name='native mapping swatch',kind='unsupported_section',state='unsupported',
                     locator=reader.loc(section,'svg',svg.start,svg.end))
        for label in svg.descendants():
            if label.tag in ('title','desc'): reader.label(section,label)


def _plot(reader,node):
    h=reader.html
    identity=node.attrs.get('id')
    key={'plot-1':'samstat_length','plot-2':'samstat_quality_start','plot-3':'samstat_quality_start',
         'plot-4':'samstat_base_start','plot-5':'samstat_mismatch','plot-6':'samstat_identity'}[identity]
    svgs=list(node.descendants('svg'))
    # Each native figure is its own occurrence; repeated global extrema retain
    # the all-report population even in independently labeled mate figures.
    wrapper=reader.section('samstat_plot_unavailable' if svgs else key,node)
    population=reader.population(wrapper)
    for svg in svgs:
        section=reader.section(key,svg,block=svg.attrs.get('aria-labelledby') or identity+'.svg')
        unavailable=reader.r.section('samstat_plot_unavailable',start=svg.start,end=svg.end,state='unsupported')
        unavailable['locator']['block']=svg.attrs.get('id') or svg.attrs.get('aria-labelledby') or identity+'.svg'
        reader.r.raw(unavailable,name=unavailable['locator']['block'],state='unsupported')
        reader.r.issue('samstat_svg_values_not_retained',affected=[reader.r.ref],required='requested_measurement')
        for item in svg.descendants():
            if item.tag not in ('desc','title') or item.stop is None: continue
            reader.label(section,item,field=item.attrs.get('id') or item.tag)
            if item.tag!='desc': continue
            if identity=='plot-1':
                pattern=rb'Read lengths range from ('+_LENGTH+rb') to ('+_LENGTH+rb')\.'
                reader.match_emit(section,item,pattern,1,'samstat_min_length',population=population,field='desc.global_min_length',length=True)
                reader.match_emit(section,item,pattern,2,'samstat_max_length',population=population,field='desc.global_max_length',length=True)
            elif identity=='plot-2':
                pattern=rb'mean base quality, from Q([0-9]+) to Q([0-9]+)\.'
                match=re.search(pattern,h.content(item))
                if match:
                    for group,metric in ((1,'samstat_min_read_quality_bin'),(2,'samstat_max_read_quality_bin')):
                        value=int(match[group]);a,b=item.inner+match.start(group),item.inner+match.end(group)
                        reader.emit(section,metric,match[group].decode(),a,b,population=population,
                            axis=dict(kind='quality_score',label='Q'+str(value),lower=value,upper=value),field='desc.global_quality_bin')
            if identity in ('plot-3','plot-4','plot-5'):
                reader.match_emit(section,item,rb'fewer than ('+_COUNT+rb') reads',1,'samstat_position_minimum_records',field='desc.position_threshold')
    section=wrapper
    for item in node.descendants('p'):
        if item.attrs.get('class') not in ('plot-na','plot-note') or item.stop is None: continue
        reader.label(section,item)
        if identity=='plot-1':
            pattern=rb'(?:All '+_COUNT+rb' reads are |The read is )('+_LENGTH+rb') long\.'
            reader.match_emit(section,item,pattern,1,'samstat_uniform_length',population=population,field='plot-note.uniform_length',length=True)
        reader.match_emit(section,item,rb'needs at least ('+_COUNT+rb')',1,'samstat_position_minimum_records',field='plot-na.position_threshold')


def _footer(reader,node):
    section=reader.section('samstat_notes',node,block='footer')
    for item in node.descendants('p'):
        if item.stop is None: continue
        reader.label(section,item)
        for word,metric,key in [('secondary','samstat_secondary_excluded_count','samstat_excluded_secondary'),
                                ('supplementary','samstat_supplementary_excluded_count','samstat_excluded_supplementary')]:
            pattern=rb'('+_COUNT+rb') '+word.encode()+rb' alignments \(not counted\)'
            if re.search(pattern,reader.html.content(item)):
                reader.match_emit(section,item,pattern,1,metric,population=reader.population(section,key=key),field=word+'_excluded')


def parse_samstat_html_2_5_0(raw: bytes, *, context: dict) -> dict:
    """Read only source-established2.5.0 textual values, never invert SVG."""
    reader=_prepare(raw,context,'samstat_html_2_5_0','SAMStat')
    if reader.html is None or not _headers(reader): return reader.finish()
    h=reader.html
    counts=defaultdict(int)
    for node in h.nodes:
        if any(parent.tag in ('script','style') for parent in _ancestors(node)): continue
        if node.tag=='dl' and node.attrs.get('class')=='strip':
            counts['summary']+=1;_summary(reader,node)
        elif node.tag=='ul' and node.attrs.get('class')=='notes':
            _notes(reader,node)
        elif node.tag=='section' and node.attrs.get('id')=='mapq':
            counts['mapping']+=1;_mapping(reader,node)
        elif node.tag=='section' and node.attrs.get('id') in {'plot-'+str(i) for i in range(1,7)}:
            _plot(reader,node)
        elif node.tag=='footer':
            counts['footer']+=1;_footer(reader,node)
        elif node.tag=='p' and node.attrs.get('class')=='banner' and node.stop is not None:
            if h.plain(node)=='This file contains no reads.':
                counts['empty']+=1
                section=reader.section('samstat_summary',node)
                token,a,b=h.direct(node)
                metric=('samstat_alignment_total_count' if reader.mode in ('SAM','BAM') else
                        'samstat_sequence_total_count' if reader.mode in ('FASTA','FASTQ') else 'samstat_reported_item_count')
                reader.emit(section,metric,token,a,b,population=None if reader.mode=='unknown' else reader.population(section),
                            state='available',value=0,field='no_reads_banner')
        elif node.tag=='script':
            section=reader.section('samstat_plot_unavailable',node,state='unsupported',block='script',kind='unsupported_section')
            reader.r.issue('unsupported_report_section',affected=[reader.r.ref],required='supported_parser')
    if counts['summary']+counts['empty']!=1 or counts['mapping']>1 or counts['footer']!=1:
        reader.r.partial(code='native_header_conflict',required='complete_native_bytes')
    if reader.mode in ('SAM','BAM') and not counts['empty'] and not counts['mapping']:
        reader.r.partial(code='source_row_absent',required='complete_native_bytes')
    htmls=[n for n in h.nodes if n.tag=='html']
    if len(htmls)!=1 or htmls[0].end is None:
        reader.r.partial(code='partial_transfer',required='complete_native_bytes')
    # Redundant observations stay retained. Contradictions never choose a winner.
    totals=[c for c in reader.r.doc['cells'] if c['metric']=='samstat_alignment_total_count' and c['state']=='available']
    for group in reader.table_groups:
        all_counts=[c for c in group if c['population_ref']==reader.pops.get(('samstat_report_records',0),{}).get('id')]
        if len(all_counts)==4 and all(c['state']=='available' for c in all_counts):
            for total in totals:
                if total['value']!=sum(c['value'] for c in all_counts): reader.incompatible(all_counts+[total])
    global_cells=defaultdict(list)
    for cell in reader.r.doc['cells']:
        if cell['metric'] in ('samstat_min_length','samstat_max_length','samstat_min_read_quality_bin','samstat_max_read_quality_bin'):
            global_cells[cell['metric']].append(cell)
    for cells in global_cells.values():
        if len({(c['value'],c['unit']) for c in cells if c['state']=='available'})>1: reader.incompatible(cells)
    return reader.finish()


def _ancestors(node):
    parent=node.parent
    while parent is not None:
        yield parent
        parent=parent.parent


def parse_samstat_bvbrc_error_html(raw: bytes, *, context: dict) -> dict:
    """Recognize the caller's error stub; one failed/null scientific sentinel."""
    reader=_prepare(raw,context,'samstat_bvbrc_error_html','FastqUtils')
    reader.r.doc['artifact']['producer_version']=None
    if reader.html is None: return reader.finish()
    h=reader.html
    headings=[n for n in h.nodes if n.tag=='h2' and n.stop is not None and h.content(n)==_FAILURE]
    if len(headings)!=1:
        section=reader.r.section('samstat_failure',start=0,end=len(raw),state='malformed')
        reader.r.raw(section,name='unrecognized caller failure',kind='error_report',state='malformed')
        reader.r.partial(section,'malformed_native','native_execution_evidence')
        return reader.finish()
    heading=headings[0]
    section=reader.r.section('samstat_failure',start=heading.start,end=len(raw),state='complete')
    section['locator']['block']='caller_error_html'
    reader.r.raw(section,name='BV-BRC run_alignment CalledProcessError HTML',kind='error_report',state='complete')
    reader.label(section,heading,field='failure_heading')
    for node in h.nodes:
        if node.tag=='p' and node.stop is not None:
            bold=[c for c in node.children if c.tag=='b']
            field=h.plain(bold[0]).rstrip(':') if len(bold)==1 else 'native_error_text'
            reader.label(section,node,'command' if field=='command' else 'native_label',field=field)
    if context['producer_version'] is not None:
        reader.r.label(section,'producer_version',context['producer_version'],reader.r.loc(section,'supplied_version_claim'))
    reader.emit(section,'samstat_alignment_total_count',None,heading.inner,heading.stop,state='failed',
                precision='not_reported',field='failure_heading',codes=('samstat_caller_failure',))
    reader.r.issue('samstat_caller_failure',affected=[reader.r.ref],required='native_execution_evidence')
    return reader.finish()


__all__=['parse_samstat_html_2_5_0','parse_samstat_bvbrc_error_html']
