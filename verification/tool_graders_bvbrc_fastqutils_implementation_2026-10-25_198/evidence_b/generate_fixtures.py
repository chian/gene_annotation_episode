from pathlib import Path
import json, shutil, hashlib
base=Path(__file__).resolve().parents[1]
fixture=base/'candidate/tests/fixtures/bvbrc_fastqutils/reports'; fixture.mkdir(parents=True,exist_ok=True)
text='''##FastQC\t0.12.1
>>Basic Statistics\tpass
#Measure\tValue
Filename\tsynthetic_R1.fastq
File type\tConventional base calls
Encoding\tSanger / Illumina 1.9
Total Sequences\t200
Total Bases\t1.2 kbp
Sequences flagged as poor quality\t3
Sequence length\t5-10
%GC\t55
>>END_MODULE
>>Per base sequence quality\twarn
#Base\tMean\tMedian\tLower Quartile\tUpper Quartile\t10th Percentile\t90th Percentile
1-5\t31.5\t32.0\tNaN\t34.0\t20.0\t40.0
>>END_MODULE
>>Per tile sequence quality\tfail
#Tile\tBase\tMean
1101\t1-5\t-2.25
>>END_MODULE
>>Per sequence quality scores\tpass
#Quality\tCount
30\t200.0
>>END_MODULE
>>Per base sequence content\twarn
#Base\tG\tA\tT\tC
1-5\t30.0\t25.0\t20.0\t25.0
>>END_MODULE
>>Per sequence GC content\tpass
#GC Content\tCount
50\t0.75
51\t1.25
>>END_MODULE
>>Per base N content\tpass
#Base\tN-Count
1-5\t10.0
>>END_MODULE
>>Sequence Length Distribution\twarn
#Length\tCount
5-10\t200.0
>>END_MODULE
>>Sequence Duplication Levels\tpass
#Total Deduplicated Percentage\t80.0
#Duplication Level\tPercentage of total
1\t70.0
>10k+\t1.0
>>END_MODULE
>>Overrepresented sequences\twarn
#Sequence\tCount\tPercentage\tPossible Source
ACGTACG\t4\t2.0\tNo Hit
>>END_MODULE
>>Adapter Content\tpass
#Position\tIllumina Universal Adapter\tNextera Transposase Sequence
1-5\t0.5\t1.25
>>END_MODULE
>>Kmer Content\tfail
#Sequence\tCount\tPValue\tObs/Exp Max\tMax Obs/Exp Position
ACGTACG\t15\t0.0002\t7.5\t1-5
>>END_MODULE
'''
(fixture/'fastqc_all_modules.txt').write_text(text)
html='''<!DOCTYPE html><html><body><div class="module"><h2 id="M0"><img alt="[OK]"/>Basic Statistics</h2><table><tr><th>Measure</th><th>Value</th></tr><tr><td>Filename</td><td>é_R1.fastq</td></tr><tr><td>Encoding</td><td>Sanger / Illumina 1.9</td></tr><tr><td>Total Sequences</td><td>200</td></tr><tr><td>Total Bases</td><td>1.2 kbp</td></tr><tr><td>Sequences flagged as poor quality</td><td>3</td></tr><tr><td>Sequence length</td><td>5-10</td></tr><tr><td>%GC</td><td>55</td></tr></table></div><div class="module"><h2 id="M1"><img alt="[WARN]"/>Per base sequence quality</h2><img src="data:image/png;base64,AAAA" alt="Per base quality graph"/></div><div class="module"><h2 id="M9"><img alt="[WARN]"/>Overrepresented sequences</h2><table><tr><th>Sequence</th><th>Count</th><th>Percentage</th><th>Possible Source</th></tr><tr><td>ACGTACG</td><td>4</td><td>2.0</td><td>No Hit</td></tr></table></div><div class="module"><h2 id="M11"><img alt="[FAIL]"/>Kmer Content</h2><table><tr><th>Sequence</th><th>Count</th><th>PValue</th><th>Obs/Exp Max</th><th>Max Obs/Exp Position</th></tr><tr><td>ACGTACG</td><td>15</td><td>0.0002</td><td>7.5</td><td>1-5</td></tr></table></div><div class="footer">Produced by <a href="http://www.bioinformatics.babraham.ac.uk/projects/fastqc/">FastQC</a>  (version 0.12.1)</div></body></html>'''
(fixture/'fastqc_tables_graph.html').write_text(html)
config='''
SUMMARISING RUN PARAMETERS
==========================
Input filename: synthetic_R1.fastq.gz
Trimming mode: {mode}
Trim Galore version: 0.6.10
Cutadapt version: 4.4
Number of cores used for trimming: 2
Quality Phred score cutoff: 20
Quality encoding type selected: ASCII+33
Using Illumina adapter for trimming (count: 12). Second best hit was Nextera (count: 2)
Adapter sequence: 'AGATCGGAAGAGC' (Illumina TruSeq, Sanger iPCR; auto-detected)
Maximum trimming error rate: 0.1 (default)
Minimum required adapter overlap (stringency): 1 bp
Minimum required sequence length before a sequence gets removed: 20 bp
Output file will be GZIP compressed

This is cutadapt 4.4 with Python 3.11
Command line parameters: -a AGATCGGAAGAGC -q 20 synthetic_R1.fastq.gz
=== Summary ===
Total reads processed: 8
Reads with adapters: 4 (50.0%)

RUN STATISTICS FOR INPUT FILE: synthetic_R1.fastq.gz
=============================================
8 sequences processed in total
'''
(fixture/'trim_first.txt').write_text(config.format(mode='paired-end'))
(fixture/'trim_single.txt').write_text(config.format(mode='single-end')+'''Sequences removed because they became shorter than the length cutoff of 20 bp:\t2 (25.0%)
Sequences removed because they contained more Ns than the cutoff of 0.1:\t1 (12.5%)
Sequences removed because after trimming they were longer than the maximum length cutoff of 100 bp:\t1 (12.5%)
''')
(fixture/'trim_second.txt').write_text(config.format(mode='paired-end').replace('synthetic_R1','synthetic_R2')+'''Number of sequence pairs removed because at least one read contained more N(s) than the specified limit of 0.1: 1 (12.50%)
Sequence pairs removed as after trimming at least one read was longer than the maximum length cutoff of 100 bp:\t1 (12.50%)
Total number of sequences analysed for the sequence pair length validation: 8

Number of sequence pairs removed because at least one read was shorter than the length cutoff (20 bp): 2 (25.00%)
''')
(fixture/'pair_stderr.txt').write_text('Left paired: 6\t\tRight paired: 6\nLeft single: 2\t\tRight single: 1\n')
repo=base.parents[1]
source=repo/'verification/tool_graders_bvbrc_fastqutils_contract_2026-10-25_193/synthetic/hostile_native_stats.json'
shutil.copyfile(source,fixture/'hostile_source_executed_synthetic.json')
shutil.copyfile(repo/'verification/tool_graders_bvbrc_fastqutils_contract_2026-10-25_193/synthetic/overwrite/hostile_report.txt',fixture/'hostile_overwritten_stub.json')
contract=repo/'verification/tool_graders_bvbrc_fastqutils_interface_2026-10-25_195'
for name,target in [('EXPECTED_SHEET_002.json','saved_native_sheet.json'),('EXPECTED_COMPONENTS_002.json','saved_native_components.json'),('ASSUMED_LINEAGE_SHEET_002.json','saved_assumed_sheet.json'),('ASSUMED_LINEAGE_COMPONENTS_002.json','saved_assumed_components.json')]:
 shutil.copyfile(contract/name,fixture/target)
manifest=[]
for path in sorted(fixture.iterdir()):
 if not path.is_file() or path.name=='PROVENANCE.json':continue
 identity='source_executed_synthetic' if path.name.startswith('hostile_') else 'handcrafted_synthetic'
 manifest.append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'identity':identity,
 'qualification':'Retained193 upstream function probe with external tools stubbed; not genuine service output.' if path.name.startswith('hostile_') else 'Handwritten native-format/contract fixture; not native program execution.'})
(fixture/'PROVENANCE.json').write_text(json.dumps(manifest,indent=2)+'\n')
