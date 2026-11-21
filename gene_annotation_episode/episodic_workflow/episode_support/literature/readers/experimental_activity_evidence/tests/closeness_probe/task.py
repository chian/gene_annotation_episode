"""The task: one ``subject_closeness`` call per pair of the commissioned plan, as the A105 page's sheet update makes it (the
episode declares the service ``job_access`` and holds ``blast_executable_directory`` and ``blast_resource_id``). It asks no
model."""
from episode_runtime import Rejected, ToolCall

from gene_annotation_episode.episodic_workflow.episode_support.literature.readers.experimental_activity_evidence.literature_subject_closeness import (
    subject_closeness)

CHILD_SLOTS = {}
SERVICES = ('job_access',)


def idle(arguments, ctx):
    return {'idle': True}


async def compare(arguments, ctx):
    return await subject_closeness(ctx, subject_record_ref=arguments['subject_record_ref'],
                                   target_record_ref=arguments['target_record_ref'])


TOOLS = {'idle': idle, 'compare': compare}


def decide(summary, feedback, ctx):
    step = len(summary['outcomes'])
    if step >= len(summary['plan']):
        return ToolCall('idle', {})
    return ToolCall('compare', summary['plan'][step])


def offered_actions(summary, ctx):
    return ['compare'] if len(summary['outcomes']) < len(summary['plan']) else ['idle']


def action(response, summary, records, ctx):
    raise Rejected('this episode asks no model')
