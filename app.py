from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime
from diccionarios import EQUIPOS, PRONOSTICO_MAP, PRONOSTICO_MAP_INV

app = Flask(__name__)
app.secret_key = "fbf62a22a2b16933f91bbf7f4204e801"

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
    return render_template("calendario.html",
                           jornadas=jornadas,
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
    eventos = [{"id": row[0], "local": row[1], "visitante": row[2]} for row in cursor.fetchall()]

    # Detectar usuario seleccionado (default vacío)
    usuario_id = None
    usuario_str = request.form.get("usuario") if request.method == "POST" else request.args.get("usuario")
    if usuario_str and usuario_str.isdigit():
        usuario_id = int(usuario_str)

    # Cargar pronósticos existentes
    pronosticos_existentes = {}
    if usuario_id:
        cursor.execute("""
            SELECT partido_id, pronostico
            FROM pronosticos
            WHERE usuario_id = ? AND partido_id IN (
                SELECT id FROM partidos WHERE jornada = ?
            )
        """, (usuario_id, jornada))
        pronosticos_existentes = {row[0]: row[1] for row in cursor.fetchall()}

    # Manejo POST
    if request.method == "POST":
        if not usuario_id:
            flash("⚠️ Debes seleccionar un usuario antes de guardar.", "danger")
            return redirect(url_for("captura_pronosticos_jornada", jornada=jornada))

        jornada_form = int(request.form.get("jornada", jornada))
        incompletos = False
        sobrescribir = False

        for event in eventos:
            partido_id = event["id"]
            pronostico_str = request.form.get(f"pronostico_{partido_id}")
            pronostico = PRONOSTICO_MAP_INV.get(pronostico_str)

            if pronostico is None:
                incompletos = True
            else:
                # Detectamos si ya existía pronóstico previo
                if pronosticos_existentes.get(partido_id) is not None:
                    sobrescribir = True
                cursor.execute("""
                    INSERT OR REPLACE INTO pronosticos (usuario_id, partido_id, pronostico)
                    VALUES (?, ?, ?)
                """, (usuario_id, partido_id, pronostico))

        if incompletos:
            flash("⚠️ Debes capturar pronóstico para todos los partidos.", "warning")
            conn.rollback()
            conn.close()
            return redirect(url_for("captura_pronosticos_jornada", jornada=jornada, usuario=usuario_id))

        conn.commit()
        conn.close()

        # Mensajes condicionales
        if sobrescribir:
            flash("⚠️ Algunos de tus pronósticos anteriores fueron sobrescritos.", "warning")
        else:
            flash("✅ Pronósticos guardados correctamente.", "success")

        return redirect(url_for("captura_pronosticos_jornada", jornada=jornada, usuario=usuario_id))


    conn.close()
    return render_template(
        "captura_pronosticos.html",
        usuarios=usuarios,
        rounds={jornada: eventos},
        eventos=eventos,
        pronosticos_existentes=pronosticos_existentes,
        usuario_seleccionado=usuario_id,
        jornada_activa=jornada,
        team_logo_map=EQUIPOS
    )

@app.route("/evaluar/<int:jornada>")
def evaluar_pronosticos_jornada(jornada):
    conn = sqlite3.connect("liga_mx.db")
    cursor = conn.cursor()

    # Obtener partidos de la jornada (con ganador incluido)
    cursor.execute("""
        SELECT id, equipo_local_nombre, equipo_visitante_nombre, ganador
        FROM partidos
        WHERE jornada = ?
        ORDER BY start_timestamp
    """, (jornada,))
    partidos = [
        {
            "id": row[0],
            "local": row[1],
            "visitante": row[2],
            "resultado": row[3]  # 1=Local, 2=Visitante, 3=Empate, NULL=No jugado
        }
        for row in cursor.fetchall()
    ]

    # Obtener usuarios
    cursor.execute("SELECT id, nombre FROM usuarios ORDER BY nombre")
    usuarios = [{"id": row[0], "nombre": row[1]} for row in cursor.fetchall()]

    # Obtener pronósticos de esta jornada
    cursor.execute("""
        SELECT usuario_id, partido_id, pronostico
        FROM pronosticos
        WHERE partido_id IN (SELECT id FROM partidos WHERE jornada = ?)
    """, (jornada,))
    pronos_raw = cursor.fetchall()

    # Organizar pronósticos por usuario y partido
    pronosticos = {u['id']: {} for u in usuarios}
    for usuario_id, partido_id, pron in pronos_raw:
        pronosticos[usuario_id][partido_id] = pron  # 1=L,2=V,3=E

    # Calcular aciertos directamente con "ganador"
    aciertos = {u['id']: 0 for u in usuarios}
    for u in usuarios:
        for p in partidos:
            prono = pronosticos.get(u['id'], {}).get(p['id'])
            if prono and p["resultado"] and prono == p["resultado"]:
                aciertos[u['id']] += 1

    conn.close()
    return render_template(
        "evaluar_pronosticos_matriz.html",
        jornada=jornada,
        usuarios=usuarios,
        partidos=partidos,
        pronosticos=pronosticos,
        PRONOSTICO_MAP=PRONOSTICO_MAP,
        team_logo_map=EQUIPOS,
        aciertos=aciertos
    )

@app.context_processor
def inject_jornada_activa():
    try:
        jornadas = obtener_jornadas()
        jornada_activa = detectar_jornada_activa(jornadas) if jornadas else None
    except Exception:
        jornada_activa = None
    return dict(jornada_activa=jornada_activa)


# ---------------- MAIN ----------------
if __name__ == "__main__":
    app.run(debug=True)
