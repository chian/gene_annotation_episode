"""Reading a held DNA record's sequence through a reader (a custody reader or a scoped store)."""


def record_sequence(reader, record_ref):
    """The sequence (upper case) of the held record ``record_ref``, read from its ``sequence_ref`` artifact."""
    return reader.get_artifact(reader.get(record_ref)['sequence_ref']).decode('ascii').strip().upper()


__all__ = ['record_sequence']
