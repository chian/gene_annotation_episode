"""Acquire a bounded W83 locus using the original genome paper's PG1070 lead."""
from __future__ import annotations

import hashlib
import argparse
import io
import json
from pathlib import Path
import re
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from gene_annotation_episode.workflow_budget import active_budget


def main():
    directory = Path(active_budget()['run_directory'])
    from Bio import SeqIO
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--feature-table',type=Path)
    args=parser.parse_args()

    endpoint = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi'
    accession = 'AE015924'

    def fetch(parameters, filename):
        request = Request(endpoint+'?'+urlencode(parameters), headers={
            'User-Agent':'gene-annotation-episode bounded A103 fixture acquisition'})
        with urlopen(request, timeout=45) as response:
            content=response.read(8*1024**2+1)
        if len(content)>8*1024**2:
            raise ValueError('bounded_acquisition_response_too_large')
        (directory/filename).write_bytes(content)
        return content

    feature_request={'db':'nuccore','id':accession,'rettype':'ft','retmode':'text'}
    content=(args.feature_table.read_bytes() if args.feature_table is not None else
        fetch(feature_request,'w83-feature-table.txt'))
    (directory/'w83-feature-table.txt').write_bytes(content)
    features=[]
    current=None
    for line in content.decode().splitlines():
        fields=line.split('\t')
        if len(fields)>=3 and fields[0] and fields[2]:
            current={'type':fields[2],'coordinates':[fields[0],fields[1]],'locus_tags':[],'protein_ids':[]}
            features.append(current)
        elif current is not None and len(fields)>=5 and fields[3] in {'locus_tag','old_locus_tag'}:
            current['locus_tags'].append(fields[4])
        elif current is not None and len(fields)>=5 and fields[3]=='protein_id':
            current['protein_ids'].extend(re.findall(r'\b[A-Z]{3}\d{5}\.\d+\b',fields[4]))
    canonical=lambda value:re.sub('[^A-Za-z0-9]','',value).upper()
    candidates=[f for f in features if f['type']=='gene' and
        'PG1070' in {canonical(t) for t in f['locus_tags']}]
    if len(candidates)!=1:
        raise ValueError('original_paper_locus_lead_not_uniquely_resolved')
    feature=candidates[0]
    coding_feature,=[f for f in features if f['type']=='CDS' and f['coordinates']==feature['coordinates']]
    protein_id,=coding_feature['protein_ids']
    positions=[int(p.strip('<>')) for p in feature['coordinates']]
    parameters={'db':'nuccore','id':accession,'rettype':'gbwithparts','retmode':'text',
        'seq_start':max(1,min(positions)-12000),'seq_stop':max(positions)+14000}
    filename='porphyromonas-kama.gb'
    window=fetch(parameters,filename)
    record,=SeqIO.parse(io.StringIO(window.decode()),'genbank')
    matches=[]
    summary=[]
    for index,cds in enumerate(record.features):
        if cds.type!='CDS':continue
        tags=[t for key in ('locus_tag','old_locus_tag') for t in cds.qualifiers.get(key,[])]
        summary.append({'feature_index':index,'locus_tags':tags,
            'protein_ids':cds.qualifiers.get('protein_id',[]),
            'product_labels':cds.qualifiers.get('product',[]),'location':str(cds.location)})
        if protein_id in cds.qualifiers.get('protein_id',[]):matches.append(cds)
    cds,=matches
    translation=''.join(cds.qualifiers['translation'])
    coding=cds.extract(record.seq)[int(cds.qualifiers.get('codon_start',['1'])[0])-1:]
    computed=str(coding.translate(table=int(cds.qualifiers.get('transl_table',['11'])[0]),cds=True))
    if computed!=translation:
        raise ValueError('acquired_locus_translation_conflict')
    entry={'request':parameters,'sha256':hashlib.sha256(window).hexdigest(),
        'source_url':endpoint,'retrieved_date':datetime.now(timezone.utc).date().isoformat(),
        'original_response':True,'whole_genome_coverage':False,
        'locus_lead_source':'https://pmc.ncbi.nlm.nih.gov/articles/PMC193775/',
        'feature_table_request':feature_request,'feature_table_sha256':hashlib.sha256(content).hexdigest()}
    result={'filename':filename,'manifest_entry':entry,
        'selector':{'protein_id':cds.qualifiers['protein_id'][0]},'features':summary,
        'interpretation':'Original genomic data and source labels; no independent experimental activity evidence.'}
    (directory/'ACQUIRED_INPUT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':main()
