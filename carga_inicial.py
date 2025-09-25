import asyncio
from playwright.async_api import async_playwright
import json

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
