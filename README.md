# Archipelago — Pokémon X / Y

Monde [Archipelago](https://archipelago.gg/) (randomizer multi-jeux) pour **Pokémon X/Y**, joué sur
**BizHawk** (cœur 3DS). Les objets au sol, les objets cachés, les cadeaux, les badges et, en option,
les dresseurs deviennent des checks. Les objets des autres joueurs arrivent directement dans ton sac.

> **Version 0.0.5** — confirmée pour **Pokémon Y (USA)**, Archipelago 0.6.7, BizHawk 2.11.1.

## Téléchargement

| Fichier | Rôle |
|---|---|
| [**Pokemon_XY_Archipelago_v0.0.5.zip**](https://github.com/OmgaCraft/ArchiPelago-Pokemon-XY/raw/main/dist/Pokemon_XY_Archipelago_v0.0.5.zip) | Tout en un : APWorld, script Lua, YAML et guide |
| [pokemon_xy.apworld](https://github.com/OmgaCraft/ArchiPelago-Pokemon-XY/raw/main/dist/pokemon_xy.apworld) | Le monde, à installer dans Archipelago |
| [pokemon_xy_connector.lua](https://github.com/OmgaCraft/ArchiPelago-Pokemon-XY/raw/main/lua/pokemon_xy_connector.lua) | Le script à charger dans BizHawk |
| [Pokemon X and Y.yaml](yaml/Pokemon%20X%20and%20Y.yaml) | Fichier joueur modèle |

## Démarrage rapide

1. Installe `pokemon_xy.apworld` (double-clic, ou Launcher > Install APWorld).
2. Copie `pokemon_xy_connector.lua` dans `C:\ProgramData\Archipelago\data\lua\`.
3. Mets le YAML dans `Players`, change `name`, génère et héberge la partie.
4. BizHawk : ouvre ton dump de Pokémon Y, puis Tools > Lua Console > ouvre `pokemon_xy_connector.lua`.
5. Lance le client BizHawk d'Archipelago, connecte-toi et charge ta sauvegarde.

**Guide complet, fenêtre d'aide et limites connues : [GUIDE_FR.md](GUIDE_FR.md).**

## Crédits

Ce projet reprend l'APWorld communautaire de **uhsfiuh (Zaitz)** :
[uhsfiuh/Pokemon-x-y-AP](https://github.com/uhsfiuh/Pokemon-x-y-AP) (v0.0.4, commit `ebf52f6`),
dont le README invite à reprendre le projet. Toute la logique, les données du jeu, les adresses
mémoire et le script Lua viennent de son travail. Le dépôt d'origine n'a pas de licence : ce dépôt
sera retiré ou adapté à la demande de l'auteur.

Changements de cette version par rapport à la v0.0.4 :
- `.apworld` reconstruit : l'original avait des `\` dans ses chemins internes et Archipelago ne le chargeait pas ;
- le client ne redonne plus tous les objets à chaque redémarrage (compteur gardé sur le serveur) ;
- rien n'est écrit en mémoire à l'écran titre (les objets étaient effacés au chargement de la sauvegarde) ;
- les objets de progression (CS, CT94, objets clés) sont reposés s'ils manquent après un plantage ;
- le script Lua gère les messages Archipelago (affichés dans BizHawk) ;
- manifeste `archipelago.json` conforme, tests du client ajoutés.

Aucun fichier du jeu n'est fourni : utilise ton propre dump.

## English

Archipelago world for Pokémon X/Y on BizHawk (3DS core), based on
[uhsfiuh/Pokemon-x-y-AP](https://github.com/uhsfiuh/Pokemon-x-y-AP) v0.0.4 with client fixes
(no duplicate items on client restart, no writes at the title screen, progression items restored,
repackaged `.apworld`). Confirmed with **Pokémon Y (USA)**. Download the zip above, install the
`.apworld`, put `pokemon_xy_connector.lua` in `Archipelago\data\lua\` and load it in BizHawk's Lua Console.

## Développement

Voir [docs/DEVELOPPEMENT.md](docs/DEVELOPPEMENT.md).
