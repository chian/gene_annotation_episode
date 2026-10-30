"""Write the finite numerical registry; no scientific calculation code."""
import json
from pathlib import Path
P=Path(__file__).resolve().parent
D=json.loads((P/'SCHEMAS_002.json').read_text())['$defs']
metrics=D['Cell']['properties']['metric']['enum']
components=D['Component']['properties']['metric']['enum']
rows={}
def add(names, formats, section, fields, units, axes, populations, meaning, precision, domain, interpretation,
        source, uncertainty='not_reported', denominator=None, missing=None):
    if isinstance(names,str): names=[names]
    for i,name in enumerate(names):
        rows[name]={'metric':name,'formats':formats,'section_key':section,
            'native_fields':fields[i] if len(names)>1 and len(fields)==len(names) and isinstance(fields[0],list) else fields,
            'units':units,'axis_kinds':axes,'population_keys':populations,'meaning':meaning,
            'precision':precision,'value_domain':domain,'interpretation':interpretation,
            'denominator':denominator,'coordinates':'closed 1-based native bins' if any(a.endswith('closed_1') for a in axes) else
                'closed native axis bins; BAM positions separately zero-based' if any('closed' in a for a in axes) else 'not_applicable',
            'uncertainty':uncertainty,'missing_behavior':missing or 'Preserve native token and explicit state; absent row is not numerical zero. Partial populations retain partial counts; no whole-population inference.',
            'reviewed_source':source}
fq='FASTQ records supplied in full;193 CONTRACT_001 sections4-6'
qcbase='sources/FastQC/uk/ac/babraham/FastQC/Modules/'
qcformats=['fastqc_data_0_12_1','fastqc_zip_0_12_1']
qchtml=qcformats+['fastqc_html_0_12_1']
trim='sources/TrimGalore/trim_galore@4edff97d22f3837d42a29e4afbfaeb6e07ffb11b'
add('fastq_read_count',['fastq'],'fastq_summary',['validated record count'],['reads'],['none'],['fastq_reads'],
    'observed_count','exact_for_retained_population','nonnegative_integer','Count complete validated FASTQ records, including zero for a complete empty file.',fq)
add('fastq_base_count',['fastq'],'fastq_summary',['sequence character count'],['bases'],['none'],['fastq_bases'],
    'observed_count','exact_for_retained_population','nonnegative_integer','Count all supplied sequence symbols; invalid symbols remain separately counted.',fq)
add('fastq_symbol_count',['fastq'],'fastq_summary',['A','C','G','T','N','other_iupac','invalid'],['bases'],['symbol'],['fastq_bases'],
    'observed_count','exact_for_retained_population','nonnegative_integer','Case-insensitive A/C/G/T/N counts; other IUPAC excludes N. Invalid symbols are not silently assigned to ambiguity.',fq)
add(['fastq_min_length','fastq_max_length'],['fastq'],'fastq_summary',[['minimum retained sequence length'],['maximum retained sequence length']],
    ['bases'],['none'],['fastq_reads'],'observed_count','exact_for_retained_population','nonnegative_integer',
    'Observed extrema over validated reads; empty population yields undefined/null, not zero-length read.',fq)
add('fastq_length_histogram_count',['fastq'],'fastq_summary',['exact sequence length','read count'],['reads'],['length_closed'],['fastq_reads'],
    'observed_count','exact_for_retained_population','nonnegative_integer','Singleton length bins contain actual read counts.',fq)
add('quality_character_count',['fastq'],'fastq_summary',['ASCII quality symbol','base count'],['bases'],['quality_ascii'],['fastq_quality_characters'],
    'observed_count','exact_for_retained_population','nonnegative_integer','Counts raw quality ASCII symbols without assuming an encoding.',fq)
add('phred_histogram_count',['sam_1_6','bam_1'],'bam_summary',['native numeric Phred quality','base count'],['bases'],['quality_score'],['bam_quality_bases'],
    'observed_count','exact_for_retained_population','nonnegative_integer','BAM numeric qualities or SAM QUAL decoded using the SAM-specified Phred+33 representation; missing qualities retained separately, never 255 as Q.',
    'sources/hts-specs/SAMv1.tex mandatory fields and BAM quality representation')
add('verified_pair_count',['fastq'],'fastq_summary',['explicit PairDeclaration','actual unique paired key correspondence'],['pairs'],['none'],['verified_read_pairs'],
    'observed_count','exact_for_retained_population','nonnegative_integer','C metadata structural join count after explicit mate/key declaration and actual one-to-one record matching; never halve read counts.',
    '193 CONTRACT_001 pairing requirements;195 PORTS_002 join_ref/Metadata.measurements')
add(['fastqc_total_sequences','fastqc_flagged_sequences'],qchtml,'fastqc_basic_statistics',
    [['Total Sequences'],['Sequences flagged as poor quality']],['reads'],['none'],['fastqc_module'],
    'observed_count','exact_for_retained_population','nonnegative_integer',
    'Native total excludes filtered sequences; flagged count is separately retained.',qcbase+'BasicStats.java')
add('fastqc_total_bases_display',qchtml,'fastqc_basic_statistics',['Total Bases lexical quantity and suffix'],['bp','kbp','Mbp','Gbp'],['none'],['fastqc_module'],
    'observed_native','native_truncated_display','nonnegative_number','Store displayed number with displayed unit and exact token. It is not an exact base denominator.',qcbase+'BasicStats.java')
add(['fastqc_min_length','fastqc_max_length'],qchtml,'fastqc_basic_statistics',[['Sequence length lower'],['Sequence length upper']],['bases'],['none'],['fastqc_module'],
    'observed_native','exact_for_retained_population','nonnegative_integer','Native displayed read-length endpoints; keep singleton/range meaning.',qcbase+'BasicStats.java')
add('fastqc_gc_percent',qchtml,'fastqc_basic_statistics',['%GC'],['percent'],['none'],['fastqc_module'],
    'native_normalized','native_truncated_display','integer_0_100','Native floor(100*(G+C)/(A+C+G+T)); source zero-denominator fallback0 is qualified, not a true GC estimate.',qcbase+'BasicStats.java',denominator='native A+C+G+T; unavailable as exact count in report')
add(['fastqc_base_quality_mean','fastqc_base_quality_median','fastqc_base_quality_lower_quartile','fastqc_base_quality_upper_quartile','fastqc_base_quality_p10','fastqc_base_quality_p90'],
    qcformats,'fastqc_per_base_quality',[[x] for x in ['Mean','Median','Lower Quartile','Upper Quartile','10th Percentile','90th Percentile']],
    ['phred'],['base_closed_1'],['fastqc_module'],'observed_native','not_reported','finite_number',
    'Grouped means average per-position means; grouped quantiles average source per-position quantiles with >100 observations. Not pooled quantiles or a per-base score histogram.',qcbase+'PerBaseQualityScores.java',
    missing='Native NaN/nonfinite -> null explicit nonfinite_native; no graph recovery from HTML.')
add('fastqc_tile_quality_deviation',qcformats,'fastqc_per_tile_quality',['Tile','Base','Mean'],['phred_deviation'],['tile_base_closed_1'],['fastqc_module'],
    'native_normalized','not_reported','finite_signed_number','Deviation from equal-tile mean, may be negative. Sample first10000 then every10th read; source tile parsing can omit module.',qcbase+'PerTileQualityScores.java')
add('fastqc_sequence_quality_count',qcformats,'fastqc_per_sequence_quality',['Quality','Count'],['reads'],['quality_score'],['fastqc_module'],
    'observed_count','exact_for_retained_population','nonnegative_integer','Histogram of integer-truncated per-read mean quality, not per-base qualities or usable Q30 numerator.',qcbase+'PerSequenceQualityScores.java')
add('fastqc_base_content_percent',qcformats,'fastqc_per_base_content',['Base','G','A','T','C'],['percent'],['base_closed_1'],['fastqc_module'],
    'native_normalized','not_reported','finite_number','Native percentages for each base/position group. Axis label preserves G/A/T/C; do not reconstruct counts or pooled weighted means.',qcbase+'PerBaseSequenceContent.java',denominator='native ACGT count per position; absent from table')
add('fastqc_n_percent',qcformats,'fastqc_per_base_n',['Base','N-Count'],['percent'],['base_closed_1'],['fastqc_module'],
    'native_normalized','not_reported','finite_number','N-Count column is percent, not count.',qcbase+'NContent.java',denominator='native N + non-N at position')
add('fastqc_sequence_gc_smoothed_count',qcformats,'fastqc_per_sequence_gc',['GC Content','Count'],['native_count'],['native_label'],['fastqc_module'],
    'native_estimate','native_estimator','nonnegative_number','Smoothed fractional histogram. Source truncates long sequences to hundred/thousand boundaries. Not integer read-bucket counts.',qcbase+'PerSequenceGCContent.java')
add('fastqc_length_bin_count',qcformats,'fastqc_length_distribution',['Length','Count'],['reads'],['length_closed'],['fastqc_module'],
    'observed_count','exact_for_retained_population','nonnegative_integer','Grouped closed length bins; cannot derive exact bases/mean from nonsingleton bins.',qcbase+'SequenceLengthDistribution.java')
add(['fastqc_total_deduplicated_percent','fastqc_duplication_bin_percent'],qcformats,'fastqc_duplication',
    [['Total Deduplicated Percentage'],['Duplication Level','Percentage of total']],['percent'],['none','duplication_bin'],['fastqc_module'],
    'native_estimate','native_estimator','nonnegative_number','Corrected bounded-tracking estimator, not observed distinct molecules; source rawTotal0 fallback100 remains qualified.',qcbase+'DuplicationLevel.java')
add('fastqc_overrepresented_count',qchtml,'fastqc_overrepresented',['Sequence','Count'],['reads'],['sequence'],['fastqc_module'],
    'observed_count','exact_for_retained_population','nonnegative_integer','Count of tracked keys, normally first50bp; first100000 distinct keys tracked. Preserve native Possible Source label as a suggestion.',qcbase+'OverRepresentedSeqs.java')
add('fastqc_overrepresented_percent',qchtml,'fastqc_overrepresented',['Sequence','Percentage'],['percent'],['sequence'],['fastqc_module'],
    'native_normalized','not_reported','nonnegative_number','Reported tracked-key percentage; empty complete table means no reported rows, not no contamination.',qcbase+'OverRepresentedSeqs.java',denominator='native total sequence count')
add('fastqc_adapter_percent',qcformats,'fastqc_adapter_content',['Position','native adapter-name column'],['percent'],['base_closed_1'],['fastqc_module'],
    'native_normalized','not_reported','nonnegative_number','Cumulative exact adapter match detection normalized by total reads then grouped position average; label is exact native adapter name. Short reads can omit table.',qcbase+'AdapterContent.java',denominator='native total read count')
add('fastqc_kmer_scaled_count',qchtml,'fastqc_kmer_content',['Sequence','Count'],['scaled_native_count'],['sequence'],['fastqc_module'],
    'native_estimate','native_estimator','nonnegative_integer','Source samples every50th read, prefix<=500 and reports count()*5; preserve this native scaling without extrapolating whole reads. At most20 reported enriched kmers.',qcbase+'KmerContent.java')
add('fastqc_kmer_pvalue',qchtml,'fastqc_kmer_content',['Sequence','PValue'],['dimensionless'],['sequence'],['fastqc_module'],
    'native_estimate','native_estimator','nonnegative_number','Native binomial-tail/multiple-kmer value, multiplied by4**k. Preserve native finite value; not annotation probability or a universal calibrated confidence.',qcbase+'KmerContent.java')
add('fastqc_kmer_obs_exp_max',qchtml,'fastqc_kmer_content',['Sequence','Obs/Exp Max','Max Obs/Exp Position'],['ratio'],['sequence'],['fastqc_module'],
    'native_normalized','not_reported','nonnegative_number','Native observed/expected ratio, despite graph label mentioning log2. Preserve position token in label/raw table.',qcbase+'KmerContent.java',denominator='source kmer expected count model')
add('trim_processed_count',['trim_galore_report_0_6_10'],'trim_summary',['sequences processed in total'],['reads'],['none'],['trim_processed'],
    'observed_count','exact_for_retained_population','nonnegative_integer','Input read-record loop count per mate report, distinct from paired validation count.',trim+' trim()')
for reason in ['short','n','long']:
    add('trim_removed_'+reason+'_count',['trim_galore_report_0_6_10'],'trim_summary',['native removed '+reason+' labelled counter'],
        ['reads'],['native_label'],['trim_removed_'+reason],'observed_count','exact_for_retained_population','nonnegative_integer',
        'Preserve each exact printed counter and native label. Different report sections/options remain separate; no assumed disjointness.',trim+' trim()')
    add('trim_removed_'+reason+'_percent',['trim_galore_report_0_6_10'],'trim_summary',['native removed '+reason+' percentage'],
        ['percent'],['native_label'],['trim_removed_'+reason],'native_normalized','native_rounded','nonnegative_number',
        'Single-read trimming percentages use sprintf %.1f; retain lexical precision and N/A.',trim+' trim()',denominator='native sequences processed in this report')
add('trim_validation_pair_count',['trim_galore_report_0_6_10'],'trim_pair_validation',['Total number of sequences analysed for the sequence pair validation'],['pairs'],['none'],['trim_pairs_in'],
    'observed_count','exact_for_retained_population','nonnegative_integer','Paired validation loop iterations/read pairs, in second mate report, not individual reads.',trim+' validate_paired_end_files()')
add('trim_removed_pair_count',['trim_galore_report_0_6_10'],'trim_pair_validation',['sequence_pairs_removed printed as removed because at least one read shorter'],['pairs'],['native_label'],['trim_pairs_removed'],
    'observed_count','exact_for_retained_population','nonnegative_integer','Mixed native counter: increments on length and N-filter branches; excludes too-long counter and zero-length maxn_fraction skip. Preserve native label and trim_pair_counter_mixed; not all pair removals.',trim+' validate_paired_end_files()')
add('trim_removed_pair_percent',['trim_galore_report_0_6_10'],'trim_pair_validation',['percentage of sequence_pairs_removed'],['percent'],['native_label'],['trim_pairs_removed'],
    'native_normalized','native_rounded','nonnegative_number','Paired-validation percentage uses sprintf %.2f, correcting193 generic one-decimal statement; same mixed-counter qualification.',trim+' validate_paired_end_files()',denominator='native pair-validation loop count')
add('trim_native_option',['trim_galore_report_0_6_10'],'trim_configuration',['native numeric option name/value'],['phred','bases','fraction','dimensionless'],['native_label'],[],
    'native_configuration','not_reported','finite_number','Source-reported configuration only: quality cutoff=Phred; length/overlap=bases; error-rate option=fraction. Never a measured sequencing error rate; unknown options remain raw labels/blocks.',trim+' trim() and printed configuration')
add('trim_adapter_detection_count',['trim_galore_report_0_6_10'],'trim_adapter_detection',['adapter label','literal auto-detection count'],['native_count'],['adapter'],[],
    'observed_count','exact_for_retained_population','nonnegative_integer','Source sampling boundary and literal count retained; no whole-input extrapolation or confidence.',trim+' autodetect_adapter_type()')
for key,field in [('left_paired','Left paired'),('right_paired','Right paired'),('left_single','Left single'),('right_single','Right single')]:
    add('fastq_pair_'+key,['fastq_pair_stderr_0_3'],'fastq_pair_summary',[field],['reads'],['none'],['fastq_pair_'+key],
        'observed_count','exact_for_retained_population','nonnegative_integer','Exact native read-record counter; not verified unique pair correspondence. Preserve inconsistent/negative/overflow diagnostics without clamping.',
        'sources/fastq-pair/fastq_pair.c@4f697f0f13d3bfa7840279e9853345f8641cb59d')
for field,key in [('reads_in','in'),('reads_out','out'),('reads_removed','removed')]:
    add('hostile_'+field,['hostile_json_1_1_0'],'hostile_report',[field],['reads'],['none'],['hostile_'+key],
        'observed_count','exact_for_retained_population','nonnegative_integer','Native primary alignment-record count from samtools -F2304; individual read records, not pairs. Native removed=in-out; no true human-contamination claim.',
        'sources/hostile_1.1.0/src/hostile/lib.py gather_stats_paired/gather_stats_single')
add('hostile_removed_proportion',['hostile_json_1_1_0'],'hostile_report',['reads_removed_proportion'],['fraction'],['none'],['hostile_in'],
    'native_normalized','native_rounded','number_0_1','Native round((reads_in-reads_out)/reads_in,5), with source zero-input fallback0 retained and qualified. Reported native proportion differs from derived undefined zero-denominator result.',
    'sources/hostile_1.1.0/src/hostile/lib.py gather_stats_paired/gather_stats_single',denominator='same native row reads_in')
for metric,field,pop in [('bam_record_count','all complete retained records','bam_records'),
    ('bam_primary_record_count','(FLAG & 0x900)==0','bam_records'),('bam_secondary_record_count','(FLAG & 0x100)!=0','bam_records'),
    ('bam_supplementary_record_count','(FLAG & 0x800)!=0','bam_records'),('bam_mapped_primary_count','primary and (FLAG & 4)==0','bam_records'),
    ('bam_mapq_unavailable_count','MAPQ==255','bam_records')]:
    add(metric,['sam_1_6','bam_1'],'bam_summary',[field],['alignment_records'],['none'],[pop],
        'observed_count','exact_for_retained_population','nonnegative_integer','Counts describe the retained record population. Mapped-only BAM is not an original read denominator; secondary/supplementary records are not independent extra reads.',
        'sources/hts-specs/SAMv1.tex mandatory fields and BAM')
add('bam_mapq_histogram_count',['sam_1_6','bam_1'],'bam_summary',['MAPQ0..254','record count'],['alignment_records'],['mapq'],['bam_records'],
    'observed_count','exact_for_retained_population','nonnegative_integer','MAPQ255 unavailable is counted separately. Numeric MAPQ is native alignment-model output, not gene-function confidence.',
    'sources/hts-specs/SAMv1.tex mandatory fields')
assert set(rows)==set(metrics),(set(metrics)-set(rows),set(rows)-set(metrics))
out={'version':'fastqutils_metric_specs_v2','scope':'C-L209-FastqUtils::api','metrics':[rows[m] for m in metrics]}
(P/'METRIC_SPECS_002.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')

specs={}
def comp(metric,method,formula,inputs,units,meaning,uncertainty='not_estimated',requirements='Complete compatible populations and finite operands; positive denominator for fractions.'):
    specs[metric]={'metric':metric,'method':method,'formula':formula,'input_fields':inputs,'units':units,
        'meaning':meaning,'uncertainty':uncertainty,'requirements':requirements,
        'missing_behavior':'Null with specific typed state/requirements; preserve actual available operands. Do not substitute zero, clamp, infer missing populations or drop sibling components.',
        'source_contract':'193 CONTRACT_001 section6 plus195 additive source/assumption corrections'}
comp('gc_acgt_fraction','composition_v1','(G+C)/(A+C+G+T)',['fastq_symbol_count axes A,C,G,T,N,other_iupac,invalid'],['fraction'],'derived_descriptive')
comp('n_fraction','composition_v1','N/all_bases',['fastq_symbol_count N','fastq_base_count'],['fraction'],'derived_descriptive')
comp('ambiguous_fraction','composition_v1','(N+other_IUPAC)/all_bases',['fastq_symbol_count N,other_iupac','fastq_base_count'],['fraction'],'derived_descriptive')
comp('mean_read_length','composition_v1','base_count/read_count',['fastq_base_count','fastq_read_count'],['bases'],'derived_descriptive')
quality='Complete per-character counts with exact source-bound declared encoding assumption, or native SAM/BAM numeric Phred qualities with missing mask. Q in0..93. Unknown/missing quality prevents whole-population quality claims; no inference from FastQC means.'
comp('mean_phred','quality_phred_v1','sum(n_Q*Q)/sum(n_Q)',['quality_character_count + EncodingBasis or phred_histogram_count'],['phred'],'derived_descriptive',requirements=quality)
comp('q_ge_threshold_fraction','quality_phred_v1','sum(n_Q where Q>=explicit threshold)/sum(n_Q)',['histogram','quality_thresholds'],['fraction'],'derived_descriptive',requirements=quality)
comp('phred_implied_expected_errors','quality_phred_v1','sum(n_Q*10**(-Q/10))',['histogram','EncodingBasis'],['expected_errors'],'phred_model_prediction','phred_model_only',quality)
comp('phred_implied_error_fraction','quality_phred_v1','phred_implied_expected_errors/sum(n_Q)',['histogram','EncodingBasis'],['fraction'],'phred_model_prediction','phred_model_only',quality)
lineage='Complete compatible explicitly selected before/after populations; observed native edge or exact source-bound lineage assumption retained. Assumption never proves recipe execution. after>before incompatible; before0 undefined fraction.'
for metric in ['read_retention_fraction','base_retention_fraction','pair_retention_fraction']:
    comp(metric,'retention_v1','after_count/before_count',['CalculationBinding before/after exact count refs','LineageBasis'],['fraction'],'derived_descriptive',requirements=lineage)
comp('removed_count','retention_v1','before_count-after_count',['before/after count refs','LineageBasis'],['reads','bases','pairs','alignment_records'],'derived_descriptive',requirements=lineage)
comp('removed_fraction','retention_v1','(before_count-after_count)/before_count',['before/after count refs','LineageBasis'],['fraction'],'derived_descriptive',requirements=lineage)
comp('native_report_retention_fraction','retention_v1','native_after_count/native_before_count',['same-row native report before/after refs','LineageBasis'],['fraction'],'native_report_derived','native_reporting_precision',lineage)
comp('distinct_mapped_read_fraction','mapping_v1','distinct input read segments having a mapped primary record / full input read count',
    ['complete input SequenceRecord[]','AlignmentRecord[] flags/QNAME/segment identity','explicit read_key_rule'],['fraction'],'derived_descriptive',
    requirements='Requires actual unique segment joins, complete input denominator and compatible selected populations. Mapped-only BAM/BAI is insufficient. No pair halving or native filename join.')
comp('primary_record_fraction','mapping_v1','bam_primary_record_count/bam_record_count',['same retained complete BAM/SAM population counts'],['fraction'],'derived_descriptive')
comp('report_count_difference','report_consistency_v1','selected report count - independently observed artifact count',['explicit report/observed measurement refs','LineageBasis'],['reads','bases','pairs','alignment_records'],'derived_descriptive',
    requirements='Same population/unit established or explicitly declared as an assumption; preserve signed difference. Native rounded percentages never silently replace exact counts.')
assert set(specs)==set(components)
(P/'COMPONENT_SPECS_002.json').write_text(json.dumps({'version':'fastqutils_component_specs_v2','components':[specs[m] for m in components]},indent=2)+'\n')
print(json.dumps({'metrics':len(rows),'components':len(specs)}))
