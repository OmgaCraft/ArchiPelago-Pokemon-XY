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
