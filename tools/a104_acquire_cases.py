"""Acquire original small A104 comparison panels, serially within one workflow.

This obtains source data only. It runs no alignment, tree inference or search
algorithm locally. Every UniProt call uses the selected skill's REST client.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from urllib.request import Request, urlopen
import zipfile
import io
import xml.etree.ElementTree as ET

from gene_annotation_episode.workflow_budget import active_budget


CLIENT = Path('/home/chia/.codex/plugins/cache/openai-curated-remote/life-science-research/1.0.3/skills/uniprot-skill/scripts/rest_request.py')
FIELDS = 'accession,id,protein_name,gene_names,organism_id,organism_name,sequence,length'


def uniprot(directory, name, query, size=12):
    request = {'base_url': 'https://rest.uniprot.org', 'path': 'uniprotkb/search',
        'params': {'query': query, 'fields': FIELDS, 'size': size, 'format': 'json'},
        'record_path': 'results', 'max_items': 1, 'max_depth': 2,
        'save_raw': True, 'raw_output_path': str(directory/(name+'.json'))}
    (directory/(name+'-request.json')).write_text(json.dumps(request, indent=2)+'\n')
    process = subprocess.run([sys.executable, '-B', str(CLIENT)], input=json.dumps(request),
                             text=True, capture_output=True)
    (directory/(name+'-client.json')).write_text(process.stdout)
    (directory/(name+'-client.stderr')).write_text(process.stderr)
    response = json.loads(process.stdout)
    if process.returncode or not response.get('ok'):
        raise ValueError('a104_original_source_acquisition_failed:'+name+':'+str(response.get('error')))
    rows = json.loads((directory/(name+'.json')).read_text())['results']
    print(json.dumps({'event': 'a104_original_sequences_acquired', 'group': name,
        'count': len(rows), 'accessions': [row['primaryAccession'] for row in rows]}), flush=True)
    return rows


def table_preview(raw):
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        strings = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            strings = [''.join(node.itertext()) for node in
                       ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('s:si', ns)]
        sheets = {}
        for name in archive.namelist():
            if name.startswith('xl/worksheets/sheet') and name.endswith('.xml'):
                rows = []
                for row in ET.fromstring(archive.read(name)).findall('.//s:row', ns):
                    values = {}
                    for cell in row.findall('s:c', ns):
                        value = cell.find('s:v', ns)
                        text = value.text if value is not None else ''.join(cell.itertext())
                        values[cell.attrib['r']] = strings[int(text)] if cell.attrib.get('t') == 's' else text
                    rows.append(values)
                sheets[name] = rows
        return sheets


def oarx(directory):
    uniprot(directory, 'target-cg0825', 'gene:cg0825 AND taxonomy_id:1718', 10)
    uniprot(directory, 'family-fabg', 'gene_exact:fabG AND taxonomy_id:2 AND reviewed:true AND length:[200 TO 350] AND fragment:false', 16)
    urls = ['https://pmc.ncbi.nlm.nih.gov/articles/instance/11223231/bin/ao4c03514_si_002.xlsx',
            'https://pubs.acs.org/doi/suppl/10.1021/acsomega.4c03514/suppl_file/ao4c03514_si_002.xlsx']
    acquisition = []
    for url in urls:
        try:
            with urlopen(Request(url, headers={'User-Agent': 'gene-annotation-episode/1'}), timeout=60) as response:
                raw = response.read()
                if not zipfile.is_zipfile(io.BytesIO(raw)):
                    raise ValueError('original_supplement_is_not_xlsx')
                table = table_preview(raw)
                acquisition.append({'requested_url': url, 'resolved_url': response.url,
                    'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)})
            (directory/'oarx-supplement.xlsx').write_bytes(raw)
            (directory/'oarx-table.json').write_text(json.dumps(table, indent=2)+'\n')
            print(json.dumps({'event': 'a104_original_supplement_acquired', 'sheets': {
                name: {'rows': len(rows), 'first_rows': rows[:3]} for name, rows in table.items()}}), flush=True)
            break
        except Exception as error:
            acquisition.append({'requested_url': url, 'error': type(error).__name__+':'+str(error)})
    (directory/'oarx-supplement-acquisition.json').write_text(json.dumps(acquisition, indent=2)+'\n')


def mj0044(directory):
    target = uniprot(directory, 'target-mj0044', 'accession:Q60352', 10)
    if len(target) != 1:
        raise ValueError('mj0044_original_accession_unresolved')
    groups = {'ipk': 'gene_exact:ipk', 'mvk': 'gene_exact:mvk',
              'thrb': 'gene_exact:thrB', 'galk': 'gene_exact:galK'}
    rows = []
    for name, query in groups.items():
        rows.extend(uniprot(directory, 'family-'+name, '('+query+') AND length:[180 TO 550] AND fragment:false', 10))
    taxa = list(dict.fromkeys([target[0]['organism']['taxonId'], *[row['organism']['taxonId'] for row in rows[:10]]]))[:8]
    query = '('+' OR '.join('organism_id:'+str(taxon) for taxon in taxa)+') AND ('+ \
        ' OR '.join('gene_exact:'+gene for gene in ('rplB', 'rpl2', 'rplC', 'rpl3', 'rpsC', 'rps3'))+') AND fragment:false'
    uniprot(directory, 'mj0044-organismal-markers', query, 500)


def refine(directory):
    uniprot(directory, 'target-ncgl0689', '(gene:NCgl0689 OR gene:cg0825) AND taxonomy_id:1718', 10)
    rows = uniprot(directory, 'family-ipk-refined',
        'protein_name:"Isopentenyl phosphate kinase" AND taxonomy_id:2157 AND length:[180 TO 550] AND fragment:false', 16)
    taxa = list(dict.fromkeys([243232, *[row['organism']['taxonId'] for row in rows]]))[:8]
    query = '('+' OR '.join('organism_id:'+str(taxon) for taxon in taxa)+') AND ('+ \
        ' OR '.join('gene_exact:'+gene for gene in ('rplB', 'rpl2', 'rplC', 'rpl3', 'rpsC', 'rps3'))+') AND fragment:false'
    uniprot(directory, 'mj0044-organismal-markers-refined', query, 500)
    url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11223231/supplementaryFiles'
    try:
        with urlopen(Request(url, headers={'User-Agent': 'gene-annotation-episode/1'}), timeout=60) as response:
            raw = response.read()
            acquisition = {'requested_url': url, 'resolved_url': response.url,
                'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)}
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            selected = [name for name in archive.namelist() if Path(name).name == 'ao4c03514_si_002.xlsx']
            if len(selected) != 1:
                raise ValueError('original_oarx_supplement_not_in_archive:'+str(archive.namelist()))
            table_raw = archive.read(selected[0])
        (directory/'oarx-supplements.zip').write_bytes(raw)
        (directory/'oarx-supplement.xlsx').write_bytes(table_raw)
        table = table_preview(table_raw)
        (directory/'oarx-table.json').write_text(json.dumps(table, indent=2)+'\n')
        print(json.dumps({'event': 'original_oarx_table_acquired', 'sheets': {
            name: {'rows': len(rows), 'first_rows': rows[:3]} for name, rows in table.items()}}), flush=True)
    except Exception as error:
        acquisition = {'requested_url': url, 'error': type(error).__name__+':'+str(error)}
    (directory/'oarx-supplement-acquisition.json').write_text(json.dumps(acquisition, indent=2)+'\n')


def ipk_family(directory):
    uniprot(directory, 'family-ipk-specific',
        'protein_name:"Isopentenyl phosphate kinase" AND length:[180 TO 550] AND fragment:false', 32)
    uniprot(directory, 'family-foma',
        'gene_exact:fomA AND protein_name:kinase AND length:[180 TO 450] AND fragment:false', 12)


if __name__ == '__main__':
    active_budget()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case', choices=('oarx', 'mj0044', 'all', 'refine', 'ipk-family'), required=True)
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args()
    directory = args.output_directory.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    if args.case == 'all':
        for name, acquire in (('oarx', oarx), ('mj0044', mj0044)):
            child = directory/name
            child.mkdir()
            acquire(child)
    else:
        {'oarx': oarx, 'mj0044': mj0044, 'refine': refine, 'ipk-family': ipk_family}[args.case](directory)
