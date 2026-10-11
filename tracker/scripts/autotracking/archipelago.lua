-- Suivi automatique : les objets reçus et les lieux validés viennent du serveur Archipelago.
-- Le pack ne COCHE jamais de lieu vers le serveur : les checks partent du client BizHawk.
ScriptHost:LoadScript("scripts/autotracking/item_mapping.lua")
ScriptHost:LoadScript("scripts/autotracking/location_mapping.lua")

CUR_INDEX = -1

local function set_active(code, active)
    local object = Tracker:FindObjectForCode(code)
    if object then object.Active = active end
end

-- Appelée à chaque (re)connexion : on repart de zéro, le serveur renvoie ensuite tout l'état.
function onClear(slot_data)
    CUR_INDEX = -1
    for _, code in pairs(ITEM_MAPPING) do
        set_active(code, false)
    end
    for _, path in pairs(LOCATION_MAPPING) do
        local section = Tracker:FindObjectForCode(path)
        if section then section.AvailableChestCount = section.ChestCount end
    end
    slot_data = slot_data or {}
    -- Valeurs du YAML (fill_slot_data) ; par défaut celles du YAML modèle.
    local hidden = slot_data["include_hidden_items"]
    set_active("opt_hidden", hidden == nil and true or hidden == true)
    set_active("opt_trainers", slot_data["trainersanity"] == true)
    set_active("opt_dowsing", slot_data["require_dowsing_machine"] == true)
end

function onItem(index, item_id, item_name, player_number)
    if index <= CUR_INDEX then return end
    CUR_INDEX = index
    local code = ITEM_MAPPING[item_id]
    if code then set_active(code, true) end
end

function onLocation(location_id, location_name)
    local path = LOCATION_MAPPING[location_id]
    if not path then return end
    local section = Tracker:FindObjectForCode(path)
    if section then section.AvailableChestCount = 0 end
end

Archipelago:AddClearHandler("pokemon_xy clear", onClear)
Archipelago:AddItemHandler("pokemon_xy item", onItem)
Archipelago:AddLocationHandler("pokemon_xy location", onLocation)
