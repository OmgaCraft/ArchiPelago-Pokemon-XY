"""
[FR] Contrôle du pack PopTracker sans PopTracker : charge ses scripts Lua dans un simulateur de l'API
et vérifie que chaque objet, lieu, règle et image existe, puis rejoue connexion, objets et lieux.

Usage (nécessite le paquet « lupa ») :
    py -3.13 -m pip install lupa
    py -3.13 tools/build_tracker.py && py -3.13 tools/check_tracker.py
"""
import json, os, sys, re
from lupa import LuaRuntime
T = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tracker")
items = json.load(open(f"{T}/items/items.json", encoding="utf-8"))
locs = json.load(open(f"{T}/locations/locations.json", encoding="utf-8"))
maps = json.load(open(f"{T}/maps/maps.json", encoding="utf-8"))
lua = LuaRuntime(unpack_returned_tuples=True)
objs, sections = {}, {}
for it in items:
    objs[it["codes"]] = lua.table(Active=False)
rules, vis = [], []
for region in locs:
    for loc in region["children"]:
        path = f"@{region['name']}/{loc['name']}/Check"
        sections[path] = lua.table(ChestCount=1, AvailableChestCount=1)
        rules += loc.get("access_rules", []); vis += loc.get("visibility_rules", [])
        assert loc["map_locations"][0]["map"] in [m["name"] for m in maps]
        for key in ("chest_unopened_img", "chest_opened_img"):
            assert os.path.exists(os.path.join(T, loc["sections"][0][key])), loc["sections"][0][key]
for it in items: assert os.path.exists(os.path.join(T, it["img"])), it["img"]
for m in maps: assert os.path.exists(os.path.join(T, m["img"])), m["img"]
loaded = []
def find(code): return objs.get(code) or sections.get(code)
def count(code):
    o = objs.get(code); return 1 if o is not None and o["Active"] else 0
class TrackerMock:
    def FindObjectForCode(self, code): return find(code)
    def ProviderCountForCode(self, code): return count(code)
    def AddItems(self, p): loaded.append(p)
    AddMaps = AddLocations = AddLayouts = AddItems
handlers = {}
class ArchipelagoMock:
    def AddClearHandler(self, n, f): handlers["clear"] = f
    def AddItemHandler(self, n, f): handlers["item"] = f
    def AddLocationHandler(self, n, f): handlers["loc"] = f
class ScriptHostMock:
    def LoadScript(self, path):
        lua.execute(open(os.path.join(T, path), encoding="utf-8").read())
Tracker, Archipelago, ScriptHost = TrackerMock(), ArchipelagoMock(), ScriptHostMock()
g = lua.globals()
g.Tracker, g.Archipelago, g.ScriptHost = Tracker, Archipelago, ScriptHost
ScriptHost.LoadScript("scripts/init.lua")
print("fichiers chargés par init.lua :", loaded)
# règles : chaque code et fonction doit exister
funcs = {"badges", "show_hidden", "show_trainers", "dowsing_ok"}
bad = set()
for rule in rules + vis:
    for token in rule.split(","):
        token = token.strip()
        if token.startswith("$"):
            if token[1:].split("|")[0] not in funcs: bad.add(token)
        elif token not in objs: bad.add(token)
print("règles invalides :", bad or "aucune", "| règles :", len(rules), "| visibilité :", len(vis))
# autotracking
im, lm = g.ITEM_MAPPING, g.LOCATION_MAPPING
assert all(c in objs for c in im.values()), "code d'objet inconnu"
assert all(p in sections for p in lm.values()), "section inconnue"
print("mappings :", len(list(im.keys())), "objets,", len(list(lm.keys())), "lieux, tous résolus")
handlers["clear"](lua.table(include_hidden_items=False, trainersanity=True, require_dowsing_machine=True))
print("options après clear :", {k: bool(objs[k]["Active"]) for k in ("opt_hidden", "opt_trainers", "opt_dowsing")})
handlers["item"](1, 200801, "Bug Badge", 1)
handlers["item"](1, 200802, "x", 1)      # même index : ignoré
handlers["item"](2, 200422, "HM03 Surf", 1)
print("badges/CS :", objs["Bug_Badge"]["Active"], objs["Cliff_Badge"]["Active"], objs["HM03_Surf"]["Active"])
print("badges(1) =", g.badges(1), "| badges(3) =", g.badges(3), "| dowsing_ok =", g.dowsing_ok())
handlers["item"](3, 200471, "Dowsing Machine", 1)
print("dowsing_ok après réception =", g.dowsing_ok())
first = list(lm.keys())[0]
handlers["loc"](first, "x")
print("lieu validé :", lm[first], "->", sections[lm[first]]["AvailableChestCount"])
handlers["clear"](None)
print("après reconnexion :", sections[lm[first]]["AvailableChestCount"], objs["Bug_Badge"]["Active"], "| cachés par défaut :", objs["opt_hidden"]["Active"])
