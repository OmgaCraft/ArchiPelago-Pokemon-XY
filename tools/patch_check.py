"""
[FR] Contrôle du patch des Poké Balls au sol sur un vrai dump (lecture seule, rien n'est installé).

Construit l'archive a/0/3/1 pour une affectation d'essai, puis vérifie :
- que le tableau relu contient exactement les objets demandés ;
- que les autres fichiers de l'archive et le code du script n'ont pas bougé.

Usage :
    py -3.13 tools/patch_check.py <dump .3ds>
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "worlds", "pokemon_xy"))

from rom import patch  # noqa: E402
from rom.amx import AMX  # noqa: E402
from rom.garc import GARC  # noqa: E402
from rom.romfs import RomFS  # noqa: E402

# Affectation d'essai : Super Bonbon (50), Master Ball (1), CT94 (619), CS03 (422).
TRIAL = {0: 50, 1: 1, 100: 619, 206: 422}


def main():
    with open(sys.argv[1], "rb") as handle:
        original = RomFS(handle).read_file(patch.FIELD_ITEM_GARC)
    before = patch.read_field_items(original)
    rebuilt_garc = patch.build_mod_files(sys.argv[1], TRIAL)[patch.FIELD_ITEM_GARC]
    after = patch.read_field_items(rebuilt_garc)

    expected = list(before)
    for index, item in TRIAL.items():
        expected[index] = item
    assert after == expected, "le tableau relu ne correspond pas"

    old, new = GARC(original), GARC(rebuilt_garc)
    assert len(old) == len(new)
    for index in range(len(old)):
        if index != patch.FIELD_ITEM_SCRIPT:
            assert old.files[index] == new.files[index], f"fichier {index} modifié par erreur"
    old_script, new_script = AMX(old.get(patch.FIELD_ITEM_SCRIPT)), AMX(new.get(patch.FIELD_ITEM_SCRIPT))
    code = old_script.data_start
    assert old_script.words[:code] == new_script.words[:code], "le code du script a changé"
    changed = [i for i, (a, b) in enumerate(zip(old_script.words, new_script.words)) if a != b]
    table = old_script.data_start + patch.FIELD_ITEM_TABLE_START
    assert changed == sorted(table + i * 3 for i in TRIAL if before[i] != TRIAL[i]), changed

    print(f"OK : {len(TRIAL)} Poké Balls changées {[(i, before[i], TRIAL[i]) for i in sorted(TRIAL)]}")
    print(f"Taille du script : {len(old.get(patch.FIELD_ITEM_SCRIPT))} -> {len(new.get(patch.FIELD_ITEM_SCRIPT))} octets")


if __name__ == "__main__":
    main()
