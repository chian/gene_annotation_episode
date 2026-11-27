"""The report of a finished run. ``build_report`` takes the run's final files and writes the PDF; ``render`` writes it
from the report's data (``collect``), page by page in the order of ``PAGES``."""
from __future__ import annotations

import importlib

from . import layout
from .collect import collect

PAGES = ('cover', 'genome_map', 'organism', 'feature_table', 'features', 'limits', 'provenance')


def render(data, out, pages=PAGES):
    sheet = layout.canvas(out, 'Genome annotation report ' + data['run']['run_id'])
    for name in pages:
        importlib.import_module('.pages.' + name, __package__).draw(sheet, data)
    sheet.save()


def build_report(workspace, journal, run_id, out):
    """Write the report of the closed run ``run_id`` to ``out``. ``workspace`` is the run's workspace folder (its
    ``state.sqlite3`` and ``artifacts``), ``journal`` its journal file. Both are only read."""
    render(collect(workspace, journal, run_id), out)
