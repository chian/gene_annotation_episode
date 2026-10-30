"""Retain handcrafted synthetic byte fixtures and inspectable numerical examples.

This is verification scaffolding, not a scientific execution operation. The
fixture encoders come from the assigned tests and no native program is run.
"""
from pathlib import Path
import gzip
import hashlib
import json
import struct
import sys

ROOT=Path(__file__).resolve().parents[1]
CANDIDATE=ROOT/'candidate'
sys.path.insert(0,str(CANDIDATE))
sys.path.insert(0,str(CANDIDATE/'tests'))

from gene_annotation_episode.bvbrc_fastqutils_contracts import json_sha256, validate_components
from gene_annotation_episode.bvbrc_fastqutils_fastq_reader import parse_fastq
from gene_annotation_episode.bvbrc_fastqutils_sam_reader import parse_sam
from gene_annotation_episode.bvbrc_fastqutils_bam_reader import parse_bam
from gene_annotation_episode.bvbrc_fastqutils_composition import calculate_composition
from gene_annotation_episode.bvbrc_fastqutils_quality import calculate_quality
from gene_annotation_episode.bvbrc_fastqutils_mapping import calculate_mapping
from test_bvbrc_fastqutils_sequence_formats import context
from test_bvbrc_fastqutils_alignment_formats import bam,record
from test_bvbrc_fastqutils_sequence_calculators import sheet_for,encoding,binding,composition_job,quality_job


def save(path,value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')


def main():
    sequence=CANDIDATE/'tests/fixtures/bvbrc_fastqutils/sequence'
    alignment=CANDIDATE/'tests/fixtures/bvbrc_fastqutils/alignment'
    files={sequence/'multiline.fastq':b'@r1 description\nACGT\nNRY\n+r1 description\n@@@\nIIII\n@r2\nGC\n+\nII\n',
           sequence/'quality_phred33.fastq':b'@quality\nACGT\n+\n!+5?\n',
           sequence/'input_reads.fastq':b'@r1\nAC\n+\nII\n@r2\nAC\n+\nII\n@r3\nAC\n+\nII\n',
           sequence/'empty.fastq':b'',
           alignment/'records.sam':b'@HD\tVN:1.6\n@SQ\tSN:ref\tLN:100\n@RG\tID:g\tSM:explicit-label\n@PG\tID:p\tPN:synthetic-encoder\tVN:1.0\n'
               b'r1\t0\tref\t1\t255\t2M\t*\t0\t0\tAC\t!I\tRG:Z:g\tPG:Z:p\tNM:i:0\tAA:A:Y\tAR:B:i,-2,3\n'
               b'r1\t256\tref\t2\t20\t2M\t*\t0\t0\tAC\tII\n'
               b'r2\t4\tref\t1\t0\t2M\t*\t0\t0\tAC\t*\n',
           alignment/'mapped_and_unmapped.bam':bam([record('r1'),record('r1',flag=256),record('r2',flag=4)]),
           alignment/'bounded_bad_record.bam':bam([record('first'),struct.pack('<I',3)+b'bad',record('last')])}
    one=b'@one\nA\n+\n!\n'; two=b'@two\nGC\n+\nII\n'
    files[sequence/'plain_named.fastq.gz']=one
    files[sequence/'concatenated.fastq.gz']=gzip.compress(one,mtime=0)+gzip.compress(two,mtime=0)
    files[sequence/'truncated.fastq.gz']=files[sequence/'concatenated.fastq.gz'][:-5]
    tags=b'AAAX'+b'BBc'+struct.pack('<b',-1)+b'CCC'+struct.pack('<B',255)+b'DDs'+struct.pack('<h',-300)
    tags+=b'EES'+struct.pack('<H',65535)+b'FFi'+struct.pack('<i',-100000)+b'GGI'+struct.pack('<I',4000000000)
    tags+=b'HHf'+struct.pack('<f',1.5)+b'IIZtext\0'+b'JJH00FF\0'+b'KKBf'+struct.pack('<I',2)+struct.pack('<ff',2.5,float('nan'))
    files[alignment/'auxiliary_types.bam']=bam([record(tags=tags),record('missing_quality',qualities=b'\xff\xff')])
    docs=[]
    fixtures=[]
    for index,(path,raw) in enumerate(files.items()):
        path.write_bytes(raw)
        fmt='sam_1_6' if path.suffix=='.sam' else 'bam_1' if path.suffix=='.bam' else 'fastq'
        parser={'sam_1_6':parse_sam,'bam_1':parse_bam,'fastq':parse_fastq}[fmt]
        source=context(raw,fmt,path.name,document='fixture_'+str(index))
        parsed=parser(raw,context=source)
        docs.append(parsed)
        fixtures.append(dict(path=str(path.relative_to(CANDIDATE)),identity='handcrafted_synthetic',
            sha256=hashlib.sha256(raw).hexdigest(),byte_count=len(raw),context=source,
            parse_scope=parsed['parse_scope'],native_document_sha256=json_sha256(parsed)))
    save(ROOT/'evidence_a/FIXTURE_MANIFEST.json',fixtures)
    save(ROOT/'evidence_a/FILLED_NATIVE_DOCUMENTS.json',docs)
    examples=[]
    for label,raw,method in [('composition',files[sequence/'multiline.fastq'],'composition'),
                             ('quality',files[sequence/'quality_phred33.fastq'],'quality')]:
        sheet=sheet_for(parse_fastq(raw,context=context(raw)))
        if method=='quality': encoding(sheet,'reads')
        job=composition_job(sheet) if method=='composition' else quality_job(sheet)
        parameters=dict(version='fastqutils_calculators_v2',analysis_id='example',calculations=[job])
        fn=calculate_composition if method=='composition' else calculate_quality
        components=fn(sheet,job=job,parameters_sha256=json_sha256(parameters))
        examples.append(dict(name=label,sheet=sheet,parameters=parameters,components=components))
    raw=files[sequence/'input_reads.fastq']; binary=files[alignment/'mapped_and_unmapped.bam']
    sheet=sheet_for(parse_fastq(raw,context=context(raw)),parse_bam(binary,context=context(binary,'bam_1',document='alignment')))
    job=binding(sheet,'mapping_v1',['fastq_reads','bam_records'],['fastq_read_count','bam_record_count','bam_primary_record_count'],read_key_rule='exact_title')
    parameters=dict(version='fastqutils_calculators_v2',analysis_id='example',calculations=[job])
    components=calculate_mapping(sheet,job=job,parameters_sha256=json_sha256(parameters))
    examples.append(dict(name='mapping',sheet=sheet,parameters=parameters,components=components))
    raw=b'@one\nACGT\n+\n5555\n@two\nGGTT\n+\nIIII\n'
    path=sequence/'two_read_numerical_example.fastq'
    path.write_bytes(raw)
    source=context(raw,document='two_read_example')
    document=parse_fastq(raw,context=source)
    docs.append(document)
    fixtures.append(dict(path=str(path.relative_to(CANDIDATE)),identity='handcrafted_synthetic',
        sha256=hashlib.sha256(raw).hexdigest(),byte_count=len(raw),context=source,
        parse_scope=document['parse_scope'],native_document_sha256=json_sha256(document)))
    sheet=sheet_for(document); encoding(sheet,'two_read_example')
    composition=composition_job(sheet); composition['calculation_id']='composition'
    quality=quality_job(sheet); quality['calculation_id']='quality'; quality['quality_thresholds']=[30]
    parameters=dict(version='fastqutils_calculators_v2',analysis_id='example',calculations=[composition,quality])
    digest=json_sha256(parameters)
    components=calculate_composition(sheet,job=composition,parameters_sha256=digest)+calculate_quality(sheet,job=quality,parameters_sha256=digest)
    examples.append(dict(name='root_requested_two_reads',sheet=sheet,parameters=parameters,components=components))
    save(ROOT/'evidence_a/FIXTURE_MANIFEST.json',fixtures)
    save(ROOT/'evidence_a/FILLED_NATIVE_DOCUMENTS.json',docs)
    for item in examples:
        validate_components(dict(schema_version='fastqutils_components_v2',sheet_sha256=json_sha256(item['sheet']),
            parameters=item['parameters'],components=item['components'],requirements=[],diagnostics=[],analysis_id='example'),sheet=item['sheet'])
    save(ROOT/'evidence_a/SAVED_SHEET_NUMERICAL_EXAMPLES.json',examples)
    summary={e['name']:[{k:r[k] for k in ('metric','threshold','state','value','numerator','denominator','meaning')}
                       for r in e['components']] for e in examples}
    save(ROOT/'evidence_a/NUMERICAL_EXAMPLE_SUMMARY.json',summary)
    print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
