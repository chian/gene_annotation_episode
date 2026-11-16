"""Current private resource binding records."""

def binding_record(binding, identifier, path):
    if binding.binding_path != path or identifier != 'root_'+path.replace('/','_'):
        raise ValueError('resource_binding_identity_conflict')
    return {'binding_id':identifier,'version':identifier+'_v1',
            'configuration':binding.owner.configuration()}
