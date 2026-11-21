"""Credit, read from the data products the episode holds (not from what a tool said): ``handoff_unit`` for the established
database, ``information_unit`` for the established matrix of bit scores and ``graded_unit`` for each graded clustering (one for
each distinct inflation); each is earned once, and a refused or repeated step earns nothing. The three units are the
commission's (the head's child credit units)."""
from gene_annotation_episode.episodic_workflow.episode_support.records.data_products import products
from gene_annotation_episode.episodic_workflow.episode_support.tools.similarity_search.sequence_homology_evidence import (
    all_vs_all_run as run)


def credit(summary, records):
    units = summary['units']
    held = [row['kind'] for row in products(records)]
    return ((units['handoff_unit'] if run.DATABASE_KIND in held else 0.0)
            + (units['information_unit'] if run.MATRIX_KIND in held else 0.0)
            + units['graded_unit'] * held.count(run.CLUSTERS_KIND))


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if ``action_type`` with ``arguments`` (``None``: over every arguments it can take now) is the
    next unit. Each term is earned once and only for a product newly held, and each tool's check refuses it outside one state, so
    a refused tool has ceiling 0:

    * ``prepare_database``: ``handoff_unit`` while no database is held and no preparation failed.
    * ``all_vs_all_blast``: ``information_unit`` while a database is held, no matrix is held and no search failed.
    * ``cluster``: ``graded_unit`` while a matrix is held and an inflation of the commission is neither clustered nor failed
      (with ``arguments``: when ITS inflation is one of those).
    * ``hold``: 0. It runs nothing and writes no record."""
    held = [row['kind'] for row in products(records)]
    failed = summary['failed']
    if action_type == 'prepare_database':
        return 0.0 if run.DATABASE_KIND in held or failed['prepare'] else float(summary['units']['handoff_unit'])
    if action_type == 'all_vs_all_blast':
        return (float(summary['units']['information_unit'])
                if run.DATABASE_KIND in held and run.MATRIX_KIND not in held and not failed['blast'] else 0.0)
    if action_type == 'cluster':
        clustered = {row['settings']['inflation'] for row in products(records, run.CLUSTERS_KIND)}
        failed_inflations = {inflation for _, inflation in failed['cluster']}
        open_ = [value for value in summary['commission']['inflations'] if value not in clustered | failed_inflations]
        if run.MATRIX_KIND not in held or not open_ or (arguments is not None and arguments['inflation'] not in open_):
            return 0.0
        return float(summary['units']['graded_unit'])
    if action_type == 'hold':
        return 0.0
    raise ValueError('all_vs_all_unknown_action_type:' + str(action_type))
