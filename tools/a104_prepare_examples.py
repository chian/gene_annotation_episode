"""Preserve reusable original inputs and prepare two real A104 examples."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from gene_annotation_episode.workflow_budget import active_budget
from tools.a104_build_mj0044 import build as build_mj0044
from tools.a104_build_oarx import build as build_oarx
from tools.a104_prepare_case import prepare


def preserve(destination, files):
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for source in files:
        target = destination/source.name
        raw = source.read_bytes()
        if target.exists() and target.read_bytes() != raw:
            raise ValueError('a104_existing_reusable_input_conflict:'+str(target))
        shutil.copy2(source, target)
        manifest[source.name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'size_bytes': len(raw)}
    (destination/'original-files.json').write_text(json.dumps({'files': manifest,
        'interpretation': 'original_source_inputs; source_annotations_are_leads_not_expected_answers'}, indent=2)+'\n')


def main():
    run = Path(active_budget()['run_directory'])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acquired', type=Path, required=True)
    parser.add_argument('--refined', type=Path, required=True)
    parser.add_argument('--ipk-specific', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    acquired = args.acquired.resolve()
    refined = args.refined.resolve()
    ipk_specific = args.ipk_specific.resolve()
    fixtures = root/'tests/fixtures/a104/real'
    oarx_files = [refined/name for name in ('oarx-supplement.xlsx', 'oarx-supplement-acquisition.json')]
    oarx_files += [acquired/'oarx'/name for name in ('family-fabg.json', 'family-fabg-request.json')]
    preserve(fixtures/'oarx', oarx_files)
    mj_names = ['target-mj0044', 'family-ipk', 'family-mvk', 'family-thrb', 'family-galk']
    mj_files = [acquired/'mj0044'/(name+suffix+'.json') for name in mj_names for suffix in ('', '-request')]
    mj_files += [refined/(name+suffix+'.json') for name in
        ('family-ipk-refined', 'mj0044-organismal-markers-refined') for suffix in ('', '-request')]
    mj_files += [ipk_specific/(name+suffix+'.json') for name in
        ('family-ipk-specific', 'family-foma') for suffix in ('', '-request')]
    preserve(fixtures/'mj0044', mj_files)
    (fixtures/'oarx/README.md').write_text('Original peptides from sheet2 of the OarX paper supplement '
        '(PMC11223231; DOI 10.1021/acsomega.4c03514) and a separately acquired reviewed FabG comparison panel. '
        'The supplied target is C. glutamicum ATCC 13032 fig:196627.14.peg.708. The paper\'s perturbation strain '
        'ATCC 14067 is a different subject. Publication names select leads; they do not establish molecular activity. '
        'The exact supplementary workbook and original acquisition metadata are preserved.\n')
    (fixtures/'mj0044/README.md').write_text('Original UniProt sequence responses and requests for Q60352/MJ0044, '
        'close archaeal and other isopentenyl-phosphate-kinase leads, FomA relatives and independent '
        'ribosomal markers. The original gene_exact:ipk query also returns IspE aliases; the refined protein-name '
        'query supplies closer archaeal leads. Broad GHMP leads are preserved as excluded sampling inputs; '
        'the native tree uses IPK/FomA amino-acid-kinase-family leads, following the primary studies '
        '(PMC1447442 and PMID 19928876). Annotation names are comparison leads, not experimental facts '
        'or an expected answer supplied to the scientific model.\n')
    for name, build in (('oarx', build_oarx), ('mj0044', build_mj0044)):
        bundle = run/(name+'-inputs.json')
        if name == 'oarx':
            build(fixtures/name, fixtures/name, bundle)
        else:
            build(fixtures/name, fixtures/name, bundle)
        directory = run/name/'case'
        value = prepare(bundle, directory)
        print(json.dumps({'event': 'a104_real_case_prepared', 'case': name, 'directory': str(directory),
            'target_ref': value['target_ref'], 'native_request_ref': value['native_request_ref']}), flush=True)


if __name__ == '__main__':
    main()
