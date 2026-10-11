"""[FR] Badges : chaque champion donne son propre badge."""

from test.bases import WorldTestBase


class TestBadgesAtTheirGym(WorldTestBase):
    game = "Pokemon X and Y"

    def test_each_gym_gives_its_badge(self):
        count = 0
        for location in self.multiworld.get_locations(self.player):
            if location.name.endswith(" Badge") and " - " in location.name:
                count += 1
                self.assertEqual(location.item.name, location.name.split(" - ", 1)[1])
                self.assertTrue(location.locked)
        self.assertEqual(count, 8)


class TestSlotData(WorldTestBase):
    game = "Pokemon X and Y"
    options = {"trainersanity": True, "require_dowsing_machine": True, "include_hidden_items": False}

    def test_options_exposed_to_the_tracker(self):
        data = self.world.fill_slot_data()
        self.assertIs(data["trainersanity"], True)
        self.assertIs(data["require_dowsing_machine"], True)
        self.assertIs(data["include_hidden_items"], False)
