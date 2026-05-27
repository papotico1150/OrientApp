import os
import flet as ft
import sqlite3
import csv
import random
import string
import json
import re
import urllib.request
import urllib.error

# ── API KEY DE GROQ ────────────────────────────────────────────────────────────
GROQ_API_KEY = "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"

# ── PALETA (imagen adjunta) ────────────────────────────────────────────────────
C_NEGRO       = '#000000'   # negro puro
C_VERDE_OSC   = '#287840'   # verde oscuro institucional
C_VERDE_MED   = '#4da92c'   # verde medio brillante
C_VERDE_CLARO = '#94c121'   # verde limón / amarillo-verde
C_GRIS        = '#b4b3b6'   # gris neutro
C_BLANCO      = '#ffffff'   # blanco puro

# Alias semánticos (mantiene compatibilidad con la lógica anterior)
c_verde         = C_VERDE_OSC
c_blanco        = C_BLANCO
c_negro         = C_NEGRO
c_gris          = C_GRIS
c_azul          = C_VERDE_MED   # reemplazamos azul por verde medio
c_verde_claro   = '#e8f5e9'     # fondo suave para tarjetas (no está en paleta, es derivado)
c_acento        = C_VERDE_CLARO # verde limón para acentos / highlights


# ── UTILIDADES ─────────────────────────────────────────────────────────────────
def generar_contrasena(longitud=8):
    caracteres = string.ascii_letters + string.digits
    return ''.join(random.choice(caracteres) for _ in range(longitud))


def generar_usuario_corto(nombre_completo: str, existente_set: set) -> str:
    partes = nombre_completo.strip().split()
    if len(partes) >= 2:
        base = f"{partes[0].lower()}_{partes[1].lower()}"
    else:
        base = nombre_completo.replace(" ", "_").lower()
    base = "".join(ch for ch in base if ch.isalnum() or ch == "_")
    if base not in existente_set:
        existente_set.add(base)
        return base
    i = 1
    while True:
        candidato = f"{base}{i}"
        if candidato not in existente_set:
            existente_set.add(candidato)
            return candidato
        i += 1


def get_db_connection(db_path: str):
    return sqlite3.connect(db_path)


def buscar_columna_csv(fieldnames: list, keywords: list):
    if not fieldnames:
        return None
    cols_lower = [str(c).lower().strip() for c in fieldnames]
    for kw in keywords:
        kw = kw.lower()
        for i, col in enumerate(cols_lower):
            if kw in col:
                return fieldnames[i]
    return None


# ── BASE DE DATOS ──────────────────────────────────────────────────────────────
def inicializar_db_y_cargar_excel(db_path: str, csv_path: str, usuarios_txt_path: str):
    conn = None
    try:
        conn = get_db_connection(db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        usuario TEXT UNIQUE NOT NULL,
                        contrasena TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS promedios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        usuario TEXT UNIQUE NOT NULL,
                        promedio_mecatronica REAL,
                        promedio_sistemas REAL,
                        promedio_procesos REAL,
                        promedio_diseno REAL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS respuestas_formulario (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        usuario TEXT NOT NULL,
                        respuestas_json TEXT,
                        respuesta_segunda_opcion TEXT)''')
        conn.commit()

        csv_data, fieldnames, col_nombre = [], [], None
        try:
            with open(csv_path, mode='r', encoding='latin-1') as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                if fieldnames:
                    col_nombre = buscar_columna_csv(fieldnames,
                                                    ["estudiante", "estudiantes"])
                    csv_data = list(reader)
        except FileNotFoundError:
            pass

        c.execute("SELECT usuario, contrasena FROM usuarios")
        usuarios_existentes = {row[0]: row[1] for row in c.fetchall()}
        user_set = set(usuarios_existentes.keys())

        usuarios_info_to_insert, promedios_to_upsert, nuevas_lineas_txt = [], [], []

        if not csv_data and not usuarios_existentes:
            nombres   = ["Juan","Carlos","Luis","Elena","Diego","Laura","Pedro","Sofia","Miguel","Lucia"]
            apellidos = ["Rodriguez","Martinez","Hernandez","Lopez","Gonzalez","Sanchez","Ramirez","Torres"]
            csv_data = [{"Estudiante": "Acero Caycedo Yecid"}, {"Estudiante": "Garcia Perez Ana"}]
            for _ in range(28):
                csv_data.append({"Estudiante": f"{random.choice(nombres)} {random.choice(apellidos)} {random.choice(apellidos)}"})
            col_nombre = "Estudiante"

        for row in (csv_data if col_nombre else []):
            nombre = str(row.get(col_nombre, '')).strip()
            if not nombre or nombre.lower() in ["nan", "none"]:
                continue
            usuario = generar_usuario_corto(nombre, user_set)
            if usuario not in usuarios_existentes:
                pwd = generar_contrasena(8)
                usuarios_info_to_insert.append((usuario, pwd))
                nuevas_lineas_txt.append(f"Usuario: {usuario} | Contraseña: {pwd}")
                usuarios_existentes[usuario] = pwd
                if usuario.startswith("acero_caycedo"):
                    vals = (round(random.uniform(3.0,4.0),2), round(random.uniform(4.0,5.0),2),
                            round(random.uniform(3.0,4.0),2), round(random.uniform(3.0,4.0),2))
                elif usuario.startswith("garcia_perez"):
                    vals = (round(random.uniform(3.0,4.0),2), round(random.uniform(3.0,4.0),2),
                            round(random.uniform(3.0,4.0),2), round(random.uniform(4.0,5.0),2))
                else:
                    vals = tuple(round(random.uniform(3.0,5.0),2) for _ in range(4))
                promedios_to_upsert.append((usuario, *vals))

        if usuarios_info_to_insert:
            c.executemany("INSERT OR IGNORE INTO usuarios (usuario, contrasena) VALUES (?,?)",
                          usuarios_info_to_insert)
            conn.commit()
        for tupla in promedios_to_upsert:
            try:
                c.execute("INSERT OR IGNORE INTO promedios "
                          "(usuario,promedio_mecatronica,promedio_sistemas,promedio_procesos,promedio_diseno) "
                          "VALUES (?,?,?,?,?)", tupla)
            except Exception:
                pass
        conn.commit()

        if nuevas_lineas_txt:
            mode = "a" if os.path.exists(usuarios_txt_path) else "w"
            try:
                with open(usuarios_txt_path, mode, encoding="utf-8") as f:
                    if mode == "w": f.write("Usuarios generados:\n")
                    for linea in nuevas_lineas_txt: f.write(linea + "\n")
            except Exception:
                pass
    except Exception:
        pass
    finally:
        if conn: conn.close()


def verificar_usuario(usuario, contrasena, db_path):
    conn = get_db_connection(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios WHERE usuario=? AND contrasena=?", (usuario, contrasena))
    result = c.fetchone()
    conn.close()
    return result


def obtener_promedios(usuario, db_path):
    conn = get_db_connection(db_path)
    c = conn.cursor()
    c.execute("SELECT promedio_mecatronica,promedio_sistemas,promedio_procesos,promedio_diseno "
              "FROM promedios WHERE usuario=?", (usuario,))
    result = c.fetchone()
    conn.close()
    if result:
        return tuple((v if v is not None else 0.0) for v in result)
    return None


def obtener_respuestas_usuario(usuario, db_path):
    conn = get_db_connection(db_path)
    c = conn.cursor()
    c.execute("SELECT respuestas_json, respuesta_segunda_opcion "
              "FROM respuestas_formulario WHERE usuario=? ORDER BY id DESC LIMIT 1", (usuario,))
    row = c.fetchone()
    conn.close()
    return row


def guardar_respuestas_formulario(usuario, respuestas_dict, segunda_opcion, db_path):
    conn = get_db_connection(db_path)
    c = conn.cursor()
    c.execute("INSERT INTO respuestas_formulario (usuario, respuestas_json, respuesta_segunda_opcion) "
              "VALUES (?,?,?)", (usuario, json.dumps(respuestas_dict), segunda_opcion))
    conn.commit()
    conn.close()


def registrar_usuario_manual(usuario, contrasena, db_path):
    conn = get_db_connection(db_path)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO usuarios (usuario, contrasena) VALUES (?,?)", (usuario, contrasena))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


# ── IA VÍA urllib (sin dependencia de groq) ───────────────────────────────────
def evaluar_con_ia(respuestas_texto: str) -> dict:
    """Llama a la API de Groq usando solo urllib (incluido en Python base)."""
    if not GROQ_API_KEY.startswith("gsk_"):
        raise ValueError("API key de Groq inválida. Debe empezar con 'gsk_'.")

    prompt = f"""
Eres un orientador vocacional experto en un instituto técnico colombiano.
Un estudiante respondió 5 preguntas sobre sus intereses y personalidad.
Tu tarea es analizar esas respuestas y asignar un puntaje de afinidad del 0 al 100 para cada una de las 4 especialidades técnicas.

Los puntajes deben sumar exactamente 200 en total (cada uno entre 0 y 100).

ESPECIALIDADES Y SEÑALES CLAVE:
- "Mecatronica": le gusta armar, reparar, electrónica, robots, circuitos, hardware, física aplicada, talleres.
- "Sistemas": le atrae programar, computadoras, videojuegos, apps, internet, lógica, software, redes.
- "Procesos": prefiere organizar, liderar, planificar, eficiencia, logística, administración, control de calidad, trabajo en equipo estructurado.
- "Diseño": disfruta dibujar, modelar en 3D, estética, creatividad visual, arte, AutoCAD, productos bonitos y funcionales.

RESPUESTAS DEL ESTUDIANTE:
{respuestas_texto}

INSTRUCCIÓN FINAL:
Devuelve ÚNICAMENTE este JSON válido, sin explicaciones ni texto extra:
{{"Mecatronica": 0, "Sistemas": 0, "Procesos": 0, "Diseño": 0}}
"""

    payload = json.dumps({
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "max_tokens": 200
    }).encode("utf-8")

    req = urllib.request.Request(
        url="https://api.groq.com/openai/v1/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "es-ES,es;q=0.9",
            "Connection": "keep-alive"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        texto = body["choices"][0]["message"]["content"].strip()
        match = re.search(r'\{.*\}', texto, re.DOTALL)
        if match:
            texto = match.group(0)
        return json.loads(texto)
    except urllib.error.HTTPError as e:
        detalle = e.read().decode("utf-8")
        raise ValueError(f"HTTP {e.code}: {detalle}")
    except Exception as e:
        raise ValueError(f"Error conectando con Groq: {e}")


# ── INTERFAZ FLET ──────────────────────────────────────────────────────────────
def main(page: ft.Page):
    page.title = "Proyecto Especialidades"
    page.horizontal_alignment = "center"
    page.vertical_alignment = "center"
    page.bgcolor = C_BLANCO

    # ── Rutas de archivos ──────────────────────────────────────────────────────
    base_dir = os.path.abspath(os.path.dirname(__file__))

    if page.platform in ("android", "ios"):
        csv_asset_path = "Notas procesadas.csv"
        app_support_dir = ""
        try:
            app_support_dir = page.get_app_support_dir()
        except Exception:
            app_support_dir = os.path.join(base_dir, "data")
            os.makedirs(app_support_dir, exist_ok=True)
        db_path_val   = os.path.join(app_support_dir, "usuarios.db")
        txt_path_val  = os.path.join(app_support_dir, "usuarios_generados.txt")
    else:
        project_root   = os.path.dirname(base_dir)
        assets_dir     = os.path.join(project_root, "assets")
        csv_asset_path = os.path.join(assets_dir, "Notas procesadas.csv")
        db_path_val    = os.path.join(base_dir, "usuarios.db")
        txt_path_val   = os.path.join(base_dir, "usuarios_generados.txt")

    inicializar_db_y_cargar_excel(db_path_val, csv_asset_path, txt_path_val)
    page.session.set("db_path", db_path_val)
    page.session.set("usuarios_txt_path", txt_path_val)

    # ── Widgets de login ───────────────────────────────────────────────────────
    correo_entry = ft.TextField(
        label="Usuario", width=300, height=45,
        border_radius=12, border_color=C_VERDE_OSC,
        bgcolor=C_BLANCO, text_size=13, color=C_NEGRO,
        label_style=ft.TextStyle(color=C_VERDE_OSC))
    contrasena_entry = ft.TextField(
        label="Contraseña", password=True, can_reveal_password=True,
        width=300, height=45, border_radius=12,
        border_color=C_VERDE_OSC, bgcolor=C_BLANCO,
        text_size=13, color=C_NEGRO,
        label_style=ft.TextStyle(color=C_VERDE_OSC))

    def iniciar_sesion(e):
        usuario  = correo_entry.value
        pwd      = contrasena_entry.value
        db_path  = page.session.get("db_path")
        if not db_path:
            _snack("Base de datos no lista.", "red")
            return
        if verificar_usuario(usuario, pwd, db_path):
            _snack("Inicio de sesión correcto", C_VERDE_OSC)
            page.session.set("current_user", usuario)
            promedios = obtener_promedios(usuario, db_path)
            if promedios and any(p > 0 for p in promedios):
                page.go("/promedios")
            else:
                page.go("/notas")
        else:
            _snack("Usuario o contraseña incorrectos", "red")

    def _snack(msg, color):
        page.snack_bar = ft.SnackBar(ft.Text(msg, color=C_BLANCO), bgcolor=color)
        page.snack_bar.open = True
        page.update()

    # ── Helpers de estilo ──────────────────────────────────────────────────────
    def _btn_primario(text, on_click, width=220):
        return ft.ElevatedButton(
            text=text, bgcolor=C_VERDE_OSC, color=C_BLANCO,
            on_click=on_click, width=width,
            style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)))

    def _btn_secundario(text, on_click, width=180):
        return ft.OutlinedButton(
            text=text, on_click=on_click, width=width,
            style=ft.ButtonStyle(
                color=C_VERDE_OSC,
                side=ft.BorderSide(color=C_VERDE_OSC, width=1.5),
                shape=ft.RoundedRectangleBorder(radius=10)))

    def _card(content, padding=25, margin=15):
        return ft.Container(
            content=content,
            padding=padding,
            margin=ft.margin.all(margin),
            border_radius=ft.border_radius.all(18),
            bgcolor=C_BLANCO,
            shadow=ft.BoxShadow(color="#22000000", blur_radius=18, offset=ft.Offset(0, 4)))

    # ══════════════════════════════════════════════════════════════════════════
    def route_change(route):
        page.views.clear()
        db_path      = page.session.get("db_path")
        txt_path     = page.session.get("usuarios_txt_path")

        if not db_path:
            page.views.append(ft.View("/", [ft.ProgressRing()]))
            page.update()
            return

        # ── LOGIN ─────────────────────────────────────────────────────────────
        login_card = _card(
            ft.Column([
                ft.Image(src="instituto.png", width=100, height=100, fit=ft.ImageFit.CONTAIN),
                ft.Container(
                    content=ft.Text("BIENVENIDO", size=20, weight="bold",
                                    color=C_VERDE_OSC),
                    padding=ft.padding.only(bottom=2)),
                ft.Text("Ingresa tus credenciales", size=11, color=C_GRIS),
                ft.Divider(color=C_VERDE_CLARO, thickness=2, height=18),
                correo_entry,
                contrasena_entry,
                ft.Container(height=4),
                _btn_primario("Iniciar Sesión", iniciar_sesion, 240),
                ft.Row([
                    ft.Text("¿No tienes cuenta?", size=11, color=C_GRIS),
                    ft.TextButton("Registrar", on_click=lambda _: page.go("/registro"),
                                  style=ft.ButtonStyle(color=C_VERDE_MED))
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=4)
            ], alignment=ft.MainAxisAlignment.CENTER,
               horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
            padding=35)

        page.views.append(ft.View(
            "/",
            [ft.Container(
                content=ft.Column([login_card],
                                   alignment=ft.MainAxisAlignment.CENTER,
                                   horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                   scroll="auto", expand=True),
                expand=True, alignment=ft.alignment.center)],
            bgcolor=C_BLANCO))

        # ── REGISTRO ──────────────────────────────────────────────────────────
        if page.route == "/registro":
            u_reg = ft.TextField(label="Usuario", width=300, height=45, border_radius=10,
                                 bgcolor=C_BLANCO, border_color=C_VERDE_OSC, color=C_NEGRO,
                                 label_style=ft.TextStyle(color=C_VERDE_OSC))
            p_reg = ft.TextField(label="Contraseña", password=True, can_reveal_password=True,
                                 width=300, height=45, border_radius=10,
                                 bgcolor=C_BLANCO, border_color=C_VERDE_OSC, color=C_NEGRO,
                                 label_style=ft.TextStyle(color=C_VERDE_OSC))

            def on_registrar(e):
                user = u_reg.value.strip(); pwd = p_reg.value.strip()
                if not user or not pwd:
                    _snack("Usuario y contraseña no pueden estar vacíos.", "orange")
                    return
                ok = registrar_usuario_manual(user, pwd, db_path)
                if ok:
                    _snack("Usuario registrado correctamente", C_VERDE_OSC)
                    try:
                        with open(txt_path, "a", encoding="utf-8") as f:
                            f.write(f"Usuario: {user} | Contraseña: {pwd}\n")
                    except Exception:
                        pass
                    page.go("/")
                else:
                    _snack("El usuario ya existe o hubo un error.", "red")

            page.views.append(ft.View("/registro", [
                ft.AppBar(title=ft.Text("Registrar Usuario", color=C_BLANCO),
                          bgcolor=C_VERDE_OSC),
                _card(ft.Column([
                    ft.Text("Crear cuenta", size=18, weight="bold", color=C_NEGRO),
                    ft.Divider(color=C_VERDE_CLARO, thickness=2),
                    u_reg, p_reg,
                    _btn_primario("Registrar", on_registrar, 240),
                    _btn_secundario("Volver", lambda _: page.go("/"))
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                   alignment=ft.MainAxisAlignment.CENTER, spacing=12))
            ], bgcolor=C_BLANCO, horizontal_alignment="center", vertical_alignment="center"))

        # ── NOTAS ─────────────────────────────────────────────────────────────
        if page.route.startswith("/notas"):
            usuario = page.session.get("current_user")
            if not usuario: return page.go("/")

            especialidades = ['Mecatronica', 'Sistemas', 'Procesos Industriales', 'Diseño']
            entradas_notas = {}
            notas_controls = []

            for esp in especialidades:
                entries = [
                    ft.TextField(label=f"P{i+1}", width=62, height=42, border_radius=8,
                                 text_align=ft.TextAlign.CENTER,
                                 input_filter=ft.InputFilter(allow=True, regex_string=r"[0-9.]"),
                                 color=C_NEGRO, border_color=C_VERDE_OSC)
                    for i in range(4)
                ]
                entradas_notas[esp] = entries
                notas_controls.append(ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Container(width=4, height=20, bgcolor=c_acento,
                                         border_radius=2),
                            ft.Text(f" {esp}", size=13, weight="bold", color=C_NEGRO)
                        ]),
                        ft.Row(entries, alignment=ft.MainAxisAlignment.CENTER, spacing=6)
                    ], spacing=6),
                    padding=ft.padding.symmetric(vertical=10, horizontal=12),
                    margin=ft.margin.symmetric(vertical=5),
                    border_radius=12, bgcolor="#f5faf5"))

            def calcular_promedio(e):
                try:
                    proms = {}
                    campos_error = []
                    for esp, entries in entradas_notas.items():
                        notas_validas = []
                        for idx, entry in enumerate(entries):
                            val_str = (entry.value or "").strip().replace(',', '.')
                            if not val_str:
                                entry.border_color = "red"
                                campos_error.append(f"P{idx+1} de {esp}")
                                continue
                            try:
                                nota = float(val_str)
                            except ValueError:
                                entry.border_color = "red"
                                campos_error.append(f"P{idx+1} de {esp}")
                                continue
                            if not (3.0 <= nota <= 5.0):
                                entry.border_color = "red"
                                campos_error.append(f"P{idx+1} de {esp} (rango 3.0-5.0)")
                                continue
                            entry.border_color = C_VERDE_OSC
                            notas_validas.append(nota)
                        if len(notas_validas) != 4:
                            page.update()
                            _snack(f"⚠️ Verifica las notas de {esp}.", "orange")
                            return
                        proms[esp] = sum(notas_validas) / 4

                    conn = get_db_connection(db_path)
                    cur  = conn.cursor()
                    # INSERT OR REPLACE funciona para usuarios nuevos Y existentes
                    cur.execute("DELETE FROM promedios WHERE usuario=?", (usuario,))
                    cur.execute("""INSERT INTO promedios
                                   (usuario,promedio_mecatronica,promedio_sistemas,promedio_procesos,promedio_diseno)
                                   VALUES (?,?,?,?,?)""",
                                (usuario, proms['Mecatronica'], proms['Sistemas'],
                                 proms['Procesos Industriales'], proms['Diseño']))
                    conn.commit()
                    conn.close()
                    mejor = max(proms, key=proms.get)
                    _snack(f"✅ Guardado correctamente. Mejor: {mejor} ({proms[mejor]:.2f})", C_VERDE_OSC)
                    page.go("/promedios")
                except Exception as ex:
                    _snack(f"Error: {ex}", "red")

            page.views.append(ft.View("/notas", [
                ft.AppBar(title=ft.Text("Mis Notas", color=C_BLANCO), bgcolor=C_VERDE_OSC),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Ingresa tus notas (escala 3.0 – 5.0)", size=14,
                                weight="bold", color=C_NEGRO, text_align=ft.TextAlign.CENTER),
                        ft.Divider(color=C_VERDE_CLARO, thickness=2),
                        *notas_controls,
                        ft.Divider(color=C_VERDE_CLARO),
                        _btn_primario("Calcular y Guardar", calcular_promedio, 260),
                        _btn_secundario("Volver", lambda _: page.go("/"))
                    ], alignment=ft.MainAxisAlignment.START,
                       horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                       scroll="auto", expand=True, spacing=12),
                    padding=20, expand=True)
            ], bgcolor=C_BLANCO))

        # ── PROMEDIOS ─────────────────────────────────────────────────────────
        if page.route == "/promedios":
            usuario = page.session.get("current_user")
            if not usuario: return page.go("/")
            promedios = obtener_promedios(usuario, db_path)
            if promedios is None: return page.go("/notas")

            labels  = ["⚙️ Mecatrónica", "💻 Sistemas", "🏭 Procesos", "🎨 Diseño"]
            ranking = sorted(enumerate(promedios), key=lambda x: x[1], reverse=True)
            mejor_i, mejor_p = ranking[0]
            mejor_label = labels[mejor_i]

            barras = []
            for i, p in ranking:
                es_mejor = (i == mejor_i)
                barras.append(ft.Column([
                    ft.Row([
                        ft.Text(labels[i], size=13, weight="bold" if es_mejor else "normal",
                                color=C_NEGRO, expand=True),
                        ft.Text(f"{p:.2f}", size=13, weight="bold" if es_mejor else "normal",
                                color=C_VERDE_OSC if es_mejor else C_GRIS)
                    ]),
                    ft.ProgressBar(
                        value=(p - 3.0) / 2.0 if p >= 3 else 0,
                        color=C_VERDE_OSC if es_mejor else C_VERDE_MED,
                        bgcolor="#e0e0e0", height=10)
                ], spacing=4))

            card_content = ft.Column([
                ft.Text("📊 Tus Promedios", size=17, weight="bold", color=C_NEGRO),
                ft.Divider(color=C_VERDE_CLARO, thickness=2),
                *barras,
                ft.Divider(color=C_VERDE_CLARO, height=20),
                ft.Container(
                    content=ft.Column([
                        ft.Text("🏆 Mejor Especialidad", size=13, color=C_GRIS),
                        ft.Text(mejor_label, size=22, weight="bold", color=C_VERDE_OSC),
                        ft.Text(f"Promedio: {mejor_p:.2f}", size=14, color=C_NEGRO),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=4),
                    padding=16, border_radius=14,
                    bgcolor="#f0faf0",
                    border=ft.border.all(2, C_VERDE_CLARO)),
                ft.Container(height=10),
                ft.Column([
                    _btn_primario("Test Vocacional IA 🤖", lambda _: page.go("/formulario"), 300),
                    _btn_secundario("Volver al inicio", lambda _: page.go("/"), 300),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8)
            ], spacing=10)

            page.views.append(ft.View("/promedios", [
                ft.AppBar(title=ft.Text(f"Resultados – {usuario}", color=C_BLANCO),
                          bgcolor=C_VERDE_OSC),
                ft.Container(
                    content=ft.Column([_card(card_content)],
                                       alignment=ft.MainAxisAlignment.CENTER,
                                       horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                       scroll="auto", expand=True),
                    expand=True, alignment=ft.alignment.center)
            ], bgcolor=C_BLANCO))

        # ── FORMULARIO IA ──────────────────────────────────────────────────────
        if page.route == "/formulario":
            usuario = page.session.get("current_user")
            if not usuario: return page.go("/")

            preguntas = {
                "q1": {
                    "label": "1. ¿Cuál de estas actividades disfrutarías más en tu trabajo?\n"
                             "⚙️ Armar o reparar máquinas y circuitos\n"
                             "💻 Programar software o aplicaciones\n"
                             "🏭 Organizar y mejorar procesos en una empresa\n"
                             "🎨 Diseñar productos o piezas en computador\n\n"
                             "Explica cuál elegirías y por qué:",
                    "ctrl": ft.TextField(multiline=True, min_lines=2, max_lines=4,
                                         border_color=C_VERDE_OSC, color=C_NEGRO,
                                         hint_text="Ej: Elegiría programar porque me gusta crear cosas con código...")
                },
                "q2": {
                    "label": "2. Imagina que tienes un proyecto libre en el instituto.\n"
                             "¿Qué harías?\n\n"
                             "Ej: Construir un brazo robótico / Crear una app / Diseñar un producto en 3D / Mejorar la organización de un taller",
                    "ctrl": ft.TextField(multiline=True, min_lines=2, max_lines=4,
                                         border_color=C_VERDE_OSC, color=C_NEGRO,
                                         hint_text="Ej: Haría una aplicación móvil que controle...")
                },
                "q3": {
                    "label": "3. ¿Qué materias o temas del colegio/instituto te han gustado más?\n\n"
                             "Ej: Matemáticas, física, informática, dibujo técnico, administración, química, arte...",
                    "ctrl": ft.TextField(multiline=True, min_lines=2, max_lines=4,
                                         border_color=C_VERDE_OSC, color=C_NEGRO,
                                         hint_text="Ej: Me gustó mucho informática y también dibujo técnico porque...")
                },
                "q4": {
                    "label": "4. ¿Cómo te describirías a ti mismo al trabajar en equipo?\n\n"
                             "Ej: Soy el que arregla los equipos / El que programa / El que organiza al grupo / El que propone ideas creativas",
                    "ctrl": ft.TextField(multiline=True, min_lines=2, max_lines=4,
                                         border_color=C_VERDE_OSC, color=C_NEGRO,
                                         hint_text="Ej: Normalmente soy el que organiza las tareas y controla los tiempos...")
                },
                "q5": {
                    "label": "5. ¿Qué te gustaría que la gente dijera de tu trabajo cuando seas profesional?\n\n"
                             "Ej: \'Él construyó ese robot\' / \'Ella programó esa app\' / \'Gracias a él la empresa funciona mejor\' / \'Diseñó ese producto\'",
                    "ctrl": ft.TextField(multiline=True, min_lines=2, max_lines=4,
                                         border_color=C_VERDE_OSC, color=C_NEGRO,
                                         hint_text="Ej: Me gustaría que dijeran que mis diseños son funcionales y bonitos...")
                },
            }

            opcion_secundaria = ft.Dropdown(
                options=[ft.dropdown.Option(key=o, text=o)
                         for o in ["Mecatronica", "Sistemas", "Diseño", "Procesos"]],
                width=300, border_radius=8, border_color=C_VERDE_OSC,
                hint_text="Elige tu 2ª opción de especialidad",
                color=C_NEGRO)

            loading_ring  = ft.ProgressRing(visible=False, color=C_VERDE_MED)
            texto_carga   = ft.Text("La IA está evaluando tus respuestas...",
                                    visible=False, color=C_VERDE_MED, italic=True)

            def enviar_respuestas(e):
                import threading

                # Validar campo por campo y resaltar el que falta
                for key, item in preguntas.items():
                    val = (item["ctrl"].value or "").strip()
                    if len(val) < 10:
                        # Resaltar el campo en rojo
                        item["ctrl"].border_color = "red"
                        item["ctrl"].helper_text = "⚠️ Este campo es obligatorio (mínimo 10 caracteres)"
                        item["ctrl"].helper_style = ft.TextStyle(color="red")
                        page.update()
                        _snack(f"⚠️ Completa la pregunta {key.upper()} antes de continuar.", "orange")
                        return
                    else:
                        # Restaurar borde verde si ya está bien
                        item["ctrl"].border_color = C_VERDE_OSC
                        item["ctrl"].helper_text = ""

                if not opcion_secundaria.value:
                    _snack("⚠️ Selecciona tu 2ª opción de especialidad.", "orange")
                    return

                # Limpiar bordes rojos antes de enviar
                for item in preguntas.values():
                    item["ctrl"].border_color = C_VERDE_OSC
                    item["ctrl"].helper_text = ""

                texto_respuestas = ""
                for key, item in preguntas.items():
                    val = (item["ctrl"].value or "").strip()
                    texto_respuestas += f"Respuesta {key}: {val}\n"

                boton_analizar = e.control
                loading_ring.visible = True
                texto_carga.visible  = True
                boton_analizar.disabled = True
                page.update()

                def tarea_ia():
                    try:
                        print(">>> Llamando a Groq via urllib...")
                        puntajes = evaluar_con_ia(texto_respuestas)
                        print(f">>> Respuesta recibida: {puntajes}")
                        guardar_respuestas_formulario(usuario, puntajes, opcion_secundaria.value, db_path)
                        _snack("¡Evaluación completada!", C_VERDE_OSC)
                        page.go("/resultados")
                    except Exception as ex:
                        print(f">>> ERROR en IA: {ex}")
                        _snack(f"Error IA: {ex}", "red")
                    finally:
                        loading_ring.visible    = False
                        texto_carga.visible     = False
                        boton_analizar.disabled = False
                        page.update()

                threading.Thread(target=tarea_ia, daemon=True).start()

            pregs_ui = [
                ft.Container(
                    content=ft.Column([
                        ft.Text(item["label"], size=13, weight="w500", color=C_NEGRO),
                        item["ctrl"]
                    ], spacing=6),
                    padding=ft.padding.symmetric(vertical=10, horizontal=14),
                    margin=ft.margin.symmetric(vertical=5),
                    border_radius=12, bgcolor="#f0faf0",
                    border=ft.border.all(1, C_VERDE_CLARO))
                for item in preguntas.values()
            ]

            form_col = ft.Column([
                ft.Text("Test Vocacional con IA 🤖", size=17, weight="bold", color=C_NEGRO),
                ft.Text("Responde con sinceridad. LLaMA 3 analizará tu perfil.", size=11, color=C_GRIS),
                ft.Divider(color=C_VERDE_CLARO, thickness=2),
                *pregs_ui,
                ft.Divider(color=C_VERDE_CLARO),
                ft.Text("Si pudieras elegir directamente, ¿cuál sería tu 2ª opción?",
                        size=13, weight="w500", color=C_NEGRO),
                opcion_secundaria,
                ft.Column([loading_ring, texto_carga],
                           horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                _btn_primario("🧠 Analizar con IA", enviar_respuestas, 250)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10)

            page.views.append(ft.View("/formulario", [
                ft.AppBar(title=ft.Text(f"Test Vocacional – {usuario}", color=C_BLANCO),
                          bgcolor=C_VERDE_OSC),
                ft.Container(
                    content=ft.Column([form_col], scroll="auto",
                                       horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                       expand=True),
                    padding=ft.padding.symmetric(horizontal=20, vertical=15), expand=True)
            ], bgcolor=C_BLANCO))

        # ── RESULTADOS IA (Vista gamificada) ──────────────────────────────────
        if page.route == "/resultados":
            usuario = page.session.get("current_user")
            if not usuario: return page.go("/")

            datos = obtener_respuestas_usuario(usuario, db_path)
            if not datos: return page.go("/formulario")

            respuestas_json, segunda_opcion = datos
            try:
                puntuaciones = json.loads(respuestas_json)
            except json.JSONDecodeError:
                _snack("Error al procesar resultados.", "red")
                return page.go("/formulario")

            ranking = sorted(puntuaciones.items(), key=lambda x: x[1], reverse=True)
            mejor_esp, mejor_pct = ranking[0]

            # ── Info completa por especialidad ─────────────────────────────────
            INFO_ESP = {
                "Mecatronica": {
                    "icono": "⚙️",
                    "titulo": "Tecnología en Mecatrónica",
                    "nivel": "Ingeniero de Sistemas Físicos",
                    "badge": "🔩 Constructor de Máquinas",
                    "descripcion": (
                        "Eres de los que disfrutan entender cómo funcionan las cosas por dentro. "
                        "La Mecatrónica combina electrónica, mecánica y programación para crear "
                        "máquinas inteligentes. Aquí diseñarás robots, sistemas automáticos y "
                        "equipos industriales que resuelven problemas del mundo real."
                    ),
                    "habilidades": ["🤖 Robótica", "⚡ Electrónica", "🔧 Mecánica", "💡 Automatización"],
                    "salida": "Técnico en Mecatrónica con salida a industria, manufactura y mantenimiento de equipos.",
                    "color_badge": "#FF6B35",
                    "color_bg": "#FFF3EE",
                },
                "Sistemas": {
                    "icono": "💻",
                    "titulo": "Tecnología en Sistemas",
                    "nivel": "Desarrollador de Software",
                    "badge": "🖥️ Arquitecto Digital",
                    "descripcion": (
                        "Tu mente piensa en lógica y algoritmos. Sistemas es para quienes "
                        "quieren crear el futuro digital: apps, páginas web, bases de datos "
                        "y soluciones de software. Si alguna vez pensaste 'yo podría hacer eso mejor', "
                        "esta es tu especialidad."
                    ),
                    "habilidades": ["📱 Desarrollo de Apps", "🌐 Redes", "🗄️ Bases de Datos", "🔐 Ciberseguridad"],
                    "salida": "Técnico en Sistemas con salida a desarrollo web, soporte TI y programación.",
                    "color_badge": "#1565C0",
                    "color_bg": "#E8F0FE",
                },
                "Procesos": {
                    "icono": "🏭",
                    "titulo": "Gestión de Procesos Industriales",
                    "nivel": "Líder de Operaciones",
                    "badge": "📋 Maestro de la Eficiencia",
                    "descripcion": (
                        "Eres el tipo de persona que ve un sistema y sabe cómo mejorarlo. "
                        "Procesos Industriales te forma para optimizar, liderar y controlar "
                        "la producción en empresas. Si te gusta organizar, planear y que todo "
                        "funcione como un reloj, aquí encontrarás tu lugar."
                    ),
                    "habilidades": ["📊 Control de Calidad", "🏗️ Logística", "👥 Liderazgo", "📈 Optimización"],
                    "salida": "Técnico en Procesos con salida a manufactura, logística y gestión empresarial.",
                    "color_badge": "#2E7D32",
                    "color_bg": "#F1F8E9",
                },
                "Diseño": {
                    "icono": "🎨",
                    "titulo": "Tecnología en Diseño",
                    "nivel": "Creador Visual",
                    "badge": "✏️ Artista Técnico",
                    "descripcion": (
                        "Tu cerebro mezcla creatividad con precisión técnica. El Diseño te "
                        "enseña a convertir ideas en productos reales: modelado 3D, planos "
                        "técnicos, renders y prototipos. Si sueñas con crear objetos que la "
                        "gente use y admire, esta es tu especialidad."
                    ),
                    "habilidades": ["🖊️ Dibujo Técnico", "🧊 Modelado 3D", "🎯 AutoCAD", "🌈 Diseño de Producto"],
                    "salida": "Técnico en Diseño con salida a industria gráfica, arquitectura y manufactura.",
                    "color_badge": "#6A1B9A",
                    "color_bg": "#F3E5F5",
                },
            }

            info = INFO_ESP.get(mejor_esp, INFO_ESP["Sistemas"])
            iconos = {k: v["icono"] for k, v in INFO_ESP.items()}

            # ── Tarjeta hero del ganador ───────────────────────────────────────
            winner_card = ft.Container(
                content=ft.Column([
                    ft.Text("✨ Tu Especialidad Recomendada", size=12,
                            color=C_BLANCO, weight="w400",
                            text_align=ft.TextAlign.CENTER),
                    ft.Text(f"{info['icono']}  {mejor_esp}",
                            size=30, weight="bold", color=C_BLANCO,
                            text_align=ft.TextAlign.CENTER),
                    ft.Container(
                        content=ft.Text(f"{mejor_pct}% de afinidad",
                                        size=14, color=C_VERDE_CLARO, weight="bold"),
                        padding=ft.padding.symmetric(horizontal=18, vertical=5),
                        border_radius=20, bgcolor="#00000033"),
                    ft.Container(
                        content=ft.Text(info["badge"], size=12, color="#FFD700",
                                        weight="bold"),
                        padding=ft.padding.symmetric(horizontal=14, vertical=4),
                        border_radius=15, bgcolor="#00000044"),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=ft.padding.symmetric(vertical=28, horizontal=20),
                border_radius=20,
                gradient=ft.LinearGradient(
                    begin=ft.alignment.top_left,
                    end=ft.alignment.bottom_right,
                    colors=[C_VERDE_OSC, C_VERDE_MED]))

            # ── Tarjeta de descripción ─────────────────────────────────────────
            desc_card = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Container(
                            content=ft.Text(info["icono"], size=30),
                            padding=10, border_radius=12,
                            bgcolor=info["color_bg"]),
                        ft.Column([
                            ft.Text(info["titulo"], size=14, weight="bold", color=C_NEGRO),
                            ft.Text(info["nivel"], size=11, color=C_GRIS, italic=True),
                        ], spacing=2, expand=True)
                    ], spacing=12),
                    ft.Divider(color=C_VERDE_CLARO, thickness=1),
                    ft.Text("¿De qué trata?", size=12, weight="bold",
                            color=C_VERDE_OSC),
                    ft.Text(info["descripcion"], size=12, color=C_NEGRO),
                    ft.Container(height=4),
                    ft.Text("Habilidades que desarrollarás:", size=12,
                            weight="bold", color=C_VERDE_OSC),
                    ft.Row(
                        [ft.Container(
                            content=ft.Text(h, size=11, color=C_NEGRO),
                            padding=ft.padding.symmetric(horizontal=10, vertical=5),
                            border_radius=20,
                            bgcolor=info["color_bg"],
                            border=ft.border.all(1, C_VERDE_CLARO))
                         for h in info["habilidades"]],
                        wrap=True, spacing=6, run_spacing=6),
                    ft.Container(height=4),
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.Icons.WORK_OUTLINE, size=15, color=C_VERDE_OSC),
                            ft.Text(info["salida"], size=11, color=C_NEGRO,
                                    expand=True, italic=True)
                        ], spacing=8),
                        padding=10, border_radius=10, bgcolor="#f0faf0",
                        border=ft.border.all(1, C_VERDE_CLARO)),
                ], spacing=10),
                padding=18, border_radius=16,
                bgcolor=C_BLANCO,
                border=ft.border.all(2, C_VERDE_CLARO),
                shadow=ft.BoxShadow(color="#11000000", blur_radius=10))

            # ── Barras de ranking ──────────────────────────────────────────────
            barra_items = []
            for i, (esp, pct) in enumerate(ranking):
                es_primero = (i == 0)
                barra_items.append(ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Text(f"{INFO_ESP.get(esp, {}).get('icono','•')} {esp}",
                                    size=13,
                                    weight="bold" if es_primero else "normal",
                                    color=C_NEGRO, expand=True),
                            ft.Text(f"{pct}%", size=13,
                                    weight="bold" if es_primero else "normal",
                                    color=C_VERDE_OSC if es_primero else C_GRIS)
                        ]),
                        ft.ProgressBar(
                            value=pct / 100,
                            color=C_VERDE_OSC if es_primero else C_VERDE_MED,
                            bgcolor="#e8e8e8", height=10)
                    ], spacing=5),
                    padding=ft.padding.symmetric(vertical=10, horizontal=14),
                    margin=ft.margin.symmetric(vertical=4),
                    border_radius=12,
                    bgcolor="#f5faf5" if es_primero else C_BLANCO,
                    border=ft.border.all(2 if es_primero else 1,
                                         C_VERDE_CLARO if es_primero else "#e0e0e0")))

            # ── Badge segunda opción ───────────────────────────────────────────
            badge_segunda = ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.STAR_OUTLINE, color=c_acento, size=16),
                    ft.Text(f"Tu 2ª opción fue: {segunda_opcion}",
                            size=12, color=C_NEGRO, italic=True)
                ], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
                padding=ft.padding.symmetric(vertical=10, horizontal=16),
                border_radius=10, bgcolor="#f9fbe7",
                border=ft.border.all(1, c_acento))

            resultados_col = ft.Column([
                winner_card,
                ft.Container(height=6),
                desc_card,
                ft.Container(height=6),
                ft.Text("Distribución de Afinidad", size=14,
                        weight="bold", color=C_NEGRO),
                ft.Divider(color=C_VERDE_CLARO, thickness=2),
                *barra_items,
                ft.Container(height=4),
                badge_segunda,
                ft.Container(height=14),
                ft.Column([
                    _btn_primario("Finalizar", lambda _: page.go("/"), 300),
                    _btn_secundario("Repetir Test", lambda _: page.go("/formulario"), 300),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8)
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8)

            page.views.append(ft.View("/resultados", [
                ft.AppBar(title=ft.Text(f"Tu Resultado – {usuario}", color=C_BLANCO),
                          bgcolor=C_VERDE_OSC),
                ft.Container(
                    content=ft.Column([_card(resultados_col, padding=18, margin=12)],
                                       alignment=ft.MainAxisAlignment.CENTER,
                                       horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                       scroll="auto", expand=True),
                    expand=True, alignment=ft.alignment.center)
            ], bgcolor=C_BLANCO))

        page.update()

    def view_pop(view):
        page.views.pop()
        top_view = page.views[-1]
        page.go(top_view.route)

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go(page.route)


if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")