"""Credit: ``prepared_unit`` for each usable prepared-data record newly established: a usable record among the rows
the episode holds whose key is not the key of a record the parent passed. A failed or incomplete record, a hold and a
repeat earn nothing. It is read from the rows the episode holds (``records``), not from what a tool said."""
from gene_annotation_episode.episodic_workflow.episode_support.records.similarity_search.sequence_homology_evidence.prepared_data import (
    prepared_credit)


def credit(summary, records):
    return prepared_credit(records, summary['prepared_unit'], known_keys=summary['prior_data_keys'])


def ceiling(summary, records, action_type, arguments, ctx):
    """The most the credit can rise if ``action_type`` with ``arguments`` is the next unit.

    The credit is ``prepared_unit`` for each distinct usable prepared-data key that is not a key the parent passed.
    One commission names one input set and one set of options, hence ONE key, so the whole credit this episode can
    ever reach is ``prepared_unit`` (the target of its yield controller); every launch of the commission builds that
    same key.
    - ``launch_local`` (any ``arguments``, or None): it can newly establish the one usable record, so it can add at
      most what is not yet earned: ``prepared_unit`` minus the credit now (``prepared_unit`` while none is earned,
      0 once the one key is earned, since a repeat of a held key earns nothing). This holds whether or not the call
      would pass the check: a rejected call makes no unit (rise 0, within the bound); a launch whose job fails or is
      incomplete earns nothing.
    - ``hold``: runs nothing and writes no record; it cannot earn: 0.
    Any other action type is not offered and cannot earn: 0."""
    if action_type == 'launch_local':
        return max(0.0, summary['prepared_unit'] - credit(summary, records))
    if action_type == 'hold':
        return 0.0
    return 0.0
