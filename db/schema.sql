CREATE TABLE IF NOT EXISTS Type (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS Pokemon (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    form TEXT,
    hp INTEGER NOT NULL,
    attack INTEGER NOT NULL,
    defense INTEGER NOT NULL,
    special_attack INTEGER NOT NULL,
    special_defense INTEGER NOT NULL,
    speed INTEGER NOT NULL,
    generation_id INTEGER NOT NULL CHECK(
        generation_id >= 1
        AND generation_id <= 9
    )
);

CREATE TABLE IF NOT EXISTS PokemonType (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pokemon_id INTEGER,
    type_id INTEGER,
    FOREIGN KEY (pokemon_id) REFERENCES Pokemon(id),
    FOREIGN KEY (type_id) REFERENCES Type(id)
);