"""[FR] Fichier de patch par joueur (.apxy) : écriture à la génération, relecture, application."""

import json
import os
import tempfile
import unittest
import zipfile
from unittest import mock

from test.bases import WorldTestBase
from worlds.pokemon_xy import patchfile
from worlds.pokemon_xy.rom import patch as rom_patch


class TestGeneratedPatch(WorldTestBase):
    game = "Pokemon X and Y"
    options = {"randomize_starters": True, "experience_multiplier": 150}

    def test_patch_file_written_and_readable(self):
        with tempfile.TemporaryDirectory() as folder:
            self.world.generate_output(folder)
            names = [name for name in os.listdir(folder) if name.endswith(".apxy")]
            self.assertEqual(len(names), 1)
            path = os.path.join(folder, names[0])
            with zipfile.ZipFile(path) as archive:
                manifest = json.loads(archive.read("archipelago.json"))
            self.assertEqual(manifest["game"], "Pokemon X and Y")
            self.assertEqual(manifest["patch_file_ending"], ".apxy")

            patch = patchfile.PokemonXYPatch(path)
            patch.read()
            data = patch.data
            self.assertEqual(data["slot"], self.player)
            self.assertTrue(data["randomize_starters"])
            self.assertEqual(data["experience_multiplier"], 150)
            self.assertIsInstance(data["rom_seed"], int)
            # Poké Balls au sol : indices valides, objets du jeu.
            self.assertTrue(all(0 <= int(i) < rom_patch.FIELD_ITEM_COUNT for i in data["item_balls"]))
            self.assertTrue(all(0 < item < 800 for item in data["item_balls"].values()))


class TestInstall(unittest.TestCase):
    def test_install_writes_stamped_mod(self):
        data = {"seed_name": "S", "slot": 2, "item_balls": {"0": 50}, "rom_seed": 1}
        built = {"a/0/3/1": b"x"}
        with tempfile.TemporaryDirectory() as root:
            emuhawk = os.path.join(root, "EmuHawk.exe")
            with mock.patch.object(rom_patch, "build_mod_files", return_value=built) as build:
                self.assertTrue(patchfile.install_patch_data(data, "rom.3ds", emuhawk))
                self.assertEqual(build.call_args[0][1], {0: 50})
            stamp = rom_patch.read_stamp(rom_patch.mods_directory(emuhawk))
            self.assertEqual((stamp["seed"], stamp["slot"], stamp["from_patch_file"]), ("S", 2, True))
