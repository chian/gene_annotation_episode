"""Tool information for explicitly configured native database utilities.

Pure descriptors do not establish installed programs or connected episode paths.
The shared execution binding must admit a descriptor before offering it to work.
"""
from __future__ import annotations
from copy import deepcopy

from jsonschema import Draft202012Validator

from .blast_preparation_contracts import OPERATION_PARAMETERS, RESTRICTION_SCHEMA
from .native_blast_contracts import finite_json_copy
from .native_blast_utility_contracts import (
    MODES, LEGACY_MODES, PREPARATION_MODES, VDB_MODES, SOFTWARE_SCHEMA,
    NATIVE_BLAST_UTILITY_REQUESTED_JOB_SCHEMA,
    _error, _path, _schema, native_blast_utility_job_schema,
    validate_native_blast_utility_job,
)

_DESCRIPTIONS = {
    'create_sequence_database': 'Build a retained nucleotide or protein BLAST database from supplied FASTA sequences.',
    'extract_sequences': 'Retrieve explicitly selected sequences or ranges from a supplied prepared BLAST database.',
    'info': 'Read the selected prepared BLAST database’s native counts, molecule and volume information.',
    'metadata': 'Retrieve the selected prepared BLAST database’s native JSON metadata and file inventory.',
    'integrity': 'Run the explicitly selected BLAST database integrity checks and preserve their actual coverage and diagnostics.',
}
_INSTRUCTIONS = {
    'create_sequence_database': (
        'Supply one plain FASTA and choose nucleotide or protein, database format4 or5, title, identifier parsing '
        'and hash-index options explicitly. Optional taxonomy maps and masking artifacts must be supplied with their '
        'own identities; selecting this job does not generate either. Keep every produced database component, including '
        'native metadata and sidecars. A zero exit does not establish that every file was captured or that a later '
        'search used the database. A failed build can leave partial files; retain them without presenting a usable '
        'prepared database. Taxonomy assignments describe the selected inputs and do not establish gene function. '),
    'extract_sequences': (
        'Select an already prepared database and an explicit list of sequence identifiers. This binding does not select '
        'a default database or retrieve all entries. Duplicate requests remain distinct. Native identifier, accession, '
        'OID and full sequence length accompany the returned sequence. A requested range uses one-based inclusive '
        'endpoints; retained normalized coordinates use zero-based half-open endpoints. The returned fragment length '
        'is distinct from the full sequence length. Preserve strand, missing identifiers and unassociated rows. '
        'Do not join records by output position or choose the first duplicate accession. get_dups and target_only '
        'are mutually exclusive native options. '),
    'info': (
        'Select the exact prepared database. Retain the native title, database format, molecule, sequence/residue '
        'counts and volume identities when reported. Select exact_length explicitly if that measurement is needed. '
        'Absent counts remain unavailable. Counts describe this database population, not the frequency of a function. '),
    'metadata': (
        'Select the exact prepared database and retain its native metadata JSON. Preserve native reported file names, '
        'byte totals, sequence counts, residue counts and original field locations. Native metadata is not itself '
        'the workflow prepared-database manifest. Writer metadata and later inspection metadata can include different '
        'file populations; do not silently substitute one byte total for another. '),
    'integrity': (
        'Select the exact prepared database and the full or sampled checking methods. Preserve the native diagnostic '
        'output and return code. Requested sampling counts do not establish actual checked counts or sampled OIDs. '
        'A sampled pass is not a full database pass. Retain useful passing sequence checks even when another check '
        'fails. Missing taxonomy data, missing files and an execution failure are distinct from evidence that '
        'sequences are corrupt. Required reference data must be explicitly configured; no lookup or download is '
        'added automatically. '),
}

# Key information by the selected pair, without changing any legacy wording.
_DESCRIPTIONS = {pair: _DESCRIPTIONS[pair[1]] for pair in LEGACY_MODES}
_INSTRUCTIONS = {pair: _INSTRUCTIONS[pair[1]] for pair in LEGACY_MODES}
_DESCRIPTIONS.update({
    ('blastdb_aliastool', 'convert_gi_list'): 'Convert one supplied text GI list to a retained native binary GI list.',
    ('blastdb_aliastool', 'convert_seqid_list'): 'Convert one supplied sequence-identifier list, optionally against an explicitly supplied BLAST database.',
    ('blastdb_aliastool', 'inspect_seqid_list'): 'Inspect a supplied native binary sequence-identifier list and preserve its reported metadata.',
    ('blastdb_aliastool', 'create_subset_alias'): 'Create a BLAST database alias using one explicitly selected identifier, taxonomy or OID restriction.',
    ('blastdb_aliastool', 'aggregate_databases'): 'Create an alias over an explicitly ordered classic and/or VDB database population.',
    ('blastdb_aliastool', 'aggregate_volumes'): 'Create an alias over an explicitly enumerated and staged BLAST database volume population.',
    ('makembindex', 'create_megablast_index'): 'Build the selected Megablast index variant from supplied nucleotide FASTA or a prepared nucleotide database.',
    ('makembindex', 'show_filters'): 'Inspect the selected nucleotide database for native masking-filter information.',
    ('makeprofiledb', 'create_profile_database'): 'Build the selected RPS, DELTA or COBALT profile database from supplied complete PSSM inputs.',
})
_INSTRUCTIONS.update({
    ('blastdb_aliastool', 'convert_gi_list'): (
        'Supply the original text identifier list and an explicit binary output path. The native command reads the '
        'staged copy; original comments, blank lines, duplicate entries and malformed entries remain retained. '
        'Use molecule unknown. Preserve native conversion diagnostics and the binary list. A reported converted-GI '
        'count is distinct from decoded stored identifiers, submitted line counts and biological sequences. '
        'No stored membership or count is inferred from file size. '),
    ('blastdb_aliastool', 'convert_seqid_list'): (
        'Supply the original text identifier list, binary output path and title explicitly. Choose the configured '
        'unbound or database-bound variant. Unbound conversion uses molecule unknown; bound conversion names the '
        'exact supplied classic database, its complete prepared manifest and its DNA or protein molecule. Retain '
        'the original list and staged copy separately, including duplicate and unmatched identifiers. Conversion '
        'does not establish alias matching or decoded binary membership. Native stored counts and database-length '
        'metadata require a separately selected list inspection if those results are needed. '),
    ('blastdb_aliastool', 'inspect_seqid_list'): (
        'Select one retained binary sequence-identifier list. Use molecule unknown and preserve its exact file '
        'subject; no live database is inferred from native volume names. Retain native stdout metadata and stderr. '
        'Stored identifier count differs from submitted occurrences or matched biological sequences. Preserve '
        'native title, date text and any database length or volume text with their reported meanings; missing '
        'metadata stays unavailable. Request the needed located values through database_fields. '),
    ('blastdb_aliastool', 'create_subset_alias'): (
        'Supply one prepared classic database and exactly one configured restriction: GI list, sequence-identifier '
        'list, taxonomy-ID list or literal OID bitmask. The selected text or binary list format must match its '
        'variant; no identifier normalization or conversion is added. Retain original and staged restriction '
        'lists separately and bind the alias references to the actual staged files. Supply the complete database '
        'dependency closure and explicit output prefix and title. Retain every generated alias/list/sidecar and '
        'native diagnostic. Alias NSEQ and LENGTH are native reported values, not a reconstructed selection or an '
        'exact extracted sequence length. Failed matching leaves the subset population unknown. '),
    ('blastdb_aliastool', 'aggregate_databases'): (
        'Choose the configured classic and/or VDB list sources explicitly, inline or file. Supply every selected '
        'database manifest and complete dependency closure. Entries retain their order, repetitions and exact '
        'database/path mapping. File lists retain original bytes and a separate staged rewrite; only selected '
        'token spans change to the declared paths. Inline tokens must be representable without guessed quoting. '
        'A VDB selection requires its actual prepared manifest, complete files and applied offline configuration; '
        'a descriptor does not establish that execution closure or authorize a download. Retain all alias members '
        'and native diagnostics. Repeated database bytes do not become independent biological populations. '),
    ('blastdb_aliastool', 'aggregate_volumes'): (
        'Supply the exact ordered volume population, selected source database and matching positive volume count. '
        'Declare complete copy mappings into the output-prefix volume namespace because native names its inputs '
        'there. Preserve original and staged database files as dependencies; they are not newly generated outputs. '
        'Do not discover or infer additional volumes from suffixes. Retain the generated alias, every new sidecar '
        'and native diagnostics, with explicit output and dependency populations. '),
    ('makembindex', 'create_megablast_index'): (
        'Select input format, old-style flag and legacy flag independently within the configured variant. Supply '
        'nucleotide FASTA for an old-style build or the complete prepared nucleotide database. A new-style build '
        'requires an explicit writable attempt copy of the database closure and captures new members beside that '
        'copy; copied source files remain dependencies. Old-style builds require an explicit output prefix. Native '
        'new-style output-prefix options can be ignored and never establish a returned file path. Retain all index '
        'members, optional ID maps, explicitly selected statistics and native diagnostics. Requested parameters '
        'remain distinct from located native effective, adjusted or ignored values. File sizes and source counts '
        'do not establish indexed sequence counts. Building an index does not establish a downstream index-using '
        'search binding. '),
    ('makembindex', 'show_filters'): (
        'Select one complete prepared nucleotide database. This invocation only requests native filter information '
        'and has no index-building parameters or outputs. Retain stdout and stderr. An empty or newline-only '
        'response does not establish zero filters; nonempty filter-row interpretation remains unavailable until '
        'its native grammar is verified. Request diagnostic streams explicitly when their bytes are needed. '),
    ('makeprofiledb', 'create_profile_database'): (
        'Select the configured RPS, DELTA or COBALT type and ASN.1 text or binary format. Supply the original '
        'whitespace-tokenized profile list and every referenced complete PssmWithParameters input with ordered '
        'line/token bindings, preserving repeated entries. Keep the original list, staged rewrite and full profile '
        'bytes separate; staging does not pad, generate or repair a matrix. Frequency ratios, matching sequence '
        'lengths and valid row counts are required; DELTA also needs weighted frequencies and independent '
        'observations, and COBALT needs core blocks. Select a positive per-volume maximum and explicit parameters. '
        'Taxonomy ID and taxonomy map are mutually exclusive. Retain every actual profile/sequence database '
        'member, auxiliary file and diagnostic, including residual ordinary database files after a failed build. '
        'A failed profile build cannot return a successful prepared profile database. Native auxiliary values '
        'retain per-volume scope and source locations; placeholder zeros, submitted profile counts and exit zero '
        'do not establish biological measurements, included-profile membership or search compatibility. '),
})


_DESCRIPTIONS.update({
    ('blast_vdb_cmd', 'extract_sequences'): 'Retrieve selected reads or reference sequences from an explicitly supplied prepared VDB dataset.',
    ('blast_vdb_cmd', 'info'): 'Read native sequence and reference-population statistics from an explicitly supplied prepared VDB dataset.',
    ('blast_vdb_cmd', 'paths'): 'List the native resolved VDB paths for the supplied prepared dataset selection.',
    ('blast_vdb_cmd', 'paths_all'): 'List native VDB paths and reported VDB/classic alias sections for the supplied prepared dataset selection.',
})
_INSTRUCTIONS.update({
    ('blast_vdb_cmd', 'extract_sequences'): (
        'Choose the configured extraction variant explicitly: selected identifiers supplied directly or in an '
        'entry-batch file, all native sequences, or all references. All-reference extraction is a separate native '
        'selection and cannot include filtered reads; filtered-read inclusion for other extraction variants is '
        'an explicit configured choice. Preserve duplicate requested identifiers and their original ordinals. '
        'The fixed output is identifier, accession, native reported length and sequence in four tab-separated '
        'columns. Native length describes the returned sequence; it is not a known full reference length or '
        'a database-search significance score. Keep reported length, counted symbols and normalized sequence '
        'separate, retaining invalid rows and missing associations. Select requested fields and sequence content '
        'explicitly in the result selector. Specific-entry results use selector ordinals; all-mode results use '
        'native row ordinals. Member, read, reference and sample relationships require the supplied original '
        'metadata bindings and their authenticated selected bytes; identifier spelling does not establish them. '),
    ('blast_vdb_cmd', 'info'): (
        'Select the exact prepared dataset population. Preserve the native sequence count, total unclipped bases, '
        'longest sequence and reported integer average with their original population and source locations. '
        'Preserve CSRA reference count/base totals separately when reported. Do not recompute a native average '
        'from other fields, infer a reference population for ordinary reads, or use these counts as function '
        'frequencies. Request the needed native field names through database_fields; absent fields remain '
        'qualified as unavailable. Native text and original input context remain separately selectable artifacts. '),
    ('blast_vdb_cmd', 'paths'): (
        'Select the exact prepared dataset and retain the native resolved VDB path strings, original line/row '
        'positions and explicitly declared dependency matches. A reported path is information, not permission '
        'to read or acquire that path. Do not add discovered paths to this invocation or infer dependencies from '
        'a filename. Request the VDB path rows and section-presence information needed by the parent. '),
    ('blast_vdb_cmd', 'paths_all'): (
        'Select the exact prepared dataset and request the needed VDB, VDB-alias and classic-BLAST-alias path '
        'sections. Preserve reported-empty, reported-values and not-reported sections distinctly, together with '
        'original line/row identities. Dependency matches use only original declared bindings. Reported alias '
        'or path strings do not authorize file acquisition, expand the dataset selection, or establish successful '
        'downstream use of an alias. '),
})


def _closed(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties),
            'additionalProperties': False}


def _vdb_variant_schema(pair):
    """Explicit resource capability choices, distinct from the shared job data."""
    selections = ([('entries', source, {'type': 'boolean'}) for source in ('entry', 'entry_batch')]
        + [('all_native_sequences', None, {'type': 'boolean'}),
           ('all_references', None, {'const': False})]
        if pair[1] == 'extract_sequences' else [(None, None, {'const': False})])
    return {'anyOf': [_closed({
        'database_source': {'enum': ['db', 'dbs_file']},
        'database_input_kind': {'const': 'path'},
        'selection_kind': {'const': kind}, 'entry_source': {'const': source},
        'include_filtered_reads': filtered}) for kind, source, filtered in selections]}


def _vdb_variant_operation_constraint(pair, variant):
    selection = (None if variant['selection_kind'] is None else
        {'properties': {'kind': {'const': variant['selection_kind']},
            **({'source': {'const': variant['entry_source']}} if variant['entry_source'] is not None else {})}})
    return {'properties': {'molecule': {'enum': ['dna']}, 'parameters': {'properties': {
        'database_selection': {'properties': {
            'source': {'const': variant['database_source']},
            'inputs': {'items': {'properties': {'kind': {'const': variant['database_input_kind']}}}}}},
        'selection': {'const': None} if selection is None else selection,
        'include_filtered_reads': {'const': variant['include_filtered_reads']}}}}}


def _variant_schema(pair):
    """Closed configuration projections of the shared operation parameters."""
    mode = pair[1]
    parameters = OPERATION_PARAMETERS[pair]['properties']
    if mode in {'convert_gi_list', 'inspect_seqid_list', 'aggregate_volumes', 'show_filters'}:
        return _closed({})
    if mode == 'convert_seqid_list':
        return _closed({'database_binding': {'enum': ['unbound', 'bound']}})
    if mode == 'create_subset_alias':
        return {'anyOf': [_closed({'restriction_kind': deepcopy(branch['properties']['kind']),
            'input_format': deepcopy(branch['properties'].get('format', {'type': 'null'}))})
            for branch in RESTRICTION_SCHEMA['anyOf']]}
    if mode == 'aggregate_databases':
        schema = _closed({key: {'enum': [None, 'inline', 'file']}
                          for key in ('classic_source', 'vdb_source')})
        schema['not'] = {'properties': {key: {'type': 'null'}
                                       for key in ('classic_source', 'vdb_source')}}
        return schema
    if mode == 'create_megablast_index':
        schema = _closed({key: deepcopy(parameters[key])
                          for key in ('input_format', 'old_style_index', 'legacy')})
        schema['anyOf'] = [{'properties': {'old_style_index': {'const': True}}},
                           {'properties': {'input_format': {'const': 'blastdb'}}}]
        return schema
    return _closed({key: deepcopy(parameters[key]) for key in ('profile_type', 'input_format')})


def _variant_operation_constraint(pair, variant):
    """One selected variant constraint, reused by descriptors and acceptance."""
    mode, parameters, molecules = pair[1], {}, ['dna', 'protein']
    if mode in {'convert_gi_list', 'inspect_seqid_list'}:
        molecules = ['unknown']
    elif mode == 'convert_seqid_list':
        bound = variant['database_binding'] == 'bound'
        parameters['seqid_database_key'] = {'type': 'string' if bound else 'null'}
        molecules = ['dna', 'protein'] if bound else ['unknown']
    elif mode == 'create_subset_alias':
        restriction = {'kind': {'const': variant['restriction_kind']}}
        if variant['input_format'] is not None:
            restriction['format'] = {'const': variant['input_format']}
        parameters['restriction'] = {'properties': restriction}
    elif mode == 'aggregate_databases':
        for source, selected in (('classic_source', 'classic_list'), ('vdb_source', 'vdb_list')):
            parameters[selected] = ({'type': 'null'} if variant[source] is None else
                {'type': 'object', 'properties': {'source': {'const': variant[source]}}})
    elif mode == 'create_megablast_index':
        parameters = {key: {'const': value} for key, value in variant.items()}
        molecules = ['dna']
    elif mode == 'show_filters':
        molecules = ['dna']
    elif mode == 'create_profile_database':
        parameters = {key: {'const': value} for key, value in variant.items()}
        molecules = ['protein']
    return {'properties': {'molecule': {'enum': molecules},
                           'parameters': {'properties': parameters}}}


def validate_native_blast_utility_bindings(rows: list[dict]) -> list[dict]:
    rows = finite_json_copy(rows)
    if type(rows) is not list: _error('binding_rows_required')
    seen = set()
    for row in rows:
        if type(row) is not dict or not {'program','mode','software','molecules'} <= set(row):
            _error('binding_shape')
        pair = row['program'],row['mode']
        if any(type(value) is not str for value in pair) or pair not in MODES or pair in seen:
            _error('binding_program_mode')
        seen.add(pair)
        preparation, vdb = pair in PREPARATION_MODES, pair in VDB_MODES
        variants = preparation or vdb
        if set(row) != {'program','mode','software','molecules'} | ({'variants'} if variants else set()):
            _error('binding_shape')
        _schema(row['software'],SOFTWARE_SCHEMA)
        _path(row['software']['executable'],absolute=True)
        if (type(row['molecules']) is not list or not row['molecules'] or
            any(type(v) is not str or v not in {'dna','protein','unknown'} for v in row['molecules']) or
            len(row['molecules']) != len(set(row['molecules']))):
            _error('binding_molecules')
        if not variants:
            if 'unknown' in row['molecules']: _error('binding_molecules')
            continue
        _schema(row['variants'], {'type': 'array', 'minItems': 1, 'uniqueItems': True,
                                 'items': _vdb_variant_schema(pair) if vdb else _variant_schema(pair)})
        permitted = set()
        for variant in row['variants']:
            constraint = _vdb_variant_operation_constraint if vdb else _variant_operation_constraint
            molecules = set(constraint(pair, variant)['properties']['molecule']['enum'])
            if not molecules.intersection(row['molecules']): _error('binding_variant_molecules')
            permitted.update(molecules)
        if not set(row['molecules']) <= permitted: _error('binding_molecules')
    return rows


def _bound_job_schema(row):
    """The same capability intersection for model-facing schema and runtime."""
    pair = row['program'], row['mode']
    schema = native_blast_utility_job_schema(program=pair[0], mode=pair[1])
    schema['properties']['software'] = {'const': row['software']}
    operation = schema['properties']['operation']['allOf']
    operation.append({'properties': {'molecule': {'enum': row['molecules']}}})
    if pair in PREPARATION_MODES or pair in VDB_MODES:
        constraint = _vdb_variant_operation_constraint if pair in VDB_MODES else _variant_operation_constraint
        operation.append({'anyOf': [constraint(pair, variant)
                                   for variant in row['variants']]})
    return schema


def native_blast_utility_binding_accepts_job(binding: dict, job: dict) -> bool:
    """Validate both records; return whether the exact selected job is bound.

    Invalid records raise the shared contract error. A valid job outside this
    binding's program, mode, software, molecule or variant returns False. No
    installation, artifact access, acquisition or execution is performed.
    """
    binding = validate_native_blast_utility_bindings([binding])[0]
    job = validate_native_blast_utility_job(job)
    return Draft202012Validator(_bound_job_schema(binding)).is_valid(job)


def native_blast_utility_tool_contracts(bindings: list[dict], *, resource_kind: str,
                                      resource_id: str) -> list[dict]:
    if resource_kind != 'local' or type(resource_id) is not str or not resource_id or '\0' in resource_id:
        _error('configured_local_resource_required')
    contracts = []
    for row in validate_native_blast_utility_bindings(bindings):
        program,mode = row['program'],row['mode']
        schema = deepcopy(NATIVE_BLAST_UTILITY_REQUESTED_JOB_SCHEMA)
        schema['properties']['native_blast_utility'] = _bound_job_schema(row)
        instructions = _INSTRUCTIONS[(program,mode)] + (
            'Commission the selected job through launch and its configured local-compute child under the caller’s '
            'allocation. It is one native utility invocation; preparation, extraction and integrity checking are '
            'separately selected operations. The infrastructure does not choose follow-up work. Retain original '
            'inputs, output files and diagnostic streams. Results acquisition uses the deterministic typed utility '
            'records and returns only the parent’s requested fields. These are supporting operations without an '
            'independent annotation-confidence score. Keep database-scale work off this local resource; remote '
            'execution requires its own actually configured resource binding.')
        if (program,mode) in PREPARATION_MODES:
            instructions += (
                ' The selected local allocation is at most 20 GiB RAM and 4 GiB scratch, with zero swap and no '
                'wall-time cap. Retain closed-writer stdout/stderr and every actual selected output member even '
                'when native fails; capture completeness does not turn failure into successful preparation. '
                'The shared preparation/inspection readers populate typed records. Select preparation fields '
                'such as kind, detail, dependencies, database_bindings and materializations only when needed; '
                'select artifact roles/ordinals and saved_data explicitly to receive their reusable bytes. '
                'Prepared-database projection is available only for the supported complete successful family '
                'and dependency closure. Identifier lists, indexes and unsupported profile/VDB projections '
                'retain artifacts with specific unavailable results. Native counts are not annotation scores.')
        if (program,mode) in VDB_MODES:
            instructions += (
                ' Supply one original prepared VDB operand, its complete file manifest, preparation receipt and '
                'explicit offline configuration, plus only the declared supporting operands and metadata files. '
                'This resource binding admits absolute path selections; alias/accession resolver mappings are '
                'not established here. Choose db or dbs_file within the configured variant. List and entry-batch '
                'bytes are staged unchanged and checked against the selected ordered tokens; no database-list '
                'rewriting, download or default cache is added. The executable, database/configuration and '
                'selected runtime files retain their original absolute paths in the isolated offline execution. '
                'Apply the caller’s local allocation within 20 GiB RAM/4 GiB scratch, zero swap and no wall cap. '
                'The two managed native outputs are stdout and stderr, with the mode’s fixed output format. '
                'Results use selector-v2 and the shared extraction/inspection records; artifact roles and '
                'saved result data require explicit selection. Preserve useful partial outputs and specific '
                'failures. Source metadata and nested provenance do not grant their file bytes. These library '
                'instructions do not establish verification of every dataset type, native format or resource.')
        contracts.append({'name':'native.'+program+'.'+mode,'description':_DESCRIPTIONS[(program,mode)],
            'resources':'local','instructions':instructions,'input_schema':schema,
            'invocation_route':{'kind':'commission','routes':[{'entry_role':'launch',
                'resource_id':resource_id,'resource_role':'launch_local'}]}})
    return contracts
