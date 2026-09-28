"""
[FR] Tests du client BizHawk sans émulateur : la mémoire du jeu est simulée et les
fonctions bizhawk.read / bizhawk.write sont remplacées. On vérifie surtout la
livraison des objets (pas de doublon au redémarrage, rien d'écrit à l'écran titre,
objets de progression rétablis).
"""

import asyncio
import unittest
from types import SimpleNamespace
from unittest import mock

from worlds.pokemon_xy import Client
from worlds.pokemon_xy.Client import (ADDR_BADGES, ADDR_BAG_MEDICINE, ADDR_BAG_TM, EVENT_FLAGS_BASE,
                                      PokemonXYClient)

MEM_START = 0x074D0000
MEM_SIZE = 0x20000

POTION = 200017
HM03_SURF = 200422
BUG_BADGE = 200801


class FakeMemory:
    def __init__(self):
        self.data = bytearray(MEM_SIZE)
        self.writes = []

    async def read(self, _bizhawk_ctx, read_list):
        return [bytes(self.data[a - MEM_START:a - MEM_START + s]) for a, s, _domain in read_list]

    async def write(self, _bizhawk_ctx, write_list):
        for address, payload, _domain in write_list:
            self.writes.append((address, bytes(payload)))
            self.data[address - MEM_START:address - MEM_START + len(payload)] = payload

    def load_save(self):
        """Simule une sauvegarde chargée : quelques drapeaux d'histoire levés."""
        self.data[EVENT_FLAGS_BASE - MEM_START] = 0x01

    def slot(self, pocket, index):
        o = pocket - MEM_START + index * 4
        return (self.data[o] | self.data[o + 1] << 8, self.data[o + 2] | self.data[o + 3] << 8)

    def clear_pocket(self, pocket, slots):
        self.data[pocket - MEM_START:pocket - MEM_START + slots * 4] = bytes(slots * 4)


class FakeContext:
    def __init__(self, items):
        self.bizhawk_ctx = object()
        self.items_received = [SimpleNamespace(item=i) for i in items]
        self.checked_locations = set()
        self.locations_checked = set()
        self.finished_game = False
        self.team, self.slot = 0, 1
        self.sent = []

    async def send_msgs(self, msgs):
        self.sent.extend(msgs)


def _fresh():
    # Instance neuve = client Archipelago redémarré (sans repasser par la métaclasse).
    client = object.__new__(PokemonXYClient)
    PokemonXYClient.__init__(client)
    return client


class TestDelivery(unittest.TestCase):
    def setUp(self):
        self.memory = FakeMemory()
        patches = [
            mock.patch.object(Client.bizhawk, "read", self.memory.read),
            mock.patch.object(Client.bizhawk, "write", self.memory.write),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def run_async(self, coro):
        return asyncio.run(coro)

    async def connect(self, client, ctx, stored):
        client.on_package(ctx, "Connected", {})
        await asyncio.sleep(0)  # laisse partir le Get
        client.on_package(ctx, "Retrieved", {"keys": {client._delivery_key: stored}})

    async def tick(self, client, ctx, count=1):
        for _ in range(count):
            client._last_ensure_check = 0.0
            await client.game_watcher(ctx)

    def test_nothing_written_at_title_screen(self):
        async def scenario():
            client, ctx = _fresh(), FakeContext([POTION, HM03_SURF, BUG_BADGE])
            await self.connect(client, ctx, None)
            await self.tick(client, ctx, 3)
            self.assertEqual(self.memory.writes, [])
            self.assertEqual(client._received_index, 0)
        self.run_async(scenario())

    def test_first_delivery_then_restart_without_duplicates(self):
        async def scenario():
            ctx = FakeContext([POTION, HM03_SURF, BUG_BADGE])
            self.memory.load_save()
            client = _fresh()
            await self.connect(client, ctx, None)
            await self.tick(client, ctx, 2)

            self.assertEqual(self.memory.slot(ADDR_BAG_MEDICINE, 0), (17, 1))
            self.assertEqual(self.memory.slot(ADDR_BAG_TM, 0), (422, 1))
            self.assertEqual(self.memory.data[ADDR_BADGES - MEM_START] & 1, 1)
            saved = [m for m in ctx.sent if m.get("cmd") == "Set"]
            self.assertEqual(saved[-1]["operations"][0], {"operation": "max", "value": 3})

            # Redémarrage du client : le serveur renvoie 3, rien ne doit être redonné.
            restarted = _fresh()
            await self.connect(restarted, ctx, 3)
            await self.tick(restarted, ctx, 3)
            self.assertEqual(self.memory.slot(ADDR_BAG_MEDICINE, 0), (17, 1))
            self.assertEqual(self.memory.slot(ADDR_BAG_TM, 0), (422, 1))
        self.run_async(scenario())

    def test_progression_restored_after_reloading_older_save(self):
        async def scenario():
            ctx = FakeContext([POTION, HM03_SURF, BUG_BADGE])
            self.memory.load_save()
            await self.connect(_fresh(), ctx, None)
            client = _fresh()
            await self.connect(client, ctx, None)
            await self.tick(client, ctx, 2)

            # Plantage avant sauvegarde : le jeu revient à un état sans les objets.
            self.memory.clear_pocket(ADDR_BAG_TM, 106)
            self.memory.clear_pocket(ADDR_BAG_MEDICINE, 60)
            self.memory.data[ADDR_BADGES - MEM_START] = 0

            restarted = _fresh()
            await self.connect(restarted, ctx, 3)
            await self.tick(restarted, ctx, 2)
            # La CS et le badge reviennent, la Potion (non essentielle) est perdue.
            self.assertEqual(self.memory.slot(ADDR_BAG_TM, 0), (422, 1))
            self.assertEqual(self.memory.data[ADDR_BADGES - MEM_START] & 1, 1)
            self.assertEqual(self.memory.slot(ADDR_BAG_MEDICINE, 0), (0, 0))
        self.run_async(scenario())

    def test_new_items_after_restart_are_delivered(self):
        async def scenario():
            ctx = FakeContext([POTION, POTION])
            self.memory.load_save()
            client = _fresh()
            await self.connect(client, ctx, 1)
            await self.tick(client, ctx)
            self.assertEqual(self.memory.slot(ADDR_BAG_MEDICINE, 0), (17, 1))
            self.assertEqual(client._received_index, 2)
        self.run_async(scenario())

    def test_waits_for_stored_counter(self):
        async def scenario():
            ctx = FakeContext([POTION])
            self.memory.load_save()
            client = _fresh()
            client.on_package(ctx, "Connected", {})
            await self.tick(client, ctx, 2)
            self.assertEqual(self.memory.slot(ADDR_BAG_MEDICINE, 0), (0, 0))
        self.run_async(scenario())

    def test_reconnect_keeps_higher_counter(self):
        async def scenario():
            ctx = FakeContext([POTION, POTION])
            self.memory.load_save()
            client = _fresh()
            await self.connect(client, ctx, None)
            await self.tick(client, ctx)
            self.assertEqual(client._received_index, 2)
            # Coupure : le serveur n'a pas reçu le dernier Set et renvoie 0.
            await self.connect(client, ctx, 0)
            await self.tick(client, ctx)
            self.assertEqual(self.memory.slot(ADDR_BAG_MEDICINE, 0), (17, 2))
        self.run_async(scenario())

    def test_item_messages_shown_by_default(self):
        async def scenario():
            from worlds._bizhawk.context import BizHawkClientContext
            ctx = BizHawkClientContext(None, None)
            ctx.slot, ctx.team = 1, 0
            client = _fresh()
            client.on_package(ctx, "Connected", {})
            await asyncio.sleep(0)
            # Mêmes paquets que le serveur envoie quand on trouve / reçoit un objet.
            found = {"type": "ItemSend", "item": SimpleNamespace(player=1), "receiving": 2}
            received = {"type": "ItemSend", "item": SimpleNamespace(player=2), "receiving": 1}
            for packet in (found, received):
                self.assertIn(ctx._categorize_text(packet), ctx.text_passthrough_categories)

            # Coupé par le joueur (/toggle_text) : une reconnexion ne le rallume pas.
            ctx.text_passthrough_categories.clear()
            client.on_package(ctx, "Connected", {})
            await asyncio.sleep(0)
            self.assertEqual(ctx.text_passthrough_categories, set())
        self.run_async(scenario())

    def test_patch_built_from_scouted_item_balls(self):
        async def scenario():
            by_flag = {flag: loc for loc, flag in Client.FIELD_ITEM_FLAGS.items()}
            ctx = FakeContext([])
            ctx.server_seed_name = "seed-1"
            ctx.server_locations = set(Client.FIELD_ITEM_FLAGS)
            ctx.locations_info = {}
            client = _fresh()
            calls = []

            def fake_write(rom_path, mod_dir, items, stamp):
                calls.append((rom_path, items, stamp))
                return True

            with mock.patch.object(Client, "read_patch_settings", return_value=("rom.3ds", "C:/BH/EmuHawk.exe")), \
                    mock.patch.object(PokemonXYClient, "_write_patch", staticmethod(fake_write)), \
                    mock.patch.object(Client.bizhawk, "display_message", mock.AsyncMock()) as shown:
                client.on_package(ctx, "Connected", {})
                await asyncio.sleep(0)
                scouts = [m for m in ctx.sent if m.get("cmd") == "LocationScouts"]
                self.assertEqual(sorted(scouts[0]["locations"]), sorted(Client.FIELD_ITEM_FLAGS))
                self.assertEqual(scouts[0]["create_as_hint"], 0)

                # Réponse du serveur : Poké Ball n° 0 = Super Bonbon pour moi, le reste pour un autre joueur.
                for loc in Client.FIELD_ITEM_FLAGS:
                    ctx.locations_info[loc] = SimpleNamespace(item=200017, player=2)
                ctx.locations_info[by_flag[0x51A]] = SimpleNamespace(item=200050, player=1)
                client.on_package(ctx, "LocationInfo", {})
                for _ in range(20):
                    await asyncio.sleep(0.01)
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0][1], {0: 50})
                self.assertEqual(calls[0][2]["seed"], "seed-1")
                shown.assert_awaited_once_with(ctx.bizhawk_ctx, Client.PATCH_REBOOT_MESSAGE)

                # Reconnexion à la même partie : pas de nouvelle demande ni de nouvelle fenêtre.
                client.on_package(ctx, "Connected", {})
                await asyncio.sleep(0)
                self.assertEqual(len([m for m in ctx.sent if m.get("cmd") == "LocationScouts"]), 1)
        self.run_async(scenario())

    def test_patch_skipped_without_rom(self):
        async def scenario():
            ctx = FakeContext([])
            ctx.seed_name = "seed-1"
            ctx.server_locations = set(Client.FIELD_ITEM_FLAGS)
            ctx.locations_info = {loc: SimpleNamespace(item=200017, player=1) for loc in Client.FIELD_ITEM_FLAGS}
            client = _fresh()
            write = mock.Mock()
            with mock.patch.object(Client, "read_patch_settings", side_effect=FileNotFoundError("aucune ROM")), \
                    mock.patch.object(PokemonXYClient, "_write_patch", staticmethod(write)):
                client.on_package(ctx, "Connected", {})
                client.on_package(ctx, "LocationInfo", {})
                for _ in range(5):
                    await asyncio.sleep(0.01)
            write.assert_not_called()
            self.assertFalse(client._patch_running)
        self.run_async(scenario())

    def test_location_flag_sends_check(self):
        async def scenario():
            ctx = FakeContext([])
            self.memory.load_save()
            client = _fresh()
            await self.connect(client, ctx, None)
            # 0x00A4 : Aquacorde Town - Received Potion from shopkeeper (id 200023).
            self.memory.data[EVENT_FLAGS_BASE - MEM_START + 0xA4 // 8] |= 1 << (0xA4 % 8)
            await self.tick(client, ctx)
            checks = [m for m in ctx.sent if m.get("cmd") == "LocationChecks"]
            self.assertIn(200023, checks[-1]["locations"])
        self.run_async(scenario())
