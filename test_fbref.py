from ScraperFC import FBref

fbref = FBref()
#liga_mx_matches = fbref.get_team_schedule("tigres-uanl")  # Puedes iterar sobre varios equipos
#fbref.get_valid_seasons('Liga MX')

liga_mx_df = fbref.scrape_matches(year="2025-2026", league="Liga MX")
print(liga_mx_df.head())