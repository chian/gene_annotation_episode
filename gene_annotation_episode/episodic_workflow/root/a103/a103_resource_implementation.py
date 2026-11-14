"""A103's actual parent-private homology resource implementation bytes."""
from pathlib import Path


def resource_implementation_bytes():
    directory = Path(__file__).parent
    # Only the two fixed parent homes and their six predefined children belong
    # to this implementation; invocation keys never contribute source paths.
    homes = (
        '',
        'homology_job_submission',
        'homology_job_monitoring',
        'homology_result_acquisition',
        'legacy_improvement',
        'legacy_improvement/homology_job_submission',
        'legacy_improvement/homology_job_monitoring',
        'legacy_improvement/homology_result_acquisition',
    )
    files = [directory / 'homology_query.py', directory / 'homology_service_setup.py']
    for home in homes:
        if home:
            own = sorted((directory / home).glob('*.py'))
        else:
            from .implementation import annotation_implementation_files
            own = list(annotation_implementation_files())
        if not own or not (directory / home / 'episode.py').is_file():
            raise ValueError('parent_private_homology_source_unavailable:' + home)
        files.extend(own)
    files.append(directory / 'resource_information.py')
    return b''.join(path.read_bytes() for path in files)
