"""Fresh private scientific descriptors must permit their original execution.

Assignment/preparation authority is separately controlled in the dispatch test;
the descriptor, compatibility check and execution-identity gate are actual.
"""
from copy import deepcopy
from types import SimpleNamespace

import pytest
from .test_private_sample_context_evidence import scientific_binding
from gene_annotation_episode.episodic_workflow.root.a108.episode_composition import scientific_binding_compatible
from gene_annotation_episode.episodic_workflow.root.a108.domain import ContractError


def test_fresh_private_scientific_descriptor_accepts_its_exact_identity():
    record=scientific_binding().as_record()
    assert scientific_binding_compatible(record,deepcopy(record))


def test_fresh_execution_identity_gate_accepts_current_private_descriptor():
    binding=scientific_binding();record=binding.as_record();validated=[]
    binding.validate_context=lambda context:validated.append(context)
    binding.restore_closed_process=lambda context:None
    context=SimpleNamespace(request={'message':{'sample_context_evidence':{'mechanics_binding':record}}})
    binding.validate_execution_context(context)
    assert validated==[context]


def test_changed_scientific_configuration_is_not_accepted_as_exact():
    record=scientific_binding().as_record();different=deepcopy(record)
    different['configuration']['child_roles']=['sample_context_evidence']
    assert not scientific_binding_compatible(record,different)
