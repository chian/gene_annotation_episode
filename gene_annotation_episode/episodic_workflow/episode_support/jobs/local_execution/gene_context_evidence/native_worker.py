"""Bounded native gene-context calculations with durable input/output files."""
from __future__ import annotations

import json
from pathlib import Path
import sys

from gene_annotation_episode.episodic_workflow.episode_support.grading.gene_context_evidence.scoring import execute, VERSION
from gene_annotation_episode.episodic_workflow.episode_support.records.gene_context_evidence.domain import canonical


def main():
    path = Path(sys.argv[1]).resolve()
    try:
        result = {'status':'completed','result':execute(json.loads(path.read_text())),
                  'worker_version':VERSION,'failure':None}
        status = 0
    except Exception as error:
        result = {'status':'failed','result':None,'worker_version':VERSION,
                  'failure':{'type':type(error).__name__,'message':str(error)}}
        status = 1
    (path.parent/'worker-result.json').write_text(canonical(result))
    raise SystemExit(status)


if __name__=='__main__':
    main()
