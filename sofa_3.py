import json
import time
from datetime import datetime
import requests

JSON_FILE = "liga_mx_apertura.json"
API_URL_TEMPLATE = "https://www.sofascore.com/api/v1/unique-tournament/11621/season/76500/events/round/{}"

# Cargar JSON existente
with open(JSON_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

ahora = time.time()

# Función para obtener los datos de una ronda desde la API
def fetch_round(round_number):
    url = API_URL_TEMPLATE.format(round_number)
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error al obtener ronda {round_number}: {response.status_code}")
        return None

# Recorrer rondas
for round_number, round_data in data.items():
    eventos = round_data.get("events", [])
    
    # Solo actualizar si hay partidos futuros
    proximo = any(event.get("startTimestamp", 0) > ahora for event in eventos)
    if proximo:
        print(f"Actualizando ronda {round_number}...")
        nueva_ronda = fetch_round(round_number)
        if nueva_ronda:
            data[round_number]["events"] = nueva_ronda.get("events", [])

# Guardar JSON actualizado
with open(JSON_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Actualización completa.")
