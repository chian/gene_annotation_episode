import os
if 'GENE_EPISODE_FRAME_CAPTURE_AUDIT' in os.environ:
    from pathlib import Path
    from gene_annotation_episode.runtime import Workflow
    from test_local_commission_frame_reconstruction import audited_capture
    Workflow.capture_local_commission_frame = audited_capture(
        Workflow.capture_local_commission_frame,
        Path(os.environ['GENE_EPISODE_FRAME_CAPTURE_AUDIT']))
