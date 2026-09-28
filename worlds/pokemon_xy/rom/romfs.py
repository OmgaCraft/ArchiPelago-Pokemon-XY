"""
[FR] Lecture de la RomFS d'un dump 3DS (.3ds/.cci) DÉCHIFFRÉ.

Formats décrits sur 3dbrew (NCSD, NCCH, RomFS/IVFC). Seule la lecture est
implémentée : les fichiers modifiés sont livrés à part (dossier de mods LayeredFS).
"""

import struct
from typing import BinaryIO, Dict, Iterator, Tuple

MEDIA_UNIT = 0x200


class RomFSError(Exception):
    pass


class RomFS:
    """Accès aux fichiers de la RomFS de la partition 0 (le jeu)."""

    def __init__(self, handle: BinaryIO):
        self.handle = handle
        header = self._read(0, 0x200)
        if header[0x100:0x104] != b"NCSD":
            raise RomFSError("Ce fichier n'est pas un dump de cartouche 3DS (.3ds/.cci).")
        partition_offset = struct.unpack_from("<I", header, 0x120)[0] * MEDIA_UNIT

        ncch = self._read(partition_offset, 0x200)
        if ncch[0x100:0x104] != b"NCCH":
            raise RomFSError("Partition 0 invalide.")
        self.title_id = struct.unpack_from("<Q", ncch, 0x118)[0]
        self.product_code = ncch[0x150:0x160].rstrip(b"\0").decode("ascii", "replace")
        flags = ncch[0x188:0x190]
        if not flags[7] & 0x04:
            raise RomFSError("Dump chiffré : il faut un dump déchiffré (NoCrypto).")
        romfs_offset = partition_offset + struct.unpack_from("<I", ncch, 0x1B0)[0] * MEDIA_UNIT

        ivfc = self._read(romfs_offset, 0x60)
        if ivfc[0:4] != b"IVFC":
            raise RomFSError("En-tête IVFC introuvable.")
        master_hash_size = struct.unpack_from("<I", ivfc, 0x08)[0]
        level3_block_size = 1 << struct.unpack_from("<I", ivfc, 0x4C)[0]
        level3_offset = romfs_offset + _align(0x60 + master_hash_size, level3_block_size)

        (header_size, _dir_hash_off, _dir_hash_len, dir_meta_off, dir_meta_len,
         _file_hash_off, _file_hash_len, file_meta_off, file_meta_len,
         file_data_off) = struct.unpack_from("<10I", self._read(level3_offset, 0x28))
        if header_size != 0x28:
            raise RomFSError("En-tête RomFS (niveau 3) inattendu.")
        self._dir_meta = self._read(level3_offset + dir_meta_off, dir_meta_len)
        self._file_meta = self._read(level3_offset + file_meta_off, file_meta_len)
        self._data_offset = level3_offset + file_data_off
        self.files: Dict[str, Tuple[int, int]] = dict(self._walk(0, ""))

    def _read(self, offset: int, size: int) -> bytes:
        self.handle.seek(offset)
        data = self.handle.read(size)
        if len(data) != size:
            raise RomFSError(f"Lecture tronquée à 0x{offset:X}.")
        return data

    def _walk(self, dir_offset: int, prefix: str) -> Iterator[Tuple[str, Tuple[int, int]]]:
        _parent, _sibling, child, first_file, _bucket, name_len = struct.unpack_from("<6I", self._dir_meta, dir_offset)
        name = self._dir_meta[dir_offset + 0x18:dir_offset + 0x18 + name_len].decode("utf-16-le")
        path = f"{prefix}{name}/" if dir_offset else ""
        file_offset = first_file
        while file_offset != 0xFFFFFFFF:
            (_fparent, fsibling, data_off, data_len, _fbucket,
             fname_len) = struct.unpack_from("<IIQQII", self._file_meta, file_offset)
            fname = self._file_meta[file_offset + 0x20:file_offset + 0x20 + fname_len].decode("utf-16-le")
            yield path + fname, (data_off, data_len)
            file_offset = fsibling
        while child != 0xFFFFFFFF:
            yield from self._walk(child, path)
            child = struct.unpack_from("<I", self._dir_meta, child + 4)[0]

    def read_file(self, path: str) -> bytes:
        if path not in self.files:
            raise RomFSError(f"Fichier absent de la RomFS : {path}")
        offset, size = self.files[path]
        return self._read(self._data_offset + offset, size)


def _align(value: int, alignment: int) -> int:
    return (value + alignment - 1) // alignment * alignment
