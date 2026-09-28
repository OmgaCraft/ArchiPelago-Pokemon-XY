"""
[FR] Scripts AMX (Pawn) compressés de Pokémon X/Y.

D'après pkNX (pkNX.Structures/Scripts, Amx.cs et PawnUtil.cs) : après l'en-tête,
le code et les données sont stockés comme une suite de mots de 32 bits, chacun
codé sur 1 à 5 octets (7 bits utiles par octet, bit 7 = « la suite continue »,
bit 6 du premier octet = signe).
"""

import struct
from typing import List

MAGIC_32 = 0xF1E0


class AMXError(Exception):
    pass


def decompress(data: bytes, count: int) -> List[int]:
    """Décode `count` mots de 32 bits (portage de PawnUtil.QuickDecompress)."""
    words: List[int] = []
    value = 0
    first = True
    position = 0
    while len(words) < count:
        if position >= len(data):
            raise AMXError("Données compressées tronquées.")
        byte = data[position]
        position += 1
        bits = byte & 0x7F
        if first:
            # Extension de signe si le bit 6 du premier octet est levé.
            value = (0xFFFFFFC0 | bits) if bits & 0x40 else bits
            first = False
        else:
            value = ((value << 7) | bits) & 0xFFFFFFFF
        if byte & 0x80:
            continue
        words.append(value)
        first = True
    return words


def compress_word(word: int) -> bytes:
    """Code un mot (portage de PawnUtil.CompressInstruction)."""
    word &= 0xFFFFFFFF
    negative = bool(word & 0x80000000)
    shadow = (~word & 0xFFFFFFFF) if negative else word
    out = []
    while True:
        byte = word & 0x7F
        if out:
            byte |= 0x80
        out.append(byte)
        word >>= 7
        shadow >>= 7
        if shadow == 0:
            break
    if len(out) < 5:
        sign_bit = 0x40 if negative else 0x00
        if (out[-1] & 0x40) != sign_bit:
            out.append(0xFF if negative else 0x80)
    return bytes(reversed(out))


def compress(words: List[int]) -> bytes:
    return b"".join(compress_word(w) for w in words)


class AMX:
    def __init__(self, data: bytes):
        self.raw = bytes(data)
        size, magic = struct.unpack_from("<IH", data, 0)
        if magic != MAGIC_32:
            raise AMXError(f"Script AMX invalide (signature 0x{magic:04X}).")
        if size != len(data):
            raise AMXError("Taille de script incohérente.")
        self.cod, self.dat, self.hea = struct.unpack_from("<III", data, 0x0C)
        self.words = decompress(data[self.cod:], (self.hea - self.cod) // 4)

    @property
    def data_start(self) -> int:
        """Indice du premier mot de données (après le code)."""
        return (self.dat - self.cod) // 4

    def build(self) -> bytes:
        body = self.raw[:self.cod] + compress(self.words)
        return struct.pack("<I", len(body)) + body[4:]
