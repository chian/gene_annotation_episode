"""``python -m gene_annotation_episode.genome_report build --workspace W --journal J --run-id R --out report.pdf``
writes the report of a finished run. ``render --data report_data.json --out report.pdf`` draws it from saved report
data; ``--pages`` names the pages to draw."""
import argparse
import json
from pathlib import Path

from .build import PAGES, build_report, render

parser = argparse.ArgumentParser(prog='python -m gene_annotation_episode.genome_report')
commands = parser.add_subparsers(dest='command', required=True)
build = commands.add_parser('build', help='The report of a finished run, from its workspace and journal.')
build.add_argument('--workspace', required=True)
build.add_argument('--journal', required=True)
build.add_argument('--run-id', required=True)
build.add_argument('--out', required=True)
drawn = commands.add_parser('render', help='The report, drawn from saved report data.')
drawn.add_argument('--data', required=True)
drawn.add_argument('--out', required=True)
drawn.add_argument('--pages', default=','.join(PAGES))
arguments = parser.parse_args()
if arguments.command == 'build':
    build_report(arguments.workspace, arguments.journal, arguments.run_id, arguments.out)
else:
    render(json.loads(Path(arguments.data).read_text()), arguments.out, arguments.pages.split(','))
