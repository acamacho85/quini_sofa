from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import json
import os
from datetime import datetime
from equipos_dict import EQUIPOS

JSON_FILE = "liga_mx_apertura_2025.json"
#USUARIOS_FILE = "usuarios.json"
#PRONOSTICOS_FILE = "pronosticos.json"
DB_FILE = "quini.db"

app = Flask(__name__)
app.secret_key = "secret_key_para_flash"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL
    )""")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS pronosticos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        jornada INTEGER NOT NULL,
        match_id TEXT NOT NULL,
        pronostico TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")
    conn.commit()
    conn.close()

def formatear_evento(evento):
    ts = evento.get("startTimestamp")
    if ts:
        dt = datetime.fromtimestamp(int(ts))
        evento["fecha_str"] = dt.strftime("%Y-%m-%d")
        evento["hora_str"] = dt.strftime("%H:%M")
    else:
        evento["fecha_str"] = "N/A"
        evento["hora_str"] = "N/A"
    return evento

def cargar_datos():
    """Carga el JSON más reciente disponible"""
    file_path = "all_rounds_updated.json" if os.path.exists("all_rounds_updated.json") else JSON_FILE
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def cargar_json(file):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def guardar_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def obtener_jornada_activa(rounds):
    """Devuelve el número de la jornada en curso o la próxima por jugar"""
    ahora = datetime.now().timestamp()
    for round_number, round_data in sorted(rounds.items(), key=lambda x: int(x[0])):
        eventos = round_data.get("events", [])
        if not eventos:
            continue

        # Checamos si alguno está en progreso o pendiente
        for e in eventos:
            start_ts = e.get("startTimestamp")
            if start_ts and int(start_ts) >= ahora:
                return round_number  # próxima jornada
            if start_ts and int(start_ts) <= ahora and not e.get("status", {}).get("type") == "finished":
                return round_number  # jornada en curso
    return list(rounds.keys())[-1]  # fallback: última jornada

@app.route("/")
def calendario():
    rounds = cargar_datos()
    # Filtrar solo las rondas/jornadas que tengan al menos un partido
    rounds_filtered = {k: v for k, v in rounds.items() if v.get('events')}
    # Ordenarlas por número
    rounds_sorted = dict(sorted(rounds_filtered.items(), key=lambda x: int(x[0])))
    #Seleccionar jornada activa o proxima
    jornada_activa = obtener_jornada_activa(rounds_sorted)
    # Formatear fecha/hora para cada evento
    for ronda in rounds_sorted.values():
        eventos = ronda.get("events", [])
        for i, e in enumerate(eventos):
            ronda["events"][i] = formatear_evento(e)
    return render_template("calendario.html", rounds=rounds_sorted, team_logo_map=EQUIPOS, jornada_activa=jornada_activa)

@app.template_filter('timestamp_to_datetime')
def timestamp_to_datetime_filter(ts):
    if ts:
        return datetime.fromtimestamp(int(ts)).strftime('%Y-%m-%d %H:%M')
    return "N/A"

@app.route("/usuarios", methods=["GET", "POST"])
def usuarios():
    usuarios = cargar_json(USUARIOS_FILE)
    if request.method == "POST":
        nombre = request.form.get("nombre")
        if nombre and nombre not in usuarios:
            usuarios.append(nombre)
            guardar_json(USUARIOS_FILE, usuarios)
        return redirect(url_for("usuarios"))
    return render_template("usuarios.html", usuarios=usuarios)

# ----------------------------
# Captura de pronósticos
# ----------------------------
@app.route("/captura_pronosticos", methods=["GET", "POST"])
@app.route("/captura_pronosticos/<int:jornada>", methods=["GET"])
def captura_pronosticos(jornada=None):
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()

    rounds = cargar_datos()
    rounds_filtered = {k: v for k, v in rounds.items() if v.get('events')}
    rounds_sorted = dict(sorted(rounds_filtered.items(), key=lambda x: int(x[0])))
    jornada_activa = jornada or obtener_jornada_activa(rounds_sorted)

    return render_template("captura_pronosticos.html",
                           rounds=rounds_sorted,
                           team_logo_map=EQUIPOS,
                           jornada_activa=jornada_activa,
                           users=users)

@app.route("/guardar_pronosticos/<int:jornada>", methods=["POST"])
def guardar_pronosticos(jornada):
    user_id = request.form.get("user_id")
    if not user_id:
        flash("Debe seleccionar un usuario")
        return redirect(url_for("captura_pronosticos", jornada=jornada))

    conn = get_db_connection()
    for key, value in request.form.items():
        if key.startswith("match_"):
            match_id = key.replace("match_", "")
            conn.execute("INSERT INTO pronosticos (user_id, jornada, match_id, pronostico) VALUES (?, ?, ?, ?)",
                         (user_id, jornada, match_id, value))
    conn.commit()
    conn.close()
    flash("Pronósticos guardados correctamente")
    return redirect(url_for("captura_pronosticos", jornada=jornada))

# ----------------------------
# Evaluación de resultados
# ----------------------------
@app.route("/evaluacion")
def evaluacion():
    conn = get_db_connection()
    users = conn.execute("SELECT * FROM users").fetchall()
    pronosticos = conn.execute("SELECT * FROM pronosticos").fetchall()
    conn.close()

    rounds = cargar_datos()
    rounds_filtered = {k: v for k, v in rounds.items() if v.get('events')}
    rounds_sorted = dict(sorted(rounds_filtered.items(), key=lambda x: int(x[0])))

    # Podemos calcular aciertos por usuario
    resultados = {}
    for p in pronosticos:
        match = None
        for r in rounds_sorted.values():
            for e in r.get("events", []):
                if str(e.get("id")) == str(p["match_id"]):
                    match = e
                    break
        if match:
            winner = match.get("winnerCode")
            pron = p["pronostico"]
            acierto = False
            if (winner == 1 and pron == "local") or (winner == 2 and pron == "visitante") or (winner == 3 and pron == "empate"):
                acierto = True
            if p["user_id"] not in resultados:
                resultados[p["user_id"]] = []
            resultados[p["user_id"]].append(acierto)

    return render_template("evaluacion.html", rounds=rounds_sorted, team_logo_map=EQUIPOS,
                           users=users, resultados=resultados)

# ----------------------------
# Usuarios
# ----------------------------
@app.route("/usuarios", methods=["GET", "POST"])
def usuarios():
    conn = get_db_connection()
    if request.method == "POST":
        username = request.form.get("username")
        if username:
            try:
                conn.execute("INSERT INTO users (username) VALUES (?)", (username,))
                conn.commit()
                flash(f"Usuario {username} agregado")
            except sqlite3.IntegrityError:
                flash(f"El usuario {username} ya existe")
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return render_template("usuarios.html", users=users)

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
