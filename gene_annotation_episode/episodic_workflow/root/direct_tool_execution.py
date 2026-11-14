"""Original substantive ordinary-tool methods: direct_tool_execution."""
from __future__ import annotations
import asyncio
from datetime import datetime
from datetime import timezone
import json
from gene_annotation_episode.acquisition import AcquisitionError
from gene_annotation_episode.acquisition import RfamModelSnapshots
from gene_annotation_episode.api_error_feedback import api_error_feedback
from gene_annotation_episode.api_error_feedback import api_error_response
from gene_annotation_episode.domain import ContractError
from gene_annotation_episode.domain import canonical
from gene_annotation_episode.domain import identity
from gene_annotation_episode.domain import validate_schema
from gene_annotation_episode.episodic_workflow.root.library import read_mapping as mapper
from gene_annotation_episode.source_locations import received_source as received_location_source
from gene_annotation_episode.literature_assets import PmcFiles
from gene_annotation_episode.image_evidence import visual_input
from gene_annotation_episode.episodic_workflow.root.library.restriction_mapping_registry import ALIASES as RESTRICTION_ALIASES
from gene_annotation_episode.episodic_workflow.root.library.restriction_mapping_registry import RestrictionOperationUnpublished
from gene_annotation_episode.episodic_workflow.root.library.restriction_mapping_registry import restriction_work_reserved
from gene_annotation_episode.episodic_workflow.root.library.restriction_mapping_registry import prepare_restriction_work
from gene_annotation_episode.episodic_workflow.root.library.restriction_mapping_registry import publish_restriction_work
from gene_annotation_episode.episodic_workflow.root.library.restriction_mapping_registry import replay_restriction_work
from gene_annotation_episode.episodic_workflow.root.library.restriction_mapping_registry import retire_restriction_work
from .tool_values import ref

class DirectToolExecution:
    def execute(self, name: str, args: dict, *, scope: dict | None = None,
                operation_key: str | None = None, permitted_record_refs=None) -> dict:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.execute_async(name, args, scope=scope, operation_key=operation_key,
                                                  permitted_record_refs=permitted_record_refs))
        raise ContractError("use_execute_async_in_running_event_loop")

    def _check_molecular_source_bytes(self, name, arguments):
        """Apply the finite Source/File receipt policies before byte tools."""
        if name in {'material.parse', 'material.read'}:
            material = self.store._require(arguments['material_ref'], {'material'})
            source = self.store._require(material['source_ref'], {'source'})
            artifact_ref = source['artifact_ref']
        elif name in {'source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references', 'source.archive.members',
                'source.xlsx.sheets', 'source.xlsx.rows', 'source.pdf.info',
                'source.pdf.text', 'source.pdf.page', 'image.view'}:
            source = self.store._require(arguments['source_ref'], {'source'})
            if name in {'source.read', 'source.locate', 'source.sequence.scan', 'source.sequence.references'}:
                from gene_annotation_episode.materials import source_window_selection
                representation = 'original' if name == 'source.sequence.references' else arguments.get('representation', 'text')
                artifact_ref, _, _ = source_window_selection(source, representation)
            else:
                artifact_ref = source['artifact_ref']
        else:
            return
        from gene_annotation_episode.molecular_reference_privacy import molecular_reference_restriction
        invocation = self._current_invocation.get()
        context = None if invocation is None else invocation[0]
        primary_profiles = {
            'ensembl': ('external', None, 'ensembl_source_primary_body_not_received'),
            'alphafold': ('external', None, 'alphafold_source_primary_body_not_received'),
            'emdb': ('external', None, 'emdb_source_primary_body_not_received'),
            'rcsb_pdb': ('external', None, 'rcsb_source_primary_body_not_received'),
            'string': ('external', None, 'string_source_primary_body_not_received'),
            'kegg': ('external', None, 'kegg_source_primary_body_not_received'),
            'reactome': ('external', None, 'reactome_source_primary_body_not_received'),
            'quickgo': ('external', None, 'quickgo_source_primary_body_not_received'),
            'pubchem': ('external', None, 'pubchem_source_primary_body_not_received'),
            'hpa': ('external', None, 'hpa_source_primary_body_not_received'),
            'ucsc': ('external', None, 'ucsc_source_primary_body_not_received'),
            'eva': ('external', None, 'eva_source_primary_body_not_received'),
            'gnomad': ('external', None, 'gnomad_source_primary_body_not_received'),
            'bvbrc_minhash': ('external', None, 'minhash_source_primary_body_not_received'),
            'public.ncbi.entrez': ('external', None, 'ncbi_entrez_source_primary_body_not_received'),
            'public.ncbi.geo': ('external', None, 'geo_source_primary_body_not_received'),
            'public.ncbi.sra.file': ('external', None, 'sra_file_source_primary_body_not_received'),
            'public.jaspar': ('external', None, 'jaspar_source_primary_body_not_received'),
            'public.encode': ('external', None, 'encode_source_primary_body_not_received'),
            'public.screen': ('external', None, 'screen_source_primary_body_not_received'),
            'analyze_cas9_mutation_outcomes': ('tool', 'ordinary_reference_edit_outcome_result_v1',
                'reference_edit_outcome_source_primary_body_not_received'),
            'predict_protein_disorder_regions': ('tool', 'ordinary_protein_disorder_result_v1',
                'protein_disorder_source_primary_body_not_received'),
            'analyze_protein_conservation': ('tool', 'ordinary_protein_conservation_result_v1',
                'protein_conservation_source_primary_body_not_received'),
            'analyze_protein_phylogeny': ('tool', 'ordinary_protein_phylogeny_result_v1',
                'protein_phylogeny_source_primary_body_not_received'),
            'detect_and_annotate_somatic_mutations': ('tool', 'ordinary_somatic_variant_result_v1',
                'somatic_variant_source_primary_body_not_received'),
            'generate_gene_embeddings_with_ESM_models': ('tool', 'esm_gene_embedding_result_v1',
                'esm_gene_embedding_source_primary_body_not_received'),
            'result.macs2.peaks': ('tool', 'ordinary_macs2_peak_result_v1',
                'macs2_peak_source_primary_body_not_received'),
            'result.variants.vcf': ('tool', 'ordinary_vcf_result_v1',
                'vcf_result_source_primary_body_not_received'),
        }
        provider = source.get('provider')
        if provider in primary_profiles:
            # Reading an admitted Source's actual primary body grants no
            # Artifact reference. Direct File admission uses its own receipt.
            origin, source_version, failure_code = primary_profiles[provider]
            if (source.get('record_type') != 'source' or source.get('origin') != origin
                    or source.get('version') != source_version or artifact_ref != source.get('artifact_ref')
                    or molecular_reference_restriction(self.store, context, source['id'], 'source',
                        providers=(provider,)) is not True
                    or molecular_reference_restriction(self.store, context, artifact_ref, 'artifact',
                        private_only=True) is False):
                raise ContractError(failure_code)
            return
        if molecular_reference_restriction(self.store, context, artifact_ref, 'artifact') is False:
            raise ContractError('molecular_source_artifact_not_granted')

    async def execute_async(self, name: str, args: dict, *, scope: dict | None = None,
                            operation_key: str | None = None, permitted_record_refs=None) -> dict:
        # Bind source readers to this exact host action's receipts. Scientific
        # dispatch and ordinary annotation dispatch use the same readers; an
        # omitted dispatch keyword must not discard their received-input port.
        # Keep an explicitly selected subset, and never infer access for an
        # unbound/manual call or for a different nested operation.
        if permitted_record_refs is None and name in {
                'source.locate', 'source.sequence.scan',
                'source.sequence.references', 'source.experimental.records'}:
            invocation = self._current_invocation.get()
            if (invocation is not None and operation_key is not None
                    and invocation[2:] == (name, args, operation_key)
                    and invocation[0].scope == scope):
                permitted_record_refs = tuple(invocation[0].received_record_refs)
        if (permitted_record_refs is not None and (not isinstance(permitted_record_refs, (list, tuple))
                or any(not isinstance(ref, str) or not ref for ref in permitted_record_refs))):
            raise ContractError('explicit_permitted_record_refs_required')
        if name == 'source.locate':
            try:
                canonical(args)
            except (TypeError, ValueError):
                # Non-JSON operands cannot have a canonical durable identity.
                return {'status': 'invalid', 'operation_ref': None, 'record_refs': [],
                    'changed_record_refs': [], 'result': None, 'feedback': {
                        'category': 'arguments_or_reference', 'code': 'source_location_arguments_not_json'}}
        token = self._publications.set([])
        batch_token = self._publication_batch.set(None)
        directories = self._mapping_directories.set([])
        native_receipts = self._native_execution_refs.set([])
        grading_failures = self._grading_failures.set([])
        permitted = self._permitted_record_refs.set(
            None if permitted_record_refs is None else tuple(permitted_record_refs))
        try:
            return await self._execute_operation_async(name, args, scope=scope, operation_key=operation_key)
        finally:
            import shutil
            for directory in self._mapping_directories.get():
                shutil.rmtree(directory)
            self._mapping_directories.reset(directories)
            self._native_execution_refs.reset(native_receipts)
            self._grading_failures.reset(grading_failures)
            self._permitted_record_refs.reset(permitted)
            self._publications.reset(token)
            self._publication_batch.reset(batch_token)

    async def _execute_operation_async(self, name: str, args: dict, *, scope: dict | None = None,
                                       operation_key: str | None = None) -> dict:
        operation_key = operation_key or identity("manual_operation", {"name": name, "args": args,
                                                "time": datetime.now(timezone.utc).isoformat()})
        from gene_annotation_episode.episodic_workflow.root.library.itc_tools import ITC_TOOL
        from gene_annotation_episode.episodic_workflow.root.library.molecular_action_custody import authenticate_molecular_invocation
        from gene_annotation_episode.episodic_workflow.root.library.itc_tools import prepare_itc_work, partial_itc_publication
        from gene_annotation_episode.molecular_measurement_tools import MolecularOperationUnpublished
        from gene_annotation_episode.episodic_workflow.root.library.liftover_tools import LIFTOVER_TOOL, prepare_liftover_work
        from gene_annotation_episode.episodic_workflow.root.library.circular_dichroism_contracts import CD_TOOL
        from gene_annotation_episode.episodic_workflow.root.library.circular_dichroism_tools import prepare_circular_dichroism_work
        from .library.protein_structure_tools import (PROTEIN_STRUCTURE_TOOLS,
            prepare_protein_structure_work, validate_prepared_protein_structure_work, SAVED_WORK_VERSION)
        from .library.flux_balance_tools import FBA_TOOL
        from .library.alphafold_acquisition_host import FILE_TOOL as ALPHAFOLD_FILE_TOOL
        from gene_annotation_episode.alphafold_acquisition import (ALPHAFOLD_FAILURE_CODES,
            validate_alphafold_receipt, failed_alphafold_receipt)
        from gene_annotation_episode.emdb_acquisition import EMDB_FAILURE_CODES, validate_emdb_receipt
        from gene_annotation_episode.rcsb_acquisition import RCSB_FAILURE_CODES, validate_rcsb_receipt
        from gene_annotation_episode.ncbi_sra_acquisition import (TOOL as SRA_FILE_TOOL, SRA_FILE_FAILURE_CODES,
            validate_sra_file_receipt, failed_sra_file_receipt)
        from gene_annotation_episode.ucsc_acquisition import UCSC_FAILURE_CODES, validate_ucsc_receipt
        from gene_annotation_episode.ensembl_acquisition import (TOOL as ENSEMBL_TOOL, ENSEMBL_FAILURE_CODES,
            validate_ensembl_receipt, failed_ensembl_receipt)
        from .library.encode_tools import TOOL as ENCODE_TOOL, FAILURE_CODES as ENCODE_FAILURE_CODES, validate_encode_receipt
        from gene_annotation_episode.screen_tools import TOOL as SCREEN_TOOL, FAILURE_CODES as SCREEN_FAILURE_CODES, validate_screen_receipt
        from gene_annotation_episode.molecular_provider_acquisition import (OPERATIONS as MOLECULAR_PROVIDER_OPERATIONS,
            PROVIDER_FAILURE_CODES, validate_provider_receipt)
        from gene_annotation_episode.variant_provider_acquisition import (OPERATIONS as VARIANT_PROVIDER_OPERATIONS,
            PROVIDER_FAILURE_CODES as VARIANT_PROVIDER_FAILURE_CODES,
            validate_provider_receipt as validate_variant_provider_receipt)
        from gene_annotation_episode.episodic_workflow.root.library.molecular_sequence_result_contracts import ORDINARY_MOLECULAR_SEQUENCE_OPERATIONS
        from gene_annotation_episode.episodic_workflow.root.library.reference_edit_outcome_tools import TOOL as REFERENCE_EDIT_TOOL, execute_reference_edit_outcome
        from gene_annotation_episode.episodic_workflow.root.library.protein_disorder_tools import TOOL as PROTEIN_DISORDER_TOOL, execute_protein_disorder_tool
        from gene_annotation_episode.episodic_workflow.root.library.vcf_result_tools import TOOL as VCF_RESULT_TOOL, execute_vcf_result
        from gene_annotation_episode.episodic_workflow.root.library.macs2_peak_tools import TOOL as MACS2_PEAK_TOOL, execute_macs2_peak_result
        HOMER_TOOL = 'find_enriched_motifs_with_homer'
        TF_BINDING_TOOL = 'identify_transcription_factor_binding_sites'
        PROTEASE_KINETICS_TOOL = 'analyze_protease_kinetics'
        PROTEIN_CONSERVATION_TOOL = 'analyze_protein_conservation'
        PROTEIN_PHYLOGENY_TOOL = 'analyze_protein_phylogeny'
        SOMATIC_VARIANT_TOOL = 'detect_and_annotate_somatic_mutations'
        ESM_GENE_EMBEDDING_TOOL = 'generate_gene_embeddings_with_ESM_models'
        ARSENIC_SPECIATION_TOOL = 'analyze_arsenic_speciation_hplc_icpms'
        ordinary_molecular_tools = {ITC_TOOL, LIFTOVER_TOOL, CD_TOOL, FBA_TOOL, *ORDINARY_MOLECULAR_SEQUENCE_OPERATIONS,
            REFERENCE_EDIT_TOOL, VCF_RESULT_TOOL, MACS2_PEAK_TOOL, HOMER_TOOL, TF_BINDING_TOOL,
            PROTEASE_KINETICS_TOOL, PROTEIN_CONSERVATION_TOOL, PROTEIN_PHYLOGENY_TOOL, SOMATIC_VARIANT_TOOL, ESM_GENE_EMBEDDING_TOOL, ARSENIC_SPECIATION_TOOL,
            PROTEIN_DISORDER_TOOL, *PROTEIN_STRUCTURE_TOOLS}
        alphafold_getters = {"public.alphafold.prediction", ALPHAFOLD_FILE_TOOL}
        rcsb_getters = {"public.rcsb.entry", "public.rcsb.file"}
        ordinary_data_getters = {"public.ncbi.entrez", "public.ncbi.geo", SRA_FILE_TOOL, "public.jaspar",
            ENCODE_TOOL, SCREEN_TOOL, *alphafold_getters, "public.emdb.entry", *rcsb_getters,
            *MOLECULAR_PROVIDER_OPERATIONS, *VARIANT_PROVIDER_OPERATIONS, "public.ucsc.request", ENSEMBL_TOOL}
        getter_failure_codes = {ENCODE_TOOL: ENCODE_FAILURE_CODES, SCREEN_TOOL: SCREEN_FAILURE_CODES,
            SRA_FILE_TOOL: SRA_FILE_FAILURE_CODES,
            **{tool: ALPHAFOLD_FAILURE_CODES for tool in alphafold_getters},
            "public.emdb.entry": EMDB_FAILURE_CODES,
            **{tool: RCSB_FAILURE_CODES for tool in rcsb_getters},
            **{tool: PROVIDER_FAILURE_CODES for tool in MOLECULAR_PROVIDER_OPERATIONS},
            **{tool: VARIANT_PROVIDER_FAILURE_CODES for tool in VARIANT_PROVIDER_OPERATIONS},
            "public.ucsc.request": UCSC_FAILURE_CODES, ENSEMBL_TOOL: ENSEMBL_FAILURE_CODES}
        getter_validators = {SRA_FILE_TOOL: validate_sra_file_receipt,
            **{tool: validate_alphafold_receipt for tool in alphafold_getters},
            "public.emdb.entry": validate_emdb_receipt,
            **{tool: validate_rcsb_receipt for tool in rcsb_getters},
            **{tool: validate_provider_receipt for tool in MOLECULAR_PROVIDER_OPERATIONS},
            **{tool: validate_variant_provider_receipt for tool in VARIANT_PROVIDER_OPERATIONS},
            "public.ucsc.request": validate_ucsc_receipt, ENSEMBL_TOOL: validate_ensembl_receipt}
        getter_source_providers = {**{tool: "alphafold" for tool in alphafold_getters},
            "public.emdb.entry": "emdb",
            **{tool: "rcsb_pdb" for tool in rcsb_getters},
            **{tool: tool.split('.')[1] for tool in MOLECULAR_PROVIDER_OPERATIONS},
            **{tool: tool.split('.')[1] for tool in VARIANT_PROVIDER_OPERATIONS},
            "public.ucsc.request": "ucsc", ENSEMBL_TOOL: "ensembl"}
        # A reference or manual operation key cannot manufacture a live action.
        # Authenticate before either new production or the saved-result return.
        molecular_authority = (authenticate_molecular_invocation(self, name, args, scope, operation_key)
            if name in ordinary_molecular_tools else None)
        alphafold_file_authority = (authenticate_molecular_invocation(self, name, args, scope, operation_key)
            if name == ALPHAFOLD_FILE_TOOL else None)
        sra_file_authority = (authenticate_molecular_invocation(self, name, args, scope, operation_key)
            if name == SRA_FILE_TOOL else None)
        ensembl_authority = (authenticate_molecular_invocation(self, name, args, scope, operation_key)
            if name == ENSEMBL_TOOL and (type(args) is not dict or args.get("operation") != "registry") else None)
        encode_authority = (authenticate_molecular_invocation(self, name, args, scope, operation_key)
            if name == ENCODE_TOOL and type(args) is dict and args.get("operation") == "file" else None)
        if name in ORDINARY_MOLECULAR_SEQUENCE_OPERATIONS:
            from .library.molecular_sequence_tools import OrdinaryMolecularSequenceTools
            backend = self.ordinary_molecular_sequence_backend
            if backend is None:
                backend = OrdinaryMolecularSequenceTools(self, configuration=None,
                    saved_modes=self._molecular_sequence_saved_modes is True)
            # This same-owner lease authenticates saved work, publishes and
            # saves before returning. Generic cached returns and _save do not
            # own this operation, including when current selection is absent.
            return await backend.execute(args, scope=scope, operation_key=operation_key,
                authority=molecular_authority, operation=name)
        if name == REFERENCE_EDIT_TOOL:
            # Pure retained-data calculations publish and save atomically in
            # the adapter's transaction, including the same-key recovery check.
            return execute_reference_edit_outcome(self, args, scope=scope,
                operation_key=operation_key, authority=molecular_authority)
        if name == PROTEIN_DISORDER_TOOL:
            return await execute_protein_disorder_tool(self, args, scope=scope,
                operation_key=operation_key, authority=molecular_authority)
        if name == VCF_RESULT_TOOL:
            return execute_vcf_result(self, args, scope=scope,
                operation_key=operation_key, authority=molecular_authority)
        if name == MACS2_PEAK_TOOL:
            return await execute_macs2_peak_result(self, args, scope=scope,
                operation_key=operation_key, authority=molecular_authority)
        if name == HOMER_TOOL:
            from gene_annotation_episode.episodic_workflow.root.library.homer_motif_tools import execute_homer_tool
            return await execute_homer_tool(self, args, scope=scope,
                operation_key=operation_key, authority=molecular_authority)
        if name == TF_BINDING_TOOL:
            from gene_annotation_episode.episodic_workflow.root.library.tf_binding_tools import execute_tf_binding_tool
            return await execute_tf_binding_tool(self, args, scope=scope,
                operation_key=operation_key, authority=molecular_authority)
        if name == PROTEASE_KINETICS_TOOL:
            from gene_annotation_episode.episodic_workflow.root.library.protease_kinetics_tools import execute_protease_kinetics_tool
            return await execute_protease_kinetics_tool(self, args, scope=scope,
                operation_key=operation_key, authority=molecular_authority)
        if name == PROTEIN_CONSERVATION_TOOL:
            from .library.protein_conservation_tools import execute_protein_conservation_tool
            return await execute_protein_conservation_tool(self, args, scope=scope,
                operation_key=operation_key, authority=molecular_authority)
        if name == PROTEIN_PHYLOGENY_TOOL:
            from .library.protein_phylogeny_tools import execute_protein_phylogeny_tool
            return await execute_protein_phylogeny_tool(self, args, scope=scope,
                operation_key=operation_key, authority=molecular_authority)
        if name == ESM_GENE_EMBEDDING_TOOL:
            from gene_annotation_episode.episodic_workflow.root.library.esm_gene_embedding_tools import execute_esm_gene_embedding_tool
            return await execute_esm_gene_embedding_tool(self, args, scope=scope,
                operation_key=operation_key, authority=molecular_authority)
        if name == SOMATIC_VARIANT_TOOL:
            from gene_annotation_episode.episodic_workflow.root.library.somatic_variant_tools import execute_somatic_variant_tool
            return await execute_somatic_variant_tool(self, args, scope=scope,
                operation_key=operation_key, authority=molecular_authority)
        if name == ARSENIC_SPECIATION_TOOL:
            from gene_annotation_episode.episodic_workflow.root.library.arsenic_speciation_tools import execute_arsenic_speciation_tool
            return await execute_arsenic_speciation_tool(self, args, scope=scope,
                operation_key=operation_key, authority=molecular_authority)
        saved = self.store.db.execute("SELECT * FROM tool_operations WHERE operation_key=?", (operation_key,)).fetchone()
        if saved:
            if saved["name"] != name or saved["arguments"] != canonical(args) or saved["scope"] != canonical(scope):
                raise ContractError("operation_key_reused_for_different_work")
            try:
                if json.loads(saved['result']).get('status') in {'completed', 'partial'}:
                    self._check_molecular_source_bytes(name, args)
                    if name in {'public.literature.sequence_identity', 'source.sequence.scan', 'source.sequence.references'}:
                        from gene_annotation_episode.literature_sequence_discovery import protein_operand
                        protein_operand(self, args['subject_ref'], scope)
                    if name in {'source.sequence.scan', 'source.sequence.references', 'source.experimental.records'}:
                        received_location_source(self.store, args['source_ref'],
                            args.get('representation', 'original'),
                            permitted_inputs=self._permitted_record_refs.get(), scope=scope)
            except ContractError as error:
                return {'status': 'invalid', 'operation_ref': saved['id'], 'record_refs': [],
                    'changed_record_refs': [], 'result': None,
                    'feedback': {'category': 'arguments_or_reference', 'code': str(error)}}
            if name in RESTRICTION_ALIASES and restriction_work_reserved(self.store, operation_key):
                try:
                    return replay_restriction_work(self, name, args, scope=scope,
                        operation_key=operation_key, permitted_record_refs=self._permitted_record_refs.get())
                except (ContractError, ValueError, KeyError) as error:
                    # Report a current authority failure without replacing the
                    # original completed operation or exposing its result.
                    return {'status': 'invalid', 'operation_ref': saved['id'], 'record_refs': [],
                        'changed_record_refs': [], 'result': None, 'feedback': {
                            'category': 'arguments_or_reference',
                            'code': str(error) if isinstance(error, ValueError) else 'invalid_tool_input'}}
            if name == 'source.locate' and json.loads(saved['result'])['status'] == 'completed':
                try:
                    artifact = received_location_source(self.store, args['source_ref'], args['representation'],
                        permitted_inputs=self._permitted_record_refs.get(), scope=scope)
                    original = json.loads(saved['result'])
                    if (original['result']['artifact_ref'] != artifact['id']
                            or original['result']['total_bytes'] != artifact['size']):
                        raise ContractError('source_location_artifact_identity_conflict')
                except ContractError as error:
                    return {'status': 'invalid', 'operation_ref': saved['id'], 'record_refs': [],
                        'changed_record_refs': [], 'result': None,
                        'feedback': {'category': 'arguments_or_reference', 'code': str(error)}}
            if name == 'result.blast.hsp':
                from .library.blast_result_views import require_permitted_hsp
                try:
                    require_permitted_hsp(args.get('observation_ref'), self._permitted_record_refs.get())
                except ContractError as error:
                    return {'status': 'invalid', 'record_refs': [], 'changed_record_refs': [],
                        'result': None, 'feedback': {'category': 'arguments_or_reference', 'code': str(error)}}
            if name in PROTEIN_STRUCTURE_TOOLS:
                try:
                    input_authority = self._protein_structure_input_authority.get()
                    if input_authority is None:
                        raise ContractError('protein_structure_input_authority_required')
                    context, _ = molecular_authority
                    input_authority.authenticate_saved_operation(context, operation_key=operation_key,
                        name=name, arguments=args, scope=scope, outcome=json.loads(saved['result']))
                except (ContractError, ValueError, KeyError) as error:
                    return {'status': 'invalid', 'operation_ref': saved['id'], 'record_refs': [],
                        'changed_record_refs': [], 'result': None, 'feedback': {
                            'category': 'arguments_or_reference',
                            'code': str(error) if isinstance(error, ContractError) else 'protein_structure_saved_result_invalid'}}
            if name == FBA_TOOL:
                try:
                    if self.ordinary_flux_balance_backend is None:
                        raise ContractError('ordinary_fba_configuration_required')
                    self.ordinary_flux_balance_backend.authenticate_saved_operation(molecular_authority[0],
                        operation_key=operation_key, name=name, arguments=args, scope=scope,
                        outcome=json.loads(saved['result']))
                except (ContractError, ValueError, KeyError) as error:
                    return {'status': 'invalid', 'operation_ref': saved['id'], 'record_refs': [],
                        'changed_record_refs': [], 'result': None, 'feedback': {
                            'category': 'arguments_or_reference', 'code': str(error)}}
            if name == ALPHAFOLD_FILE_TOOL:
                try:
                    outcome = json.loads(saved['result'])
                    # Failed acquisition without a response has no Source to
                    # authenticate; its exact original failure stays cached.
                    if not (outcome.get('result') is None and outcome.get('status') in {
                            'invalid', 'unavailable', 'failed'}):
                        from .library.alphafold_acquisition_host import authenticate_saved_alphafold_file
                        authenticate_saved_alphafold_file(self, args,
                            authority=alphafold_file_authority, outcome=outcome)
                except (ContractError, ValueError, KeyError) as error:
                    code = str(error) if isinstance(error, ContractError) else 'data_acquisition_failed'
                    code = code if code in ALPHAFOLD_FAILURE_CODES else 'data_acquisition_failed'
                    return {'status': 'invalid', 'operation_ref': saved['id'], 'record_refs': [],
                        'changed_record_refs': [], 'result': failed_alphafold_receipt(code),
                        'feedback': {'category': 'arguments_or_reference', 'code': code}}
            if name == SRA_FILE_TOOL:
                try:
                    from gene_annotation_episode.ncbi_sra_acquisition_host import authenticate_saved_sra_file
                    authenticate_saved_sra_file(self, args, authority=sra_file_authority,
                        operation_key=operation_key, outcome=json.loads(saved['result']))
                except (ContractError, ValueError, KeyError, TypeError) as error:
                    code = str(error) if isinstance(error, ValueError) else 'sra_file_saved_outcome_conflict'
                    code = code if code in SRA_FILE_FAILURE_CODES else 'sra_file_saved_outcome_conflict'
                    return {'status': 'invalid', 'operation_ref': saved['id'], 'record_refs': [],
                        'changed_record_refs': [], 'result': failed_sra_file_receipt(code),
                        'feedback': {'category': 'arguments_or_reference', 'code': code}}
            if name == ENSEMBL_TOOL:
                try:
                    from gene_annotation_episode.ensembl_acquisition_host import authenticate_saved_ensembl_request
                    authenticate_saved_ensembl_request(self, args, authority=ensembl_authority,
                        outcome=json.loads(saved['result']))
                except (ContractError, ValueError, KeyError, TypeError) as error:
                    code = str(error) if isinstance(error, ValueError) else 'ensembl_saved_result_conflict'
                    code = code if code in ENSEMBL_FAILURE_CODES else 'ensembl_saved_result_conflict'
                    return {'status': 'invalid', 'operation_ref': saved['id'], 'record_refs': [],
                        'changed_record_refs': [], 'result': failed_ensembl_receipt(code),
                        'feedback': {'category': 'arguments_or_reference', 'code': code}}
            if name == ENCODE_TOOL and type(args) is dict and args.get('operation') == 'file':
                try:
                    from .library.encode_tools import authenticate_saved_encode_request
                    authenticate_saved_encode_request(self, args, authority=encode_authority,
                        outcome=json.loads(saved['result']))
                except (ContractError, ValueError, KeyError, TypeError) as error:
                    code = str(error) if isinstance(error, ContractError) else 'encode_saved_outcome_conflict'
                    code = code if code in ENCODE_FAILURE_CODES else 'encode_saved_outcome_conflict'
                    return {'status': 'invalid', 'operation_ref': saved['id'], 'record_refs': [],
                        'changed_record_refs': [], 'result': validate_encode_receipt({
                            'acquired': False, 'source_ref': None, 'data_ref': None, 'failure_code': code}),
                        'feedback': {'category': 'arguments_or_reference', 'code': code}}
            return json.loads(saved["result"])
        operation_ref = identity("operation", {"key": operation_key, "name": name, "arguments": args})
        result = {"status": "invalid", "operation_ref": operation_ref, "record_refs": [], "result": None, "feedback": None}
        try:
            if name in {"public.rfam.search", "public.rfam.collect"}:
                raise ContractError("rfam_requires_api_execution_episode")
            catalog = self.catalog(scope)
            if name not in catalog:
                raise ContractError("unknown_tool")
            try:
                validate_schema(args, catalog[name]["input_schema"])
            except ContractError as error:
                # Explain the existing schema failure without a second
                # validation or a new successful-path assessment.
                feedback = (mapper.parameter_schema_failure(error.__cause__)
                    if name == "reads.map" and error.__cause__ is not None else None)
                if feedback is not None:
                    raise ContractError(feedback["code"], detail=feedback["detail"]) from error
                raise
            self.store.validate_scope(scope)
            self._check_molecular_source_bytes(name, args)
            if name in RESTRICTION_ALIASES:
                return await self._restriction_operation_async(name, args, scope, operation_key)
            # Network acquisition happens before scientific publication. No
            # SQLite write transaction is held while waiting on a provider.
            snapshot = (self._estimate_native(args, scope) if name == 'execution.estimate' else
                await self.ordinary_flux_balance_backend.prepare(args, scope=scope, operation_key=operation_key,
                    authority=molecular_authority) if name == FBA_TOOL else
                await prepare_itc_work(self, args, scope=scope, operation_key=operation_key,
                    authority=molecular_authority) if name == ITC_TOOL else
                await prepare_liftover_work(self, args, scope=scope, operation_key=operation_key,
                    authority=molecular_authority) if name == LIFTOVER_TOOL else
                await prepare_circular_dichroism_work(self, args, scope=scope, operation_key=operation_key,
                    authority=molecular_authority) if name == CD_TOOL else
                await prepare_protein_structure_work(self, name, args, scope=scope, operation_key=operation_key,
                    authority=molecular_authority, input_authority=self._protein_structure_input_authority.get())
                    if name in PROTEIN_STRUCTURE_TOOLS else
                await self._prepare_sequence_work_async(name, args, scope) if name in {"sequence.align", "reads.align", "genes.predict"} else
                await self._document_async(name, args) if name.startswith(("source.archive.", "source.pdf.", "source.xlsx.")) else
                await self._native_cmsearch_async(args, scope) if name == "rna.cmsearch" else
                await self._native_mapping_async(args, scope) if name == "reads.map" else
                await self._alphafold_file_async(args, authority=alphafold_file_authority)
                    if name == ALPHAFOLD_FILE_TOOL else
                await self._sra_file_async(args, authority=sra_file_authority, operation_key=operation_key)
                    if name == SRA_FILE_TOOL else
                await self._ensembl_request_async(args, authority=ensembl_authority)
                    if name == ENSEMBL_TOOL else
                await self._encode_request_async(args, authority=encode_authority)
                    if name == ENCODE_TOOL else
                await self._acquire_async(name, args, scope, operation_key) if name.startswith("public.") else None)
            with self.store.transaction():
                try:
                    if name in PROTEIN_STRUCTURE_TOOLS:
                        if snapshot.get('version') == SAVED_WORK_VERSION:
                            from .library.protein_structure_publication import publish_protein_structure_action_result
                            result['result'], result['record_refs'] = publish_protein_structure_action_result(
                                self, snapshot, authority=molecular_authority)
                            if snapshot['redisplay'] is not None:
                                result['status'] = snapshot['redisplay']['status']
                                result['feedback'] = snapshot['redisplay']['feedback']
                            else:
                                incomplete = any(view['outcome']['version'] == 'protein_structure_action_unavailable_v1'
                                    or view['outcome'].get('state') != 'complete' for view in result['result']['views'])
                                result['status'] = 'partial' if result['result']['issues'] or incomplete else 'completed'
                                if result['status'] == 'partial':
                                    worker = snapshot['worker']
                                    execution = None if worker is None else worker['execution']
                                    failed_execution = execution is not None and (execution['outcome'] != 'returned'
                                        or execution['returncode'] != 0)
                                    result['feedback'] = {'category': 'execution' if failed_execution else 'representation',
                                        'code': 'protein_structure_selected_result_partial',
                                        'source_ref': result['result']['source_ref']}
                                    if failed_execution and execution['failure'] is not None:
                                        result['feedback']['cause_code'] = execution['failure']['code']
                        elif snapshot['bundle'] is None or snapshot['capture'] is None:
                            checked = validate_prepared_protein_structure_work(self, snapshot, authority=molecular_authority)
                            diagnostic_ref = self.store.artifact(canonical({
                                'version': 'protein_structure_terminal_diagnostic_v1',
                                'invocation': checked['invocation'], 'execution': checked['execution'],
                                'capture': checked['capture'], 'issues': checked['issues']}), 'application/json')
                            self._written.append(diagnostic_ref)
                            result.update(status='failed', record_refs=[diagnostic_ref],
                                result={'issues': checked['issues']}, feedback={
                                    'category': 'execution', 'code': 'protein_structure_bundle_unavailable',
                                    'diagnostic_ref': diagnostic_ref})
                        else:
                            from .library.protein_structure_publication import publish_protein_structure_action_result
                            result['result'], result['record_refs'] = publish_protein_structure_action_result(
                                self, snapshot, authority=molecular_authority)
                            incomplete = any(view['outcome']['version'] == 'protein_structure_action_unavailable_v1'
                                or view['outcome'].get('state') != 'complete' for view in result['result']['views'])
                            result['status'] = ('partial' if result['result']['issues'] or incomplete
                                or snapshot['bundle']['native_status'] != 'complete' else 'completed')
                            if result['status'] == 'partial':
                                result['feedback'] = {'category': ('execution'
                                    if snapshot['execution']['outcome'] != 'returned'
                                    or snapshot['execution']['returncode'] != 0 else 'representation'),
                                    'code': 'protein_structure_selected_result_partial',
                                    'source_ref': result['result']['source_ref']}
                    else:
                        result["result"], result["record_refs"] = self._perform(name, args, scope, snapshot)
                        result["status"] = "completed"
                    if name in ordinary_data_getters and not result["result"]["acquired"]:
                        result.update(status="partial", feedback={"category": "acquisition",
                            "code": result["result"]["failure_code"],
                            "source_ref": result["result"]["source_ref"]})
                        if (name == "public.ncbi.entrez"
                                and result["result"]["failure_code"] == "ncbi_entrez_native_error_response"
                                and result["result"]["source_ref"] is not None):
                            result["feedback"]["response"] = api_error_response(snapshot)
                            result["feedback"]["detail"] = {
                                "explanation": "The complete returned NCBI error response is included in feedback.response. "
                                    "For searches, inspect errorlist and querytranslation even when hits are present "
                                    "before choosing any revised request.",
                                "read_with": "source.read",
                                "read_query": {"source_ref": result["result"]["source_ref"],
                                    "representation": "original", "offset": 0}}
                    if name in ordinary_molecular_tools:
                        result['changed_record_refs'] = list(self._written)
                    if name == FBA_TOOL and result['result']['failures']:
                        result.update(status='partial', feedback={'category': 'numerical_execution',
                            'code': 'flux_balance_selected_result_partial', 'source_ref': result['result']['source_ref']})
                    if name in {ITC_TOOL, LIFTOVER_TOOL, CD_TOOL} and snapshot.get('operational_failure') is not None:
                        failure = snapshot['operational_failure']
                        result.update(status='partial', feedback={'category': 'execution',
                            'code': failure['code'], 'source_ref': result['result']['source_ref']})
                    elif name == ITC_TOOL and args['mode'] == 'fit' and result['result']['failure_location'] is not None:
                        result.update(status='partial', feedback={'category': 'numerical_execution',
                            'code': 'selected_itc_fit_failed',
                            'source_ref': result['result']['source_ref']})
                    elif name == LIFTOVER_TOOL and result['result']['failure'] is not None:
                        result.update(status='partial', feedback={'category': 'numerical_execution',
                            'code': result['result']['failure']['code'],
                            'source_ref': result['result']['source_ref']})
                    elif name == LIFTOVER_TOOL and result['result']['parsing_state'] in {'partial', 'invalid'}:
                        result.update(status='partial', feedback={'category': 'representation',
                            'code': 'liftover_native_rows_invalid',
                            'source_ref': result['result']['source_ref']})
                    elif name == CD_TOOL and snapshot['stored']['components']['issues']:
                        result.update(status='partial', feedback={'category': 'numerical_input',
                            'code': 'circular_dichroism_partial_measurements',
                            'source_ref': result['result']['source_ref']})
                    if name == "image.view":
                        # Only this host adapter can select a visual input. Never
                        # read attachment instructions from nested provider/model
                        # content, historical child work or a query response.
                        result["visual_inputs"] = [visual_input(self.store, result["result"]["view_ref"])]
                    if name == "reads.align" and result["result"].get("errors"):
                        result.update(status="partial" if result["record_refs"] else
                            "failed" if any(row.get("category") == "execution" for row in result["result"]["errors"]) else "invalid",
                            feedback={"category": "partial_execution" if result["record_refs"] else
                                "execution" if any(row.get("category") == "execution" for row in result["result"]["errors"]) else "arguments_or_reference",
                                "code": "selected_read_alignments_incomplete",
                                "rows": result["result"]["errors"]})
                    if name == "reads.map" and result["result"].get("projection_error_count"):
                        result.update(status="partial", feedback={"category": "representation",
                            "code": "native_mapping_rows_partially_projected", "rows": result["result"]["projection_errors"],
                            "error_count": result["result"]["projection_error_count"],
                            "error_source_ref": result["result"]["error_source_ref"]})
                    if name == "reads.map" and result["result"].get("resource_failure"):
                        result.update(status="partial" if result["result"]["reported_placement_count"] else "failed",
                            feedback={"category": "execution", "code": "local_job_resource_limit",
                                "source_ref": result["result"]["source_ref"],
                                "phase": result["result"]["resource_failure"]["phase"],
                                **result["result"]["resource_failure"]["operational"]})
                    elif name == "reads.map" and result["result"]["native_returncode"] != 0:
                        result.update(status="partial" if result["result"]["reported_placement_count"] else "failed",
                            feedback={"category": "execution", "code": "native_mapping_error",
                                "native_phase": result["result"]["native_phase"],
                                "native_returncode": result["result"]["native_returncode"],
                                "source_ref": result["result"]["source_ref"]})
                    if name == "material.parse":
                        attempt = result["result"]["parse_attempt"]
                        result["status"] = attempt["status"]
                        if attempt["status"] != "completed":
                            result["feedback"] = {"category": "representation", "code": attempt["code"],
                                "parse_ref": attempt["id"]}
                    if name == "source.xlsx.rows" and result["result"]["status"] != "completed":
                        result.update(status=result["result"]["status"],
                            feedback={"category": "representation", "code": "xlsx_rows_partially_decoded",
                                "source_ref": result["result"]["source_ref"],
                                "cell_error_count": result["result"]["cell_error_count"],
                                "row_error_count": result["result"]["row_error_count"],
                                "parse_failures": result["result"]["parse_failures"]})
                    if name in {"public.rhea.search", "public.rhea.reaction", "public.chebi.search", "public.chebi.compound"} and result["result"].get("projection_errors"):
                        result.update(status="partial", feedback={"category": "representation",
                            "code": "chemistry_rows_partially_projected",
                            "source_ref": result["result"]["source_ref"],
                            "rows": result["result"]["projection_errors"]})
                    if name in {"public.uniprot.record", "public.uniprot.search"} and result["result"].get("projection_errors"):
                        result.update(status="partial", feedback={"category": "representation",
                            "code": "uniprot_rows_partially_projected",
                            "source_ref": result["result"]["source_ref"],
                            "rows": result["result"]["projection_errors"]})
                    if name in {"public.rfam.search", "public.rfam.collect", "public.blast.search", "public.blast.collect"} and result["result"].get("projection_errors"):
                        result.update(status="partial", feedback={"category": "representation",
                            "code": "blast_rows_partially_projected" if name.startswith("public.blast.") else "rfam_rows_partially_projected", "source_ref": result["result"]["source_ref"],
                            "rows": result["result"]["projection_errors"]})
                    if isinstance(snapshot, RfamModelSnapshots) and snapshot.metadata_error:
                        error = snapshot.metadata_error
                        result.update(status="partial", feedback={**api_error_feedback(error), "category": "provider",
                            "code": "rfam_metadata_acquisition_failed", "cause_code": error.code,
                            "diagnostic_ref": self._acquisition_diagnostic(error),
                            "retained_model_ref": result["result"]["model_ref"]})
                    if isinstance(snapshot, PmcFiles) and snapshot.error:
                        result.update(status="partial", feedback={**api_error_feedback(snapshot.error),
                            "category": "provider", "code": snapshot.error.code,
                            "diagnostic_ref": self._acquisition_diagnostic(snapshot.error)})
                    if name in {"public.pmc.files", "public.pmc.asset"} and result["result"].get("representation_feedback"):
                        feedback = result["result"]["representation_feedback"]
                        if isinstance(snapshot, PmcFiles) and snapshot.error:
                            feedback = {**feedback, "acquisition_error": result["feedback"]}
                        result.update(status="partial", feedback=feedback)
                except Exception as error:
                    # Keep completed independent publications. A failed parser
                    # or later row does not erase an acquired source or an
                    # earlier valid candidate. Report the exact retained rows.
                    if not self._written:
                        raise
                    if name == ITC_TOOL:
                        retained, references = partial_itc_publication(self, snapshot)
                        result.update(status='partial', record_refs=references,
                            changed_record_refs=list(self._written), result=retained,
                            feedback={'category': 'representation', 'code': 'itc_result_projection_failed',
                                'diagnostic_ref': self.store.artifact(f'{type(error).__name__}: {error}', 'text/plain')})
                    elif name in PROTEIN_STRUCTURE_TOOLS:
                        # Retained native work survives a publication failure.
                        # A Source or unfinished descriptor is not a qualified
                        # scientific delivery and grants no private controls.
                        result.update(status='partial', record_refs=[], changed_record_refs=[],
                            result={'retained_record_refs': []}, feedback={
                                'category': 'representation', 'code': 'protein_structure_result_publication_incomplete',
                                'diagnostic_ref': self.store.artifact(f'{type(error).__name__}: {error}', 'text/plain')})
                    elif name in ordinary_data_getters:
                        sources = [reference for reference in dict.fromkeys(self._written)
                            if self.store.get(reference).get("record_type") == "source"
                            and self.store.get(reference).get("provider") == getter_source_providers.get(name, name)]
                        failure_code = (str(error) if isinstance(error, ContractError)
                            else "data_acquisition_publication_incomplete")
                        if name in getter_failure_codes and failure_code not in getter_failure_codes[name]:
                            failure_code = 'data_acquisition_publication_incomplete'
                        result.update(status="partial", record_refs=sources, changed_record_refs=sources,
                            result={"acquired": False, "source_ref": sources[0] if sources else None,
                                "data_ref": None, "failure_code": failure_code}, feedback={
                                "category": "acquisition", "code": failure_code,
                                "diagnostic_ref": self.store.artifact(f"{type(error).__name__}: {error}", "text/plain")})
                        if name == SCREEN_TOOL:
                            result["result"] = validate_screen_receipt(result["result"])
                        elif name in getter_validators:
                            result["result"] = getter_validators[name](result["result"])
                    else:
                        result.update(status="partial", record_refs=list(dict.fromkeys(self._written)),
                            result={"retained_record_refs": list(dict.fromkeys(self._written))},
                            feedback={"category": "partial_execution", "code": str(error) if isinstance(error, ContractError) else "adapter_partial_result",
                                      "diagnostic_ref": self.store.artifact(f"{type(error).__name__}: {error}", "text/plain")})
                    if isinstance(error, ContractError) and error.detail:
                        result["feedback"]["detail"] = error.detail
                    result["feedback"].update(api_error_feedback(error))
                self._save(operation_key, name, args, scope, result)
            return result
        except (RestrictionOperationUnpublished, MolecularOperationUnpublished):
            # Leave runtime_actions.result unfinished so restore re-enters the
            # same selected operation and original handle, before any credit.
            raise
        except AcquisitionError as error:
            operational = error.operational or {}
            diagnostic = (operational.get("cause") or {}).get("diagnostic_ref")
            if diagnostic is None and error.snapshot is not None:
                from dataclasses import asdict
                metadata = asdict(error.snapshot)
                metadata.pop("content")
                metadata["content_ref"] = self.store.artifact(error.snapshot.content, error.snapshot.media_type)
                diagnostic = self.store.artifact(canonical(metadata), "application/json")
            elif diagnostic is None and error.diagnostic is not None:
                diagnostic = self.store.artifact(canonical({"representation": "local_exception",
                    "details": error.diagnostic}), "application/json")
            result.update(status="unavailable" if error.code.endswith(("not_configured", "not_installed", "missing")) else "failed",
                          feedback={**api_error_feedback(error),
                              "category": "execution" if error.code.startswith("local_job_") or error.phase in {
                              'native_execution', 'local_execution', 'local_preflight', 'local_admission'} else "provider", "code": error.code, "retry_after": error.retry_after,
                                    "job_ref": error.job_ref, "diagnostic_ref": diagnostic,
                                    **({"phase": error.phase} if error.phase is not None else {}),
                                    **operational})
            if name in {ITC_TOOL, LIFTOVER_TOOL, CD_TOOL} and operational.get('known_terminal') is True:
                result['status'] = 'failed'
        except (ContractError, ValueError, KeyError) as error:
            result["feedback"] = {**api_error_feedback(error), "category": "arguments_or_reference",
                "code": str(error) if isinstance(error, ContractError) else "invalid_tool_input"}
            if isinstance(error, ContractError) and error.detail:
                result["feedback"]["detail"] = error.detail
        except Exception as error:
            diagnostic = self.store.artifact(f"{type(error).__name__}: {error}", "text/plain")
            result.update(status="failed", feedback={**api_error_feedback(error),
                "category": "execution", "code": "adapter_execution_failed",
                                                    "diagnostic_ref": diagnostic})
        # Failed attempts are durable audit, not acquired scientific units.
        # An operation key identifies this attempt; later attempts need a new key.
        if name in ordinary_data_getters and result["result"] is None:
            failure_code = (result.get("feedback") or {}).get("code", "data_acquisition_failed")
            if name in getter_failure_codes and failure_code not in getter_failure_codes[name]:
                failure_code = 'invalid_tool_input' if result['status'] == 'invalid' else 'data_acquisition_failed'
            result["result"] = {"acquired": False, "source_ref": None, "data_ref": None,
                "failure_code": failure_code}
            if name == SCREEN_TOOL:
                result["result"] = validate_screen_receipt(result["result"])
            elif name in getter_validators:
                result["result"] = getter_validators[name](result["result"])
        with self.store.transaction():
            self._save(operation_key, name, args, scope, result)
        return result

    async def _restriction_operation_async(self, name, args, scope, operation_key):
        try:
            await prepare_restriction_work(self, name, args, scope=scope,
                operation_key=operation_key, permitted_record_refs=self._permitted_record_refs.get())
            with self.store.transaction():
                result = publish_restriction_work(self, operation_key)
                self._written.extend(result['record_refs'])
                self._save(operation_key, name, args, scope, result)
        except Exception as error:
            if restriction_work_reserved(self.store, operation_key):
                raise RestrictionOperationUnpublished(str(error)) from error
            raise
        # The original scientific outcome is already committed. A cleanup
        # failure must not reach the generic failed-attempt INSERT path.
        try:
            retire_restriction_work(self, operation_key)
        except (OSError, ContractError, AcquisitionError):
            pass  # The durable job memo retains cleanup failure and scratch.
        except Exception as error:
            # Preserve the committed operation on an unexpected cleanup error
            # as well; generic failed-attempt recording would insert it twice.
            raise RestrictionOperationUnpublished(str(error)) from error
        return result

    def _save(self, key: str, name: str, args: dict, scope: dict | None, result: dict) -> None:
        failures = self._grading_failures.get()
        if failures:
            if result['status'] == 'completed':
                result['status'] = 'partial'
            if result.get('feedback') is None:
                result['feedback'] = {'category': 'grading_input',
                    'code': 'tool_grading_input_rejected', 'failures': list(failures)}
            else:
                # Preserve an execution/provider/representation failure already
                # reported for the same selected action.
                result['feedback']['grading_failures'] = list(failures)
        receipts = self._native_execution_refs.get()
        if receipts:
            result['native_execution_refs'] = list(dict.fromkeys(receipts))
            result['record_refs'] = list(dict.fromkeys([*result['record_refs'], *receipts]))
        batch = self._publication_batch.get()
        if batch is not None:
            result["published_batch"] = dict(batch)
        self.store.db.execute("INSERT INTO tool_operations VALUES(?,?,?,?,?,?)",
            (key, result["operation_ref"], name, canonical(args), canonical(scope), canonical(result)))

