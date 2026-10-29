from dataclasses import dataclass
from Options import PerGameCommonOptions, DefaultOnToggle, Toggle, Choice, Range

class IncludeHiddenItems(DefaultOnToggle):
    """Include hidden items scattered across Kalos in the location pool."""
    display_name = "Include Hidden Items"

class RequireDowsingMachine(Toggle):
    """Require the Dowsing Machine item in logic to access hidden ground items."""
    display_name = "Require Dowsing Machine for Hidden Items"

class TrainerSanity(Toggle):
    """Include beating in-game trainers (Youngsters, Lasses, Gym Trainers, Rivals) as location checks."""
    display_name = "Trainersanity"

class RandomizeWildPokemon(Toggle):
    """Replace the wild Pokemon of every route and cave (grass, water, fishing, hordes) with Pokemon of a
    similar strength. Needs the game patch: see the guide."""
    display_name = "Randomize Wild Pokemon"

class RandomizeTrainers(Toggle):
    """Replace the Pokemon of every trainer, gym leaders and rivals included, with Pokemon of a similar
    strength. Levels are kept and the trainers use the moves their Pokemon learn at that level."""
    display_name = "Randomize Trainers"

class RandomizeStarters(Toggle):
    """Replace the three Kalos starters and the three Kanto starters with other basic Pokemon."""
    display_name = "Randomize Starters"

class RandomizeMoves(Toggle):
    """Shuffle the moves Pokemon learn by level-up. Moves learned at level 5 or earlier stay the same."""
    display_name = "Randomize Moves"

class RandomizeAbilities(Toggle):
    """Shuffle the abilities of every Pokemon species."""
    display_name = "Randomize Abilities"

class ExperienceMultiplier(Range):
    """Experience gained in battle, in percent: 100 is the normal game, 200 doubles it, 25 divides it by four."""
    display_name = "Experience Multiplier (%)"
    range_start = 25
    range_end = 400
    default = 100

class Goal(Choice):
    """Goal condition for completing the multiworld."""
    display_name = "Goal"
    option_pokemon_league = 0
    default = 0

@dataclass
class PokemonXYOptions(PerGameCommonOptions):
    include_hidden_items: IncludeHiddenItems
    require_dowsing_machine: RequireDowsingMachine
    trainersanity: TrainerSanity
    randomize_wild_pokemon: RandomizeWildPokemon
    randomize_trainers: RandomizeTrainers
    randomize_starters: RandomizeStarters
    randomize_moves: RandomizeMoves
    randomize_abilities: RandomizeAbilities
    experience_multiplier: ExperienceMultiplier
    goal: Goal

@dataclass
class PokemonYOptions(PerGameCommonOptions):
    include_hidden_items: IncludeHiddenItems
    require_dowsing_machine: RequireDowsingMachine
    trainersanity: TrainerSanity
    randomize_wild_pokemon: RandomizeWildPokemon
    randomize_trainers: RandomizeTrainers
    randomize_starters: RandomizeStarters
    randomize_moves: RandomizeMoves
    randomize_abilities: RandomizeAbilities
    experience_multiplier: ExperienceMultiplier
    goal: Goal

@dataclass
class PokemonXOptions(PerGameCommonOptions):
    include_hidden_items: IncludeHiddenItems
    require_dowsing_machine: RequireDowsingMachine
    trainersanity: TrainerSanity
    randomize_wild_pokemon: RandomizeWildPokemon
    randomize_trainers: RandomizeTrainers
    randomize_starters: RandomizeStarters
    randomize_moves: RandomizeMoves
    randomize_abilities: RandomizeAbilities
    experience_multiplier: ExperienceMultiplier
    goal: Goal

pokemon_y_options = {
    "include_hidden_items": IncludeHiddenItems,
    "require_dowsing_machine": RequireDowsingMachine,
    "trainersanity": TrainerSanity,
    "randomize_wild_pokemon": RandomizeWildPokemon,
    "randomize_trainers": RandomizeTrainers,
    "randomize_starters": RandomizeStarters,
    "randomize_moves": RandomizeMoves,
    "randomize_abilities": RandomizeAbilities,
    "experience_multiplier": ExperienceMultiplier,
    "goal": Goal,
}

option_definitions = pokemon_y_options
