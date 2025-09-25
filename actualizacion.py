import json
import time
import requests

# Cargar JSON inicial con todas las rondas
JSON_FILE = "liga_mx_apertura_2025.json"
with open(JSON_FILE, "r", encoding="utf-8") as f:
    all_rounds = json.load(f)

# Función para actualizar solo partidos próximos o en curso
def update_upcoming_matches(all_rounds, base_url="https://www.sofascore.com/api/v1/match/"):
    now = int(time.time())  # timestamp actual
    for round_number, round_data in all_rounds.items():
        for event in round_data["events"]:
            start_ts = event.get("startTimestamp", 0)
            status_type = event.get("status", {}).get("type", "")

            # Solo actualizar si el partido no terminó
            if status_type != "finished" and start_ts >= now - 3600:  # 1 hora antes hasta futuros
                match_id = event.get("id")
                if match_id:
                    try:
                        resp = requests.get(f"{base_url}{match_id}")
                        if resp.status_code == 200:
                            match_data = resp.json()
                            # Actualizamos score y estado
                            event["homeScore"] = match_data.get("homeScore", event["homeScore"])
                            event["awayScore"] = match_data.get("awayScore", event["awayScore"])
                            event["status"] = match_data.get("status", event["status"])
                        else:
                            print(f"Partido {match_id} no disponible: {resp.status_code}")
                    except Exception as e:
                        print(f"Error al actualizar partido {match_id}: {e}")

# Ejecutar la actualización
update_upcoming_matches(all_rounds)

# Guardar JSON actualizado
with open("all_rounds_updated.json", "w", encoding="utf-8") as f:
    json.dump(all_rounds, f, ensure_ascii=False, indent=2)
