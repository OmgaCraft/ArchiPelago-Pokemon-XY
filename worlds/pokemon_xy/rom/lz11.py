"""
[FR] Compression LZ11 (en-tête 0x11) utilisée par certaines archives du jeu (rencontres sauvages).

Décodage complet et encodeur avec références arrière (glouton, fenêtre de 4 Kio) : les fichiers
recompressés ont une taille proche de l'original, comme ceux que le jeu attend.
"""

import struct


class LZ11Error(Exception):
    pass


def is_lz11(data: bytes) -> bool:
    return len(data) >= 4 and data[0] == 0x11


def decompress(data: bytes) -> bytes:
    if not is_lz11(data):
        raise LZ11Error("Pas de l'LZ11.")
    size = data[1] | (data[2] << 8) | (data[3] << 16)
    position = 4
    if size == 0:
        size = struct.unpack_from("<I", data, 4)[0]
        position = 8
    out = bytearray()
    while len(out) < size:
        flags = data[position]
        position += 1
        for bit in range(7, -1, -1):
            if len(out) >= size:
                break
            if not flags & (1 << bit):
                out.append(data[position])
                position += 1
                continue
            first = data[position]
            indicator = first >> 4
            if indicator == 0:
                length = (((first & 0x0F) << 4) | (data[position + 1] >> 4)) + 0x11
                offset = (((data[position + 1] & 0x0F) << 8) | data[position + 2]) + 1
                position += 3
            elif indicator == 1:
                length = (((first & 0x0F) << 12) | (data[position + 1] << 4) | (data[position + 2] >> 4)) + 0x111
                offset = (((data[position + 2] & 0x0F) << 8) | data[position + 3]) + 1
                position += 4
            else:
                length = indicator + 1
                offset = (((first & 0x0F) << 8) | data[position + 1]) + 1
                position += 2
            if offset > len(out):
                raise LZ11Error("Référence arrière invalide.")
            for _ in range(length):
                out.append(out[-offset])
    return bytes(out[:size])


def compress(data: bytes) -> bytes:
    """
    Compresse en LZ11 avec références arrière (recherche gloutonne du plus long motif dans les 4 Kio
    précédents), pour produire des fichiers de taille proche de l'original.
    """
    size = len(data)
    if size > 0xFFFFFF or size == 0:
        out = bytearray([0x11, 0, 0, 0]) + struct.pack("<I", size)
    else:
        out = bytearray([0x11, size & 0xFF, (size >> 8) & 0xFF, (size >> 16) & 0xFF])
    window, max_length = 0x1000, 0x10110
    table = {}
    position = 0
    while position < size:
        flag_index = len(out)
        out.append(0)
        flags = 0
        for bit in range(7, -1, -1):
            if position >= size:
                break
            best_length = best_distance = 0
            if position + 3 <= size:
                key = data[position:position + 3]
                for candidate in reversed(table.get(key, ())):
                    distance = position - candidate
                    if distance > window:
                        break
                    length = 3
                    limit = min(max_length, size - position)
                    while length < limit and data[candidate + length] == data[position + length]:
                        length += 1
                    if length > best_length:
                        best_length, best_distance = length, distance
                        if length == limit:
                            break
            if best_length >= 3:
                flags |= 1 << bit
                offset = best_distance - 1
                if best_length <= 0x10:
                    out += bytes([((best_length - 1) << 4) | (offset >> 8), offset & 0xFF])
                elif best_length <= 0x110:
                    value = best_length - 0x11
                    out += bytes([value >> 4, ((value & 0xF) << 4) | (offset >> 8), offset & 0xFF])
                else:
                    value = best_length - 0x111
                    out += bytes([0x10 | (value >> 12), (value >> 4) & 0xFF, ((value & 0xF) << 4) | (offset >> 8),
                                  offset & 0xFF])
                step = best_length
            else:
                out.append(data[position])
                step = 1
            for covered in range(position, min(position + step, size - 2)):
                bucket = table.setdefault(data[covered:covered + 3], [])
                bucket.append(covered)
                if len(bucket) > 64:
                    del bucket[0]
            position += step
        out[flag_index] = flags
    return bytes(out)
