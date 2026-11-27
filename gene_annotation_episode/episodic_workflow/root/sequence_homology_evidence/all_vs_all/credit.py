"""Credit, read from what the episode holds (not from what a tool said): ``handoff_unit`` for the established database,
``information_unit`` for the established matrix of bit scores and ``graded_unit`` for the committed (graded) clustering; each is earned
once, and a refused or repeated step earns nothing. The tries of the clustering are working results and earn nothing: the head's credit
reads only the committed, graded clustering, so tries neither add nor dilute it.
The three units are the commission's (the head's child credit units)."""
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import products
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import (
    all_vs_all_run as run)


def credit(summary, records):
    units = summary['units']
    held = [row['kind'] for row in products(records)]
    return ((units['handoff_unit'] if run.DATABASE_KIND in held else 0.0)
            + (units['information_unit'] if run.MATRIX_KIND in held else 0.0)
            + (units['graded_unit'] if summary['committed'] else 0.0))


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if ``action_type`` with ``arguments`` (``None``: over every arguments it can take now) is the
    next unit. Each term is earned once and only for a product newly held, so a repeat of a step whose product is held has
    ceiling 0:

    * ``prepare_database``: ``handoff_unit`` while no database is held.
    * ``all_vs_all_blast``: ``information_unit`` while a database is held and no matrix is held.
    * ``cluster``: 0. A try is a working result and earns nothing (the credit reads the committed clustering only).
    * ``commit_clustering``: ``graded_unit`` while none is committed and a clustering is held (``summary['committable']``;
      with ``arguments``: when its ``clusters_ref`` is one
      of them), else 0.
    * ``hold``: 0. It runs nothing and writes no record."""
    held = [row['kind'] for row in products(records)]
    if action_type == 'prepare_database':
        return 0.0 if run.DATABASE_KIND in held else float(summary['units']['handoff_unit'])
    if action_type == 'all_vs_all_blast':
        return (float(summary['units']['information_unit'])
                if run.DATABASE_KIND in held and run.MATRIX_KIND not in held else 0.0)
    if action_type == 'commit_clustering':
        if summary['committed'] or not summary['committable']:
            return 0.0
        return (float(summary['units']['graded_unit'])
                if arguments is None or arguments['call']['clusters_ref'] in summary['committable'] else 0.0)
    if action_type in ('cluster', 'hold'):
        return 0.0
    raise ValueError('all_vs_all_unknown_action_type:' + str(action_type))
