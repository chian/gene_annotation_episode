"""Original standalone scientific-credit protocol."""
from ..communication import plain

def scientific_credit(services, context, receiver_selection):
        workflow = services.workflow
        local = len(context.path) > 1
        projector = workflow.scientific_projector_for_context(context)
        arguments = {}
        if local:
            request = context.request
            contract = request['report_contract']
            arguments.update(assignment={'goal': plain(request['goal']), 'scope': plain(context.scope), 'purpose': contract['decision'], 'schema': plain(contract['measurements']['schema']), 'initial_report': plain(request['message']['initial_report'])}, episode_id=context.episode_id, run_id=context.run_id)
            annotation = services.proposed_annotation_for(context)
            if annotation is not None:
                arguments['assignment']['proposed_annotation_ref'] = annotation
            elif services.annotation_task_required():
                raise ValueError('scientific_task_requires_original_proposed_annotation')
        arguments.update(workflow.projector_receipt_arguments(projector, context.episode_id))
        result = workflow.projection_view(projector, plain(context.scope), **arguments)
        if local and arguments['assignment'].get('proposed_annotation_ref') is not None:
            result['proposed_annotation_ref'] = arguments['assignment']['proposed_annotation_ref']
        return result
