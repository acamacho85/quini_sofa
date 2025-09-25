from flask import Flask, render_template
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
    return render_template("index.html", rounds=rounds_sorted, team_logo_map=EQUIPOS, jornada_activa=jornada_activa)

@app.template_filter('timestamp_to_datetime')
def timestamp_to_datetime_filter(ts):
    if ts:
        return datetime.fromtimestamp(int(ts)).strftime('%Y-%m-%d %H:%M')
    return "N/A"

if __name__ == "__main__":
    app.run(debug=True)
