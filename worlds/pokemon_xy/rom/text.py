"""
[FR] Fichiers texte de Pokémon X/Y (format Gen 6), lecture et réécriture.

D'après pkNX (pkNX.Structures/Text/TextFile.cs) : une section unique, une table
(offset, longueur) par ligne, puis les lignes en UTF-16 chiffrées par un XOR
dont la clé dépend du numéro de ligne. Les variables (nom du joueur, etc.)
sont gardées telles quelles : on ne remplace que des lignes entières.
"""

import struct
from typing import List

KEY_BASE = 0x7C89
KEY_ADVANCE = 0x2983
KEY_VARIABLE = 0x0010


class TextError(Exception):
    pass


def _crypt(data: bytes, key: int) -> bytes:
    out = bytearray(data)
    for i in range(0, len(out), 2):
        out[i] ^= key & 0xFF
        out[i + 1] ^= key >> 8
        key = ((key << 3) | (key >> 13)) & 0xFFFF
    return bytes(out)


def _line_key(index: int) -> int:
    return (KEY_BASE + KEY_ADVANCE * index) & 0xFFFF


class TextFile:
    def __init__(self, data: bytes):
        sections, count, total, initial_key, section_offset = struct.unpack_from("<HHIII", data, 0)
        if sections != 1 or initial_key != 0 or section_offset + total != len(data):
            raise TextError("Fichier texte invalide.")
        # Lignes déchiffrées, en unités UTF-16, sans le terminateur 0.
        self.lines: List[List[int]] = []
        for index in range(count):
            offset, length = struct.unpack_from("<iH", data, section_offset + 4 + index * 8)
            raw = data[section_offset + offset:section_offset + offset + length * 2]
            units = list(struct.unpack(f"<{length}H", _crypt(raw, _line_key(index))))
            if units and units[-1] == 0:
                units.pop()
            self.lines.append(units)

    def get_plain(self, index: int) -> str:
        """Texte lisible de la ligne ; les variables apparaissent comme « {VAR} »."""
        units, out, i = self.lines[index], [], 0
        while i < len(units):
            unit = units[i]
            if unit == 0:
                break  # terminateur : la suite n'est que du remplissage
            if unit == KEY_VARIABLE and i + 1 < len(units):
                i += 2 + units[i + 1]
                out.append("{VAR}")
                continue
            out.append(chr(unit))
            i += 1
        return "".join(out)

    def set_plain(self, index: int, text: str) -> None:
        """Remplace une ligne par un texte simple (sans variables)."""
        self.lines[index] = [ord(c) for c in text]

    def build(self) -> bytes:
        count = len(self.lines)
        table = bytearray()
        blob = bytearray()
        base = 4 + count * 8
        for index, units in enumerate(self.lines):
            encoded = _crypt(struct.pack(f"<{len(units) + 1}H", *units, 0), _line_key(index))
            if len(encoded) % 4 == 2:
                encoded += b"\0\0"  # alignement sur 4 octets, comme le jeu
            table += struct.pack("<iHH", base + len(blob), len(units) + 1, 0)
            blob += encoded
        section = struct.pack("<I", 4 + len(table) + len(blob)) + table + blob
        header = struct.pack("<HHIII", 1, count, len(section), 0, 0x10)
        return header + section
