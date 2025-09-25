import asyncio
from playwright.async_api import async_playwright
import json

TOURNAMENT_ID = 11621  # Liga MX Apertura
SEASON_ID = 76500
TOTAL_ROUNDS = 20  # Cambia según la cantidad de rondas que quieras scrape

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        all_rounds = {}

        # Interceptar respuestas XHR de Sofascore que contienen "events/round"
        async def handle_response(response):
            url = response.url
            if f"/events/round/" in url:
                try:
                    data = await response.json()
                    round_number = int(url.split("/round/")[-1])
                    all_rounds[round_number] = data
                    print(f"Ronda {round_number} capturada con {len(data.get('events', []))} partidos")
                except Exception as e:
                    print("Error leyendo JSON:", e)

        page.on("response", handle_response)

        # Abrir la página principal del torneo
        await page.goto(f"https://www.sofascore.com/es/torneo/futbol/mexico/liga-mx-apertura/{TOURNAMENT_ID}")

        # Hacer click en cada ronda para que se dispare la request XHR
        for round_number in range(1, TOTAL_ROUNDS + 1):
            round_url = f"https://www.sofascore.com/api/v1/unique-tournament/{TOURNAMENT_ID}/season/{SEASON_ID}/events/round/{round_number}"
            await page.goto(round_url)
            await asyncio.sleep(1)  # Espera que la request se dispare y sea capturada

        await browser.close()

        # Guardar resultados en JSON
        with open("liga_mx_apertura.json", "w", encoding="utf-8") as f:
            json.dump(all_rounds, f, ensure_ascii=False, indent=2)

        print("Datos guardados en liga_mx_apertura.json")

# Ejecutar en Jupyter o script
asyncio.run(main())
