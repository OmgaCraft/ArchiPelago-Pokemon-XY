-- Fonctions appelées par les règles d'accès ("$badges|3") et de visibilité ("$show_hidden").
-- Elles reprennent les règles de worlds/pokemon_xy/Rules.py.
BADGE_CODES = {"Bug_Badge", "Cliff_Badge", "Rumble_Badge", "Plant_Badge",
               "Voltage_Badge", "Fairy_Badge", "Psychic_Badge", "Iceberg_Badge"}

function has(code)
    return Tracker:ProviderCountForCode(code) > 0
end

-- Au moins N badges (les CS exigent un nombre de badges dans la logique du monde).
function badges(amount)
    local count = 0
    for _, code in ipairs(BADGE_CODES) do
        if has(code) then count = count + 1 end
    end
    return count >= (tonumber(amount) or 0)
end

function show_hidden()
    return has("opt_hidden")
end

function show_trainers()
    return has("opt_trainers")
end

-- Les objets cachés ne demandent la Machine Cherch'Objet que si l'option du YAML est active.
function dowsing_ok()
    return (not has("opt_dowsing")) or has("Dowsing_Machine")
end
