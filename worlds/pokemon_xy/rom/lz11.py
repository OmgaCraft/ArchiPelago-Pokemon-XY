"""
[FR] Compression LZ11 (en-tête 0x11) utilisée par certaines archives du jeu (rencontres sauvages).

Décodage complet ; l'encodeur écrit uniquement des octets littéraux (aucune référence arrière) :
le fichier est un peu plus gros mais reste un LZ11 valide, que le jeu décompresse normalement.
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
    size = len(data)
    if size > 0xFFFFFF:
        header = b"\x11\x00\x00\x00" + struct.pack("<I", size)
    else:
        header = bytes([0x11, size & 0xFF, (size >> 8) & 0xFF, (size >> 16) & 0xFF])
    out = bytearray(header)
    for start in range(0, size, 8):
        block = data[start:start + 8]
        out.append(0)  # huit octets littéraux : tous les bits de contrôle à 0
        out += block
    return bytes(out)
