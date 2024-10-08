import csv
import io
import sqlite3

from flask import Flask, g, jsonify, redirect, render_template, request, url_for

app = Flask(__name__)
DATABASE_PATH = "db/pokemon.db"


def get_db():
    """
    Connect to the SQLite database. If no connection exists in the current app context, create one.
    """
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE_PATH)
        db.row_factory = (
            sqlite3.Row
        )  # This allows row objects to be treated like dictionaries
    return db


def init_db() -> None:
    """
    Initialize the database with the schema and populate initial data.
    """
    with app.app_context():
        db = get_db()
        cur = db.cursor()

        # Execute schema.sql script to create database tables
        with app.open_resource("../db/schema.sql") as f:
            cur.executescript(f.read().decode("utf8"))

        # Insert initial Pokemon types into the Type table if it is empty
        cur.execute("SELECT COUNT(*) FROM Type")
        count = cur.fetchone()[0]
        if count == 0:
            cur.execute(
                """
                INSERT INTO 
                    Type (name)
                VALUES
                    ('Normal'),
                    ('Fire'),
                    ('Water'),
                    ('Electric'),
                    ('Grass'),
                    ('Ice'),
                    ('Fighting'),
                    ('Poison'),
                    ('Ground'),
                    ('Flying'),
                    ('Psychic'),
                    ('Bug'),
                    ('Rock'),
                    ('Ghost'),
                    ('Dragon'),
                    ('Dark'),
                    ('Steel'),
                    ('Fairy');
                """
            )

        db.commit()


def import_csv(file: str) -> None:
    """
    Import Pokemon data from a CSV file and insert it into the database.
    """
    with app.app_context():
        db = get_db()
        cur = db.cursor()

        csvfile = io.StringIO(file)
        reader = csv.DictReader(csvfile)
        for row in reader:
            # Check if the Pokemon already exists in the database
            cur.execute(
                """
                SELECT * FROM Pokemon WHERE pokemon_id = ? AND name = ? AND form = ? AND hp = ? AND attack = ? AND defense = ? AND special_attack = ? AND special_defense = ? AND speed = ? AND generation_id = ?
                """,
                (
                    row["Number"],
                    row["Name"],
                    row["Form"],
                    row["HP"],
                    row["Attack"],
                    row["Defense"],
                    row["Sp.Attack"],
                    row["Sp.Defense"],
                    row["Speed"],
                    row["Generation"],
                ),
            )
            if cur.fetchone() is None:
                # If the Pokemon does not exist with the exact same details, insert it
                cur.execute(
                    """
                    INSERT INTO Pokemon (pokemon_id, name, form, hp, attack, defense, special_attack, special_defense, speed, generation_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        row["Number"],
                        row["Name"],
                        row["Form"],
                        row["HP"],
                        row["Attack"],
                        row["Defense"],
                        row["Sp.Attack"],
                        row["Sp.Defense"],
                        row["Speed"],
                        row["Generation"],
                    ),
                )

                types = (row["Type 1"], row["Type 2"])
                for type in types:
                    if type and type.strip():
                        # Check if the PokemonType already exists in the database
                        cur.execute(
                            """
                            SELECT * FROM PokemonType WHERE pokemon_id = ? AND type_id = (SELECT id FROM Type WHERE name = ?)
                            """,
                            (cur.lastrowid, type),
                        )
                        if cur.fetchone() is None:
                            # If the PokemonType does not exist, insert it
                            cur.execute(
                                """
                                INSERT INTO PokemonType (pokemon_id, type_id)
                                VALUES (?, (SELECT id FROM Type WHERE name = ?))
                                """,
                                (cur.lastrowid, type),
                            )
        db.commit()


@app.route("/")
def index():
    """
    Render the main page displaying a list of Pokemon with pagination.
    """
    db = get_db()
    cur = db.cursor()

    # Pagination
    page = request.args.get(key="page", default=1, type=int)
    per_page = 25
    offset = (page - 1) * per_page

    cur.execute(
        """
        SELECT
            Pokemon.*,
            GROUP_CONCAT(Type.name) as types
        FROM
            Pokemon
            INNER JOIN PokemonType ON Pokemon.id = PokemonType.pokemon_id
            INNER JOIN Type ON PokemonType.type_id = Type.id
        GROUP BY
            Pokemon.id
        LIMIT ? OFFSET ?
    """,
        (per_page, offset),
    )
    pokemon = cur.fetchall()

    return render_template("index.html", cur=cur, pokemon=pokemon, page=page)


@app.route("/upload", methods=["GET", "POST"])
def upload():
    """
    Handle file upload and import CSV data into the database.
    """
    if request.method == "POST":
        if "csvFile" not in request.files:
            return "No file part"
        file = request.files["csvFile"]
        if file.filename == "":
            return "No selected file"
        if file:
            file_content = file.read().decode("utf8")
            import_csv(file_content)
            return redirect(url_for("index"))
    return redirect(url_for("index"))


@app.route("/query", methods=["GET"])
def query():
    """
    Search and filter Pokemon by name and attributes, return results as JSON.
    """
    name = request.args.get("name", "")
    page = request.args.get(key="page", default=1, type=int)
    per_page = 25
    offset = (page - 1) * per_page

    filters = []
    allowed_filters = [
        "hp",
        "attack",
        "defense",
        "special_attack",
        "special_defense",
        "speed",
        "generation_id",
    ]

    for attr in allowed_filters:
        min_val = request.args.get(f"min_{attr}")
        max_val = request.args.get(f"max_{attr}")
        if min_val:
            filters.append(f"{attr} >= {min_val}")
        if max_val:
            filters.append(f"{attr} <= {max_val}")

    filter_clause = " AND ".join(filters) if filters else "1=1"

    db = get_db()
    cur = db.cursor()

    cur.execute(
        f"""
        SELECT
            Pokemon.*,
            GROUP_CONCAT(Type.name) as types
        FROM
            Pokemon
            INNER JOIN PokemonType ON Pokemon.id = PokemonType.pokemon_id
            INNER JOIN Type ON PokemonType.type_id = Type.id
        WHERE
            Pokemon.name LIKE ? AND {filter_clause}
        GROUP BY
            Pokemon.id
        LIMIT ? OFFSET ?
    """,
        ("%" + name + "%", per_page, offset),
    )
    rows = cur.fetchall()

    results = [dict(row) for row in rows]
    return jsonify(results)


@app.route("/insert", methods=["POST"])
def insert():
    data = request.get_json()
    db = get_db()
    cur = db.cursor()

    edit_id = data.get("editId")  # Get the edit ID from the incoming data

    if edit_id:  # If editId is present, perform an update
        # Update existing Pokémon
        cur.execute(
            """
            UPDATE Pokemon
            SET pokemon_id = ?, name = ?, form = ?, hp = ?, attack = ?, defense = ?, special_attack = ?, special_defense = ?, speed = ?, generation_id = ?
            WHERE id = ?
            """,
            (
                data["number"],
                data["name"],
                data["form"],
                data["hp"],
                data["attack"],
                data["defense"],
                data["special_attack"],
                data["special_defense"],
                data["speed"],
                data["generation"],
                edit_id,  # Include the edit ID to specify which Pokémon to update
            ),
        )
    else:  # If no editId, perform an insert
        # Insert new Pokémon
        cur.execute(
            """
            INSERT INTO Pokemon (pokemon_id, name, form, hp, attack, defense, special_attack, special_defense, speed, generation_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["number"],
                data["name"],
                data["form"],
                data["hp"],
                data["attack"],
                data["defense"],
                data["special_attack"],
                data["special_defense"],
                data["speed"],
                data["generation"],
            ),
        )
        pokemon_id = cur.lastrowid  # Get the ID of the newly inserted Pokémon

    # Insert or update Pokémon types
    types = (data["type1"].lower().capitalize(), data["type2"].lower().capitalize())
    for type_name in types:
        if type_name and type_name.strip():
            # Fetch the type ID
            cur.execute("SELECT id FROM Type WHERE name = ?", (type_name,))
            type_id = cur.fetchone()
            if type_id:
                # Check if the type already exists for this Pokémon
                cur.execute(
                    "SELECT id FROM PokemonType WHERE pokemon_id = ? AND type_id = ?",
                    (edit_id if edit_id else pokemon_id, type_id[0]),
                )
                existing_type = cur.fetchone()

                if not existing_type:  # If the type doesn't exist, insert it
                    cur.execute(
                        """
                        INSERT INTO PokemonType (pokemon_id, type_id)
                        VALUES (?, ?)
                        """,
                        (edit_id if edit_id else pokemon_id, type_id[0]),
                    )
            else:
                print(f"Type '{type_name}' not found in Type table.")

    db.commit()
    return jsonify({"status": "success"})


@app.teardown_appcontext
def close_connection(exception):
    """
    Close the database connection at the end of the request.
    """
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


if __name__ == "__main__":
    with app.app_context():
        init_db()  # Initialize the database if the script is run directly

    app.run(debug=True)  # Run the Flask app in debug mode
