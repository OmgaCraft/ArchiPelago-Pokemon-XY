-- Pack PopTracker Pokémon X/Y Archipelago (voir tools/build_tracker.py).
ScriptHost:LoadScript("scripts/logic.lua")

Tracker:AddItems("items/items.json")
Tracker:AddMaps("maps/maps.json")
Tracker:AddLocations("locations/locations.json")
Tracker:AddLayouts("layouts/tabs.json")
Tracker:AddLayouts("layouts/tracker.json")

-- Réglages par défaut du YAML, avant toute connexion : objets cachés visibles, dresseurs masqués.
local hidden = Tracker:FindObjectForCode("opt_hidden")
if hidden then hidden.Active = true end

ScriptHost:LoadScript("scripts/autotracking/archipelago.lua")
