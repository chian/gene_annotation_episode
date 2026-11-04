"""Measured gene context over actual genomic records and declared comparisons.

These functions retain observations, not functional annotations. Sequence
identification and target attribution are separate, receipt-driven operations.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import hashlib
import io
import math
from pathlib import Path
from urllib.parse import unquote

from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqFeature import CompoundLocation, SeqFeature, SimpleLocation
from Bio.SeqRecord import SeqRecord

from .comparative_ops import genbank_neighborhood, _focal_arc
from .domain import ContractError, canonical


VERSION = 'a103_measured_gene_context_v1'
PROFILE = 'a103_bounded_context_progress_v1'
MAX_FILE_BYTES = 32 * 1024**2
MAX_PANEL = 32
MAX_COMPONENTS = 16
MAX_FLANK_BP = 100_000


def require(condition, code):
    if not condition:
        raise ContractError(code)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _gff_records(content, sequence_content, genetic_code):
    """Project explicit GFF3 CDS segments into SeqRecords in original frames."""
    require(genetic_code is not None, 'a103_gff_translation_table_required')
    if not sequence_content and '##FASTA' in content:
        sequence_content = content.split('##FASTA',1)[1].lstrip()
    records = {r.id:r for r in SeqIO.parse(io.StringIO(sequence_content), 'fasta')}
    require(records, 'a103_gff_actual_fasta_required')
    groups = defaultdict(list)
    metadata = {}
    for line in content.splitlines():
        if line.startswith('##FASTA'):
            break
        if not line or line.startswith('#'):
            continue
        row = line.split('\t')
        require(len(row) == 9 and row[0] in records, 'a103_gff_feature_or_sequence_invalid')
        start, end = int(row[3])-1, int(row[4])
        require(0 <= start < end <= len(records[row[0]]), 'a103_gff_interval_invalid')
        attrs = {}
        for field in row[8].split(';'):
            if '=' in field:
                key, value = field.split('=', 1)
                attrs[key] = [unquote(v) for v in value.split(',')]
        strand = {'+':1, '-':-1, '.':None, '?':None}.get(row[6])
        require(row[6] in {'+', '-', '.', '?'}, 'a103_gff_strand_invalid')
        identity = (row[0], row[2], tuple(attrs.get('Parent', attrs.get('ID', [str(len(groups))]))))
        groups[identity].append((start, end, strand, row[7], attrs))
        metadata[identity] = attrs
    for (record_id, kind, _), parts in groups.items():
        strand = parts[0][2]
        require(all(p[2] == strand for p in parts), 'a103_gff_compound_strands_conflict')
        parts.sort(key=lambda p:p[0], reverse=strand == -1)
        locations = [SimpleLocation(a,b,strand=s) for a,b,s,_,_ in parts]
        location = locations[0] if len(locations)==1 else CompoundLocation(locations, operator='join')
        attrs = metadata[(record_id,kind,_)]
        qualifiers = {k:list(v) for k,v in attrs.items()}
        if 'Name' in attrs:
            qualifiers.setdefault('gene', attrs['Name'])
        if 'ID' in attrs:
            qualifiers.setdefault('locus_tag', attrs['ID'])
        if kind == 'CDS':
            qualifiers['locus_tag'] = attrs.get('locus_tag',attrs.get('Parent',attrs.get('ID',['unidentified'])))
            require(strand in {-1,1} and all(p[3] in {'0','1','2'} for p in parts),
                    'a103_gff_cds_phase_required')
            phase = int(parts[0][3])
            consumed = parts[0][1]-parts[0][0]-phase
            for part in parts[1:]:
                require(int(part[3]) == (-consumed) % 3, 'a103_gff_cds_phase_conflict')
                consumed += part[1]-part[0]
            qualifiers['codon_start'] = [str(phase+1)]
            qualifiers['transl_table'] = [str(genetic_code)]
            qualifiers.setdefault('protein_id', attrs.get('protein_id', attrs.get('ID', ['unidentified'])))
        records[record_id].features.append(SeqFeature(location, type=kind, qualifiers=qualifiers))
    for record in records.values():
        record.annotations.update(molecule_type='DNA', topology='linear')
    return list(records.values())


def parse_records(content, *, format='genbank', sequence_content=None, genetic_code=None):
    require(len(content.encode()) <= MAX_FILE_BYTES, 'a103_genome_file_size_limit')
    if format == 'gff3':
        records = _gff_records(content, sequence_content or '', genetic_code)
    else:
        require(format == 'genbank', 'a103_genomic_format_not_supported')
        records = list(SeqIO.parse(io.StringIO(content), 'genbank'))
    require(records, 'a103_no_genomic_records')
    require(all(str(r.annotations.get('molecule_type','')).lower() not in {'protein','aa'} for r in records),
            'a103_actual_genomic_record_required')
    return records


def _translation(record, feature):
    qualifiers = feature.qualifiers
    declared = ''.join(qualifiers.get('translation', [''])).replace(' ','').upper().rstrip('*')
    code = int(qualifiers.get('transl_table', ['1'])[0])
    offset = int(qualifiers.get('codon_start', ['1'])[0])-1
    exact = (feature.location is not None and all(type(p.start).__name__ == type(p.end).__name__ == 'ExactPosition'
             and p.ref is None for p in feature.location.parts))
    calculated = None
    reason = None
    try:
        nucleotide = str(feature.extract(record.seq))[offset:]
        if len(nucleotide) % 3:
            reason = 'partial_codon'
        else:
            try:
                calculated = str(Seq(nucleotide).translate(table=code, cds=True))
            except Exception:
                calculated = str(Seq(nucleotide).translate(table=code)).rstrip('*')
        if declared and calculated is not None and declared != calculated:
            reason = 'source_translation_exception' if qualifiers.get('transl_except') else 'declared_translation_conflict'
        if '*' in (calculated or ''):
            reason = 'internal_stop'
    except Exception:
        nucleotide = None
        reason = 'sequence_or_location_unavailable'
    if 'pseudo' in qualifiers or 'pseudogene' in qualifiers or any(v.lower()=='true' for v in qualifiers.get('partial',[])):
        reason = 'partial_or_pseudogene_annotation'
    sequence = declared or calculated
    return {'sequence':sequence, 'declared_sequence':declared or None,
            'calculated_sequence':calculated, 'nucleotide_sequence':nucleotide,
            'genetic_code':code, 'codon_start':offset+1, 'exact_boundaries':exact,
            'status':'verified' if sequence and reason is None and exact else 'qualified',
            'qualification':reason, 'translation_exception':qualifiers.get('transl_except', [])}


def bind_locus(request):
    content = Path(request['input_path']).read_text()
    records = parse_records(content, format=request['format'],
        sequence_content=Path(request['sequence_path']).read_text() if request.get('sequence_path') else None,
        genetic_code=request.get('genetic_code'))
    accession = request['accession']
    matches = [r for r in records if accession in {r.id, r.name, *r.annotations.get('accessions', [])}]
    require(len(matches) == 1, 'a103_genomic_record_not_unique')
    record = matches[0]
    selector = request['selector']
    require(len(selector)==1 and set(selector)<={'locus_tag','protein_id','coordinate'}, 'a103_choose_one_locus_selector')
    kind, value = next(iter(selector.items()))
    selected = [(i,f) for i,f in enumerate(record.features) if f.type=='CDS' and
        ((type(value) is int and f.location is not None and value in f.location) if kind=='coordinate'
         else value in f.qualifiers.get(kind, []))]
    distinct = {(str(f.location), tuple(f.qualifiers.get('protein_id',[]))) for _,f in selected}
    normalized = []
    for i,feature in selected:
        tr = _translation(record, feature)
        normalized.append({'source_feature_index':i, 'location':str(feature.location),
            'segments':[[int(p.start),int(p.end)] for p in feature.location.parts] if feature.location else [],
            'strand':feature.location.strand if feature.location else None,
            'locus_tags':feature.qualifiers.get('locus_tag',[]),
            'protein_ids':feature.qualifiers.get('protein_id',[]), 'translation':tr})
    projection = io.StringIO()
    SeqIO.write([record], projection, 'genbank')
    binding = {'schema':'a103_locus_binding_v1', 'producer_operation':'context.bind_locus',
        'target_ref':request['target_ref'], 'file_source_ref':request['file_source_ref'],
        'sequence_source_ref':request.get('sequence_source_ref'),
        'source_file_sha256':hashlib.sha256(content.encode()).hexdigest(),
        'source_format':request['format'], 'accession':record.id,
        'record_length':len(record), 'topology':record.annotations.get('topology','unknown'),
        'organism':record.annotations.get('organism'), 'source_request':request.get('source_request'),
        'source_annotations':{k:record.annotations.get(k) for k in ('accessions','sequence_version','taxonomy')},
        'selector':deepcopy(selector), 'selected_loci':normalized,
        'selection_status':'selected' if len(distinct)==1 else 'not_found' if not selected else 'ambiguous',
        'genbank_projection':projection.getvalue(), 'coordinate_system':'zero_based_half_open',
        'interpretation':'actual_source_locus; target_organism_and_function_require_separate_attribution'}
    if len(distinct)==1:
        binding['locus'] = normalized[0]
    binding['native_input_placement'] = None
    query = request.get('query_sequence')
    molecule = request.get('query_molecule')
    if query and len(distinct)==1:
        placements = []
        if molecule=='protein':
            for index,feature in enumerate(record.features):
                if feature.type!='CDS':continue
                tr = _translation(record,feature)
                if tr['status']!='verified':continue
                seq = tr['sequence']
                offset = seq.find(query)
                while offset>=0 and len(placements)<65:
                    placements.append({'feature_index':index,'reference_start':offset,
                        'reference_end':offset+len(query),'target_intervals':[[0,len(query)]]})
                    offset = seq.find(query,offset+1)
        elif molecule in {'dna','rna'}:
            bases = str(record.seq).upper()
            query = query.upper().replace('U','T')
            for strand,pattern in ((1,query),(-1,str(Seq(query).reverse_complement()))):
                offset = bases.find(pattern)
                while offset>=0 and len(placements)<65:
                    intervals = []
                    for start,end in binding['locus']['segments']:
                        a,b = max(offset,start),min(offset+len(pattern),end)
                        if a<b:
                            intervals.append([a-offset,b-offset] if strand==1 else [offset+len(pattern)-b,offset+len(pattern)-a])
                    placements.append({'feature_index':binding['locus']['source_feature_index'],
                        'reference_start':offset,'reference_end':offset+len(pattern),'strand':strand,
                        'target_intervals':sorted(intervals)})
                    offset = bases.find(pattern,offset+1)
        binding['native_input_placement'] = {'molecule':molecule,
            'state':'unique' if len(placements)==1 and placements[0]['feature_index']==binding['locus']['source_feature_index']
                and placements[0]['target_intervals'] else 'ambiguous' if placements else 'not_found',
            'placements':placements,'selection_scope':'actual_acquired_record_only; unexamined_genomes_not_excluded',
            'candidate_limit_reached':len(placements)>=65}
    return binding


def neighborhood(binding, left_bp, right_bp):
    require(binding['selection_status']=='selected', 'a103_unambiguous_locus_required')
    require(all(type(v) is int and 0 <= v <= MAX_FLANK_BP for v in (left_bp,right_bp)), 'a103_flank_limit')
    # The existing parser retains original fetch frames, partialness and circular
    # boundaries. The GFF projection is explicitly a projection, never raw input.
    raw = genbank_neighborhood(binding['genbank_projection'], accession=binding['accession'],
        selector={**binding['selector'],'feature_kind':'CDS'}, left_bp=left_bp, right_bp=right_bp,
        source_request=binding.get('source_request'))
    record = next(SeqIO.parse(io.StringIO(binding['genbank_projection']), 'genbank'))
    cds = []
    for f in raw['features']:
        if f['kind']!='CDS':
            continue
        parts = f['segments']
        local = [p for p in parts if p.get('ref') in {None,binding['accession']}]
        exact = bool(local) and len(local)==len(parts) and all(
            p.get('start_kind')==p.get('end_kind')=='ExactPosition' for p in parts)
        cds.append({'source_feature_index':f['source_feature_index'], 'source_feature_key':f.get('source_feature_key'),
            'segments':[[p['start'],p['end']] for p in local], 'strand':f['strand'],
            'exact_boundaries':exact, 'qualifiers':deepcopy(f['qualifiers']),
            'translation':_translation(record, record.features[f['source_feature_index']]),
            'focal':f['source_feature_index']==binding['locus']['source_feature_index']})
    unique = {}
    for row in cds:
        key = digest([row['segments'],row['strand'],row['qualifiers'].get('protein_id')])
        unique.setdefault(key,row)
    cds = sorted(unique.values(),key=lambda f:min(p[0] for p in f['segments']) if f['segments'] else math.inf)
    result = {'schema':'a103_neighborhood_v1', 'producer_operation':'reference.neighborhood',
        'target_ref':binding['target_ref'], 'accession':binding['accession'],
        'source_file_sha256':binding['source_file_sha256'], 'organism':binding['organism'],
        'raw_neighborhood':raw, 'cds':cds, 'regulatory_features':[
            f for f in raw['features'] if f['kind'] not in {'gene','CDS','source'}],
        'gene_order_reference_axis':[f['source_feature_index'] for f in cds],
        'source_labels_are':'source_annotations_not_experimental_characterizations'}
    return result


def pair_organization(sheet, left_index, right_index):
    require(right_index is None or left_index!=right_index,'a103_distinct_neighbor_cds_required')
    cds = sheet['cds']
    left = next((f for f in cds if f['source_feature_index']==left_index), None)
    right = next((f for f in cds if f['source_feature_index']==right_index), None)
    if left is None or right is None or not left['exact_boundaries'] or not right['exact_boundaries']:
        return {'state':'unresolved','missing':['actual_exact_component_footprints']}
    a,b = min(p[0] for p in left['segments']),max(p[1] for p in left['segments'])
    c,d = min(p[0] for p in right['segments']),max(p[1] for p in right['segments'])
    if a <= c:
        gap, sign = c-b, 1
    else:
        gap, sign = a-d, -1
    raw = sheet['raw_neighborhood']
    circular = raw['window']['wrap_permitted']
    length = raw['source']['length']
    if circular:
        originals = {f['source_feature_index']:f for f in raw['features']}
        left_arc = _focal_arc(originals[left_index],raw['source'],True)
        right_arc = _focal_arc(originals[right_index],raw['source'],True)
        if left_arc is None or right_arc is None or any(y-x>length for x,y in (left_arc,right_arc)):
            return {'state':'unresolved','missing':['unambiguous_native_circular_feature_arc']}
        a,b = left_arc
        candidates = []
        for offset in (-length,0,length):
            c,d = right_arc[0]+offset,right_arc[1]+offset
            signed = c-b if a<=c else a-d
            candidates.append((max(0,signed),signed,1 if a<=c else -1,c,d))
        _,gap,sign,c,d = min(candidates,key=lambda r:(r[0],abs(r[1])))
    directions = (left['strand'], right['strand'])
    orientation = ('same' if directions[0]==directions[1] and directions[0] in {'+','-'} else
        'convergent' if directions == (('+' if sign==1 else '-'),('-' if sign==1 else '+')) else
        'divergent' if directions == (('-' if sign==1 else '+'),('+' if sign==1 else '-')) else 'unknown')
    lrank, rrank = cds.index(left),cds.index(right)
    intervening = abs(rrank-lrank)-1
    if circular and gap>=0:
        intervening = min(intervening,len(cds)-abs(rrank-lrank)-1)
    overlap = sum(max(0,min(b,d)-max(a,c)) for a,b in left['segments'] for c,d in right['segments'])
    return {'state':'measured','left_feature_index':left_index,'right_feature_index':right_index,
        'left_segments':left['segments'],'right_segments':right['segments'],
        'gap_bp':gap,'overlap_bp':overlap,'intervening_annotated_cds':intervening,
        'orientation':orientation,'right_direction_from_left':sign,'circular_arc_used':circular,
        'left_strand':left['strand'],'right_strand':right['strand'],'missing':[]}


def compare_neighborhoods(rows, definition):
    require(1 <= len(rows) <= MAX_PANEL, 'a103_panel_size_limit')
    measured = []
    seen = set()
    genome_groups = {}
    for row in rows:
        sheet = row['neighborhood']
        genome_key = sheet['accession'].split('.')[0]
        require(genome_key not in genome_groups or genome_groups[genome_key]==row['sampling_group'],
                'a103_same_genome_conflicting_sampling_groups')
        genome_groups[genome_key] = row['sampling_group']
        identity = digest([sheet['source_file_sha256'],sheet['accession'],row['left_feature_index'],row['right_feature_index']])
        require(identity not in seen, 'a103_duplicate_locus_in_panel')
        seen.add(identity)
        pair = pair_organization(sheet,row['left_feature_index'],row['right_feature_index'])
        match = None
        if row['right_feature_index'] is None and row.get('partner_absence_evaluable'):
            pair = {'state':'measured_nondetection','missing':[],
                'scope':'declared_neighborhood_CDS_inventory','native_detection_ref':row['right_detection_ref']}
            match = False
        if pair['state']=='measured':
            match = (pair['gap_bp'] <= definition['maximum_gap_bp'] and
                pair['intervening_annotated_cds'] <= definition['maximum_intervening_genes'] and
                (definition['orientation']=='any' or pair['orientation']==definition['orientation']) and
                (definition['order']=='any' or pair['right_direction_from_left']==(1 if definition['order']=='left_before_right' else -1)))
        measured.append({k:v for k,v in row.items() if k!='neighborhood'} | {
            'locus_measurement_key':identity,'genome_key':genome_key,'organization':pair,'relationship_holds':match})
    eligible = [r for r in measured if r['relationship_holds'] is not None]
    groups = defaultdict(lambda:defaultdict(list))
    for row in eligible:
        groups[row['sampling_group']][row['genome_key']].append(float(row['relationship_holds']))
    fraction = sum(r['relationship_holds'] for r in eligible)/len(eligible) if eligible else None
    balanced = (math.fsum(math.fsum(math.fsum(v)/len(v) for v in genomes.values())/len(genomes)
        for genomes in groups.values())/len(groups)) if groups else None
    return {'schema':'a103_recurrence_v1','producer_operation':'context.compare_neighborhoods',
        'definition':deepcopy(definition),'rows':measured,'supporting_loci':sum(r['relationship_holds'] for r in eligible),
        'evaluable_loci':len(eligible),'unknown_loci':len(rows)-len(eligible),
        'evaluable_genomes':len({r['genome_key'] for r in eligible}),
        'native_fraction':fraction,'sampling_group_count':len(groups),'group_balanced_fraction':balanced,
        'sampling_groups':{k:dict(v) for k,v in groups.items()},
        'sampling_aggregation':'mean_loci_within_genome_then_mean_genomes_within_group_then_mean_groups',
        'interpretation':'conservation_of_declared_arrangement_in_explicit_panel_not_exact_function_probability'}


def fusion(binding, regions):
    require(binding['selection_status']=='selected', 'a103_unambiguous_fusion_cds_required')
    sequence = binding['locus']['translation']['sequence']
    require(sequence and len(regions)>=2, 'a103_fusion_actual_regions_required')
    spans = []
    for row in regions:
        start,end = row['start'],row['end']
        require(0 <= start < end <= len(sequence), 'a103_fusion_region_invalid')
        require(all(end<=a or start>=b for a,b in spans), 'a103_fusion_regions_overlap')
        spans.append((start,end))
    return {'schema':'a103_fusion_v1','producer_operation':'context.fusion',
        'regions':deepcopy(regions),'coding_locus':deepcopy(binding['locus']),
        'same_coding_product':True,'observed_link_fraction':1.,
        'interpretation':'observed_linkage_of_attributed_regions_in_one_coding_product; molecular_activity_unestablished'}


def fisher_enrichment(a,b,c,d):
    """One-sided exact hypergeometric tail, with actual 2x2 counts retained."""
    require(all(type(v) is int and v>=0 for v in (a,b,c,d)), 'a103_contingency_counts_invalid')
    n = a+b+c+d
    if not n or not (a+b) or not (c+d) or not (a+c) or not (b+d):
        return None
    low,high = max(a,(a+b)+(a+c)-n),min(a+b,a+c)
    denominator = math.lgamma(n+1)-math.lgamma(a+b+1)-math.lgamma(c+d+1)
    def logchoose(n,k):
        return math.lgamma(n+1)-math.lgamma(k+1)-math.lgamma(n-k+1)
    terms = [logchoose(a+c,k)+logchoose(b+d,a+b-k)-denominator for k in range(low,high+1)]
    maximum = max(terms)
    return min(1.,math.exp(maximum)*math.fsum(math.exp(v-maximum) for v in terms))


def cooccurrence(rows):
    require(1 <= len(rows) <= MAX_PANEL, 'a103_panel_size_limit')
    require(len({r['genome_key'] for r in rows})==len(rows), 'a103_duplicate_genome_in_panel')
    known = [r for r in rows if None not in (r['left_present'],r['right_present'])]
    a = sum(r['left_present'] and r['right_present'] for r in known)
    b = sum(r['left_present'] and not r['right_present'] for r in known)
    c = sum(not r['left_present'] and r['right_present'] for r in known)
    d = sum(not r['left_present'] and not r['right_present'] for r in known)
    effect = a/(a+b)-c/(c+d) if a+b and c+d else None
    p = fisher_enrichment(a,b,c,d)
    L = -math.log10(p) if p is not None and p>0 else None
    bounded = L/(1+L) if L is not None and effect is not None and effect>0 else (0. if p is not None else None)
    groups = {r['sampling_group'] for r in known}
    # The raw test assumes independent rows. Correlated sampling stays visible
    # and cannot silently mint an independent-row significance contribution.
    independent = len(groups)==len(known)
    return {'schema':'a103_cooccurrence_v1','producer_operation':'context.cooccurrence',
        'rows':deepcopy(rows),'contingency':{'both':a,'left_only':b,'right_only':c,'neither':d},
        'evaluable_genomes':len(known),'unknown_genomes':len(rows)-len(known),
        'risk_difference':effect,'p_value':p,'log10_significance':L,
        'native_significance_index':bounded if independent else None,
        'sampling_group_count':len(groups),'independent_row_test_eligible':independent,
        'null_model':'fixed_margin_one_sided_hypergeometric_enrichment',
        'multiple_comparison_adjustment':'none; one explicitly selected comparison',
        'normalization':'positive_effect_only_L_over_1_plus_L; L=-log10(p)',
        'interpretation':'association_under_recorded_detection_scope_not_necessity_or_physical_interaction'}


def binding_summary(binding):
    return {k:deepcopy(v) for k,v in binding.items() if k!='genbank_projection'}


def execute(request):
    operation = request['operation']
    if operation=='bind':
        return bind_locus(request)
    if operation=='neighborhood':
        return neighborhood(request['binding'],request['left_bp'],request['right_bp'])
    if operation=='compare':
        return compare_neighborhoods(request['rows'],request['definition'])
    if operation=='fusion':
        return fusion(request['binding'],request['regions'])
    if operation=='cooccurrence':
        return cooccurrence(request['rows'])
    if operation=='detection':
        from .a103_detection import detect
        return detect(request)
    raise ContractError('a103_unbound_native_operation')
