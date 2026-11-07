"""
[FR] Extrait de la ROM la position (zone, X, Y) des dresseurs qui ont un check.

Règle vérifiée sur Pokémon Y USA : le personnage d'une zone (a/0/1/2, même format que pour les Poké Balls,
voir extract_ball_positions.py) dont le mot en 0x0A vaut 1260 + le drapeau « dresseur battu » du check
est ce dresseur (225 des 254 dresseurs du monde sont retrouvés, toujours dans la zone attendue : arène de
Santalune = zone 56, de Cyllage = 160, etc.).

Usage : py -3.13 tools/extract_trainer_positions.py "<dump.3ds>"   ->  tools/assets/trainer_positions.json
Les chefs d'arène sont les personnages de modèle 15 à 22 (Violette, Lino, Cornélia, Amaryllis, Lem, Valériane,
Astera, Urup) dans la zone de leur arène ; leur position sert à placer les badges (leader_positions.json).
Les personnages « mobiles » (arènes de Poivressel et d'Anistar) n'ont pas de position lisible (valeurs
absurdes, > 1500) : ils sont ignorés.

Le JSON ne contient que des coordonnées {drapeau: {zone, x, y}}, il peut être versionné.
"""
import json, os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "worlds", "pokemon_xy"))
from rom.romfs import RomFS  # noqa: E402
from rom.garc import GARC  # noqa: E402
from rom import lz11  # noqa: E402

TRAINER_SCRIPT_OFFSET = 1260   # script du personnage = drapeau du check + 1260
# Badge -> (modèle du chef d'arène, zone de son arène). Zones d'arène lues avec les dresseurs (Santalune 56,
# Cyllage 160, Shalour 175, Coumarine 191, Laverre 203, Anistar 215, Snowbelle 226) ; Lem : zone 78 (6e étage).
LEADERS = {"Bug Badge": (15, 56), "Cliff Badge": (16, 160), "Rumble Badge": (17, 175), "Plant Badge": (18, 191),
           "Voltage Badge": (19, 78), "Fairy Badge": (20, 203), "Psychic Badge": (21, 215), "Iceberg Badge": (22, 226)}
VALID = 1500


def main(path):
    rom = RomFS(open(path, "rb"))
    zones = GARC(rom.read_file("a/0/1/2"))
    by_script, leaders = {}, {}
    for z in range(360):
        d = lz11.decompress(zones.files[z][0])
        n = struct.unpack_from("<H", d, 2)[0]
        o = struct.unpack_from("<%dI" % (n + 1), d, 4)
        s = d[o[1]:o[2]]
        nf, nn = s[4], s[5]
        p = 12 + 0x14 * nf
        for _ in range(nn):
            e = s[p:p + 0x30]; p += 0x30
            script = struct.unpack_from("<H", e, 10)[0]
            x, y = struct.unpack_from("<HH", e, 0x28)
            if x > VALID or y > VALID:
                continue
            if 3000 <= script < 4000:
                by_script[script] = {"zone": z, "x": x, "y": y}
            model = struct.unpack_from("<H", e, 2)[0]
            for badge, (leader_model, leader_zone) in LEADERS.items():
                if model == leader_model and z == leader_zone and script < 100:
                    leaders[badge] = {"zone": z, "x": x, "y": y}
    out = {str(script - TRAINER_SCRIPT_OFFSET): v for script, v in sorted(by_script.items())}
    target = os.path.join(HERE, "assets", "trainer_positions.json")
    with open(target, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=0)
    print(len(out), "dresseurs ->", target)
    target = os.path.join(HERE, "assets", "leader_positions.json")
    with open(target, "w", encoding="utf-8") as f:
        json.dump(leaders, f, ensure_ascii=False, indent=0)
    print(len(leaders), "chefs d'arène ->", target, sorted(leaders))


if __name__ == "__main__":
    main(sys.argv[1])
