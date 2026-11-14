"""Pure selected BV-BRC facts and receiver values.

``QualifiedResult`` is a host-established precondition, not an authentication
token: this module cannot establish custody by inspecting JSON flags. It checks
the supplied records' relationships and projects only the frozen selection.
Fact ``collection`` accompanies the publication's source binding. Materialized
cells instead identify their actual input source and collection; these can
differ when the publication joins several collections.
There is no Store, transport, calculator, model, action, credit or prompt here.
Model-facing rendering is deliberately a separate, unfinished boundary.
"""
from __future__ import annotations
from gene_annotation_episode.episodic_workflow.root.a110.library.received_execution_information.historical_bvbrc_data_schema import fact_schemas
_MEANINGS = ('Selected retained response and page coverage; document counts are acquisition metadata.', 'Native matching-document counts with their exact population and availability.', "Native field buckets and saved fractions of the same response's exact document population.", 'Explicitly selected native rows, numerical measurements and source metadata cells.', 'Selected feature occurrences and their recorded AA/NA sequence associations.', 'Selected molecular measurements with recorded result, bioset, experiment and feature relationships.')

def bvbrc_data_fact_sources() -> dict:
    """Detached source descriptors accepted by the existing closed form guard."""
    return {name: {'type': 'array', 'meaning': meaning, 'report_schema': definition} for (name, definition), meaning in zip(fact_schemas().items(), _MEANINGS)}
