import os
import json
import requests

# Archivos JSON de ejemplo
json_file = "liga_mx_apertura_2025.json"
# Carpeta donde se guardarán los logos
logos_folder = "logos"
os.makedirs(logos_folder, exist_ok=True)

# Cargar JSON
with open(json_file, "r", encoding="utf-8") as f:
    data = json.load(f)

# Recorrer todas las jornadas
for jornada, jornada_data in data.items():
    events = jornada_data.get("events", [])
    for event in events:
        for team_type in ["homeTeam", "awayTeam"]:
            team = event.get(team_type)
            if not team:
                continue

            team_id = team.get("id")
            team_name = team.get("name", "Unknown Team")

            if not team_id:
                print(f"No hay ID para {team_name}, saltando...")
                continue

            logo_path = os.path.join(logos_folder, f"{team_id}.png")
            # Si ya existe, no volver a descargar
            if os.path.exists(logo_path):
                continue

            logo_url = f"https://img.sofascore.com/api/v1/team/{team_id}/image"
            response = requests.get(logo_url)
            if response.status_code == 200:
                with open(logo_path, "wb") as f_logo:
                    f_logo.write(response.content)
                print(f"Logo descargado: {team_name}")
            else:
                print(f"No se pudo descargar el logo de {team_name} (URL: {logo_url})")