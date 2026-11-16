"""Saved-sheet recalculation and saved-result validation with I/O disabled."""
from copy import deepcopy
import builtins
import io
import os
from pathlib import Path
import socket
import subprocess

from gene_annotation_episode.episodic_workflow.root.library import bvbrc_msa_formats, xmfa_formats, bvbrc_msa_xmfa_inputs
from gene_annotation_episode.episodic_workflow.root.library import phylogeny_formats
from test_bvbrc_msa_provider import native_operands, parse_msa_frequency_table, parameters, entropy_request, extract_msa_sheet, calculate_msa


def forbid(*args,**kwargs):
    raise AssertionError('saved provider operation attempted I/O, parsing or a forbidden calculation')


def block_io(monkeypatch):
    for target,names in [(builtins,['open']),(io,['open']),(Path,['open','read_text','read_bytes','write_text','write_bytes']),
        (os,['open','read','write','stat','listdir','scandir','system']),(socket,['socket','create_connection','getaddrinfo']),
        (subprocess,['run','Popen','check_output','check_call','call'])]:
        for name in names:
            monkeypatch.setattr(target,name,forbid)
    for module,names in [(bvbrc_msa_formats,['parse_msa_frequency_table']),(phylogeny_formats,['parse_aligned_fasta','parse_newick']),
        (xmfa_formats,['parse_mauve_xmfa']),(bvbrc_msa_xmfa_inputs,['verify_xmfa_source_inputs','extract_msa_xmfa_bindings','parse_aligned_fasta'])]:
        for name in names:
            monkeypatch.setattr(module,name,forbid)


def test_changed_parameters_recalculate_without_mutating_native_data(monkeypatch):
    op,table=native_operands(); sheet=extract_msa_sheet(**op)['value']; saved=deepcopy(sheet)
    original=parameters(entropy_request(table=table)); changed=deepcopy(original); changed['requests'][0]['native_rounding']=None
    with monkeypatch.context() as guard:
        block_io(guard)
        before=calculate_msa(sheet,original); after=calculate_msa(sheet,changed)
    a,b=before['results'][0]['value'],after['results'][0]['value']
    assert a['sites'][1]['native_score_recalculated']['value']==92
    assert b['sites'][1]['native_score_recalculated']['state']=='not_measured'
    assert a['sites'][1]['literal_entropy_bits']==b['sites'][1]['literal_entropy_bits']
    assert sheet==saved


