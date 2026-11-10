"""Resume the original interrupted science with bounded serial model processes.

The original source snapshot, request, scientific actions and numerical policy
stay unchanged. This explicit local-resource adapter retires each model worker
after its decision; the original runtime restores its complete visible history.
"""
from __future__ import annotations

import argparse
import ast
import asyncio
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def bind_method_super(function, class_name):
    """Preserve the original class binding when a method is compiled alone."""
    receiver = function.args.args[0].arg
    class ExplicitSuper(ast.NodeTransformer):
        def visit_Call(self, node):
            node = self.generic_visit(node)
            if isinstance(node.func, ast.Name) and node.func.id == 'super' and not node.args and not node.keywords:
                node.args = [ast.Name(id=class_name, ctx=ast.Load()), ast.Name(id=receiver, ctx=ast.Load())]
            return node
    return ast.fix_missing_locations(ExplicitSuper().visit(function))


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case-directory', type=Path, required=True)
    parser.add_argument('--repair-axis-publication', action='store_true')
    parser.add_argument('--native-reader-intake', action='store_true')
    parser.add_argument('--refresh-resource-policy', action='store_true')
    parser.add_argument('--parent-wait-availability', action='store_true')
    parser.add_argument('--repair-monitor-control', action='store_true')
    parser.add_argument('--repair-native-scope', action='store_true')
    parser.add_argument('--repair-parent-guidance', action='store_true')
    parser.add_argument('--repair-closed-replay', action='store_true')
    parser.add_argument('--repair-relationship-correspondence', action='store_true')
    parser.add_argument('--integrated', action='store_true')
    args = parser.parse_args()
    case = args.case_directory.resolve()
    source = case.parent/'source'
    sys.path.insert(0, str(source))
    import gene_annotation_episode.workflow_budget as original_budget
    policy = None
    if args.refresh_resource_policy:
        current = load('gene_annotation_episode.a104_current_environment_policy',
                       root/'gene_annotation_episode/workflow_budget.py')
        original_budget.ENVIRONMENT_BOUNDS = dict(current.ENVIRONMENT_BOUNDS)
        # Refresh the environmental checks together with their current policy.
        # The explicit opt-in leaves the saved scientific runtime and decisions
        # unchanged.
        original_budget.active_budget = current.active_budget
        original_budget.native_budget = current.native_budget
        policy = {'bounds': dict(current.ENVIRONMENT_BOUNDS),
                  'verification_callables': ['active_budget', 'native_budget'],
                  'source_sha256': hashlib.sha256((root/'gene_annotation_episode/workflow_budget.py').read_bytes()).hexdigest()}
    run = Path(original_budget.active_budget()['run_directory'])
    adapter_path = run/'serial_model_resources.py'
    shutil.copy2(root/'gene_annotation_episode/serial_model_resources.py', adapter_path)
    adapter = load('gene_annotation_episode.a104_resume_resources', adapter_path)
    original = load('a104_original_scientific_driver', source/'examples/a104_evolutionary_investigation.py')
    original.ModelConnection = adapter.SerialModelConnection
    register = original.register_resume
    def register_adapter(directory, repository, payload, schedule):
        command = ['/usr/bin/env', 'PYTHONPATH='+str(root), sys.executable, '-B', str(Path(__file__).resolve()),
            '--case-directory', str(case)]
        for flag in ('refresh_resource_policy', 'repair_axis_publication', 'native_reader_intake',
                     'parent_wait_availability', 'repair_monitor_control', 'repair_native_scope',
                     'repair_parent_guidance', 'repair_closed_replay', 'repair_relationship_correspondence', 'integrated'):
            if getattr(args, flag):
                command.append('--'+flag.replace('_', '-'))
        return register(directory, repository, command, schedule)
    original.register_resume = register_adapter
    repair = None
    if args.repair_axis_publication:
        import gene_annotation_episode.runtime as runtime
        tree = ast.parse((root/'gene_annotation_episode/runtime.py').read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Workflow')
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'publish_axis_information')
        repair_path = run/'axis_publication_repair.py'
        repair_path.write_text(ast.unparse(method)+'\n')
        namespace = dict(vars(runtime))
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(repair_path), 'exec'), namespace)
        runtime.Workflow.publish_axis_information = namespace['publish_axis_information']
        repair = {'method': 'Workflow.publish_axis_information',
                  'sha256': hashlib.sha256(repair_path.read_bytes()).hexdigest(),
                  'change': 'canonical_evidence_set_order; reuse_exact_existing_immutable_request'}
    monitor_repair = None
    if args.repair_monitor_control:
        import gene_annotation_episode.hpc_episodes as hpc
        tree = ast.parse((root/'gene_annotation_episode/hpc_episodes.py').read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'HPCEpisodes')
        method = next(node for node in cls.body if isinstance(node, ast.AsyncFunctionDef) and node.name == 'execute')
        repair_path = run/'monitor_control_repair.py'
        repair_path.write_text(ast.unparse(method)+'\n')
        namespace = dict(vars(hpc))
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(repair_path), 'exec'), namespace)
        hpc.HPCEpisodes.execute = namespace['execute']
        monitor_repair = {'method': 'HPCEpisodes.execute',
            'sha256': hashlib.sha256(repair_path.read_bytes()).hexdigest(),
            'change': 'missing_monitor_controller_returns_recorded_recovery_feedback; original_job_and_commission_retained'}
    scope_repair = None
    if args.repair_native_scope:
        import gene_annotation_episode.a104_hpc as hpc_reader
        import gene_annotation_episode.a104_tools as a104_tools
        tree = ast.parse((root/'gene_annotation_episode/a104_hpc.py').read_text())
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'import_result')
        repair_path = run/'native_scope_repair.py'
        repair_path.write_text(ast.unparse(function)+'\n')
        namespace = dict(vars(hpc_reader))
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(repair_path), 'exec'), namespace)
        hpc_reader.import_result = a104_tools.import_result = namespace['import_result']
        scope_repair = {'function': 'a104_hpc.import_result',
            'sha256': hashlib.sha256(repair_path.read_bytes()).hexdigest(),
            'change': 'mutual_scope_containment_for_equivalent_geometry; exact_original_ledger_receipt_and_native_bytes_required'}
    replay_repair = None
    if args.repair_closed_replay:
        import gene_annotation_episode.runtime as runtime
        tree = ast.parse((root/'gene_annotation_episode/runtime.py').read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Workflow')
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == '_closed_child_commission')
        repair_path = run/'closed_replay_repair.py'
        repair_path.write_text(ast.unparse(method)+'\n')
        namespace = dict(vars(runtime))
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(repair_path), 'exec'), namespace)
        runtime.Workflow._closed_child_commission = namespace['_closed_child_commission']
        replay_repair = {'method': 'Workflow._closed_child_commission',
            'sha256': hashlib.sha256(repair_path.read_bytes()).hexdigest(),
            'change': 'authenticate_original_receiver_attributions_against_frozen_completion_evidence; no_regrading_or_new_receipts'}
    correspondence_repair = None
    if args.repair_relationship_correspondence:
        import gene_annotation_episode.a104_scoring as scoring
        import gene_annotation_episode.a104_interpretation as interpretation
        import gene_annotation_episode.a104_tools as tool_module
        repairs = []
        for module, class_name, function_name in (
                (scoring, None, 'relationship_inventory'),
                (interpretation, None, 'compare_placements'),
                (tool_module, 'A104ToolRegistry', 'execute_async')):
            tree = ast.parse((root/'gene_annotation_episode'/Path(module.__file__).name).read_text())
            nodes = (next(node for node in tree.body if isinstance(node, ast.ClassDef)
                          and node.name == class_name).body if class_name else tree.body)
            function = next(node for node in nodes if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                            and node.name == function_name)
            if class_name:
                function = bind_method_super(function, class_name)
            path = run/('relationship_'+function_name+'.py')
            path.write_text(ast.unparse(function)+'\n')
            namespace = dict(vars(module))
            exec(compile(ast.Module(body=[function], type_ignores=[]), str(path), 'exec'), namespace)
            setattr(getattr(module, class_name) if class_name else module, function_name, namespace[function_name])
            repairs.append({'function': module.__name__+'.'+(class_name+'.' if class_name else '')+function_name,
                            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        correspondence_repair = {'functions': repairs,
            'change': 'native_member_identity_branch_inventory; reject_distinct_compatible_edges_as_replicates; '
                      'retain_original_native_outputs_and_prior_records'}
    intake = None
    if args.native_reader_intake or args.parent_wait_availability or args.repair_parent_guidance:
        from copy import deepcopy
        helper_tree = ast.parse((root/'gene_annotation_episode/a104_investigation.py').read_text())
        helper = next(node for node in helper_tree.body if isinstance(node, ast.FunctionDef)
                      and node.name == 'parent_generation_schema')
        helper_path = run/'parent_generation_schema.py'
        helper_path.write_text(ast.unparse(helper)+'\n')
        helper_namespace = {'deepcopy': deepcopy}
        exec(compile(ast.Module(body=[helper], type_ignores=[]), str(helper_path), 'exec'), helper_namespace)
        original.parent_generation_schema = helper_namespace['parent_generation_schema']
        tree = ast.parse((root/'examples/a104_evolutionary_investigation.py').read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'CommissionedParent')
        method = next(node for node in cls.body if isinstance(node, ast.AsyncFunctionDef) and node.name == 'complete')
        intake_path = run/'native_reader_intake.py'
        intake_path.write_text(ast.unparse(method)+'\n')
        namespace = dict(vars(original))
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(intake_path), 'exec'), namespace)
        original.CommissionedParent.complete = namespace['complete']
        intake = {'sha256': hashlib.sha256(intake_path.read_bytes()).hexdigest(),
                  'parent_generation_sha256': hashlib.sha256(helper_path.read_bytes()).hexdigest(),
                  'change': 'decode_received_native_sources; offer_parent_waits_only_for_actual_pending_work; '
                    'explicit_closed_child_form_contract_and_distinct_followup_guidance; no_new_native_job_or_credit'}
    (run/'RESUME.json').write_text(json.dumps({'case_directory': str(case),
        'original_source_snapshot_unchanged': str(source),
        'resource_adapter_sha256': hashlib.sha256(adapter_path.read_bytes()).hexdigest(),
        'axis_publication_repair': repair,
        'monitor_control_repair': monitor_repair,
        'native_scope_repair': scope_repair,
        'closed_replay_repair': replay_repair,
        'relationship_correspondence_repair': correspondence_repair,
        'native_reader_intake': intake,
        'environment_policy': policy,
        'scientific_policy': 'original; no_new_native_job_or_stopping_budget'}, indent=2)+'\n')
    asyncio.run(original.run(argparse.Namespace(case_directory=case, repository_root=root,
        model_config=None, integrated=args.integrated)))


if __name__ == '__main__':
    main()
