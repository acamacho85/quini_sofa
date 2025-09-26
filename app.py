from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime
from equipos_dict import EQUIPOS

app = Flask(__name__)

def obtener_jornadas():
    conn = sqlite3.connect("liga_mx.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM partidos ORDER BY jornada, start_timestamp")
    partidos_raw = cursor.fetchall()

    jornadas = {}
    for p in partidos_raw:
        partido = {
            "id": p[0],
            "slug": p[1],
            "start_timestamp": p[2],
            "status_code": p[3],
            "status_desc": p[4],
            "equipo_local": p[5],
            "equipo_local_id": p[6],
            "equipo_visitante": p[7],
            "equipo_visitante_id": p[8],
            "goles_local": p[9],
            "goles_visitante": p[10],
            "ganador": p[11],
            "jornada": p[12],
            "fecha_str": datetime.fromtimestamp(p[2]).strftime("%d/%m/%Y"),
            "hora_str": datetime.fromtimestamp(p[2]).strftime("%H:%M")
        }

        jornadas.setdefault(p[12], []).append(partido)

    conn.close()

    # Convertir a lista de objetos jornada
    jornadas_list = [{"numero": j, "partidos": jornadas[j]} for j in sorted(jornadas.keys())]
    return jornadas_list

def detectar_jornada_activa(jornadas):
    now = int(datetime.now().timestamp())
    for jornada in jornadas:
        partidos = jornada["partidos"]
        if any(p["start_timestamp"] > now and p["status_code"] != 100 for p in partidos):
            return str(jornada["numero"])
    return str(jornadas[-1]["numero"])  # última si todas terminaron

@app.route("/")
@app.route("/calendario")
def mostrar_calendario():
    jornadas = obtener_jornadas()
    jornada_activa = detectar_jornada_activa(jornadas)

    return render_template("calendario.html",
                           jornadas=jornadas,
                           jornada_activa=jornada_activa,
                           team_logo_map=EQUIPOS)

@app.route("/usuarios", methods=["GET", "POST"])
def gestion_usuarios():
    conn = sqlite3.connect("liga_mx.db")
    cursor = conn.cursor()

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        if nombre:
            cursor.execute("INSERT OR IGNORE INTO usuarios (nombre) VALUES (?)", (nombre,))
            conn.commit()
            return redirect(url_for("gestion_usuarios"))

    cursor.execute("SELECT id, nombre FROM usuarios ORDER BY nombre")
    usuarios = [{"id": row[0], "nombre": row[1]} for row in cursor.fetchall()]
    conn.close()

    return render_template("usuarios.html", usuarios=usuarios)

@app.route("/pronosticos/<int:jornada>", methods=["GET", "POST"])
def captura_pronosticos_jornada(jornada):
    conn = sqlite3.connect("liga_mx.db")
    cursor = conn.cursor()

    # Obtener usuarios
    cursor.execute("SELECT id, nombre FROM usuarios ORDER BY nombre")
    usuarios = [{"id": row[0], "nombre": row[1]} for row in cursor.fetchall()]

    # Obtener partidos de la jornada
    cursor.execute("""
        SELECT id, equipo_local_nombre, equipo_visitante_nombre
        FROM partidos
        WHERE jornada = ?
        ORDER BY start_timestamp
    """, (jornada,))
    eventos = [{"id": row[0], "homeTeam": {"name": row[1]}, "awayTeam": {"name": row[2]}} for row in cursor.fetchall()]

    if request.method == "POST":
        usuario_id = request.form.get("usuario")
        jornada_form = int(request.form.get("jornada"))

        for event in eventos:
            partido_id = event["id"]
            pronostico_str = request.form.get(f"pronostico_{partido_id}")
            pronostico_map = {"local": 1, "empate": 2, "visitante": 3}
            pronostico = pronostico_map.get(pronostico_str)

            if pronostico:
                cursor.execute("""
                    INSERT OR REPLACE INTO pronosticos (usuario_id, partido_id, pronostico)
                    VALUES (?, ?, ?)
                """, (usuario_id, partido_id, pronostico))

        conn.commit()
        conn.close()
        return redirect(url_for("mostrar_calendario"))

    conn.close()
    return render_template("captura_pronosticos.html",
                           jornada_activa=jornada,
                           usuarios=usuarios,
                           rounds={jornada: eventos},
                           eventos=eventos)

@app.route("/evaluar/<int:jornada>")
def evaluar_pronosticos_jornada(jornada):
    conn = sqlite3.connect("liga_mx.db")
    cursor = conn.cursor()

    # Obtener pronósticos con resultados
    cursor.execute("""
        SELECT u.id, u.nombre, p.jornada, pa.equipo_local_nombre, pa.equipo_visitante_nombre,
               p.pronostico, pa.ganador
        FROM pronosticos p
        JOIN usuarios u ON p.usuario_id = u.id
        JOIN partidos pa ON p.partido_id = pa.id
        WHERE pa.jornada = ? AND pa.ganador IS NOT NULL
        ORDER BY u.nombre, pa.start_timestamp
    """, (jornada,))

    pronosticos = []
    for row in cursor.fetchall():
        pronosticos.append({
            "usuario": {"id": row[0], "nombre": row[1]},
            "jornada": row[2],
            "local": row[3],
            "visitante": row[4],
            "pronostico": row[5],
            "resultado": row[6]
        })

    conn.close()
    return render_template("evaluar_pronosticos.html", pronosticos=pronosticos, jornada_activa=jornada)

# ---------------- MAIN ----------------

if __name__ == "__main__":
    app.run(debug=True)