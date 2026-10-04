# Guide — Pokémon X/Y Archipelago (v0.0.8)

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

### Première connexion : choisir ton fichier de jeu (une seule fois)

Le client a besoin du fichier de ton jeu pour construire le patch. Il ne le modifie jamais : il
lit dedans, puis range un petit fichier modifié dans le dossier de mods de BizHawk
(`3DS\User\load\mods\0004000000055E00`).

1. Fais comme d'habitude : BizHawk avec Pokémon Y, le script Lua, puis le client BizHawk
   d'Archipelago connecté au serveur.
2. Juste après la connexion, une fenêtre Windows s'ouvre :
   **« Select Pokemon Y (USA) ROM, decrypted (.3ds) »**.
   Elle s'ouvre parfois **derrière** les autres fenêtres : si tu ne la vois pas, regarde la barre des tâches.
3. Dans cette fenêtre, va chercher **le même fichier `.3ds` que tu ouvres dans BizHawk**
   (File > Open ROM), sélectionne-le, puis clique sur **Ouvrir**.
4. Regarde la fenêtre du client BizHawk :
   - `Patch du jeu : … Poké Ball(s) au sol modifiée(s)` puis `Patch Archipelago installé…` :
     c'est réussi, passe à l'étape suivante ;
   - `Échec du patch du jeu : Dump chiffré…` : ton fichier est chiffré (voir plus bas) ;
   - `Patch du jeu non installé…` : aucun fichier choisi (fenêtre fermée ou annulée).

   Dans les deux derniers cas, le jeu marche quand même, comme avant le patch.
5. Archipelago retient ton choix : la fenêtre ne s'ouvrira plus. Si tu l'as fermée sans choisir,
   elle reviendra au prochain lancement du client.

**Chiffré ou déchiffré ?** Si BizHawk t'a demandé les fichiers `aes_keys.txt` et `seeddb.bin` quand
tu as ouvert le jeu la première fois, ton dump est chiffré : le patch ne marche pas avec. Sinon, il
est déchiffré et tout va bien.

**Ton fichier n'apparaît pas dans la fenêtre ?** Elle n'affiche que les fichiers `.3ds`. Les dumps
`.cia` ne sont pas pris en charge par le patch.

**Changer de fichier plus tard :** ouvre `C:\ProgramData\Archipelago\host.yaml` avec le Bloc-notes,
cherche `pokemon_xy_settings`, et corrige le chemin de la ligne `rom_file`.

### Ensuite : redémarrer le jeu une fois

Sauvegarde en jeu, puis Emulation > Reboot Core dans BizHawk. Un message te le rappelle à l'écran.
Le patch est refait tout seul à chaque nouvelle partie (il faudra alors redémarrer une fois de plus).

### Bon à savoir sur le patch

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

- **Badges — « Suppress »** : si tu as déjà reçu le badge d'une arène sans avoir battu le champion
  (option `randomize_badges`, ou partie générée avant la v0.0.8), le champion refuse le combat. Clique « Suppress » sur ce badge, parle au champion, bats-le :
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
| `randomize_badges` | Mélange les badges dans le multiworld (défaut : non, chaque champion donne son badge). Activé, un badge reçu avant le combat fait refuser le combat au champion : clique « Suppress » pour ce badge dans la fenêtre d'aide, puis parle-lui. |
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
