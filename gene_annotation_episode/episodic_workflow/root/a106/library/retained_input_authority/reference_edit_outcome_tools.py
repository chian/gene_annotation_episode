"""Ordinary retained reference/edit analysis, without a native worker.

Only actual selected actions and admitted records may supply the pure kernel.
Public Source bytes contain the public value packet; raw captures and input
strings remain in private custody. Reading a Source never grants its Files.
"""
from copy import deepcopy
from gene_annotation_episode.episodic_workflow.root.a106.library.retained_input_authority import reference_edit_outcomes as core

def reference_edit_outcome_fact_sources():
    """The exact public group; only its result Source is a semantic reference."""
    return {'reference_edit_outcomes': dict(type='array', meaning='Recorded reference/edited nucleotide outcome groups, preserving ordered submitted occurrences, selected native correspondence, observed edit types, explicit gap bins, supplied guide/template comparisons, units, missingness and declared versus classified populations; these values do not infer repair mechanisms.', report_schema=dict(type='array', items=deepcopy(core.RETURN_SCHEMA), **{'x-source': 'reference_edit_outcomes'}))}
