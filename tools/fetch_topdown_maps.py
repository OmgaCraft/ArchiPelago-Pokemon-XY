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


# Autres cartes vues du dessus, sous un nom différent : titre du fichier -> nom enregistré.
EXTRA = {
    "Route 3 Vue d'ensemble XY.png": "Route 3",
    "Forêt de Neuvartault Vue d'ensemble XY.png": "Forêt de Neuvartault",
    "Cave Connecterre Vue d'Ensemble XY.png": "Cave Connecterre",
    "Caverne Gelée 1 XY.png": "Caverne Gelée 1", "Caverne Gelée 2 XY.png": "Caverne Gelée 2",
    "Caverne Gelée RdC XY.png": "Caverne Gelée RdC", "Caverne Gelée extérieur XY.png": "Caverne Gelée extérieur",
    "Grotte Miroitante -1 XY.png": "Grotte Miroitante -1", "Grotte Miroitante -2 XY.png": "Grotte Miroitante -2",
    "Grotte Miroitante RdC XY.png": "Grotte Miroitante RdC",
    "Grotte Étincelante 1 XY.png": "Grotte Étincelante 1", "Grotte Étincelante 2 XY.png": "Grotte Étincelante 2",
    "Labos Lysandre Vue d'ensemble Premier Sous-Sol XY.png": "Labos Lysandre 1",
    "Labos Lysandre Vue d'Ensemble Deuxième Sous-Sol XY.png": "Labos Lysandre 2",
    "Labos Lysandre Vue d'Ensemble Troisième Sous-Sol XY.png": "Labos Lysandre 3",
}


def main():
    os.makedirs(TARGET, exist_ok=True)
    wanted = [(t, t.split(":", 1)[1].replace(" carte XY.png", "").replace("'", "")) for t in titles()]
    wanted += [("Fichier:" + title, name) for title, name in EXTRA.items()]
    for title, name in wanted:
        info = api(action="query", titles=title, prop="imageinfo", iiprop="url")
        page = next(iter(info["query"]["pages"].values()))
        if "imageinfo" not in page:
            print("introuvable :", title)
            continue
        url = page["imageinfo"][0]["url"]
        target = os.path.join(TARGET, name + ".png")
        if not os.path.exists(target):
            request = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=30) as response, open(target, "wb") as handle:
                handle.write(response.read())
            time.sleep(0.4)
    print(len(os.listdir(TARGET)), "cartes dans", TARGET)


if __name__ == "__main__":
    main()
