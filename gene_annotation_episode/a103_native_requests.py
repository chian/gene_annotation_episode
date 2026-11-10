"""Receipt-bound preparation and publication for existing A103 calculations.

These adapters execute no scientific algorithm. They preserve the same inputs,
host provenance and numerical publishers as the original local operations.
"""
from copy import deepcopy
import json

from .a103_publication import binding_body, publish, received_measurement
from .a103_scoring import binding_summary, digest, require
from .domain import canonical


OPERATIONS = ('context.bind_locus', 'reference.neighborhood', 'context.compare_neighborhoods',
    'context.fusion', 'context.detection_inventory', 'context.cooccurrence')


def prepare(registry, name, arguments, *, context, scope, known, invocation):
    args = deepcopy(arguments)
    store = registry.store
    assets, refs = {}, set()

    def received(reference):
        registry._received(reference, known)
        refs.add(reference)

    def file(field, reference, format):
        path, identity = registry._file(reference, format, known, invocation)
        refs.add(reference)
        assets[field] = {'path': str(path), 'identity': identity, 'source_ref': reference}
        return str(path)

    require(name in OPERATIONS, 'a103_hpc_native_operation_required')
    if name == 'reference.neighborhood':
        received(args['binding_ref'])
        locus = binding_body(store, args['binding_ref'], known)
        target, regions = registry._target(locus['target_ref'], known, scope)
        refs.add(locus['target_ref'])
    else:
        target, regions = registry._target(args['target_ref'], known, scope)
        refs.add(args['target_ref'])
    updates = {'target_ref': target, 'target_regions': regions}
    if name == 'context.bind_locus':
        path = file('input_path', args['file_source_ref'], 'genbank_text' if args['format']=='genbank' else 'gff3_text')
        sequence = file('sequence_path', args['sequence_source_ref'], 'fasta_text') if args['sequence_source_ref'] else None
        source = store.get(args['file_source_ref'])
        original = json.loads(store.get_artifact(source['request_ref'])) if source.get('request_ref') else None
        if original and 'request' in original: original = original['request']
        if original and 'params' in original: original = original['params']
        native = {'operation': 'bind', **args, 'target_ref': target, 'input_path': path,
            'sequence_path': sequence, 'source_request': original,
            'query_sequence': registry._sequence(args['target_ref']), 'query_molecule': store.subject_molecule(args['target_ref'])}
        updates.update(material_ref=args['target_ref'], supplied_target_genome=
            args['file_source_ref'] in registry.a103_target_genomic_sources.get(target, []))
        publication_refs = [target,args['file_source_ref']]
        mapping = store.sequence_mapping(args['target_ref']) if store.subject_molecule(args['target_ref']) in {'dna','rna'} else None
    elif name == 'reference.neighborhood':
        native = {'operation': 'neighborhood', 'binding': locus, 'left_bp': args['left_bp'], 'right_bp': args['right_bp']}
        updates.update(binding_ref=args['binding_ref'], target_regions=locus['target_regions'])
        publication_refs = [args['binding_ref']]
        mapping = None
    elif name == 'context.compare_neighborhoods':
        for reference in [args['partner_reference_ref'], *args['definition_source_refs']]: received(reference)
        rows = []
        for row in args['rows']:
            received(row['neighborhood_ref'])
            measured = received_measurement(store, row['neighborhood_ref'])
            require(measured is not None and measured['body']['schema']=='a103_neighborhood_v1', 'a103_actual_neighborhood_required')
            anchor = binding_body(store, measured['body']['binding_ref'], known)
            refs.add(measured['body']['binding_ref'])
            require(row['left_feature_index']==anchor['locus']['source_feature_index'], 'a103_context_left_must_be_bound_focal_locus')
            selected = {**row, 'neighborhood': measured['body']}
            if row['right_feature_index'] is None:
                selected['partner_absence_evaluable'] = False
                detection = row.get('right_detection_ref')
                if detection is not None:
                    received(detection)
                    proof = received_measurement(store, detection)
                    require(proof is not None and proof['body']['schema']=='a103_detection_v1'
                        and proof['body'].get('neighborhood_ref')==row['neighborhood_ref']
                        and proof['body']['component_ref']==args['partner_reference_ref'], 'a103_absence_specific_query_or_neighborhood_conflict')
                    require(proof['body']['present'] is not True, 'a103_negative_context_conflicts_with_actual_detection')
                    selected['partner_absence_evaluable'] = proof['body']['present'] is False
            rows.append(selected)
        native = {'operation': 'compare', 'rows': rows, 'definition': args['definition']}
        publication_refs = [args['partner_reference_ref'],*args['definition_source_refs'],*[row['neighborhood_ref'] for row in args['rows']]]
        updates.update(partner_reference_ref=args['partner_reference_ref'], definition_source_refs=args['definition_source_refs'],
            comparison_group=digest([target, args['partner_reference_ref'], args['definition'], sorted(
                (r['neighborhood_ref'],r['left_feature_index'],r['right_feature_index'],r['sampling_group']) for r in args['rows'])]),
            comparison_variant=digest(args))
        mapping = None
    elif name == 'context.fusion':
        received(args['binding_ref'])
        locus = binding_body(store, args['binding_ref'], known)
        for reference in [*args['definition_source_refs'], *[row['component_ref'] for row in args['regions']],
                *[row['alignment_ref'] for row in args['regions'] if row['alignment_ref']]]: received(reference)
        native = {'operation': 'fusion', 'binding': locus, 'regions': args['regions']}
        publication_refs = [args['binding_ref'],*args['definition_source_refs'],*[row['component_ref'] for row in args['regions']]]
        updates.update(binding_ref=args['binding_ref'], definition_source_refs=args['definition_source_refs'],
            comparison_group=digest([target,args['binding_ref'],[(r['start'],r['end'],r['component_ref']) for r in args['regions']]]),
            comparison_variant=digest(args))
        mapping = None
    elif name == 'context.detection_inventory':
        from .a103_detection import search_receipt
        metadata, query = search_receipt(store,args['snapshot_ref'],args['native_source_ref'],args['component_ref'],known)
        for reference in [args['snapshot_ref'],args['component_ref'],*args['binding_refs']]: received(reference)
        native_path = file('native_path', args['native_source_ref'], 'hmmer3_text')
        database_path = file('database_path', args['database_source_ref'], 'fasta_text')
        bindings = [binding_body(store, reference, known) for reference in args['binding_refs']]
        neighborhood = None
        if args.get('neighborhood_ref'):
            received(args['neighborhood_ref'])
            neighborhood = received_measurement(store,args['neighborhood_ref'])
            require(neighborhood is not None and neighborhood['body']['schema']=='a103_neighborhood_v1'
                and neighborhood['body']['binding_ref'] in args['binding_refs'], 'a103_detection_actual_neighborhood_scope_required')
            neighborhood = neighborhood['body']
        native = {'operation': 'detection', **args, 'native_path': native_path, 'database_path': database_path,
            'search_metadata': metadata, 'bindings': bindings, 'query_sequence': query, 'neighborhood': neighborhood}
        updates.update(binding_refs=args['binding_refs'])
        publication_refs = [args['snapshot_ref'],args['native_source_ref'],args['database_source_ref'],args['component_ref'],*args['binding_refs']]
        mapping = None
    else:
        for reference in [args['left_reference_ref'],args['right_reference_ref'],*args['definition_source_refs']]: received(reference)
        rows, detections = [], []
        for row in args['rows']:
            states = []
            for field, component in (('left_detection_ref',args['left_reference_ref']),('right_detection_ref',args['right_reference_ref'])):
                received(row[field])
                proof = received_measurement(store,row[field])
                require(proof is not None and proof['body']['schema']=='a103_detection_v1', 'a103_actual_detection_inventory_required')
                require(proof['body']['genome_key']==row['genome_key'] and proof['body']['component_ref']==component, 'a103_detection_operand_conflict')
                states.append(proof['body']['present']); detections.append(row[field])
            rows.append({**row,'left_present':states[0],'right_present':states[1]})
        native = {'operation': 'cooccurrence', 'rows': rows}
        publication_refs = [*detections,*args['definition_source_refs']]
        updates.update(detection_refs=detections,left_reference_ref=args['left_reference_ref'],right_reference_ref=args['right_reference_ref'],
            definition_source_refs=args['definition_source_refs'],detection_scope='actual_received_detection_inventories',
            comparison_group=digest([target,args['left_reference_ref'],args['right_reference_ref'],sorted(r['genome_key'] for r in rows)]),
            comparison_variant=digest(args))
        mapping = None
    return {'operation':name,'arguments':args,'native_request':native,'updates':updates,
        'assets':assets,'evidence_refs':sorted(refs),'publication_refs':publication_refs,
        'target_mapping':mapping,'scope':deepcopy(scope)}


def publish_result(registry, plan, native_result):
    """Apply the original host augmentation and publish the original A103 sheet."""
    body, records = deepcopy(native_result), []
    store, args, name = registry.store, plan['arguments'], plan['operation']
    body.update(deepcopy(plan['updates']))
    if name == 'context.bind_locus':
        placement = body.get('native_input_placement')
        if placement and placement['state']=='unique' and placement['molecule'] in {'dna','rna'}:
            mapping = plan['target_mapping']
            require(mapping['units_per_symbol']==1, 'a103_original_nucleotide_map_required')
            positions = [p for part in mapping['path'] for p in (range(part['end']-1,part['start']-1,-1)
                if part['strand']=='-' else range(part['start'],part['end']))]
            selected = sorted({positions[p] for start,end in placement['placements'][0]['target_intervals'] for p in range(start,end)})
            spans = []
            for position in selected:
                if spans and position==spans[-1][1]: spans[-1][1]+=1
                else: spans.append([position,position+1])
            body['target_regions'] = spans
        if body['selection_status']=='selected' and body['locus']['translation']['status']=='verified':
            reference = registry._protein(body['locus']['translation']['sequence'],args['file_source_ref'],
                body['accession']+'.CDS.'+str(body['locus']['source_feature_index']))
            body['protein_reference_ref'] = reference
            records.append(reference)
        reference = publish(store,binding_summary(body),[*plan['publication_refs'],*records])
        store.db.execute('INSERT OR IGNORE INTO a103_bindings VALUES(?,?)',(reference,canonical(body)))
    else:
        if name == 'reference.neighborhood':
            locus = plan['native_request']['binding']
            for row in body['cds']:
                if row['translation']['status']=='verified':
                    reference = registry._protein(row['translation']['sequence'],locus['file_source_ref'],
                        locus['accession']+'.CDS.'+str(row['source_feature_index']))
                    row['protein_reference_ref'] = reference
                    records.append(reference)
        reference = publish(store,body,[*plan['publication_refs'],*records])
    records.append(reference)
    return list(dict.fromkeys(records)), reference
