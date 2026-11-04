"""Read-only ELF metadata inspection for bounded verification code."""
import struct


def elf64_x86_metadata(raw):
    """Inspect supplied bytes only; no loader, ldd, executable or discovery call.

    Program headers bind file-backed dynamic strings. Static executables may
    legitimately have neither PT_INTERP nor PT_DYNAMIC. This inspection does
    not attest that a loader or any declared dependency can actually run.
    """
    def require(condition, code):
        if not condition:
            raise ValueError(code)

    def read_at(offset, length):
        require(type(offset) is int and type(length) is int and offset >= 0 and length >= 0
            and offset <= len(raw) and length <= len(raw) - offset, "elf_range_invalid")
        return raw[offset:offset + length]

    ident = read_at(0, 16)
    require(ident[:4] == b"\x7fELF" and ident[4] == 2 and ident[5] == 1
        and ident[6] == 1 and ident[7] in (0, 3) and ident[8] == 0,
        "elf64_little_endian_required")
    values = struct.unpack("<HHIQQQIHHHHHH", read_at(16, 48))
    kind, machine, version, entry, phoff, shoff, flags, ehsize, phsize, phcount, shsize, shcount, shnames = values
    require(kind in (2, 3) and machine == 62 and version == 1 and ehsize >= 64,
        "linux_x86_64_executable_required")
    require(phcount not in (0, 65535) and phsize >= 56 and phoff <= len(raw)
        and phcount <= (len(raw) - phoff) // phsize, "elf_program_headers_invalid")
    headers, loads, dynamics, interpreters = [], [], [], []
    for index in range(phcount):
        row = struct.unpack("<IIQQQQQQ", read_at(phoff + index * phsize, 56))
        ptype, pflags, offset, address, physical, filesz, memsz, alignment = row
        read_at(offset, filesz)
        item = dict(index=index, type=ptype, flags=pflags, offset=offset, virtual_address=address,
            physical_address=physical, file_size=filesz, memory_size=memsz, alignment=alignment)
        headers.append(item)
        if ptype == 1:
            require(memsz >= filesz, "elf_load_geometry_invalid")
            loads.append(item)
        elif ptype == 2:
            dynamics.append(item)
        elif ptype == 3:
            value = read_at(offset, filesz)
            require(bool(value) and value.endswith(b"\0") and b"\0" not in value[:-1], "elf_interpreter_invalid")
            interpreters.append(value[:-1].decode("ascii"))
    require(bool(loads) and len(interpreters) <= 1 and len(dynamics) <= 1,
        "elf_execution_metadata_invalid")
    entries = []
    if dynamics:
        dynamic = dynamics[0]
        require(dynamic["file_size"] % 16 == 0, "elf_dynamic_geometry_invalid")
        terminated = False
        for position in range(dynamic["offset"], dynamic["offset"] + dynamic["file_size"], 16):
            tag, value = struct.unpack("<qQ", read_at(position, 16))
            entries.append({"tag": tag, "value": value})
            if tag == 0:
                terminated = True
                break
        require(terminated, "elf_dynamic_unterminated")
    string_tags = {1: "needed", 14: "sonames", 15: "rpaths", 29: "runpaths"}
    strings = {name: [] for name in string_tags.values()}
    if any(row["tag"] in string_tags for row in entries):
        addresses = [row["value"] for row in entries if row["tag"] == 5]
        sizes = [row["value"] for row in entries if row["tag"] == 10]
        require(len(addresses) == len(sizes) == 1, "elf_dynamic_strings_unbound")
        address, size = addresses[0], sizes[0]
        offsets = {row["offset"] + address - row["virtual_address"] for row in loads
            if row["virtual_address"] <= address and address - row["virtual_address"] <= row["file_size"]
            and size <= row["file_size"] - (address - row["virtual_address"])}
        require(len(offsets) == 1, "elf_dynamic_strings_unbound")
        table = read_at(offsets.pop(), size)
        for row in entries:
            if row["tag"] not in string_tags:
                continue
            index = row["value"]
            require(index < len(table), "elf_dynamic_string_invalid")
            end = table.find(b"\0", index)
            require(end >= index, "elf_dynamic_string_invalid")
            strings[string_tags[row["tag"]]].append(table[index:end].decode("ascii"))
    return dict(elf_class=64, byte_order="little", osabi=ident[7], abi_version=ident[8],
        machine=machine, type=kind, entry=entry, program_headers=headers,
        interpreter=interpreters[0] if interpreters else None,
        dynamic_present=bool(dynamics), dynamic_entries=entries, **strings,
        section_header_offset=shoff, section_header_size=shsize, section_header_count=shcount,
        section_name_index=shnames, flags=flags, deployment_verified=False)
