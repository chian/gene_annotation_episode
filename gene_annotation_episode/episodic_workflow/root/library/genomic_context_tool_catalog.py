"""Original genomic context operation declarations for the shared registry."""
from copy import deepcopy
from gene_annotation_episode.domain import obj
from ..a103.a103_scoring import MAX_PANEL, MAX_FLANK_BP


REF = {'type':'string','format':'reference'}
NULL_REF = {'anyOf':[REF,{'type':'null'}]}
REFS = {'type':'array','items':REF,'uniqueItems':True}
TEXT = {'type':'string','minLength':1}
INT = {'type':'integer','minimum':0}
NAMES = ('context.bind_locus','reference.neighborhood','context.compare_neighborhoods',
    'context.fusion','context.cooccurrence','context.contrast','context.association_channels','context.detection_inventory',
    'context.request_hpc')


def catalog():
    entries = {
        'context.bind_locus':('Bind an actual supplied GenBank or GFF3+FASTA CDS to its sequence and original genomic record. Preserve ambiguity, translation checks, construct/record identity and whether this file is caller-associated target material or a reference. This alone earns no association credit.',
            obj({'target_ref':REF,'file_source_ref':REF,'accession':TEXT,
                'format':{'enum':['genbank','gff3']},'sequence_source_ref':NULL_REF,
                'genetic_code':{'type':['integer','null'],'minimum':1},
                'selector':{'oneOf':[obj({'locus_tag':TEXT}),obj({'protein_id':TEXT}),obj({'coordinate':INT})]}})),
        'reference.neighborhood':('Measure the actually acquired neighborhood around a received A103 locus binding. Retain native features, gene order, strand, signed gaps/overlaps, regulatory footprints, fetched boundaries and original coordinates. Source product labels remain source annotations. This does not infer an operon or exact function.',
            obj({'binding_ref':REF,'left_bp':{'type':'integer','minimum':0,'maximum':MAX_FLANK_BP},
                'right_bp':{'type':'integer','minimum':0,'maximum':MAX_FLANK_BP}})),
        'context.compare_neighborhoods':('Measure a declared gene-organization relationship over an explicit panel. Identify actual left/right CDS indices, sampling groups and a fixed relationship definition. Exact component identities or received native alignments qualify each row automatically; unknown rows retain their denominators and bounds. Neighbor homology scores never substitute for a context statistic.',
            obj({'target_ref':REF,'partner_reference_ref':REF,'definition_source_refs':{**REFS,'minItems':1},
                'rows':{'type':'array','minItems':2,'maxItems':MAX_PANEL,'items':obj({
                    'neighborhood_ref':REF,'left_feature_index':INT,'right_feature_index':{'type':['integer','null'],'minimum':0},
                    'sampling_group':TEXT,'right_detection_ref':NULL_REF},
                    required=['neighborhood_ref','left_feature_index','right_feature_index','sampling_group'])},
                'definition':obj({'maximum_gap_bp':{'type':'integer','minimum':0,'maximum':MAX_FLANK_BP},
                    'maximum_intervening_genes':{'type':'integer','minimum':0,'maximum':128},
                    'orientation':{'enum':['any','same','convergent','divergent']},
                    'order':{'enum':['any','left_before_right','right_before_left']}})})),
        'context.fusion':('Measure linkage of explicitly attributed nonoverlapping domains/regions within one actual coding product. Each region needs its own received component sequence/map and definition source. Emit local target features when mapped; fused architecture does not automatically establish activities of every domain or the whole protein.',
            obj({'target_ref':REF,'binding_ref':REF,'definition_source_refs':{**REFS,'minItems':1},
                'regions':{'type':'array','minItems':2,'maxItems':16,'items':obj({'start':INT,'end':INT,
                    'component_ref':REF,'alignment_ref':NULL_REF})}})),
        'context.cooccurrence':('Calculate an exact association test from actual admitted detection inventories, with an explicit genome panel. Presence, detection-limited absence and unknown remain distinct. Retain contingency counts, direction, null, sampling groups and correction status; related samples cannot silently count as independent.',
            obj({'target_ref':REF,'left_reference_ref':REF,'right_reference_ref':REF,
                'definition_source_refs':{**REFS,'minItems':1},'rows':{'type':'array','minItems':2,'maxItems':MAX_PANEL,
                    'items':obj({'genome_key':TEXT,'sampling_group':TEXT,'left_detection_ref':REF,'right_detection_ref':REF})}})),
        'context.detection_inventory':('Collect a detection state from an actually completed parent-delivered native phmmer search. Requires the registered parsed-search receipt, actual native output Source, exact searched FASTA Source, component query and measured genomic records. Complete examined CDS coverage permits only detection-limited absence within those records; unexamined sequence or incomplete annotations remain unknown. This port performs no sequence search.',
            obj({'target_ref':REF,'binding_refs':{**REFS,'minItems':1,'maxItems':MAX_PANEL},
                'snapshot_ref':REF,'native_source_ref':REF,'database_source_ref':REF,'component_ref':REF,
                'neighborhood_ref':NULL_REF},required=['target_ref','binding_refs','snapshot_ref','native_source_ref','database_source_ref','component_ref'])),
        'context.contrast':('Compare actual context measurements against explicit alternative relationships. Retain exceptions, paralogs, optional modules and source-grounded incompatibility witnesses. This functional interpretation does not add a second copy of underlying native context credit.',
            obj({'target_ref':REF,'function_ref':REF,'supporting_source_refs':REFS,
                'opposing_source_refs':REFS,'incompatibility_witness_refs':{**REFS,'minItems':1}})),
        'context.association_channels':('Extract native STRING neighborhood/fusion/phylogenetic-profile fields separately from one received complete provider result. Preserve exact endpoints, taxon and version. Combined, expression, experimental and text-mining scores are not A103 channel substitutes.',
            obj({'target_ref':REF,'source_ref':REF,'left_native_id':TEXT,'right_native_id':TEXT,
                'left_reference_ref':REF,'right_actual_ref':REF,'right_reference_ref':REF})),
    }
    from ..a103.a103_native_requests import OPERATIONS
    request_schema = {'oneOf':[obj({'operation':{'const':name},'arguments':deepcopy(entries[name][1]),
        'resource_id':TEXT}) for name in OPERATIONS]}
    entries['context.request_hpc'] = ('Freeze an A103 native investigation from actually received genomic records, '
        'locus bindings, panels or completed detector output. Return an exact commission for the configured '
        'HPC parent and its prediction/execution sisters. This operation runs no context calculation or '
        'sequence search. The original received result is automatically graded and attributed. Reuse '
        'received measurements; missing identities and unexamined sequence remain unknown.',request_schema)
    return {name:{'description':description,'resources':'local','input_schema':schema}
            for name,(description,schema) in entries.items()}


