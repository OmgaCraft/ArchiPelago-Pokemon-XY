# Pokémon X and Y Archipelago Setup Guide

This guide will walk you through setting up and playing a **Pokémon X and Y** Archipelago Multiworld game using BizHawk (3DS core "Encore") and the Archipelago BizHawk Client.

---

## 📋 Requirements

* **Archipelago**: v0.6.7 (tested).
* **Emulator**: BizHawk 2.10 or newer (tested with 2.11.1).
* **Game ROM**: Your own dump of **Pokémon Y (USA)**, preferably decrypted. Pokémon X and other regions are not confirmed.
* **Lua Connector**: `pokemon_xy_connector.lua` (included in the release). Put it in `Archipelago\data\lua\`: it needs the `json.lua` and `base64.lua` files there.
* **APWorld Package**: `pokemon_xy.apworld` (included in the release).

---

## ⚙️ Installation & Setup

### 1. Install the `.apworld` File
Copy `pokemon_xy.apworld` into your Archipelago installation's `custom_worlds` folder:
* **Windows**: `C:\ProgramData\Archipelago\custom_worlds\` or inside your standalone Archipelago installation directory.

### 2. Generate a Multiworld Seed
1. Create or place a `Pokemon X and Y.yaml` player file into your Archipelago `Players` directory.
2. Run `ArchipelagoGenerate.exe` to build your `.zip` multiworld seed.
3. Host the room locally via `ArchipelagoServer.exe` or upload the seed to [archipelago.gg](https://archipelago.gg).

---

## 🎮 How to Play & Connect

1. **Launch BizHawk**:
   * Open BizHawk and load your **Pokémon X** or **Pokémon Y** ROM.

2. **Open Lua Console**:
   * In BizHawk, navigate to `Tools -> Lua Console`.
   * Click `Script -> Open Script...` and select `pokemon_xy_connector.lua`.

3. **Launch Archipelago BizHawk Client**:
   * Open `ArchipelagoBizHawkClient.exe`.
   * Connect to your Archipelago server (e.g. `localhost:38281`).

4. **Enjoy your Multiworld!**:
   * The client will automatically connect to your BizHawk emulator and sync items and location checks bidirectionally in real-time.
