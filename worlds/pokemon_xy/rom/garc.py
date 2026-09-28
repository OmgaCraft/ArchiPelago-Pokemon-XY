"""
[FR] Archives GARC de Pokémon X/Y (version 0x0400), lecture et réécriture.

Structure (d'après pkNX, pkNX.Containers/GARC) :
  en-tête « CRAG » (0x1C), puis sections FATO (index), FATB (positions), FIMB (données).
Chaque entrée FATB a un vecteur de 32 bits : un sous-fichier par bit levé
(start, end, length relatifs au début des données FIMB). Les données sont
alignées sur 4 octets et complétées par des 0xFF.
"""

import struct
from typing import List, Optional

GARC_MAGIC = b"CRAG"
FATO_MAGIC = b"OTAF"
FATB_MAGIC = b"BTAF"
FIMB_MAGIC = b"BMIF"
VERSION_4 = 0x0400
PAD_TO = 4


class GARCError(Exception):
    pass


class GARC:
    def __init__(self, data: bytes):
        magic, header_size, bom, version, chunks, data_offset, file_size, largest = \
            struct.unpack_from("<4sIHHIIII", data, 0)
        if magic != GARC_MAGIC or bom != 0xFEFF or chunks != 4:
            raise GARCError("En-tête GARC invalide.")
        if version != VERSION_4 or header_size != 0x1C:
            raise GARCError(f"Version de GARC non prise en charge : 0x{version:04X}.")

        position = header_size
        fato_magic, fato_size, count = struct.unpack_from("<4sIH", data, position)
        if fato_magic != FATO_MAGIC:
            raise GARCError("Section FATO introuvable.")
        position += fato_size

        fatb_magic, fatb_size, fatb_count = struct.unpack_from("<4sII", data, position)
        if fatb_magic != FATB_MAGIC or fatb_count != count:
            raise GARCError("Section FATB invalide.")
        entries_position = position + 0xC
        position += fatb_size

        fimb_magic, _fimb_header, _fimb_size = struct.unpack_from("<4sII", data, position)
        if fimb_magic != FIMB_MAGIC or position + 0xC != data_offset:
            raise GARCError("Section FIMB invalide.")

        # files[i][bit] = contenu du sous-fichier, None si absent.
        self.files: List[List[Optional[bytes]]] = []
        cursor = entries_position
        for _ in range(count):
            vector = struct.unpack_from("<I", data, cursor)[0]
            cursor += 4
            subfiles: List[Optional[bytes]] = [None] * 32
            for bit in range(32):
                if vector & (1 << bit):
                    start, _end, length = struct.unpack_from("<III", data, cursor)
                    cursor += 12
                    subfiles[bit] = data[data_offset + start:data_offset + start + length]
            self.files.append(subfiles)

    def __len__(self) -> int:
        return len(self.files)

    def get(self, index: int, subfile: int = 0) -> bytes:
        data = self.files[index][subfile]
        if data is None:
            raise GARCError(f"Sous-fichier {index}/{subfile} absent.")
        return data

    def set(self, index: int, data: bytes, subfile: int = 0) -> None:
        if self.files[index][subfile] is None:
            raise GARCError(f"Sous-fichier {index}/{subfile} absent.")
        self.files[index][subfile] = bytes(data)

    def build(self) -> bytes:
        entries = bytearray()
        offsets = []
        blob = bytearray()
        largest = 0
        for subfiles in self.files:
            offsets.append(len(entries))
            vector = sum(1 << bit for bit, sub in enumerate(subfiles) if sub is not None)
            entries += struct.pack("<I", vector)
            for sub in subfiles:
                if sub is None:
                    continue
                start = len(blob)
                blob += sub
                blob += b"\xFF" * (-len(sub) % PAD_TO)
                entries += struct.pack("<III", start, len(blob), len(sub))
                largest = max(largest, len(sub))

        fato = struct.pack("<4sIHH", FATO_MAGIC, 0xC + 4 * len(offsets), len(offsets), 0xFFFF)
        fato += b"".join(struct.pack("<I", o) for o in offsets)
        fatb = struct.pack("<4sII", FATB_MAGIC, 0xC + len(entries), len(self.files)) + entries
        fimb = struct.pack("<4sII", FIMB_MAGIC, 0xC, len(blob))
        data_offset = 0x1C + len(fato) + len(fatb) + len(fimb)
        header = struct.pack("<4sIHHIIII", GARC_MAGIC, 0x1C, 0xFEFF, VERSION_4, 4,
                             data_offset, data_offset + len(blob), largest)
        return bytes(header + fato + fatb + fimb + blob)
