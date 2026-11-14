def install_primary_result_readers(owner):
    from gene_annotation_episode.episodic_workflow.root.a104.scientific_process.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.native_hmmer_result_acquisition import NativeHMMERResultAcquisition
    owner.native_hmmer_results = NativeHMMERResultAcquisition(owner)
    from gene_annotation_episode.episodic_workflow.root.a104.scientific_process.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.native_blast_masking_result_acquisition import NativeBLASTMaskingResultAcquisition
    from gene_annotation_episode.episodic_workflow.root.a104.library.native_blast_masking_returns import NativeBLASTMaskingReturns
    owner.native_blast_masking_results = NativeBLASTMaskingResultAcquisition(owner)
    owner.native_blast_masking_returns = NativeBLASTMaskingReturns(owner)
    from gene_annotation_episode.episodic_workflow.root.a104.scientific_process.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.native_blast_utility_result_acquisition import NativeBLASTUtilityResultAcquisition
    from gene_annotation_episode.episodic_workflow.root.a104.library.native_blast_utility_returns import NativeBLASTUtilityReturns
    owner.native_blast_utility_results = NativeBLASTUtilityResultAcquisition(owner)
    owner.native_blast_utility_returns = NativeBLASTUtilityReturns(owner)
    owner.native_blast_results = owner.native_blast_returns = None
    owner.native_blast_standard_database_results = owner.native_blast_standard_database_returns = None
    if any((configuration.get('native_blast_standard_database') for configuration in owner.resources.values())):
        from gene_annotation_episode.episodic_workflow.root.a104.scientific_process.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.native_blast_standard_database_result_acquisition import StandardBLASTDatabaseResultAcquisition
        from gene_annotation_episode.episodic_workflow.root.a104.library.native_blast_standard_database_returns import StandardBLASTDatabaseReturns
        owner.native_blast_standard_database_results = StandardBLASTDatabaseResultAcquisition(owner)
        owner.native_blast_standard_database_returns = StandardBLASTDatabaseReturns(owner)
    owner.native_blast_database_results = owner.native_blast_database_returns = None
    if any((configuration.get('native_blast_database') for configuration in owner.resources.values())):
        from gene_annotation_episode.episodic_workflow.root.a104.scientific_process.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.native_blast_database_result_acquisition import NativeBLASTDatabaseResultAcquisition
        from gene_annotation_episode.episodic_workflow.root.a104.library.native_blast_database_returns import NativeBLASTDatabaseReturns
        owner.native_blast_database_results = NativeBLASTDatabaseResultAcquisition(owner)
        owner.native_blast_database_returns = NativeBLASTDatabaseReturns(owner)
    if any((configuration.get('native_blast') for configuration in owner.resources.values())):
        from gene_annotation_episode.episodic_workflow.root.a104.scientific_process.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.native_blast_result_acquisition import NativeBLASTResultAcquisition
        from gene_annotation_episode.episodic_workflow.root.a104.library.native_blast_returns import NativeBLASTReturns
        owner.native_blast_results = NativeBLASTResultAcquisition(owner)
        owner.native_blast_returns = NativeBLASTReturns(owner)

def install_preparation_result_readers(owner):
    owner.native_hmmer_preparation_results = owner.native_hmmer_preparation_returns = None
    if any((configuration.get('native_hmmer_preparation') for configuration in owner.resources.values())):
        from gene_annotation_episode.episodic_workflow.root.a104.scientific_process.hpc_work_planning.hpc_allocation_execution.execution_result_acquisition.native_hmmer_preparation_result_acquisition import NativeHmmerPreparationResultAcquisition
        from gene_annotation_episode.episodic_workflow.root.a104.native_hmmer_preparation_returns import NativeHmmerPreparationReturns
        owner.native_hmmer_preparation_results = NativeHmmerPreparationResultAcquisition(owner)
        owner.native_hmmer_preparation_returns = NativeHmmerPreparationReturns(owner)
