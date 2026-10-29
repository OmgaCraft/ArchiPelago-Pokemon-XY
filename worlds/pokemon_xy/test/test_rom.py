"""
[FR] Tests des formats du jeu (AMX, GARC, texte) et de la construction du patch,
sur des données synthétiques : aucun fichier du jeu n'est nécessaire.
"""

import json
import os
import struct
import tempfile
import unittest

from worlds.pokemon_xy.rom import amx, patch
from worlds.pokemon_xy.rom.garc import GARC
from worlds.pokemon_xy.rom.text import TextFile, _crypt, _line_key


def make_amx(words, code_words):
    """Script AMX minimal : en-tête 0x40 octets, puis les mots compressés."""
    cod = 0x40
    dat = cod + code_words * 4
    hea = cod + len(words) * 4
    header = bytearray(cod)
    struct.pack_into("<HBBHH", header, 4, amx.MAGIC_32, 11, 11, 0, 8)
    struct.pack_into("<III", header, 0x0C, cod, dat, hea)
    body = bytes(header) + amx.compress(words)
    return struct.pack("<I", len(body)) + body[4:]


def make_garc(files):
    garc = GARC.__new__(GARC)
    garc.files = [[data] + [None] * 31 for data in files]
    return garc.build()


def make_text(lines):
    text = TextFile.__new__(TextFile)
    text.lines = [[ord(c) for c in line] for line in lines]
    return text.build()


def field_item_script(items):
    code = [0x2E, 0x30, 0x2E]  # quelques instructions quelconques
    data = [0xC1, 9, 1, 0xCD, 9, 1, 0xFFFFFFFF, 0, 0]
    for index, item in enumerate(items):
        data += [item, 1, index]
    return make_amx(code + data, len(code))


class TestAmx(unittest.TestCase):
    def test_compress_roundtrip(self):
        values = [0, 1, 0x3F, 0x40, 0x7F, 0x80, 0x1FFF, 0x2000, 0xFFFF, 0x7FFFFFFF,
                  0x80000000, 0xFFFFFFFF, 0xFFFFFFC0, 0xFFFFFFBF, 12345678]
        self.assertEqual(amx.decompress(amx.compress(values), len(values)), values)

    def test_build_after_edit(self):
        script = amx.AMX(make_amx([1, 2, 3, 4, 5], 2))
        self.assertEqual(script.build(), script.raw)
        script.words[3] = 700
        self.assertEqual(amx.AMX(script.build()).words, [1, 2, 3, 700, 5])


class TestGarcAndText(unittest.TestCase):
    def test_garc_roundtrip_and_set(self):
        raw = make_garc([b"abc", b"defgh", b""])
        garc = GARC(raw)
        self.assertEqual(garc.build(), raw)
        garc.set(1, b"xyz12345")
        rebuilt = GARC(garc.build())
        self.assertEqual([rebuilt.get(i) for i in range(3)], [b"abc", b"xyz12345", b""])

    def test_text_roundtrip_and_replace(self):
        raw = make_text(["Potion", "Poké Ball", "Élixir"])
        text = TextFile(raw)
        self.assertEqual(text.build(), raw)
        self.assertEqual(text.get_plain(1), "Poké Ball")
        text.set_plain(0, "Objet AP")
        self.assertEqual(TextFile(text.build()).get_plain(0), "Objet AP")

    def test_line_encryption_is_symmetric(self):
        data = b"P\0o\0t\0"
        self.assertEqual(_crypt(_crypt(data, _line_key(5)), _line_key(5)), data)


class TestFieldItemPatch(unittest.TestCase):
    def setUp(self):
        self.original = [17, 4, 26] + [1] * (patch.FIELD_ITEM_COUNT - 3)
        files = [b"x"] * 0x11 + [field_item_script(self.original)] + [b"y"]
        self.garc = make_garc(files)

    def test_read_and_build(self):
        self.assertEqual(patch.read_field_items(self.garc), self.original)
        rebuilt = patch.build_field_items(self.garc, {1: 11, 206: 50})
        items = patch.read_field_items(rebuilt)
        self.assertEqual(items[:3], [17, 11, 26])
        self.assertEqual(items[206], 50)
        # Les autres fichiers de l'archive ne bougent pas.
        self.assertEqual(GARC(rebuilt).get(0x12), b"y")

    def test_only_own_regular_items_are_native(self):
        game_ids = frozenset([17, 50, 422, 651])
        scouted = [
            (1000, 200050, 1),   # Rare Candy pour moi -> donnée par la Poké Ball
            (1001, 200017, 2),   # Potion pour un autre joueur -> objet d'origine
            (1002, 200801, 1),   # badge -> objet d'origine
            (1003, 200651, 1),   # Poké Flûte (objet rare) -> objet d'origine
            (1004, 200422, 1),   # CS03 -> objet d'origine (cadeau de PNJ détecté dans le sac)
            (1005, 200050, 1),   # lieu qui n'est pas une Poké Ball au sol
        ]
        flags = {1000: 0x51A, 1001: 0x51B, 1002: 0x51C, 1003: 0x51D, 1004: 0x5E8, 1005: 0x0A4}
        self.assertEqual(patch.field_items_from_scouts(scouted, flags, 1, game_ids), {0: 50})

    def test_mods_directory_follows_bizhawk_config(self):
        with tempfile.TemporaryDirectory() as root:
            emuhawk = os.path.join(root, "EmuHawk.exe")
            self.assertEqual(patch.mods_directory(emuhawk),
                             os.path.join(root, "3DS", "User", "load", "mods", "0004000000055E00"))
            config = {"PathEntries": {"Paths": [{"Type": "User", "Path": "./Perso", "System": "3DS"}]}}
            with open(os.path.join(root, "config.ini"), "w", encoding="utf-8") as handle:
                json.dump(config, handle)
            self.assertEqual(patch.mods_directory(emuhawk),
                             os.path.join(root, "3DS", "Perso", "load", "mods", "0004000000055E00"))

    def test_write_mod_reports_changes(self):
        with tempfile.TemporaryDirectory() as root:
            files = {"a/0/3/1": b"data"}
            self.assertTrue(patch.write_mod(root, files, {"seed": "1"}))
            self.assertFalse(patch.write_mod(root, files, {"seed": "1"}))
            self.assertTrue(patch.write_mod(root, {"a/0/3/1": b"other"}, {"seed": "2"}))
            with open(os.path.join(root, "romfs", "a", "0", "3", "1"), "rb") as handle:
                self.assertEqual(handle.read(), b"other")


class TestLz11(unittest.TestCase):
    def test_roundtrip_literal_encoder(self):
        from worlds.pokemon_xy.rom import lz11
        data = bytes(range(256)) * 3 + b"fin"
        self.assertEqual(lz11.decompress(lz11.compress(data)), data)

    def test_decodes_back_references(self):
        from worlds.pokemon_xy.rom import lz11
        # « ab » en littéraux, puis une référence de longueur 6 à distance 2 : « abababab ».
        stream = bytes([0x11, 8, 0, 0, 0b00100000, ord("a"), ord("b"), 0x50, 0x01])
        self.assertEqual(lz11.decompress(stream), b"abababab")


class TestRandomizerHelpers(unittest.TestCase):
    def _randomizer(self):
        from worlds.pokemon_xy.rom import randomize
        engine = randomize.Randomizer.__new__(randomize.Randomizer)
        engine.table = bytearray(randomize.PERSONAL_SIZE * 3)
        engine.random = __import__("random").Random(1)
        return randomize, engine

    def test_experience_multiplier_is_clamped(self):
        randomize, engine = self._randomizer()
        struct.pack_into("<H", engine.table, 1 * randomize.PERSONAL_SIZE + 0x22, 63)
        struct.pack_into("<H", engine.table, 2 * randomize.PERSONAL_SIZE + 0x22, 60000)
        engine.set_experience_multiplier(200)
        self.assertEqual(struct.unpack_from("<H", engine.table, randomize.PERSONAL_SIZE + 0x22)[0], 126)
        self.assertEqual(struct.unpack_from("<H", engine.table, 2 * randomize.PERSONAL_SIZE + 0x22)[0], 0xFFFF)
        engine.set_experience_multiplier(25)
        self.assertEqual(struct.unpack_from("<H", engine.table, randomize.PERSONAL_SIZE + 0x22)[0], 32)

    def test_nothing_requested_builds_nothing(self):
        from worlds.pokemon_xy.rom import randomize
        self.assertEqual(randomize.build("inexistant.3ds", 1, False, False, False, False, False, 100), {})

    def test_same_seed_same_result(self):
        randomize, first = self._randomizer()
        _, second = self._randomizer()
        for engine in (first, second):
            engine.bst = {sp: 300 + sp for sp in range(1, 200)}
            engine._pools = {}
        picks = [[engine.random_species(50) for _ in range(5)] for engine in (first, second)]
        self.assertEqual(picks[0], picks[1])
        self.assertTrue(all(sp not in randomize.EXCLUDED_SPECIES for sp in picks[0]))


class TestStaleFiles(unittest.TestCase):
    def test_disabled_option_removes_its_old_file(self):
        with tempfile.TemporaryDirectory() as root:
            patch.write_mod(root, {"a/0/3/1": b"1", "a/0/1/2": b"2"}, {"seed": "x"})
            other = os.path.join(root, "romfs", "autre.bin")  # fichier d'un autre mod : intouchable
            with open(other, "wb") as handle:
                handle.write(b"?")
            self.assertTrue(patch.write_mod(root, {"a/0/3/1": b"1"}, {"seed": "x"}))
            self.assertFalse(os.path.exists(os.path.join(root, "romfs", "a", "0", "1", "2")))
            self.assertTrue(os.path.exists(os.path.join(root, "romfs", "a", "0", "3", "1")))
            self.assertTrue(os.path.exists(other))
