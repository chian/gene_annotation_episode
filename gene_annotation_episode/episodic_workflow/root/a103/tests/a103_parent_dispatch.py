"""Explicit query selection for the scripted parent in the real A103 harness.

This does not grade evidence or predict a function. The native search still
runs through the A101 sibling and searches the declared complete panel.
"""
from __future__ import annotations

import hashlib
import json
import re


def pending_sequence_requests(store, target, known, attachments, needs, *, submitted_queries=(),native_component_refs=()):
    known = set(known)
    submitted_queries = set(submitted_queries)
    native_component_refs = set(native_component_refs)
    sequences = {}

    def sequence(ref):
        if not isinstance(ref,str) or ref not in known:
            return None
        if ref not in sequences:
            row = store.get(ref)
            sequences[ref] = (store.get_artifact(row['sequence_ref']).decode('ascii').strip().upper()
                if row.get('sequence_ref') and store.subject_molecule(ref)=='protein' else None)
        return sequences[ref]

    target_sequence = sequence(target)
    explicit, legacy, inferred = [], [], []
    measurement_needs = {}
    for need_ref, need in needs:
        if need_ref not in known:
            continue
        required = need.get('required_information','')
        try:
            structured = json.loads(required)
        except (TypeError, ValueError):
            structured = None
        if isinstance(structured,dict):
            if structured.get('measurement_or_request_ref'):
                measurement_needs[structured['measurement_or_request_ref']] = need_ref
            operands = structured.get('required_operands',[])
            for operand in operands if isinstance(operands,list) else []:
                if isinstance(operand,dict) and operand.get('use')=='partner_in_exact_neighborhood':
                    explicit.append((operand.get('query_ref'),operand.get('actual_component_ref'),
                        need_ref,operand.get('neighborhood_ref'),'scoped_component_detection'))
            continue
        text = need.get('question','')+' '+required
        if not re.search(r'sequence|align|homolog|correspond|domain',text,re.I):
            continue
        available = set(need.get('available_record_refs',[]))
        supplied = sorted(ref for ref in available if sequence(ref) is not None)
        actual_components = [ref for ref in supplied if ref in native_component_refs]
        if actual_components:
            explicit.extend((ref,None,need_ref,None,'received_genomic_component_identification')
                for ref in actual_components)
            legacy.extend((target,ref,need_ref,None,'requested_target_correspondence')
                for ref in supplied if ref not in native_component_refs and ref!=target)
        elif len(supplied)==1 and re.search(r'\b(?:search(?:es)?|screen(?:ing)?|phmmer|blastp?)\b',text,re.I):
            # A real BioY request supplied the BioN-family query explicitly.
            # Replacing it with the annotation target changes the experiment.
            explicit.append((supplied[0],None,need_ref,None,'explicit_received_search_query'))
        else:
            available.update(re.findall(r'(?:reference|product|input)_[a-f0-9]{24,64}',text))
            legacy.extend((target,ref,need_ref,None,'requested_target_correspondence')
                for ref in sorted(available) if ref!=target and sequence(ref) is not None)

    def links(value, need_ref):
        if isinstance(value,dict):
            if value.get('factor') is None and value.get('actual_subject_ref') and value.get('reference_subject_ref'):
                inferred.append((value['actual_subject_ref'],value['reference_subject_ref'],need_ref,None,
                    'specific_native_sequence_correspondence'))
            for child in value.values():
                links(child,need_ref)
        elif isinstance(value,list):
            for child in value:
                links(child,need_ref)

    for attachment in attachments:
        if attachment.get('target_ref')==target:
            links(attachment,measurement_needs.get(attachment['measurement_ref']))

    requests = {}
    for query, reference, need_ref, neighborhood, purpose in [*explicit,*inferred,*legacy]:
        peptide = sequence(query)
        if peptide is None:
            continue
        if reference is not None and sequence(reference) is None:
            if purpose=='scoped_component_detection':
                reference = None  # This search requires its query and panel, not an unreceived candidate sequence.
            else:
                continue
        if neighborhood is not None and neighborhood not in known:
            continue
        key = hashlib.sha256(peptide.encode('ascii')).hexdigest()
        if key in submitted_queries:
            continue
        canonical_query = target if target_sequence is not None and peptide==target_sequence else query
        request = requests.setdefault(key,{'query_ref':canonical_query,'query_sequence_sha256':key,
            'requested_query_refs':[],'reference_refs':[],'neighborhood_refs':[],
            'need_refs':[],'purposes':[],'evidence_refs':[]})
        for field,values in (
            ('requested_query_refs',[query]),('reference_refs',[reference]),
            ('neighborhood_refs',[neighborhood]),('need_refs',[need_ref]),('purposes',[purpose]),
            ('evidence_refs',[canonical_query,query,reference,neighborhood]),
        ):
            request[field].extend(value for value in values if value is not None and value not in request[field])
    return list(requests.values())
