"""Keep each ordinary metric description specific, without repeated field families."""
from pathlib import Path
import importlib.util
import pprint

p=Path(__file__).resolve().parent/'candidate/gene_annotation_episode/bvbrc_fastqutils_samstat_specs.py'
spec=importlib.util.spec_from_file_location('samstat_description_registry',p)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
metrics=module.SAMSTAT_METRICS
for item in metrics.values():
    definitions=item.pop('native_source_definitions',[])
    if definitions:
        item['source_field_ids']=[d['field_id'] for d in definitions]
        item['native_precision_description']=' '.join(dict.fromkeys(d['precision'] for d in definitions))
        item['source_evidence']=list(dict.fromkeys(s for d in definitions for s in d['source_evidence']))
        item['qualifications']=list(dict.fromkeys(s for d in definitions for s in d['qualifications']))

inputs={
 'samstat_alignment_bin_count':['2.2.3 mappingtableval[1 or3][bin0..3]','2.5.0 mapq four rows: Reads / Read1 / Read2 columns'],
 'samstat_alignment_total_count':['2.2.3 mappingtableval[1 or3][4] native per-mate Total','2.2.3 paired overview reads exact integer or (exact:N) suffix','2.5.0 strip Reads/Reads(R1+R2): exact sublabel or unscaled count','2.5.0 no-reads banner with explicit SAM/BAM mode','caller-failure heading: failed/null sentinel only'],
 'samstat_sequence_total_count':['2.2.3 FASTX File statistics reads exact integer or (exact:N) suffix','2.5.0 FASTA/FASTQ strip Reads: exact sublabel or unscaled count','2.5.0 no-reads banner only with explicit FASTA/FASTQ mode'],
 'samstat_total_base_count':['2.5.0 strip Bases exact span.sub integer, else unscaled N bp main token; n/a stays unavailable'],
 'samstat_reported_bin_fraction':['2.2.3 mappingtableval[2 or4][bin0..4] including explicit Total fraction'],
 'samstat_reported_bin_percent':['2.5.0 mapq table % of reads column for each bin'],
 'samstat_reported_mapped_percent':['2.5.0 strip % mapped dd main value'],
 'samstat_reported_ge30_percent':['2.5.0 strip % MAPQ >=30 dd main value'],
 'samstat_paired_flag_record_count_display':['2.2.3 paired in sequencing sentence count; native K/M/G display converted to alignment-record display units'],
 'samstat_proper_pair_flag_record_count_display':['2.2.3 properly paired sentence count; native K/M/G display converted to alignment-record display units'],
 'samstat_paired_flag_percent':['2.2.3 paired in sequencing sentence parenthesized percentage'],
 'samstat_proper_pair_flag_percent':['2.2.3 properly paired sentence parenthesized percentage'],
 'samstat_legacy_mean_phred':['2.2.3 SAM/BAM bq_R{mate}_{bin}_{offset}.y; bq_R*_end_*.y; bq_norm_R*.y'],
 'samstat_legacy_phred_sem':['2.2.3 SAM/BAM corresponding bq*.error_y.array'],
 'samstat_legacy_quality_index_mean':['2.2.3 FASTX bq*.y with native offset-zero/capped-index defect'],
 'samstat_legacy_quality_index_sem':['2.2.3 FASTX bq*.error_y.array with native offset-zero/capped-index defect'],
 'samstat_median_length':['2.5.0 header reads(median LENGTH) native value and unit'],
 'samstat_n50_length':['2.5.0 strip N50 dd main LENGTH value and unit'],
 'samstat_min_length':['2.5.0 plot1 accessible desc Read lengths range from MIN to MAX: MIN token; global even in mate figures'],
 'samstat_max_length':['2.5.0 plot1 accessible desc Read lengths range from MIN to MAX: MAX token; global even in mate figures'],
 'samstat_uniform_length':['2.5.0 plot1 note All N reads are LENGTH long / The read is LENGTH long'],
 'samstat_min_read_quality_bin':['2.5.0 plot2 desc mean base quality from QMIN to QMAX: MIN integer bin'],
 'samstat_max_read_quality_bin':['2.5.0 plot2 desc mean base quality from QMIN to QMAX: MAX integer bin'],
 'samstat_mismatch_unavailable_record_count':['2.5.0 notes Mismatch profile excludes X of Y mapped reads: X'],
 'samstat_identity_unavailable_record_count':['2.5.0 notes Identity unavailable for X of Y mapped reads: X'],
 'samstat_mapped_note_record_count':['2.5.0 either unavailable note X of Y mapped reads: Y; repeated denominator retained'],
 'samstat_secondary_excluded_count':['2.5.0 footer N secondary alignments(not counted): N'],
 'samstat_supplementary_excluded_count':['2.5.0 footer N supplementary alignments(not counted): N'],
 'samstat_position_minimum_records':['2.5.0 notes/plot-na/accessible desc fewer than N reads or needs at least N: N configuration'],
 'samstat_beyond_axis_percent':['2.5.0 notes X% of bases lie beyond position1000: X native rounded percent'],
 'samstat_beyond_axis_percent_upper_bound':['2.5.0 notes &lt;0.1% of bases lie beyond position1000: strict upper bound0.1'],
}
for base in 'ACGTN':
    for suffix in ('count','rounded_bin_mean'):
        inputs[f'samstat_base_{base}_{suffix}']=[f'2.2.3 bc_R{{mate}}_{{bin}}_{base}.y / end / norm variants; '+('unclustered integer' if suffix=='count' else 'clustered rounded native mean')]
        inputs[f'samstat_mismatch_{base}_{suffix}']=[f'2.2.3 mis_R{{mate}}_{{bin}}_{base}.y; read-base symbol{base}; '+('unclustered integer' if suffix=='count' else 'clustered rounded native mean')]
for event,prefix in [('insertion','ins'),('deletion','del')]:
    for suffix in ('count','rounded_bin_mean'):
        inputs[f'samstat_{event}_open_{suffix}']=[f'2.2.3 {prefix}_R{{mate}}__{{bin}}.y; '+('unclustered gap-opening integer' if suffix=='count' else 'clustered rounded mean of gap-opening counts')]
for metric,fields in inputs.items():metrics[metric]['native_fields']=fields
metrics['samstat_paired_flag_percent']['denominator']='All producer-retained alignment records, including unpaired records. Native one-decimal percentage of paired-flag records; no pair count.'
metrics['samstat_proper_pair_flag_percent']['denominator']='Producer-retained paired-flag alignment records. Native one-decimal percentage also carrying proper-pair flag; no pair count.'
metrics['samstat_paired_flag_record_count_display']['denominator']=None
metrics['samstat_proper_pair_flag_record_count_display']['denominator']=None
metrics['samstat_position_minimum_records']['denominator']=None
metrics['samstat_position_minimum_records']['interpretation']='Producer display-coverage threshold in records/reads; configuration, not an observed population cardinality.'
for metric in ('samstat_secondary_excluded_count','samstat_supplementary_excluded_count'):
    metrics[metric]['denominator']=None
for metric in ('samstat_alignment_bin_count','samstat_alignment_total_count','samstat_sequence_total_count','samstat_total_base_count'):
    metrics[metric]['denominator']=None
metrics['samstat_alignment_bin_count']['interpretation']='Contributing alignment-record count for one native MAPQ bin and mate/report stratum.2.2.3 excludes secondary but includes supplementary;2.5.0 excludes both. Native high bin includes MAPQ255; no read-name deduplication, molecules or pairs.'
metrics['samstat_alignment_total_count']['interpretation']='Exact contributing alignment-record total explicitly printed by the recognized version.2.2.3 excludes secondary but includes supplementary;2.5.0 excludes both. Report-wide and per-mate totals are repeated/overlapping native populations, not independently summable. Caller failure has null measurement.'
metrics['samstat_sequence_total_count']['interpretation']='Count of processed FASTA/FASTQ sequences where native mode establishes FASTX. Alignment outcomes are not inferred. An unknown-mode empty banner uses samstat_reported_item_count instead.'
metrics['samstat_total_base_count']['interpretation']='Full sequence bases contributed by included primary alignment records or FASTX sequences, including soft clips; absent SEQ has no positive sequence contribution. Native n/a is not zero.'
p.write_text('"""Concrete SAMstat native/component descriptions; no executable scoring language.\n\n'
             'Sealed207 revision002 plus root-authorized212 unknown-input-kind banner.\n'
             'Descriptions preserve version-specific populations and native precision.\n"""\n\n'
             +'SAMSTAT_METRICS = '+pprint.pformat(metrics,sort_dicts=False,width=115)+'\n\n'
             +'SAMSTAT_COMPONENTS = '+pprint.pformat(module.SAMSTAT_COMPONENTS,sort_dicts=False,width=115)+'\n')
print('Concrete native specs:',len(metrics),'bytes:',p.stat().st_size)
