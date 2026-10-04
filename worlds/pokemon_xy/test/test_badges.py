"""[FR] Badges : par défaut, chaque champion donne son propre badge."""

from test.bases import WorldTestBase


class TestBadgesAtTheirGym(WorldTestBase):
    game = "Pokemon X and Y"

    def test_each_gym_gives_its_badge(self):
        for location in self.multiworld.get_locations(self.player):
            if location.name.endswith(" Badge") and " - " in location.name:
                self.assertEqual(location.item.name, location.name.split(" - ", 1)[1])
                self.assertTrue(location.locked)


class TestRandomizedBadges(WorldTestBase):
    game = "Pokemon X and Y"
    options = {"randomize_badges": True}

    def test_badges_are_in_the_pool(self):
        badges = [item for item in self.multiworld.itempool if item.name.endswith(" Badge")]
        self.assertEqual(len(badges), 8)
