"""
[FR] Télécharge dans tools/assets/topmaps/ les cartes vues du dessus de Pokémon X/Y depuis Bulbapedia
(fichiers « <lieu> XY.png » : captures d'écran du jeu, © Nintendo / Game Freak / Creatures, déposées
sur Bulbapedia au titre de l'utilisation équitable).

Ces images servent uniquement à situer les checks dans le tracker (voir « Cartes » dans le README).
Dossier ignoré par git ; ce sont les images recomposées dans tracker/images/maps/ qui sont publiées.

Usage : py -3.13 tools/fetch_topdown_maps.py
"""
import json
import os
import time
import urllib.parse
import urllib.request


API = "https://bulbapedia.bulbagarden.net/w/api.php"
TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "topmaps")
HEADERS = {"User-Agent": "Pokemon-XY-Archipelago-tracker/1.0 (projet personnel, GitHub OmgaCraft)"}

PLACES = [
    "Vaniville Town", "Aquacorde Town", "Santalune City", "Camphrier Town", "Cyllage City", "Ambrette Town",
    "Geosenge Town", "Shalour City", "Coumarine City", "Laverre City", "Dendemille Town", "Anistar City",
    "Couriway Town", "Snowbelle City", "Pokémon Village", "Azure Bay", "Lost Hotel", "Santalune Forest",
    "Connecting Cave", "Glittering Cave", "Kalos Power Plant", "Parfum Palace", "Poké Ball Factory",
    "Tower of Mastery", "Lumiose City", "Kiloude City", "Victory Road", "Pokémon League", "Chamber of Emptiness",
    "Unknown Dungeon", "Lysandre Labs", "Terminus Cave", "Frost Cavern", "Reflection Cave",
]
FLOORS = ["1F", "2F", "3F", "4F", "B1F", "B2F", "B3F", "Entrance", "Outside"]


def api(**params):
    params["format"] = "json"
    request = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


# Pages Bulbapedia dont on prend les cartes « <nom> XY.png » (intérieurs, étages, quartiers...).
PAGES = ["Santalune Gym", "Cyllage Gym", "Shalour Gym", "Coumarine Gym", "Lumiose Gym", "Laverre Gym", "Anistar Gym",
         "Snowbelle Gym", "Victory Road (Kalos)", "Lumiose City", "Pokémon League (Kalos)", "Terminus Cave",
         "Poké Ball Factory", "Glittering Cave", "Parfum Palace", "Shabboneau Castle", "Frost Cavern",
         "Reflection Cave", "Tower of Mastery", "Kalos Power Plant", "Chamber of Emptiness"]
SKIP = ("Icon", "Hat", "Dress", "VS", "Symbol", "Sprite", "Exterior", "exterior", "Badge", "Prism Tower")


def page_titles():
    found = []
    for page in PAGES:
        data = api(action="query", titles=page, prop="images", imlimit=120, redirects=1)
        for item in next(iter(data["query"]["pages"].values())).get("images", []):
            if item["title"].endswith(" XY.png") and not any(word in item["title"] for word in SKIP):
                found.append(item["title"])
    return found


def candidates():
    names = [f"Kalos Route {n}" for n in range(1, 23)] + PLACES
    names += [f"{place} {floor}" for place in ("Frost Cavern", "Reflection Cave", "Terminus Cave", "Glittering Cave",
                                              "Victory Road", "Lysandre Labs", "Kalos Power Plant", "Poké Ball Factory")
              for floor in FLOORS]
    return [f"File:{name} XY.png" for name in names]


def main():
    os.makedirs(TARGET, exist_ok=True)
    titles = sorted(set(candidates() + page_titles()))
    found = {}
    for start in range(0, len(titles), 40):
        data = api(action="query", titles="|".join(titles[start:start + 40]), prop="imageinfo", iiprop="url|size", iilimit=5)
        for page in data["query"]["pages"].values():
            if "imageinfo" in page:
                # Version la plus récente de taille raisonnable : les versions « propres » de 3500 px n'ont pas
                # les icônes (objets, entrées) qui servent au calage ; les anciennes versions les gardent.
                versions = page["imageinfo"]
                found[page["title"]] = next((v for v in versions if v["width"] <= 1100), versions[0])
    for title, info in sorted(found.items()):
        stem = title.split(":", 1)[1][:-len(" XY.png")]
        target = os.path.join(TARGET, stem + ".png")
        if os.path.exists(target):
            continue
        request = urllib.request.Request(info["url"], headers=HEADERS)
        with urllib.request.urlopen(request, timeout=60) as response, open(target, "wb") as handle:
            handle.write(response.read())
        time.sleep(0.4)
    print(len(os.listdir(TARGET)), "cartes dans", TARGET)


if __name__ == "__main__":
    main()
