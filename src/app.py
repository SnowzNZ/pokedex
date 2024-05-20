import csv
import io
import sqlite3

from flask import Flask, g, redirect, render_template, request, url_for

app = Flask(__name__)
DATABASE_PATH = "db/pokemon.db"


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE_PATH)
        db.row_factory = sqlite3.Row

    return db


def init_db() -> None:
    with app.app_context():
        db = get_db()

        cur = db.cursor()

        with app.open_resource("../db/schema.sql") as f:
            cur.executescript(f.read().decode("utf8"))  # type: ignore

        # Insert the Pokemon types into the Type table
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
    with app.app_context():
        db = get_db()

        cur = db.cursor()

        csvfile = io.StringIO(file)
        reader = csv.DictReader(csvfile)
        for row in reader:
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
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT * FROM Pokemon")
    pokemon = cur.fetchall()

    return render_template("index.html", cur=cur, pokemon=pokemon)


@app.route("/upload", methods=["GET", "POST"])
def upload():
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


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


if __name__ == "__main__":
    with app.app_context():
        init_db()

    app.run(debug=True)
