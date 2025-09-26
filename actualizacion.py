import json
import time
import requests
import sqlite3

# Cargar JSON inicial con todas las rondas
JSON_FILE = "liga_mx_apertura_2025.json"
with open(JSON_FILE, "r", encoding="utf-8") as f:
    all_rounds = json.load(f)

# Lista para guardar partidos que sí se actualizaron
partidos_actualizados = []

# Función para actualizar solo partidos próximos o en curso
def update_upcoming_matches(all_rounds, base_url="https://www.sofascore.com/api/v1/match/"):
    now = int(time.time())  # timestamp actual
    for round_number, round_data in all_rounds.items():
        for event in round_data.get("events", []):  # protección contra KeyError
            start_ts = event.get("startTimestamp", 0)
            status_type = event.get("status", {}).get("type", "")

            # Solo actualizar si el partido no terminó y está cerca o en curso
            if status_type != "finished" and start_ts >= now - 3600:
                match_id = event.get("id")
                if match_id:
                    try:
                        resp = requests.get(f"{base_url}{match_id}")
                        time.sleep(1)  # evitar bloqueo por exceso de peticiones
                        if resp.status_code == 200:
                            match_data = resp.json()
                            event["homeScore"] = match_data.get("homeScore", event.get("homeScore"))
                            event["awayScore"] = match_data.get("awayScore", event.get("awayScore"))
                            event["status"] = match_data.get("status", event.get("status"))
                            event["winnerCode"] = match_data.get("winnerCode", event.get("winnerCode"))
                            partidos_actualizados.append(event)
                        else:
                            print(f"⚠️ Partido {match_id} no disponible: {resp.status_code}")
                    except Exception as e:
                        print(f"Error al actualizar partido {match_id}: {e}")

# Ejecutar la actualización
update_upcoming_matches(all_rounds)

# Guardar JSON solo si hubo actualizaciones
if partidos_actualizados:
    with open("all_rounds_updated.json", "w", encoding="utf-8") as f:
        json.dump(all_rounds, f, ensure_ascii=False, indent=2)
    print(f"{len(partidos_actualizados)} partidos actualizados. JSON guardado.")

    # Actualizar la base de datos
    conn = sqlite3.connect("liga_mx.db")
    cursor = conn.cursor()

    for event in partidos_actualizados:
        partido_id = event.get("id")
        if not partido_id:
            continue

        cursor.execute("SELECT id FROM partidos WHERE id = ?", (partido_id,))
        if cursor.fetchone():
            cursor.execute('''
                UPDATE partidos SET
                    start_timestamp = ?,
                    status_code = ?,
                    status_desc = ?,
                    goles_local = ?,
                    goles_visitante = ?,
                    ganador = ?
                WHERE id = ?
            ''', (
                event.get("startTimestamp", 0),
                event.get("status", {}).get("code", 0),
                event.get("status", {}).get("description", ""),
                event.get("homeScore", {}).get("current", 0),
                event.get("awayScore", {}).get("current", 0),
                event.get("winnerCode", None),
                partido_id
            ))

    conn.commit()
    conn.close()
    print("Base de datos actualizada correctamente.")
else:
    print("No hubo partidos disponibles para actualizar. JSON no guardado. BD no modificada.")