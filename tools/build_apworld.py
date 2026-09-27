"""
Construit dist/pokemon_xy.apworld depuis worlds/pokemon_xy, comme le composant
« Build APWorlds » d'Archipelago 0.6.7 (worlds/LauncherComponents.py) :
- chemins du zip en « / » (l'apworld d'origine utilisait « \\ », illisible par Archipelago) ;
- __pycache__ exclus ;
- manifeste complété par game, version et compatible_version (worlds/Files.py).

Usage :
    py -3.13 tools/build_apworld.py            # construit dist/pokemon_xy.apworld
    py -3.13 tools/build_apworld.py --install  # et le copie avec le connecteur Lua dans Archipelago
"""

import argparse
import json
import os
import shutil
import sys
import zipfile

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORLD_NAME = "pokemon_xy"
WORLD_DIR = os.path.join(PROJECT_DIR, "worlds", WORLD_NAME)
LUA_FILE = os.path.join(PROJECT_DIR, "lua", "pokemon_xy_connector.lua")
DIST_DIR = os.path.join(PROJECT_DIR, "dist")
ARCHIPELAGO_DIR = r"C:\ProgramData\Archipelago"

# Valeurs de worlds/Files.py (container_version et APWorldContainer.get_manifest) en 0.6.7.
CONTAINER_VERSION = 7
APWORLD_COMPATIBLE_VERSION = 7

IGNORED_DIRS = {"__pycache__", ".git", "__MACOSX"}
IGNORED_FILES = {".DS_Store", ".apignore", ".gitignore"}


def build():
    with open(os.path.join(WORLD_DIR, "archipelago.json"), encoding="utf-8") as handle:
        manifest = json.load(handle)
    manifest["version"] = CONTAINER_VERSION
    manifest["compatible_version"] = APWORLD_COMPATIBLE_VERSION

    os.makedirs(DIST_DIR, exist_ok=True)
    target = os.path.join(DIST_DIR, WORLD_NAME + ".apworld")
    count = 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for root, dirs, files in os.walk(WORLD_DIR):
            dirs[:] = sorted(d for d in dirs if d not in IGNORED_DIRS)
            for name in sorted(files):
                path = os.path.join(root, name)
                relative = os.path.relpath(path, WORLD_DIR).replace(os.sep, "/")
                if name in IGNORED_FILES or relative == "archipelago.json":
                    continue
                archive.write(path, f"{WORLD_NAME}/{relative}")
                count += 1
        archive.writestr(f"{WORLD_NAME}/archipelago.json", json.dumps(manifest))
    print(f"{target} : {count} fichier(s) + manifeste {manifest}")
    build_bundle(target, manifest.get("world_version", "dev"))
    return target


def build_bundle(apworld, version):
    """Zip tout-en-un pour les joueurs : APWorld, script Lua, YAML et guide."""
    bundle = os.path.join(DIST_DIR, f"Pokemon_XY_Archipelago_v{version}.zip")
    contents = [
        (apworld, os.path.basename(apworld)),
        (LUA_FILE, os.path.basename(LUA_FILE)),
        (os.path.join(PROJECT_DIR, "yaml", "Pokemon X and Y.yaml"), "Pokemon X and Y.yaml"),
        (os.path.join(PROJECT_DIR, "GUIDE_FR.md"), "GUIDE_FR.md"),
    ]
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for source, name in contents:
            archive.write(source, name)
    print(f"{bundle} : {', '.join(name for _, name in contents)}")


def install(apworld):
    destinations = [
        (apworld, os.path.join(ARCHIPELAGO_DIR, "custom_worlds", WORLD_NAME + ".apworld")),
        (LUA_FILE, os.path.join(ARCHIPELAGO_DIR, "data", "lua", os.path.basename(LUA_FILE))),
    ]
    for source, destination in destinations:
        if not os.path.isdir(os.path.dirname(destination)):
            sys.exit(f"Dossier introuvable : {os.path.dirname(destination)}")
        shutil.copyfile(source, destination)
        print(f"Installé : {destination}")


def main():
    parser = argparse.ArgumentParser(description="Construit l'apworld Pokémon X/Y.")
    parser.add_argument("--install", action="store_true", help="Copie aussi l'apworld et le connecteur dans Archipelago")
    args = parser.parse_args()
    apworld = build()
    if args.install:
        install(apworld)


if __name__ == "__main__":
    main()
