# Guide — Pokémon X/Y Archipelago (v0.0.7)

## Ce qu'il te faut

| Élément | Détail |
|---|---|
| Archipelago | 0.6.7 (testé), Windows |
| BizHawk | 2.10 ou plus récent (cœur 3DS « Encore ») ; testé avec 2.11.1 |
| Jeu | Ton propre dump de **Pokémon Y (USA) (En,Ja,Fr,De,Es,It,Ko)**, de préférence déchiffré |

- Un dump **chiffré** marche aussi, mais BizHawk demandera alors `aes_keys.txt` et `seeddb.bin`,
  issus de ta console (Config > Firmwares, section 3DS).
- Les adresses mémoire ont été relevées sur ce dump précis (hash BizHawk
  `0C0C54FC3A0DA480061D661BA3A5644F`). **Pokémon X ou une autre région : non garanti.**
  Au démarrage, le client affiche `Dump recognised` si ton dump est le bon.

## Installation

1. Télécharge `Pokemon_XY_Archipelago.zip` (dossier [`dist/`](dist)) et décompresse-le.
2. **APWorld** : double-clique sur `pokemon_xy.apworld`, ou Launcher Archipelago > « Install APWorld ».
   Tu peux aussi le copier à la main dans `C:\ProgramData\Archipelago\custom_worlds\`.
3. **Script Lua** : copie `pokemon_xy_connector.lua` dans `C:\ProgramData\Archipelago\data\lua\`.
   Il doit être dans ce dossier, car il utilise les fichiers `json.lua` et `base64.lua` qui s'y trouvent.

(Si Archipelago est installé ailleurs, remplace `C:\ProgramData\Archipelago` par ton dossier.)

## Jouer

1. **YAML** : copie `Pokemon X and Y.yaml` dans `C:\ProgramData\Archipelago\Players` et change `name`.
2. **Générer** : lance `ArchipelagoGenerate.exe` (ou Launcher > Generate). La partie arrive dans
   `C:\ProgramData\Archipelago\output`.
3. **Héberger** : dépose le `.zip` sur [archipelago.gg](https://archipelago.gg/uploads), ou lance `ArchipelagoServer.exe`.
4. **BizHawk** (`EmuHawk.exe`) :
   - File > Open ROM > ton dump de Pokémon Y ;
   - Tools > Lua Console, puis Script > Open Script > `C:\ProgramData\Archipelago\data\lua\pokemon_xy_connector.lua`.
     Une fenêtre « X/Y Archipelago Helper » s'ouvre : garde-la ouverte.
5. **Client** : lance `ArchipelagoBizHawkClient.exe` (ou Launcher > BizHawk Client), entre l'adresse du
   serveur, puis ton nom de slot.
6. **Charge ta partie** (ou termine l'intro d'une nouvelle partie). Les objets reçus n'arrivent
   qu'une fois la sauvegarde chargée, jamais à l'écran titre.

Quand tu ramasses une Poké Ball, le script retire tout seul l'objet d'origine, puis te donne l'objet Archipelago.

## Le patch du jeu (Poké Balls au sol)

Depuis la v0.0.7, **une Poké Ball au sol qui contient un objet pour toi l'annonce vraiment** :
« Vous avez obtenu un Super Bonbon » au lieu de l'objet d'origine.

- **Première connexion** : le client te demande ton dump de Pokémon Y (le fichier `.3ds` déchiffré).
  Il s'en sert pour construire un petit fichier modifié, qu'il range dans le dossier de mods de
  BizHawk (`3DS\User\load\mods\0004000000055E00`). Ton dump n'est jamais modifié.
- **Ensuite, redémarre le jeu une fois** : sauvegarde en jeu, puis Emulation > Reboot Core dans
  BizHawk. Un message te le rappelle à l'écran. Le patch est refait tout seul à chaque nouvelle partie.
- Ça marche aussi sur une partie déjà commencée : pas besoin de regénérer.
- Pour l'instant, seules les **207 Poké Balls au sol** sont concernées, et seulement pour **tes**
  objets. Un objet pour un autre joueur, un badge ou un objet rare garde le nom de l'objet d'origine.
  Les objets cachés et les cadeaux des personnages ne changent pas non plus.
- Sans le patch (ROM refusée, dump chiffré…), le jeu marche comme avant. Pour le désactiver :
  `patch_game: false` dans `host.yaml`, section `pokemon_xy_settings`.

## Les messages : ce que tu as vraiment trouvé

Sans le patch, ou pour un objet destiné à un autre joueur, la boîte de dialogue du jeu annonce
**l'objet d'origine** de la Poké Ball, par exemple « Vous avez obtenu une Potion ».

Ce que tu as vraiment trouvé s'affiche **en bas à gauche de l'écran de BizHawk**. Les messages
restent aussi dans la console Lua et dans le client :

| Message | Signification |
|---|---|
| `Toi found their Absolite (…)` | L'objet était pour toi : il remplace la Potion dans ton sac. |
| `Toi sent Potion to Ami (…)` | L'objet part chez un autre joueur : la Potion d'origine est retirée de ton sac. |
| `Ami sent Absolite to Toi (…)` | Un autre joueur t'a envoyé un objet. |

- Si les messages sont coupés, agrandis la fenêtre de BizHawk (View > Window Size).
- Pour les masquer, tape `/toggle_text outgoing off` ou `/toggle_text incoming off` dans le client.
  Remplace `off` par `on` pour les réafficher.

## La fenêtre d'aide (Helper)

- **Badges — « Suppress »** : si tu as déjà reçu le badge d'une arène sans avoir battu le champion,
  le champion refuse le combat. Clique « Suppress » sur ce badge, parle au champion, bats-le :
  le check part et le badge revient.
- **« Got it »** : six objets n'ont pas de drapeau détectable (CS03 Surf, CS04 Force, CS05 Cascade,
  Machine Cherch'Objet, Elevator Key, Poké Flûte). Quand le jeu te donne l'un d'eux, clique
  « Got it » : le check part et l'objet d'origine est retiré (sauf si Archipelago te l'a déjà donné).
- **Roadblock (Ronflex, Route 7)** : si Ronflex réapparaît derrière toi et te bloque, désactive-le ici.
- Les boutons **« Cheat »** ne servent qu'en secours, si quelque chose casse.

## Bon à savoir

- **Sauvegarde souvent en jeu.** Le nombre d'objets déjà livrés est gardé sur le serveur. Si BizHawk
  plante avant une sauvegarde, les objets ordinaires reçus depuis sont perdus. Les CS, la CT94,
  les objets clés de progression, les badges et les Rollers sont reposés automatiquement.
- **Nouvelle partie avec le même slot** : les objets ordinaires déjà reçus ne sont pas redonnés.
- Les savestates de BizHawk sont gérés par le script. Sauvegarde quand même en jeu.

## Options du YAML

| Option | Effet |
|---|---|
| `include_hidden_items` | Les objets cachés deviennent des checks (défaut : oui). |
| `require_dowsing_machine` | Les objets cachés ne sont dans la logique qu'avec la Machine Cherch'Objet (défaut : non). |
| `trainersanity` | Battre les dresseurs devient un check (défaut : non, beaucoup de checks en plus). |
| `goal` | `pokemon_league` : entrer au Panthéon. |

## Limites connues

- Rien n'est détecté avant la Potion donnée par le vendeur de Quarellis (Aquacorde Town) : c'est normal au début.
- Logique approximative par endroits : par exemple Ronflex dépend du feu d'artifice dans le jeu,
  mais de la Poké Flûte dans la logique.
- Certains objets reçus peuvent atterrir dans la mauvaise poche du sac.
- Trois Sbires Team Flare de la Glittering Cave n'ont pas de check.
- BizHawk se fige parfois ; le client se reconnecte ensuite.
- Cette version n'a pas encore été testée sur une partie complète : signale les problèmes dans les
  [Issues](https://github.com/OmgaCraft/ArchiPelago-Pokemon-XY/issues), avec le journal du client BizHawk.
