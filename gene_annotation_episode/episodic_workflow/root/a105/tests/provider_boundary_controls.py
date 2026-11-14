"""Exact retained call/method boundaries with controlled provider operands only."""
import ast
import asyncio
import builtins
from copy import deepcopy
from types import MethodType, SimpleNamespace

def one(items): value, = items; return value
def form(node): return ast.dump(node, include_attributes=False)
def owner(raw, name): return one(n for n in ast.parse(raw).body if isinstance(n, ast.ClassDef) and n.name == name)
def method(cls, name): return one(n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
def compiled(node, namespace):
    exec(compile(ast.fix_missing_locations(ast.Module(body=[deepcopy(node)], type_ignores=[])), '<authenticated-controlled-method>', 'exec'), namespace)
    return namespace[node.name]
def exercise(axis, original_runtime_bytes, provider_before_bytes, provider_after_bytes,
             original_private_bytes, corrected_private_bytes, owner_name):
    assert __debug__ and axis == 'a105'
    original_provider = owner(provider_before_bytes, 'ModelConnection')
    assert form(original_provider) == form(owner(provider_after_bytes, 'ModelConnection'))
    provider_methods = [method(original_provider, n) for n in ('complete', 'complete_with_presentation')]
    captures = ast.parse(provider_after_bytes).body
    at = one(i for i,n in enumerate(captures) if isinstance(n,ast.ClassDef) and n.name == 'ModelConnection')
    capture_nodes = captures[at+1:at+4]
    expected = ast.parse("_ORIGINAL_MODEL_COMPLETE = ModelConnection.complete\n_ORIGINAL_MODEL_COMPLETE_WITH_PRESENTATION = ModelConnection.complete_with_presentation\n_ORIGINAL_MODEL_INSTANCE_DICT = ModelConnection.__dict__['__dict__']\n").body
    assert list(map(form,capture_nodes)) == list(map(form,expected))
    current_owner = owner(original_private_bytes, owner_name); fixed_owner = owner(corrected_private_bytes, owner_name)
    current = method(current_owner,'complete_decision'); fixed = method(fixed_owner,'decision_completion')
    assert isinstance(current,ast.AsyncFunctionDef) and isinstance(fixed,ast.FunctionDef)
    calls = {}
    for name in ('call','exchange_decision'):
        original_method = one(n for n in ast.walk(ast.parse(original_runtime_bytes)) if isinstance(n,ast.AsyncFunctionDef) and n.name == name
            and any(isinstance(c,ast.Call) and ast.unparse(c.func) == 'self.workflow.provider.complete' for c in ast.walk(n)))
        original = one(n for n in ast.walk(original_method) if isinstance(n,ast.Call) and ast.unparse(n.func) == 'self.workflow.provider.complete')
        before_call = one(n for n in ast.walk(method(current_owner,name)) if isinstance(n,ast.Call) and ast.unparse(n.func) == 'self.complete_decision')
        after_call = one(n for n in ast.walk(method(fixed_owner,name)) if isinstance(n,ast.Call) and ast.unparse(n.func) == 'self.decision_completion()')
        assert len(original.args) == 5 and not original.keywords and not before_call.keywords and not after_call.keywords
        assert list(map(form,before_call.args)) == list(map(form,original.args[2:]))
        assert list(map(form,after_call.args)) == list(map(form,original.args))
        calls[name] = {'original':original,'current':before_call,'fixed':after_call}
    scenarios = ('default','subclass_complete','instance_complete','base_complete','callable_complete',
        'subclass_presentation','instance_presentation','base_presentation','custom_complete_forbidden_presentation_lookup',
        'raising_presentation_property','side_effect_presentation_descriptor','instance_original_function_shadow',
        'raising_instance_dict','unrelated_borrowed_complete','custom_dict_contains','colliding_nonstring_key','raising_metaclass_dict')
    arrangements = [(name,raises) for name in scenarios for raises in (False,True)] + [
        ('raising_complete_before_schema',False),('schema_mutates_provider',False),('schema_mutates_episode',False)]
    records = []
    root_imports = []; provider_class_proofs = []
    for call_name, expressions in calls.items():
        for scenario, raises in arrangements:
            shared_result = object(); alternate_result = object(); shared_error = RuntimeError('completion sentinel')
            getter_error = LookupError('complete getter sentinel'); schema_error = ValueError('schema sentinel')
            descriptor_error = LookupError('descriptor sentinel'); observations = {}
            for variant in ('original','current','fixed'):
                events = []; operand_checks = []; operands = [object(),object(),object()]
                episode = object(); changed_episode = object(); renderer = object()
                ns = {'__builtins__':builtins.__dict__}
                compiled(ast.ClassDef(name='ModelConnection',bases=[],keywords=[],body=deepcopy(provider_methods),decorator_list=[]),ns)
                for declaration in capture_nodes:
                    exec(compile(ast.fix_missing_locations(ast.Module(body=[deepcopy(declaration)],type_ignores=[])), '<captured-real-defaults>','exec'),ns)
                base = ns['ModelConnection']
                provider_class_proofs.append(base is ns['ModelConnection'] and all(
                    vars(base)[name].__globals__ is ns
                    and vars(base)[name].__code__.co_filename == '<authenticated-controlled-method>'
                    for name in ('complete', 'complete_with_presentation')))
                def tracked_get(self,name):
                    if name in ('complete','complete_with_presentation'):
                        events.append('get_'+name)
                        if name == 'complete' and scenario == 'raising_complete_before_schema': raise getter_error
                        if name == 'complete_with_presentation' and scenario == 'custom_complete_forbidden_presentation_lookup': raise descriptor_error
                    return object.__getattribute__(self,name)
                attributes = {'__getattribute__':tracked_get}
                if scenario == 'raising_instance_dict':
                    def raising_dict(self): events.append('instance_dict_property');raise descriptor_error
                    attributes['__dict__'] = property(raising_dict)
                class Meta(type):
                    def __getattribute__(self,name):
                        if name == '__dict__': events.append('metaclass_dict');raise descriptor_error
                        return type.__getattribute__(self,name)
                Tracking = (Meta if scenario == 'raising_metaclass_dict' else type)('Tracking',(base,),attributes)
                def check_operands(episode_id,role,instructions,context,output_schema):
                    operand_checks.append(episode_id is episode and role == 'REASONING' and all(a is b for a,b in zip((instructions,context,output_schema),operands)))
                async def custom_complete(self,episode_id,role,instructions,context,output_schema):
                    check_operands(episode_id,role,instructions,context,output_schema);events.append('custom_complete')
                    if raises: raise shared_error
                    return shared_result
                async def custom_presentation(self,*args,**kwargs):
                    check_operands(*args);events.append('custom_presentation')
                    if raises: raise shared_error
                    return shared_result
                if scenario in ('subclass_complete','custom_complete_forbidden_presentation_lookup'): Tracking.complete=custom_complete
                if scenario == 'base_complete': base.complete=custom_complete
                if scenario == 'subclass_presentation': Tracking.complete_with_presentation=custom_presentation
                if scenario == 'base_presentation': base.complete_with_presentation=custom_presentation
                if scenario == 'raising_presentation_property':
                    def raising_property(self): events.append('presentation_property');raise descriptor_error
                    Tracking.complete_with_presentation=property(raising_property)
                if scenario == 'side_effect_presentation_descriptor':
                    class Descriptor:
                        def __get__(self,instance,kind):
                            events.append('presentation_descriptor');return MethodType(custom_presentation,instance)
                    Tracking.complete_with_presentation=Descriptor()
                provider = Tracking()
                if scenario == 'unrelated_borrowed_complete':
                    Other=type('Unrelated',(),{'__getattribute__':tracked_get});provider=Other()
                    provider.complete=MethodType(ns['_ORIGINAL_MODEL_COMPLETE'],provider)
                    provider.complete_with_presentation=MethodType(ns['_ORIGINAL_MODEL_COMPLETE_WITH_PRESENTATION'],provider)
                if scenario == 'instance_complete': provider.complete=MethodType(custom_complete,provider)
                if scenario == 'instance_presentation': provider.complete_with_presentation=MethodType(custom_presentation,provider)
                if scenario == 'instance_original_function_shadow': provider.complete_with_presentation=ns['_ORIGINAL_MODEL_COMPLETE_WITH_PRESENTATION']
                if scenario == 'callable_complete':
                    class Callable:
                        async def __call__(self,*args): return await custom_complete(provider,*args)
                    provider.complete=Callable()
                class Lock:
                    async def __aenter__(self):events.append('lock_enter')
                    async def __aexit__(self,*args):events.append('lock_exit')
                async def serial(self,episode_id,role,instructions,context,output_schema,**kwargs):
                    check_operands(episode_id,role,instructions,context,output_schema)
                    assert not kwargs or kwargs == {'prompt_renderer':renderer}
                    events.append('serial_with_renderer' if kwargs else 'serial_original')
                    if raises: raise shared_error
                    return shared_result
                provider.worker_lock=Lock();provider._complete_serial=MethodType(serial,provider)
                if scenario == 'custom_dict_contains':
                    class CustomDict(dict):
                        def __contains__(self,key): events.append('custom_contains');raise descriptor_error
                    provider.__dict__ = CustomDict(ns['_ORIGINAL_MODEL_INSTANCE_DICT'].__get__(provider))
                if scenario == 'colliding_nonstring_key':
                    class Collision:
                        def __hash__(self): return hash('complete_with_presentation')
                        def __eq__(self,value): events.append('custom_key_equality');return False
                    ns['_ORIGINAL_MODEL_INSTANCE_DICT'].__get__(provider)[Collision()] = object()
                def specialist(source):events.append('specialist');return SimpleNamespace(decision_prompt_renderer=renderer)
                source=SimpleNamespace(episode_id=episode,workflow=SimpleNamespace(provider=provider,specialist=specialist))
                async def replacement_complete(*args):events.append('replacement_complete');return alternate_result
                replacement_provider=SimpleNamespace(complete=replacement_complete)
                def project(value):
                    assert value is operands[2];events.append('schema_operand')
                    if scenario == 'raising_complete_before_schema':raise schema_error
                    if scenario == 'schema_mutates_provider':source.workflow.provider=replacement_provider
                    if scenario == 'schema_mutates_episode':source.episode_id=changed_episode
                    return value
                class Request:
                    def __getitem__(self,key):
                        events.append('request_'+key)
                        return project(operands[2]) if key == 'output_schema' else operands[{'instructions':0,'context':1}[key]]
                import_name=f'gene_annotation_episode.episodic_workflow.root.{axis}.providers'
                original_import=builtins.__import__
                def importer(name,globals=None,locals=None,fromlist=(),level=0):
                    if name == import_name:
                        assert level == 0 and tuple(fromlist) == ('_ORIGINAL_MODEL_COMPLETE','_ORIGINAL_MODEL_COMPLETE_WITH_PRESENTATION','_ORIGINAL_MODEL_INSTANCE_DICT')
                        return SimpleNamespace(**{key:ns[key] for key in fromlist})
                    if name == 'gene_annotation_episode.episodic_workflow.root.providers':
                        root_names = ('_ORIGINAL_MODEL_COMPLETE', '_ORIGINAL_MODEL_COMPLETE_WITH_PRESENTATION',
                            '_ORIGINAL_MODEL_COMPLETE_SERIAL', '_ORIGINAL_MODEL_INSTANCE_DICT',
                            '_ORIGINAL_MODEL_SESSION_TYPE', '_ORIGINAL_SESSION_COMPLETE', '_ORIGINAL_SESSION_PRESENTATION')
                        assert level == 0 and tuple(fromlist) == root_names
                        module = original_import(name, globals, locals, fromlist, level)
                        from pathlib import Path
                        import hashlib
                        root_file = Path(__file__).absolute().parents[2] / 'providers.py'
                        session_file = root_file.with_name('model_session.py')
                        assert module.__name__ == name and Path(module.__file__).absolute() == root_file
                        assert hashlib.sha256(root_file.read_bytes()).hexdigest() == '5196484b900d37500734f1725e58ad7ffa87bc16797a3408315ec590adf99aa9'
                        assert hashlib.sha256(session_file.read_bytes()).hexdigest() == '6d118158a5e6f8be4b3afa1afbbd09d1f7d328763e5100ec81a267daee59fc34'
                        session = module._ORIGINAL_MODEL_SESSION_TYPE
                        assert session.__module__ == 'gene_annotation_episode.episodic_workflow.root.model_session'
                        identities = (module.ModelConnection.complete, module.ModelConnection.complete_with_presentation,
                            module.ModelConnection._complete_serial, vars(module.ModelConnection)['__dict__'],
                            module.ModelConnection.session_type, session.complete, session._presentation)
                        assert all(vars(module)[key] is value for key, value in zip(root_names, identities, strict=True))
                        root_imports.append(dict(module=module.__name__, path=str(root_file),
                            sha256=hashlib.sha256(root_file.read_bytes()).hexdigest(),
                            session_module=session.__module__, session_path=str(session_file),
                            session_sha256=hashlib.sha256(session_file.read_bytes()).hexdigest(),
                            capture_names=list(root_names), captures_match_defining_owners=True))
                        return module
                    assert level == 0 and ((name == 'types' and tuple(fromlist) == ('MethodType',)) or (name == 'inspect' and tuple(fromlist) == ('getattr_static',)))
                    return original_import(name,globals,locals,fromlist,level)
                execution={'__builtins__':{**builtins.__dict__,'__import__':importer},'_action_generation_schema':project}
                if variant != 'original':
                    helper=compiled(current if variant == 'current' else fixed,execution)
                    setattr(source,helper.__name__,MethodType(helper,source))
                wrapper=ast.parse('async def invoke(self,instructions,context,schema,request):\n return None').body[0]
                wrapper.body[0]=ast.Return(ast.Await(deepcopy(expressions[variant])))
                invoke=compiled(wrapper,execution)
                events.clear()
                try:
                    answer=asyncio.run(invoke(source,*operands,Request()))
                    assert answer is shared_result or (variant == 'current' and scenario == 'schema_mutates_provider' and answer is alternate_result)
                    outcome='return_identity' if answer is shared_result else 'introduced_changed_provider'
                except BaseException as error:
                    if error is shared_error:outcome='exception_identity'
                    elif error is getter_error:outcome='getter_exception_identity'
                    elif variant == 'current' and error is schema_error:outcome='introduced_schema_before_getter'
                    elif variant == 'current' and error is descriptor_error:outcome='introduced_descriptor_error'
                    elif variant == 'current' and scenario == 'instance_original_function_shadow' and type(error) is TypeError:outcome='introduced_unbound_presentation_call'
                    else:raise
                observations[variant]={'events':list(events),'outcome':outcome,'operand_identities':list(operand_checks)}
            baseline=observations['original'];corrected=observations['fixed'];old=observations['current']
            assert all(baseline['operand_identities']) and all(corrected['operand_identities'])
            assert 'instance_dict_property' not in corrected['events']
            assert 'get_complete_with_presentation' not in corrected['events']
            assert 'presentation_property' not in corrected['events'] and 'presentation_descriptor' not in corrected['events']
            assert 'custom_contains' not in corrected['events'] and 'custom_key_equality' not in corrected['events']
            assert 'metaclass_dict' not in corrected['events']
            if scenario == 'raising_complete_before_schema':
                assert baseline['outcome'] == corrected['outcome'] == 'getter_exception_identity'
                assert baseline['events'] == corrected['events'] == ['get_complete']
                assert old['outcome'] == 'introduced_schema_before_getter'
            else:
                assert baseline['outcome'] == corrected['outcome'] == ('exception_identity' if raises else 'return_identity')
                args=['schema_operand'] if call_name == 'call' else ['request_instructions','request_context','request_output_schema','schema_operand']
                custom=scenario in ('subclass_complete','instance_complete','base_complete','callable_complete','custom_complete_forbidden_presentation_lookup')
                assert baseline['events'] == ['get_complete',*args,*(['custom_complete'] if custom else ['lock_enter','serial_original','lock_exit'])]
                presented=scenario in ('default','raising_instance_dict','schema_mutates_provider','schema_mutates_episode','custom_dict_contains')
                assert corrected['events'] == (['get_complete',*args,'specialist','lock_enter','serial_with_renderer','lock_exit'] if presented else baseline['events'])
                if custom:assert old['events'] != baseline['events']
                if scenario == 'schema_mutates_provider':assert old['outcome'] == 'introduced_changed_provider'
                if scenario == 'schema_mutates_episode':assert old['operand_identities'] == [False]
            records.append({'axis':axis,'owner':owner_name,'original_call':call_name,'scenario':scenario,'raises':raises,'observations':observations})
    return {'records':records,'controlled_exact_method_boundary':True,
        'controlled_provider_classes_from_captured_source':bool(provider_class_proofs) and all(provider_class_proofs),
        'root_defining_import_observations':root_imports,
        'real_provider_workflow_executed':False,'new_candidate_or_application_authority':False}
