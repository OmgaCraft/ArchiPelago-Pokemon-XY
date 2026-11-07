"""
[FR] Télécharge dans tools/assets/zones/ une capture d'écran par zone de Kalos (Serebii, Pokéarth).

Ces images appartiennent à leurs auteurs et à Nintendo : elles ne sont jamais ajoutées au dépôt
(dossier ignoré par git). tools/build_tracker.py s'en sert pour fabriquer, dans local/, une version
du tracker qui montre le visuel de chaque route à côté de ses checks.

Usage :
    py -3.13 tools/fetch_zone_images.py
    py -3.13 tools/build_tracker.py        # écrit aussi local/Pokemon_XY_Tracker.zip
"""

import os
import re
import time
import urllib.request

from PIL import Image

BASE = "https://www.serebii.net"
TARGET = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "zones")
HEADERS = {"User-Agent": "Mozilla/5.0 (Pokemon-XY-Archipelago tracker, usage personnel)"}


def fetch(path):
    request = urllib.request.Request(BASE + path, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read()


def main():
    os.makedirs(TARGET, exist_ok=True)
    index = fetch("/pokearth/kalos/").decode("utf-8", "replace")
    pages = sorted(set(re.findall(r'href="(?:https://www\.serebii\.net)?(/pokearth/kalos/[^"]+\.shtml)"', index)))
    print(len(pages), "zones")
    for page in pages:
        slug = os.path.basename(page)[:-len(".shtml")].replace("'", "")
        html = fetch(page).decode("utf-8", "replace")
        for number, image in enumerate(sorted(set(re.findall(r'(/pokearth/maps/kalos/[^"]+\.(?:jpg|png))', html))), 1):
            target = os.path.join(TARGET, f"{slug}_{number}{os.path.splitext(image)[1]}")
            if os.path.exists(target):
                continue
            with open(target, "wb") as handle:
                handle.write(fetch(image))
            try:
                Image.open(target).verify()
            except Exception:  # page d'erreur au lieu d'une image
                os.remove(target)
                print("image invalide ignorée :", slug, number)
        time.sleep(0.4)  # on ménage le site
    print(len(os.listdir(TARGET)), "fichiers dans", TARGET)


if __name__ == "__main__":
    main()
