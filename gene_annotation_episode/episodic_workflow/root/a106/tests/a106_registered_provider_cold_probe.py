"""Fresh-process entry orders for actual A106 provider and mixed namespaces."""
import importlib
import json
import sys

PACKAGE = 'gene_annotation_episode.episodic_workflow.root.a106'
ENTRIES = {
    'literature_report': ('published_evidence_assessment', 'report_delivery', 'LiteratureReportDelivery', 'finish'),
    'launch_report': ('execution_job_submission', 'report_delivery', 'OperationalReportDelivery', 'finish'),
    'monitor_report': ('execution_progress_assessment', 'report_delivery', 'MonitorReportDelivery', 'finish'),
    'literature_inputs': ('published_evidence_assessment', 'decision_inputs', 'LiteratureDecisionInputs', 'decision_inputs'),
    'launch_inputs': ('execution_job_submission', 'decision_inputs', 'OperationalDecisionInputs', 'decision_inputs'),
    'monitor_inputs': ('execution_progress_assessment', 'decision_inputs', 'MonitorDecisionInputs', 'decision_inputs'),
    'scientific_builtin': ('scientific_process', 'task_decision', 'ScientificTaskDecision', 'conversation_key'),
}


def main():
    assert len(sys.argv) == 2 and sys.argv[1] in ENTRIES
    home, module, class_name, name = ENTRIES[sys.argv[1]]
    assert PACKAGE + '.runtime' not in sys.modules
    imported = importlib.import_module(PACKAGE + '.' + home + '.' + module)
    runtime = importlib.import_module(PACKAGE + '.runtime')
    function = vars(getattr(imported, class_name))[name]
    assert function.__module__ == imported.__name__ and function.__qualname__ == class_name + '.' + name
    assert function.__closure__ is None
    if name == 'decision_inputs':
        presentation = importlib.import_module(PACKAGE + '.' + home + '.decision_presentation')
        assert function.__globals__ is vars(imported)
        assert imported.prepare_completed_work is presentation.prepare_completed_work
        assert presentation.prepare_completed_work.__globals__ is vars(runtime)
        for provider in ('child_option_information', 'set', 'ValueError'):
            getter = vars(imported)['_a106_original_global_' + provider]
            assert getter.__globals__ is vars(runtime) and getter.__code__.co_names == (provider,)
    else:
        assert function.__globals__ is vars(runtime)
    print(json.dumps({'entry': sys.argv[1], 'home': home, 'member': class_name + '.' + name, 'passed': True}))


if __name__ == '__main__':
    main()
