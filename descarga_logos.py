import os
import json
import requests

# Archivos JSON de ejemplo
json_file = "liga_mx_apertura_2025.json"

# Carpeta donde guardar los logos
logos_dir = "static/logos"
os.makedirs(logos_dir, exist_ok=True)

# Función para descargar una imagen
def download_logo(url, filename):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        with open(filename, "wb") as f:
            f.write(response.content)
        print(f"Logo guardado: {filename}")
    except Exception as e:
        print(f"No se pudo descargar {url}: {e}")

# Leer JSON
with open(json_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# Crear un set para evitar duplicados
teams_downloaded = set()

# Iterar por todas las jornadas y eventos
for jornada, jornada_data in data.items():
    events = jornada_data.get("events", [])
    for event in events:
        for team_type in ["homeTeam", "awayTeam"]:
            team = event.get(team_type)
            if not team:
                continue
            team_id = team["id"]
            if team_id in teams_downloaded:
                continue  # ya descargado
            # URL del logo (ajusta si tu JSON tiene otra ruta)
            # Aquí usamos un placeholder; ajusta según la estructura de tu JSON
            logo_url = team.get("logoUrl") or team.get("images", {}).get("default")
            if not logo_url:
                print(f"No hay URL para {team['name']}")
                continue
            filename = os.path.join(logos_dir, f"{team_id}.png")
            download_logo(logo_url, filename)
            teams_downloaded.add(team_id)

print("Descarga de logos finalizada.")
