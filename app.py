from flask import Flask, render_template, request, redirect, url_for
import json
import os
from datetime import datetime
from equipos_dict import EQUIPOS

JSON_FILE = "liga_mx_apertura_2025.json"

app = Flask(__name__)

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

def obtener_jornada_activa(rounds):
    """Devuelve el número de la jornada en curso o la próxima por jugar"""
    ahora = datetime.now().timestamp()
    for round_number, round_data in sorted(rounds.items(), key=lambda x: int(x[0])):
        eventos = round_data.get("events", [])
        if not eventos:
            continue
        for e in eventos:
            start_ts = e.get("startTimestamp")
            if start_ts and int(start_ts) >= ahora:
                return round_number
            if start_ts and int(start_ts) <= ahora and not e.get("status", {}).get("type") == "finished":
                return round_number
    return list(rounds.keys())[-1]

# ---------------- RUTAS PRINCIPALES ----------------

@app.route("/")
def mostrar_calendario():
    rounds = cargar_datos()
    rounds_filtered = {k: v for k, v in rounds.items() if v.get('events')}
    rounds_sorted = dict(sorted(rounds_filtered.items(), key=lambda x: int(x[0])))
    jornada_activa = obtener_jornada_activa(rounds_sorted)
    # Formatear fecha/hora para cada evento
    for ronda in rounds_sorted.values():
        eventos = ronda.get("events", [])
        for i, e in enumerate(eventos):
            ronda["events"][i] = formatear_evento(e)
    return render_template(
        "calendario.html",
        rounds=rounds_sorted,
        team_logo_map=EQUIPOS,
        jornada_activa=jornada_activa
    )

# ---------------- USUARIOS ----------------

USUARIOS_FILE = "usuarios.json"

@app.route("/usuarios", methods=["GET", "POST"])
def gestion_usuarios():
    if os.path.exists(USUARIOS_FILE):
        with open(USUARIOS_FILE, "r", encoding="utf-8") as f:
            usuarios = json.load(f)
    else:
        usuarios = []

    if request.method == "POST":
        nuevo_usuario = request.form.get("nombre")
        if nuevo_usuario and nuevo_usuario not in usuarios:
            usuarios.append(nuevo_usuario)
            with open(USUARIOS_FILE, "w", encoding="utf-8") as f:
                json.dump(usuarios, f, indent=2)
        return redirect(url_for("gestion_usuarios"))

    return render_template("usuarios.html", usuarios=usuarios)

# ---------------- CAPTURA DE PRONOSTICOS ----------------

PRONOSTICOS_FILE = "pronosticos.json"

@app.route("/captura_pronosticos/<jornada>", methods=["GET", "POST"])
def captura_pronosticos_jornada(jornada):
    rounds = cargar_datos()
    round_data = rounds.get(jornada, {})
    eventos = round_data.get("events", [])

    if request.method == "POST":
        pronosticos = {}
        for e in eventos:
            key = f"{e['id']}"
            pronosticos[key] = request.form.get(key)
        # Guardar pronósticos
        if os.path.exists(PRONOSTICOS_FILE):
            with open(PRONOSTICOS_FILE, "r", encoding="utf-8") as f:
                all_pronosticos = json.load(f)
        else:
            all_pronosticos = {}
        all_pronosticos[jornada] = pronosticos
        with open(PRONOSTICOS_FILE, "w", encoding="utf-8") as f:
            json.dump(all_pronosticos, f, indent=2)
        return redirect(url_for("captura_pronosticos_jornada", jornada=jornada))

    return render_template(
        "captura_pronosticos.html",
        jornada=jornada,
        eventos=eventos,
        team_logo_map=EQUIPOS
    )

# ---------------- EVALUACION DE PRONOSTICOS ----------------

@app.route("/evaluar_pronosticos/<jornada>")
def evaluar_pronosticos_jornada(jornada):
    rounds = cargar_datos()
    round_data = rounds.get(jornada, {})
    eventos = round_data.get("events", [])

    if os.path.exists(PRONOSTICOS_FILE):
        with open(PRONOSTICOS_FILE, "r", encoding="utf-8") as f:
            all_pronosticos = json.load(f)
        pronosticos = all_pronosticos.get(jornada, {})
    else:
        pronosticos = {}

    # Determinar resultado real usando winnerCode: 1=Local, 2=Empate, 3=Visitante
    resultados = {}
    for e in eventos:
        wc = e.get("winnerCode")
        if wc == 1:
            resultado = "local"
        elif wc == 2:
            resultado = "visitante"
        else:
            resultado = "empate"
        resultados[e["id"]] = resultado

    return render_template(
        "evaluar_pronosticos.html",
        jornada=jornada,
        eventos=eventos,
        pronosticos=pronosticos,
        resultados=resultados,
        team_logo_map=EQUIPOS
    )

# ---------------- FILTROS JINJA ----------------

@app.template_filter('timestamp_to_datetime')
def timestamp_to_datetime_filter(ts):
    if ts:
        return datetime.fromtimestamp(int(ts)).strftime('%Y-%m-%d %H:%M')
    return "N/A"

# ---------------- MAIN ----------------

if __name__ == "__main__":
    app.run(debug=True)
