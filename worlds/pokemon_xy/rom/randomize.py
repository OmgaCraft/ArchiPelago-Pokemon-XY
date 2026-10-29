"""
[FR] Randomisation du jeu, écrite dans le dossier de mods (aucun fichier d'origine n'est distribué).

Formats vérifiés sur Pokémon Y (USA), d'après PokeRandomizer (ArcanoxDragon) et pkNX :
- fiches des Pokémon : a/2/1/8, dernier fichier = table de 0x40 octets par espèce
  (talents 0x18-0x1A, expérience de base u16 en 0x22, stades d'évolution en 0x09) ;
- capacités apprises : a/2/1/4, un fichier par espèce, paires (capacité u16, niveau u16) ;
- rencontres sauvages : a/0/1/2, fichiers LZ11, 94 entrées de 4 octets par zone à partir du
  décalage lu en 0x10 (+ 0x10) ;
- dresseurs : a/0/3/8 (20 octets) et a/0/4/0 (équipes) ;
- starters : DllPoke3Select.cro (données) et DllField.cro (code).

Sécurité : on ne tire que des espèces proches en force de l'originale, que des capacités et des
talents déjà présents dans le jeu, et on laisse intactes les capacités apprises au niveau 5 ou moins.
"""

import random
import struct
from typing import Dict, List, Optional

from . import lz11
from .garc import GARC
from .romfs import RomFS

PERSONAL_GARC = "a/2/1/8"
LEARNSET_GARC = "a/2/1/4"
ENCOUNTER_GARC = "a/0/1/2"
TRAINER_DATA_GARC = "a/0/3/8"
TRAINER_TEAM_GARC = "a/0/4/0"
STARTER_SELECT_CRO = "DllPoke3Select.cro"
STARTER_FIELD_CRO = "DllField.cro"

PERSONAL_SIZE = 0x40
MAX_SPECIES = 721
# Espèces jamais tirées au sort : événements, formes obligatoires, Pokémon sans équivalent jouable.
EXCLUDED_SPECIES = frozenset({151, 385, 386, 489, 490, 491, 492, 493, 494, 647, 648, 649, 678, 718, 719, 720, 721})
MAX_RANDOM_BST = 599
BST_WINDOWS = (40, 70, 110, 200)
SAFE_MOVE_LEVEL = 5
ENCOUNTER_ENTRIES = 94
ENCOUNTER_BYTES = ENCOUNTER_ENTRIES * 4

# Octets du fichier DllField.cro (section code) et DllPoke3Select.cro (section données).
CRO_CODE_OFFSET, CRO_CODE_SIZE, CRO_DATA_OFFSET, CRO_DATA_SIZE = 0xB0, 0xB4, 0xB8, 0xBC
FIELD_STARTER_BASE = 0xF7EDC
FIELD_STARTER_STRIDE = 0x18
FIELD_STARTER_INDEX = {"kalos": 0, "kanto": 3}
SELECT_STARTER_BASE = 0x10
SELECT_STARTER_STRIDE = 0x54


class RandomizerError(Exception):
    pass


class Randomizer:
    """Construit les fichiers modifiés à partir de la RomFS d'un dump."""

    def __init__(self, rom: RomFS, seed: int):
        self.rom = rom
        self.random = random.Random(seed)
        self.personal = GARC(rom.read_file(PERSONAL_GARC))
        self.table = bytearray(self.personal.get(len(self.personal) - 1))
        self.learnsets = GARC(rom.read_file(LEARNSET_GARC))
        self.species_count = min(MAX_SPECIES, len(self.table) // PERSONAL_SIZE - 1)
        self._pools: Dict[int, List[int]] = {}
        self.bst = {sp: sum(self.table[sp * PERSONAL_SIZE:sp * PERSONAL_SIZE + 6]) for sp in range(1, self.species_count + 1)}
        self.files: Dict[str, bytes] = {}

    # ---- espèces ----------------------------------------------------------

    def _candidates(self, species: int) -> List[int]:
        if species in self._pools:
            return self._pools[species]
        target = self.bst.get(species, 400)
        usable = [sp for sp in self.bst if sp not in EXCLUDED_SPECIES and self.bst[sp] <= MAX_RANDOM_BST]
        for window in BST_WINDOWS:
            pool = [sp for sp in usable if abs(self.bst[sp] - target) <= window]
            if len(pool) >= 8:
                break
        self._pools[species] = pool or usable
        return self._pools[species]

    def random_species(self, original: int) -> int:
        return self.random.choice(self._candidates(original))

    # ---- rencontres sauvages ---------------------------------------------

    def randomize_wild(self) -> None:
        garc = GARC(self.rom.read_file(ENCOUNTER_GARC))
        changed = 0
        for index in range(len(garc)):
            raw = garc.get(index)
            try:
                data = bytearray(lz11.decompress(raw))
                start = struct.unpack_from("<i", data, 0x10)[0] + 0x10
                end = struct.unpack_from("<i", data, 0x14)[0]
            except (lz11.LZ11Error, struct.error, IndexError):
                continue
            if start <= 0 or end - start < ENCOUNTER_BYTES or start + ENCOUNTER_BYTES > len(data):
                continue
            mapping: Dict[int, int] = {}
            for entry in range(ENCOUNTER_ENTRIES):
                position = start + entry * 4
                packed = struct.unpack_from("<H", data, position)[0]
                species = packed & 0x7FF
                if species == 0 or species > MAX_SPECIES:
                    continue
                if species not in mapping:
                    mapping[species] = self.random_species(species)
                struct.pack_into("<H", data, position, mapping[species])  # forme 0
                changed += 1
            garc.set(index, lz11.compress(bytes(data)))
        if not changed:
            raise RandomizerError("Aucune rencontre sauvage trouvée.")
        self.files[ENCOUNTER_GARC] = garc.build()

    # ---- dresseurs --------------------------------------------------------

    def randomize_trainers(self) -> None:
        data_garc = GARC(self.rom.read_file(TRAINER_DATA_GARC))
        team_garc = GARC(self.rom.read_file(TRAINER_TEAM_GARC))
        if len(data_garc) != len(team_garc):
            raise RandomizerError("Dresseurs : données et équipes de tailles différentes.")
        for index in range(len(data_garc)):
            data = bytearray(data_garc.get(index))
            team = team_garc.get(index)
            count = data[3] if len(data) > 3 else 0
            if not count or len(team) % count:
                continue
            fmt = data[0]
            has_moves, has_item = bool(fmt & 1), bool(fmt & 2)
            size = len(team) // count
            expected = 8 + (2 if has_item else 0) + (8 if has_moves else 0)
            if size != expected:
                continue
            members = bytearray()
            for member in range(count):
                entry = bytearray(team[member * size:(member + 1) * size])
                species = struct.unpack_from("<H", entry, 4)[0]
                if 0 < species <= MAX_SPECIES:
                    struct.pack_into("<H", entry, 4, self.random_species(species))
                    struct.pack_into("<H", entry, 6, 0)   # forme 0
                    entry[1] = 0                          # talent et sexe : au hasard
                # Sans capacités écrites, le jeu choisit celles du niveau (voir le learnset de la nouvelle espèce).
                members += entry[:8 + (2 if has_item else 0)]
            data[0] = fmt & ~1
            data_garc.set(index, bytes(data))
            team_garc.set(index, bytes(members))
        self.files[TRAINER_DATA_GARC] = data_garc.build()
        self.files[TRAINER_TEAM_GARC] = team_garc.build()

    # ---- starters ---------------------------------------------------------

    def _starter_pool(self) -> List[int]:
        pool = []
        for sp in self.bst:
            if sp in EXCLUDED_SPECIES:
                continue
            stage = self.table[sp * PERSONAL_SIZE + 9]
            if stage == 1 and 270 <= self.bst[sp] <= 350:
                pool.append(sp)
        return pool

    @staticmethod
    def _cro_section(raw: bytes, offset_pointer: int, size_pointer: int):
        return struct.unpack_from("<I", raw, offset_pointer)[0], struct.unpack_from("<I", raw, size_pointer)[0]

    def randomize_starters(self) -> None:
        pool = self._starter_pool()
        if len(pool) < 6:
            raise RandomizerError("Pas assez d'espèces pour les starters.")
        picks = self.random.sample(pool, 6)
        chosen = {"kalos": picks[:3], "kanto": picks[3:]}

        select = bytearray(self.rom.read_file(STARTER_SELECT_CRO))
        data_offset, _ = self._cro_section(select, CRO_DATA_OFFSET, CRO_DATA_SIZE)
        field = bytearray(self.rom.read_file(STARTER_FIELD_CRO))
        code_offset, _ = self._cro_section(field, CRO_CODE_OFFSET, CRO_CODE_SIZE)
        # Dans DllPoke3Select, l'écran de choix liste d'abord les starters de Kalos, puis ceux de Kanto.
        for group, order in (("kalos", 0), ("kanto", 1)):
            for slot, species in enumerate(chosen[group]):
                struct.pack_into("<H", select, data_offset + SELECT_STARTER_BASE + (order * 3 + slot) * SELECT_STARTER_STRIDE, species)
                struct.pack_into("<H", field, code_offset + FIELD_STARTER_BASE
                                 + (FIELD_STARTER_INDEX[group] + slot) * FIELD_STARTER_STRIDE, species)
        self.files[STARTER_SELECT_CRO] = bytes(select)
        self.files[STARTER_FIELD_CRO] = bytes(field)
        self.starters = chosen

    # ---- fiches et capacités ---------------------------------------------

    def _valid_abilities(self) -> List[int]:
        found = set()
        for sp in range(1, len(self.table) // PERSONAL_SIZE):
            found.update(self.table[sp * PERSONAL_SIZE + 0x18:sp * PERSONAL_SIZE + 0x1B])
        found.discard(0)
        return sorted(found)

    def randomize_abilities(self) -> None:
        pool = self._valid_abilities()
        for sp in range(1, len(self.table) // PERSONAL_SIZE):
            base = sp * PERSONAL_SIZE + 0x18
            first, second, hidden = self.table[base:base + 3]
            if first == 0:
                continue
            new_first = self.random.choice(pool)
            new_second = new_first if second in (0, first) else self.random.choice(pool)
            new_hidden = self.random.choice(pool) if hidden else 0
            self.table[base:base + 3] = bytes([new_first, new_second, new_hidden])

    def randomize_moves(self) -> None:
        pool = set()
        parsed = {}
        for index in range(len(self.learnsets)):
            raw = self.learnsets.get(index)
            moves = []
            for position in range(0, len(raw) - 3, 4):
                move, level = struct.unpack_from("<HH", raw, position)
                if move == 0xFFFF:
                    break
                moves.append((position, move, level))
            parsed[index] = moves
            pool.update(move for _, move, _ in moves)
        pool = sorted(pool)
        for index, moves in parsed.items():
            data = bytearray(self.learnsets.get(index))
            used = {move for _, move, level in moves if level <= SAFE_MOVE_LEVEL}
            for position, move, level in moves:
                if level <= SAFE_MOVE_LEVEL:
                    continue
                for _ in range(20):
                    candidate = self.random.choice(pool)
                    if candidate not in used:
                        break
                used.add(candidate)
                struct.pack_into("<H", data, position, candidate)
            self.learnsets.set(index, bytes(data))
        self.files[LEARNSET_GARC] = self.learnsets.build()

    def set_experience_multiplier(self, percent: int) -> None:
        for sp in range(1, len(self.table) // PERSONAL_SIZE):
            position = sp * PERSONAL_SIZE + 0x22
            value = struct.unpack_from("<H", self.table, position)[0]
            struct.pack_into("<H", self.table, position, max(1, min(0xFFFF, round(value * percent / 100))))

    def finish(self) -> Dict[str, bytes]:
        """Reconstruit l'archive des fiches (toujours, car elle porte talents et expérience)."""
        self.personal.set(len(self.personal) - 1, bytes(self.table))
        self.files[PERSONAL_GARC] = self.personal.build()
        return self.files


def build(rom_path: str, seed: int, wild: bool, trainers: bool, starters: bool, moves: bool, abilities: bool,
          experience_percent: int) -> Dict[str, bytes]:
    """Fichiers de mods pour les réglages demandés ; {} si rien n'est modifié."""
    if not any((wild, trainers, starters, moves, abilities)) and experience_percent == 100:
        return {}
    with open(rom_path, "rb") as handle:
        rom = RomFS(handle)
        randomizer = Randomizer(rom, seed)
        if wild:
            randomizer.randomize_wild()
        if trainers:
            randomizer.randomize_trainers()
        if starters:
            randomizer.randomize_starters()
        if abilities:
            randomizer.randomize_abilities()
        if moves:
            randomizer.randomize_moves()
        if experience_percent != 100:
            randomizer.set_experience_multiplier(experience_percent)
        if abilities or experience_percent != 100:
            return randomizer.finish()
        files = dict(randomizer.files)
        return files
