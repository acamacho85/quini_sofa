import json
import asyncio
from playwright.async_api import async_playwright
import sqlite3

JSON_FILE = "liga_mx_apertura_2025.json"
TOURNAMENT_ID = 11621  # Liga MX Apertura
SEASON_ID = 76500
TOTAL_ROUNDS = 20  # Cambia según la cantidad de rondas que quieras scrape

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        all_rounds = {}

        # Función para capturar la respuesta JSON de cada ronda
        async def get_round_json(round_number):
            url = f"https://www.sofascore.com/api/v1/unique-tournament/{TOURNAMENT_ID}/season/{SEASON_ID}/events/round/{round_number}"
            
            # Esperar que la respuesta XHR llegue
            async with page.expect_response(lambda resp: f"/events/round/{round_number}" in resp.url) as resp_info:
                await page.goto(url)
            response = await resp_info.value

            try:
                data = await response.json()
                all_rounds[round_number] = data
                print(f"Ronda {round_number} capturada con {len(data.get('events', []))} partidos")
            except Exception as e:
                print(f"Error leyendo JSON de la ronda {round_number}: {e}")

        # Iterar sobre todas las rondas
        for round_number in range(1, TOTAL_ROUNDS + 1):
            await get_round_json(round_number)

        await browser.close()

        # Guardar resultados en JSON
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(all_rounds, f, ensure_ascii=False, indent=2)

        print(f"Datos guardados en {JSON_FILE}")

# Ejecutar
asyncio.run(main())

conn = sqlite3.connect('liga_mx.db')
cursor = conn.cursor()

cursor.execute('DROP TABLE IF EXISTS partidos')
cursor.execute('DROP TABLE IF EXISTS usuarios')
cursor.execute('DROP TABLE IF EXISTS pronosticos')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS partidos (
        id INTEGER PRIMARY KEY,
        slug TEXT,
        start_timestamp INTEGER,
        status_code INTEGER,
        status_desc TEXT,
        equipo_local_nombre TEXT,
        equipo_local_id INTEGER,
        equipo_visitante_nombre TEXT,
        equipo_visitante_id INTEGER,
        goles_local INTEGER,
        goles_visitante INTEGER,
        ganador INTEGER,
        jornada INTEGER
    )
''')
cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL
    )
''')
cursor.execute('''    
    CREATE TABLE IF NOT EXISTS pronosticos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER,
        partido_id INTEGER,
        pronostico INTEGER CHECK(pronostico IN (1, 2, 3)),
        FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
        FOREIGN KEY(partido_id) REFERENCES partidos(id),
        UNIQUE(usuario_id, partido_id)
    )           
''')

conn.commit()


with open(JSON_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

for jornada_num, jornada_data in data.items():
    events = jornada_data.get('events', [])

    for event in events:
        partido = (
            event['id'],
            event['slug'],
            event['startTimestamp'],
            event['status']['code'],
            event['status']['description'],
            event['homeTeam']['name'],
            event['homeTeam']['id'],
            event['awayTeam']['name'],
            event['awayTeam']['id'],
            event.get('homeScore', {}).get('current', 0),
            event.get('awayScore', {}).get('current', 0),
            event.get('winnerCode', None),
            int(jornada_num)
        )
        cursor.execute("""
            INSERT OR IGNORE INTO partidos VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, partido)

conn.commit()
conn.close()

print(f"Datos cargados a la BD")