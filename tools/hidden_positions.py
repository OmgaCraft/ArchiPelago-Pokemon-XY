"""[FR] Positions approximatives des objets cachés (machine Cherche-Objet), tirées des descriptions de Bulbapedia.

Les positions exactes ne sont pas dans la ROM (seule la table des 151 objets y est : script 26 de a/0/3/1).
Chaque entrée : "Lieu - Found Objet": [carte, x, y], x et y en fraction (0 à 1) de l'image de la carte.
Régénère tools/assets/hidden_positions.json : py -3.13 tools/hidden_positions.py
"""
import json
import os

R = "Kalos Route "
H = {
    # Villes
    "Santalune City": {"Great Ball": ("Santalune City", .22, .52), "Antidote": ("Santalune City", .08, .45),
                       "Super Potion": ("Santalune City", .11, .39)},
    "Camphrier Town": {"Antidote": ("Camphrier Town", .43, .48), "Ether": ("Camphrier Town", .50, .88)},
    "Parfum Palace": {"Pretty Wing (recurring)": ("Parfum Palace Courtyard", .65, .22), "X Sp. Atk": ("Parfum Palace Courtyard", .27, .50),
                      "Rare Candy": ("Parfum Palace Courtyard", .50, .36)},
    "Ambrette Town": {"X Attack": ("Ambrette Town", .15, .80), "Rare Candy": ("Ambrette Town", .18, .60)},
    "Cyllage City": {"Ether": ("Cyllage City", .62, .90), "X Speed": ("Cyllage City", .82, .62),
                     "Protein": ("Cyllage City", .74, .82), "Pearl": ("Cyllage City", .24, .27)},
    "Shalour City": {"Max Repel": ("Shalour City", .63, .17), "X Sp. Atk": ("Shalour City", .12, .60),
                     "Stardust (recurring)": ("Shalour City", .33, .35)},
    "Coumarine City": {"Elixir": ("Coumarine City", .06, .08), "Awakening": ("Coumarine City", .27, .27),
                       "Max Repel": ("Coumarine City", .57, .70)},
    "Laverre City": {"Tiny Mushroom (recurring)": ("Laverre City", .25, .90), "Ultra Ball": ("Laverre City", .33, .50),
                     "Leaf Stone": ("Laverre City", .82, .25)},
    "Anistar City": {"Escape Rope": ("Anistar City", .90, .50), "Sun Stone": ("Anistar City", .40, .30),
                     "Pretty Wing (recurring)": ("Anistar City", .62, .55), "Super Repel": ("Anistar City", .60, .82)},
    "Couriway Town": {"Pretty Wing": ("Couriway Town", .30, .35), "Ether": ("Couriway Town", .40, .38),
                      "Poké Ball": ("Couriway Town", .50, .22), "Burn Heal": ("Couriway Town", .33, .83),
                      "Prism Scale (recurring)": ("Couriway Town", .80, .58)},
    "Dendemille Town": {"Heal Ball": ("Dendemille Town", .07, .74), "Nugget": ("Dendemille Town", .60, .80),
                        "X Speed": ("Dendemille Town", .04, .07)},
    "Snowbelle City": {"Icy Rock": ("Snowbelle City", .68, .20), "X Sp. Atk": ("Snowbelle City", .30, .40),
                       "Full Heal": ("Snowbelle City", .40, .30)},
    "Kiloude City": {"Max Revive": ("Kiloude City", .52, .10), "PP Up": ("Kiloude City", .85, .45)},
    "Pokémon Village": {"Honey": ("Pokémon Village", .60, .70), "Pretty Wing": ("Pokémon Village", .40, .45),
                        "Honey (2)": ("Pokémon Village", .18, .55)},
    "Azure Bay": {"Star Piece": ("Azure Bay", .86, .46), "Heart Scale": ("Azure Bay", .13, .45),
                  "Hyper Potion": ("Azure Bay", .25, .78)},
    "Poké Ball Factory": {"Dusk Ball": ("Poké Ball Factory", .10, .20), "Burn Heal": ("Poké Ball Factory", .38, .75),
                          "Poké Ball": ("Poké Ball Factory", .28, .83), "Hyper Potion": ("Poké Ball Factory", .75, .77)},
    # Routes
    "Route 4": {"Honey (recurring)": (R + "4", .20, .90), "Honey (recurring) (2)": (R + "4", .43, .19),
                "Honey (recurring) (3)": (R + "4", .25, .16), "Super Potion": (R + "4", .60, .09)},
    "Route 5": {"Paralyze Heal": (R + "5", .77, .27), "Super Potion": (R + "5", .60, .52)},
    "Route 6": {"Antidote": (R + "6", .50, .45), "Tiny Mushroom": (R + "6", .82, .45)},
    "Route 8": {"Super Potion": (R + "8", .73, .37), "Escape Rope": (R + "8", .60, .56),
                "Pearl (recurring)": (R + "8", .42, .58), "Ultra Ball": (R + "8", .50, .86),
                "Heart Scale": (R + "8", .25, .15), "Stardust (recurring)": (R + "8", .30, .72),
                "Heart Scale (recurring)": (R + "8", .42, .82)},
    "Route 9": {"Super Repel": (R + "9", .89, .52)},
    "Route 10": {"Revive": (R + "10", .52, .77), "Paralyze Heal": (R + "10", .50, .60), "Burn Heal": (R + "10", .50, .47)},
    "Route 11": {"Super Potion": (R + "11", .55, .62), "Thunder Stone": (R + "11", .95, .30)},
    "Route 12": {"Honey (recurring)": (R + "12", .60, .30), "Net Ball": (R + "12", .35, .90),
                 "Ice Heal": (R + "12", .90, .78), "Water Stone": (R + "12", .85, .45)},
    "Route 13": {"Power Plant Pass": (R + "13", .22, .72), "Guard Spec.": (R + "13", .76, .47),
                 "Heat Rock": (R + "13", .36, .33), "Nest Ball": (R + "13", .37, .84), "Hyper Potion": (R + "13", .15, .55),
                 "PP Up": (R + "13", .14, .78), "X Accuracy": (R + "13", .80, .52), "Stardust": (R + "13", .78, .30),
                 "Fire Stone": (R + "13", .93, .55), "Star Piece": (R + "13", .42, .58)},
    "Route 14": {"Super Potion": (R + "14", .12, .90), "Tiny Mushroom": (R + "14", .33, .43), "Revive": (R + "14", .20, .28)},
    "Route 15": {"HP Up": (R + "15", .60, .90), "Antidote": (R + "15", .38, .08), "Tiny Mushroom": (R + "15", .55, .25),
                 "X Defense": (R + "15", .87, .38), "Pretty Wing": (R + "15", .56, .93)},
    "Route 16": {"Repel": (R + "16", .20, .30), "Rare Candy": (R + "16", .35, .65), "Big Mushroom": (R + "16", .50, .82),
                 "Max Revive": (R + "16", .80, .12)},
    "Route 17": {"Timer Ball": (R + "17", .32, .14), "Paralyze Heal": (R + "17", .90, .72)},
    "Route 18": {"Poké Ball": (R + "18", .20, .37), "Ether": (R + "18", .62, .30), "Honey": (R + "18", .60, .83),
                 "Super Potion": (R + "18", .82, .72)},
    "Route 19": {"Net Ball": (R + "19", .69, .17), "Antidote": (R + "19", .92, .65), "Damp Rock": (R + "19", .52, .88),
                 "Escape Rope": (R + "19", .30, .70), "Timer Ball": (R + "19", .27, .60)},
    "Route 20": {"Repeat Ball": (R + "20", .85, .42), "Antidote": (R + "20", .56, .67), "Mental Herb": (R + "20", .38, .25),
                 "Tiny Mushroom": (R + "20", .33, .40), "Balm Mushroom": (R + "20", .23, .73)},
    "Route 21": {"Guard Spec.": (R + "21", .72, .50), "PP Up": (R + "21", .27, .78), "Pearl String": (R + "21", .68, .22),
                 "Elixir": (R + "21", .36, .10)},
    "Route 22": {"Max Elixir": (R + "22", .70, .84), "Full Restore": (R + "22", .62, .78)},
    # Grottes
    "Frost Cavern": {"Escape Rope": ("Frost Cavern 1F", .33, .85), "X Sp. Def": ("Frost Cavern 1F", .20, .30),
                     "Ice Heal": ("Frost Cavern 1F", .25, .78), "Dusk Ball": ("Frost Cavern 1F", .72, .10),
                     "Dire Hit": ("Frost Cavern 1F", .62, .30), "Pearl": ("Frost Cavern 2F", .15, .65),
                     "Super Potion": ("Frost Cavern 2F", .35, .80), "Ice Heal (2)": ("Frost Cavern 2F", .45, .12),
                     "Elixir": ("Frost Cavern 3F", .62, .65), "PP Up": ("Frost Cavern 3F", .42, .07)},
    "Terminus Cave": {"Normal Gem": ("Terminus Cave 1F Zygarde chamber", .50, .40),
                      "Dusk Ball": ("Terminus Cave 1F Entrance", .12, .50), "Hyper Potion": ("Terminus Cave 1F Entrance", .22, .42),
                      "Moon Stone": ("Terminus Cave B1F Center", .68, .10), "Iron": ("Terminus Cave B1F Center", .15, .35),
                      "Max Potion": ("Terminus Cave B1F Center", .55, .62), "Dire Hit": ("Terminus Cave B1F Center", .62, .78),
                      "Max Repel": ("Terminus Cave B1F Center", .85, .28), "Big Nugget": ("Terminus Cave 1F Zygarde chamber", .75, .20)},
    "Victory Road": {"X Attack": ("Kalos Victory Road First cave", .62, .35), "Hyper Potion": ("Kalos Victory Road First grove", .20, .45),
                     "Full Heal": ("Kalos Victory Road Second grove", .85, .64), "Ultra Ball": ("Kalos Victory Road Second cave", .33, .52),
                     "Smooth Rock": ("Kalos Victory Road Second cave", .31, .11), "Revive": ("Kalos Victory Road Second cave", .32, .80),
                     "Pretty Wing": ("Kalos Victory Road Third cave", .70, .55), "Escape Rope": ("Kalos Victory Road Third cave", .30, .62),
                     "Max Repel": ("Kalos Victory Road Third cave", .90, .38), "X Defense": ("Kalos Victory Road Third cave", .52, .20),
                     "Max Ether": ("Kalos Victory Road Second grove", .52, .75), "Star Piece": ("Kalos Victory Road Gate", .50, .62)},
}

if __name__ == "__main__":
    out = {f"{group} - Found {item}": list(value) for group, items in H.items() for item, value in items.items()}
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "assets", "hidden_positions.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(out, handle, ensure_ascii=False, indent=0)
    print(len(out), "positions ->", path)
