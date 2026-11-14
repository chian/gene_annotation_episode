"""Own-axis recorded resource and received-value presentation; selects no work."""
from ..received_blast_job_information import blast_scientific_owner, blast_axis_summaries
from ..execution_resource_information import resource_information_for_id, execution_capabilities
from copy import deepcopy
import json
KINDS = {'local': 'local', 'pbs_ssh': 'hpc', 'hmmer_api': 'api', 'api': 'api'}

class RecordedExecutionInformation:
    def __init__(self, readers):
        self.readers = readers
        self.resources = deepcopy(readers.factory_record["resources"])
        self.initial_information = deepcopy(readers.factory_record["initial_information"])
        self.store, self.run_id = readers.store, readers.run_id
        self.api_execution = readers.api_execution
        self.job_progress_provider = readers.job_progress_provider

    _resource_information = resource_information_for_id

    capabilities = execution_capabilities

    _blast_scientific_owner = blast_scientific_owner

    _blast_axis_summaries = staticmethod(blast_axis_summaries)

def resource_information(readers):
    value = RecordedExecutionInformation(readers)
    return {'execution_resource_capabilities': [value._resource_information(key) for key in value.resources],
        'execution_initial_information': deepcopy(value.initial_information)}

def received_api_information(context, readers):
    return {'received_bvbrc_values': [] if readers.api_execution is None else
        readers.api_execution.received_bvbrc_context(context)}

def _received_blast_information(context, readers):
    value = RecordedExecutionInformation(readers)
    if value.api_execution is None or not any(service.service == "ncbi_blast"
            for service in value.api_execution.services.values()):
        return None
    jobs = value.api_execution.received_blast_jobs(context, value.job_progress_provider)
    for job in jobs:
        job.update(value._blast_scientific_owner(job["origin_episode_id"]))
    return value, jobs

def annotation_blast_information(context, readers):
    received = _received_blast_information(context, readers)
    if received is None:
        return {}
    value, jobs = received
    return {"received_blast_jobs": value._blast_axis_summaries(jobs),
        "received_blast_jobs_meaning": 'Saved original BLAST jobs for received handoffs; root sees one summary per annotation, axis and subject, while the scientific owner sees its original handles. Status is only as of observed_at; the scheduling estimate is recalculated locally as of forecast_as_of without a new provider observation. No status request is made to build this view. The scientific owner can work locally or return its handoff upward; the annotation root can choose another axis. A later owner may monitor or fetch the same handoff without a new submission. Waiting earns no scientific credit.'}

def scientific_blast_information(context, readers):
    received = _received_blast_information(context, readers)
    if received is None:
        return {}
    _, jobs = received
    return {"received_blast_jobs": jobs,
        "received_blast_jobs_meaning": 'Saved original BLAST jobs for received handoffs; root sees one summary per annotation, axis and subject, while the scientific owner sees its original handles. Status is only as of observed_at; the scheduling estimate is recalculated locally as of forecast_as_of without a new provider observation. No status request is made to build this view. The scientific owner can work locally or return its handoff upward; the annotation root can choose another axis. A later owner may monitor or fetch the same handoff without a new submission. Waiting earns no scientific credit.'}

def received_rna_information(context, readers):
    if readers.native_rna_structure_returns is None:
        return {}
    return {"received_rna_structure_values": readers.native_rna_structure_returns.received_context(context),
        "received_rna_comparison_values": readers.rna_structure_comparison_returns.received_context(context)}
