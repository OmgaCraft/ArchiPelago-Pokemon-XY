"""
[FR] Télécharge dans tools/assets/topmaps/ les cartes vues du dessus de Poképédia (« <lieu> carte XY.png »).

Ces images appartiennent à leurs auteurs et à Nintendo : elles ne sont jamais ajoutées au dépôt
(dossier ignoré par git), seule la version locale du tracker s'en sert.

Usage : py -3.13 tools/fetch_topdown_maps.py
"""
import json, os, re, time, urllib.parse, urllib.request

API = "https://www.pokepedia.fr/api.php"
TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "topmaps")
HEADERS = {"User-Agent": "Mozilla/5.0 (Pokemon-XY-Archipelago tracker, usage personnel)"}


def api(**params):
    params["format"] = "json"
    request = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def titles():
    """Tous les fichiers « … carte XY.png » (balayage de l'espace Fichier par préfixes)."""
    found = set()
    for prefix in ["Route", "Bourg", "Baie", "Cromlac", "Flusselles", "Fort", "H", "La ", "Mozheim", "Neuvartault",
                   "Port", "Quarellis", "Relifac", "Roche", "Romant", "Village", "Yantreizh", "Auffrac"]:
        cont = {}
        while True:
            data = api(action="query", list="allpages", apnamespace=6, apprefix=prefix, aplimit=500, **cont)
            for page in data["query"]["allpages"]:
                if re.search(r" carte XY\.png$", page["title"]):
                    found.add(page["title"])
            if "continue" not in data:
                break
            cont = data["continue"]
    return sorted(found)


def main():
    os.makedirs(TARGET, exist_ok=True)
    for title in titles():
        info = api(action="query", titles=title, prop="imageinfo", iiprop="url")
        page = next(iter(info["query"]["pages"].values()))
        url = page["imageinfo"][0]["url"]
        name = title.split(":", 1)[1].replace(" carte XY.png", "").replace("'", "")
        target = os.path.join(TARGET, name + ".png")
        if not os.path.exists(target):
            request = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=30) as response, open(target, "wb") as handle:
                handle.write(response.read())
            time.sleep(0.4)
    print(len(os.listdir(TARGET)), "cartes dans", TARGET)


if __name__ == "__main__":
    main()
