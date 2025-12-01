# app.py (versión corregida y mejorada)
from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
import psycopg2
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = "clave_super_secreta"  # cámbiala por una segura en producción

# ----------------------
# Conexión a la base de datos (Postgres) - forzando UTF8
# ----------------------

def conectar_bd():
    DATABASE_URL = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def conectar_bd_lector():
    DATABASE_URL = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# ----------------------
# Decorador login (único y consistente)
# ----------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('usuario_id'):
            flash("Debes iniciar sesión para acceder a esta página.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ----------------------
# Rutas principales
# ----------------------
@app.route('/')
def index():
    return render_template('index.html')

# ----------------------
# Registro
# ----------------------
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        correo = request.form.get('correo', '').strip()
        contrasena = request.form.get('contraseña', '').strip()
        tipo = request.form.get('tipo', '').strip().lower()  # estudiante o empresa

        if not nombre or not correo or not contrasena or not tipo:
            flash("Todos los campos obligatorios", "danger")
            return render_template('registro.html')

        # Leer los campos dinámicos según tipo
        if tipo == 'estudiante':
            carrera = request.form.get('n_carrera', '').strip()
            if not carrera:
                flash("Debes indicar tu carrera", "danger")
                return render_template('registro.html')
        else:
            nombre_empresa = request.form.get('n_empresa', '').strip()
            if not nombre_empresa:
                flash("Debes completar los datos de la empresa", "danger")
                return render_template('registro.html')

        try:
            conn = conectar_bd()
            cursor = conn.cursor()

            # Insertar usuario
            cursor.execute(
                "INSERT INTO usuarios (nombre, correo, contrasena, tipo) VALUES (%s,%s,%s,%s) RETURNING id",
                (nombre, correo, contrasena, tipo)
            )
            usuario_id = cursor.fetchone()[0]

            # Insertar según tipo
            if tipo == 'estudiante':
                cursor.execute(
                    "INSERT INTO estudiantes (usuario_id, carrera) VALUES (%s,%s)",
                    (usuario_id, carrera)
                )
            else:
                cursor.execute(
                    "INSERT INTO empresas (usuario_id, nombre_empresa) VALUES (%s,%s)",
                    (usuario_id, nombre_empresa)
                )

            conn.commit()
            flash("Registro exitoso. Ahora inicia sesión.", "success")
            return redirect(url_for('login'))

        except Exception as e:
            if conn:
                conn.rollback()
            flash(f"Error al registrar usuario: {e}", "danger")
            return render_template('registro.html')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('registro.html')


# ----------------------
# Login
# ----------------------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        correo = request.form.get('correo', '').strip()
        contrasena = request.form.get('contraseña', '').strip()

        if not correo or not contrasena:
            flash("Debes ingresar correo y contraseña", "warning")
            return render_template('login.html')
        conn = None
        cursor = None
        try:
            conn = conectar_bd()
            cursor = conn.cursor()
            cursor.execute("SELECT id, tipo, nombre, correo FROM usuarios WHERE correo=%s AND contrasena=%s", (correo, contrasena))
            usuario = cursor.fetchone()
            if usuario:
                usuario_id, tipo, nombre_db, correo_db = usuario[0], usuario[1], usuario[2], usuario[3]
                # Guardar datos en session para usarlos en el panel lateral / templates
                session['usuario_id'] = usuario_id
                session['tipo'] = tipo
                session['nombre'] = nombre_db
                session['correo'] = correo_db

                # cargar datos extra según tipo (empresa -> nombre_empresa ; estudiante -> carrera)
                if tipo.lower() == 'empresa':
                    # intentar obtener nombre_empresa
                    cursor.execute("SELECT nombre_empresa FROM empresas WHERE usuario_id=%s", (usuario_id,))
                    row = cursor.fetchone()
                    session['empresa'] = row[0] if row and row[0] else ''
                    flash("Bienvenido a OportuniLink (Empresa)", "success")
                    return redirect(url_for('inicio_empresa'))
                else:
                    cursor.execute("SELECT carrera FROM estudiantes WHERE usuario_id=%s", (usuario_id,))
                    row = cursor.fetchone()
                    session['carrera'] = row[0] if row and row[0] else ''
                    flash("Bienvenido a OportuniLink (Estudiante)", "success")
                    return redirect(url_for('inicio_estudiante'))
            else:
                flash("Usuario o contraseña incorrecta", "danger")
                return render_template('login.html')
        except Exception as e:
            flash(f"Error al iniciar sesión: {e}", "danger")
            return render_template('login.html')
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    return render_template('login.html')

# ----------------------
# Logout
# ----------------------
@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash("Has cerrado sesión.", "info")
    return redirect(url_for('index'))

# ----------------------
# INICIO - Estudiante (feed)
# ----------------------
# inicio_estudiante

@app.route('/inicio_estudiante')
def inicio_estudiante():
    if 'usuario_id' not in session or session.get('tipo') != 'estudiante':
        # Redirigir si no está logueado o no es estudiante
        return redirect(url_for('login'))

    # Obtener parámetro de búsqueda y filtro
    q = request.args.get('q', '').lower()
    filtro = request.args.get('filtro', '').lower()

    publicaciones = []

    conn = conectar_bd_lector()
    cursor = conn.cursor()

    # 1️⃣ Obtener ofertas
    if filtro in ('', 'ofertas'):
        cursor.execute("""
            SELECT o.titulo, o.descripcion, o.fecha_creacion, e.nombre_empresa
            FROM ofertas o
            JOIN empresas e ON o.id_empresa = e.usuario_id
            WHERE %s = '' OR o.titulo ILIKE %s OR o.descripcion ILIKE %s
            ORDER BY o.fecha_creacion DESC
        """, (q, f"%{q}%", f"%{q}%"))
        for row in cursor.fetchall():
            publicaciones.append({
                'tipo': 'oferta',
                'titulo': row[0],
                'descripcion': row[1],
                'fecha': row[2],
                'nombre_empresa': row[3]
            })

    # 2️⃣ Obtener tutorías
    if filtro in ('', 'tutorias'):
        cursor.execute("""
            SELECT t.titulo, t.descripcion, t.fecha_publicacion, u.nombre
            FROM tutorias t
            JOIN usuarios u ON t.estudiante_id = u.id
            WHERE %s = '' OR t.titulo ILIKE %s OR t.descripcion ILIKE %s
            ORDER BY t.fecha_publicacion DESC
        """, (q, f"%{q}%", f"%{q}%"))
        for row in cursor.fetchall():
            publicaciones.append({
                'tipo': 'tutoria',
                'titulo': row[0],
                'descripcion': row[1],
                'fecha': row[2],
                'nombre_estudiante': row[3]
            })

    # 3️⃣ Obtener empresas
    if filtro in ('', 'empresas'):
        cursor.execute("""
            SELECT e.nombre_empresa, u.correo
            FROM empresas e
            JOIN usuarios u ON e.usuario_id = u.id
            WHERE %s = '' OR e.nombre_empresa ILIKE %s OR u.nombre ILIKE %s
            ORDER BY e.nombre_empresa
        """, (q, f"%{q}%", f"%{q}%"))
        for row in cursor.fetchall():
            publicaciones.append({
                'tipo': 'empresa',
                'nombre_empresa': row[0],
                'correo': row[1]
            })

    # Ordenar todas las publicaciones por fecha si tienen fecha
    publicaciones.sort(key=lambda x: x.get('fecha') or datetime.min, reverse=True)


    # Aplicar filtro
    if filtro in ['ofertas', 'tutorias', 'empresas']:
        tipo_map = {'ofertas': 'oferta', 'tutorias': 'tutoria', 'empresas': 'empresa'}
        publicaciones = [p for p in publicaciones if p['tipo'] == tipo_map[filtro]]
    else:
        publicaciones = publicaciones

    # Aplicar búsqueda
    if q:
        publicaciones = [
            p for p in publicaciones
            if (p.get('titulo') and q in p['titulo'].lower()) or
               (p.get('descripcion') and q in p['descripcion'].lower()) or
               (p.get('nombre_empresa') and q in p['nombre_empresa'].lower())
        ]

    return render_template('inicio_estudiante.html', publicaciones=publicaciones)

# ----------------------
# INICIO - Empresa (feed)
# ----------------------
# inicio_empresa
@app.route('/inicio_empresa')
@login_required
def inicio_empresa():
    if session['tipo'] != 'empresa':
        flash("Acceso denegado.", "danger")
        return redirect(url_for('index'))

    usuario_id = session['usuario_id']
    q = request.args.get('q', '').strip()
    filtro = request.args.get('filtro', '').lower()

    publicaciones = []

    conn = conectar_bd_lector()
    cursor = conn.cursor()

    try:
        # 1️⃣ Obtener ofertas
        if filtro in ('', 'ofertas'):
            cursor.execute("""
                SELECT o.titulo, o.descripcion, o.fecha_creacion, e.nombre_empresa
                FROM ofertas o
                JOIN empresas e ON o.id_empresa = e.usuario_id
                WHERE %s = '' OR o.titulo ILIKE %s OR o.descripcion ILIKE %s
                ORDER BY o.fecha_creacion DESC
            """, (q, f"%{q}%", f"%{q}%"))
            for row in cursor.fetchall():
                publicaciones.append({
                    'tipo': 'oferta',
                    'titulo': row[0],
                    'descripcion': row[1],
                    'fecha': row[2],
                    'nombre_empresa': row[3]
                })

        # 2️⃣ Obtener tutorías
        if filtro in ('', 'tutorias'):
            cursor.execute("""
                SELECT t.titulo, t.descripcion, t.fecha_publicacion, u.nombre
                FROM tutorias t
                JOIN usuarios u ON t.estudiante_id = u.id
                WHERE %s = '' OR t.titulo ILIKE %s OR t.descripcion ILIKE %s
                ORDER BY t.fecha_publicacion DESC
            """, (q, f"%{q}%", f"%{q}%"))
            for row in cursor.fetchall():
                publicaciones.append({
                    'tipo': 'tutoria',
                    'titulo': row[0],
                    'descripcion': row[1],
                    'fecha': row[2],
                    'nombre_estudiante': row[3]
                })

        # 3️⃣ Obtener empresas
        if filtro in ('', 'empresas'):
            cursor.execute("""
                SELECT e.nombre_empresa, u.correo
                FROM empresas e
                JOIN usuarios u ON e.usuario_id = u.id
                WHERE %s = '' OR e.nombre_empresa ILIKE %s OR u.nombre ILIKE %s
                ORDER BY e.nombre_empresa
            """, (q, f"%{q}%", f"%{q}%"))
            for row in cursor.fetchall():
                publicaciones.append({
                    'tipo': 'empresa',
                    'nombre_empresa': row[0],
                    'correo': row[1]
                })

        # Ordenar todas las publicaciones por fecha si tienen fecha
        publicaciones.sort(key=lambda x: x.get('fecha') or datetime.min, reverse=True)

        # Obtener perfil flotante
        cursor.execute("SELECT nombre, correo, nombre_empresa FROM usuarios u JOIN empresas e ON u.id = e.usuario_id WHERE u.id=%s", (usuario_id,))
        perfil = cursor.fetchone()
        session['nombre'] = perfil[0]
        session['correo'] = perfil[1]
        session['empresa'] = perfil[2]

    finally:
        cursor.close()
        conn.close()

    return render_template('inicio_empresa.html', publicaciones=publicaciones)

# ----------------------
# PERFIL - redirección por tipo
# ----------------------
@app.route('/perfil')
@login_required
def perfil():
    if session.get('tipo') == 'estudiante':
        return redirect(url_for('perfil_estudiante'))
    else:
        return redirect(url_for('perfil_empresa'))

# ----------------------
# Perfil estudiante
# ----------------------
@app.route('/perfil_estudiante')
@login_required
def perfil_estudiante():
    usuario_id = session['usuario_id']
    conn = conectar_bd_lector()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.nombre, u.correo, e.carrera
        FROM usuarios u
        JOIN estudiantes e ON u.id = e.usuario_id
        WHERE u.id = %s
    """, (usuario_id,))
    perfil = cursor.fetchone()
    cursor.close()
    conn.close()

    # Guardamos en sesión para la ventana flotante
    session['nombre'] = perfil[0]
    session['correo'] = perfil[1]
    session['carrera'] = perfil[2]

    return render_template('perfil_estudiante.html', perfil=perfil)
# ----------------------
# Perfil empresa
# ----------------------
@app.route('/perfil_empresa')
@login_required
def perfil_empresa():
    usuario_id = session['usuario_id']
    conn = conectar_bd_lector()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.nombre, u.correo, em.nombre_empresa
        FROM usuarios u
        JOIN empresas em ON u.id = em.usuario_id
        WHERE u.id = %s
    """, (usuario_id,))
    perfil = cursor.fetchone()
    cursor.close()
    conn.close()

    # Guardamos en sesión para la ventana flotante
    session['nombre'] = perfil[0]
    session['correo'] = perfil[1]
    session['empresa'] = perfil[2]

    return render_template('perfil_empresa.html', perfil=perfil)

# ----------------------
# Editar perfil estudiante
# ----------------------
@app.route('/editar_perfil_estudiante', methods=['GET','POST'])
@login_required
def editar_perfil_estudiante():
    if session.get('tipo') != 'estudiante':
        flash("Acceso denegado.", "danger")
        return redirect(url_for('index'))

    usuario_id = session['usuario_id']
    conn = None
    cursor = None
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        if request.method == 'POST':
            nombre = request.form.get('nombre', '').strip()
            correo = request.form.get('correo', '').strip()
            carrera = request.form.get('carrera', '').strip()
            if not nombre or not correo:
                flash("Nombre y correo son obligatorios.", "warning")
                return redirect(url_for('editar_perfil_estudiante'))

            cursor.execute("UPDATE usuarios SET nombre=%s, correo=%s WHERE id=%s", (nombre, correo, usuario_id))
            cursor.execute("UPDATE estudiantes SET carrera=%s WHERE usuario_id=%s", (carrera, usuario_id))
            conn.commit()
            # actualizar session
            session['nombre'] = nombre
            session['correo'] = correo
            session['carrera'] = carrera
            flash("Perfil actualizado correctamente.", "success")
            return redirect(url_for('perfil_estudiante'))

        cursor.execute("SELECT u.nombre, u.correo, s.carrera FROM usuarios u JOIN estudiantes s ON u.id = s.usuario_id WHERE u.id=%s", (usuario_id,))
        perfil = cursor.fetchone()
        return render_template('editar_perfil.html', perfil=perfil, tipo='estudiante')
    except Exception as e:
        if conn:
            conn.rollback()
        flash(f"Error al editar perfil: {e}", "danger")
        return redirect(url_for('perfil_estudiante'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ----------------------
# Editar perfil empresa
# ----------------------
@app.route('/editar_perfil_empresa', methods=['GET','POST'])
@login_required
def editar_perfil_empresa():
    if session.get('tipo') != 'empresa':
        flash("Acceso denegado.", "danger")
        return redirect(url_for('index'))

    usuario_id = session['usuario_id']
    conn = None
    cursor = None
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        if request.method == 'POST':
            nombre = request.form.get('nombre', '').strip()
            correo = request.form.get('correo', '').strip()
            nombre_empresa = request.form.get('nombre_empresa', '').strip()

            if not nombre or not correo or not nombre_empresa:
                flash("Todos los campos son obligatorios.", "warning")
                return redirect(url_for('editar_perfil_empresa'))

            cursor.execute("UPDATE usuarios SET nombre=%s, correo=%s WHERE id=%s", (nombre, correo, usuario_id))
            cursor.execute("UPDATE empresas SET nombre_empresa=%s WHERE usuario_id=%s", (nombre_empresa, usuario_id))
            conn.commit()
            # actualizar session
            session['nombre'] = nombre
            session['correo'] = correo
            session['empresa'] = nombre_empresa
            flash("Perfil actualizado correctamente.", "success")
            return redirect(url_for('perfil_empresa'))

        cursor.execute("SELECT u.nombre, u.correo, e.nombre_empresa FROM usuarios u JOIN empresas e ON u.id= e.usuario_id WHERE u.id=%s", (usuario_id,))
        perfil = cursor.fetchone()
        return render_template('editar_perfil.html', perfil=perfil, tipo='empresa')
    except Exception as e:
        if conn:
            conn.rollback()
        flash(f"Error al editar perfil: {e}", "danger")
        return redirect(url_for('perfil_empresa'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ----------------------
# Ver empresas
# ----------------------
@app.route('/ver_empresas')
@login_required
def ver_empresas():
    conn = None
    cursor = None
    try:
        conn = conectar_bd_lector()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.nombre, u.correo, e.nombre_empresa
            FROM usuarios u
            JOIN empresas e ON u.id = e.usuario_id
            ORDER BY e.nombre_empresa
        """)
        empresas = []
        for row in cursor.fetchall():
            empresas.append({
                'id': row[0],
                'nombre': row[1],
                'correo': row[2],
                'nombre_empresa': row[3],
            })
        return render_template('ver_empresas.html', empresas=empresas)
    except Exception as e:
        flash(f"Error al obtener empresas: {e}", "danger")
        return redirect(url_for('index'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ----------------------
# Ver estudiantes
# ----------------------
@app.route('/ver_estudiantes')
@login_required
def ver_estudiantes():
    conn = None
    cursor = None
    try:
        conn = conectar_bd_lector()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.nombre, u.correo, s.carrera
            FROM usuarios u
            JOIN estudiantes s ON u.id = s.usuario_id
            ORDER BY u.nombre
        """)
        estudiantes = []
        for row in cursor.fetchall():
            estudiantes.append({
                'id': row[0],
                'nombre': row[1],
                'correo': row[2],
                'carrera': row[3]
            })
        return render_template('ver_estudiantes.html', estudiantes=estudiantes)
    except Exception as e:
        flash(f"Error al obtener estudiantes: {e}", "danger")
        return redirect(url_for('index'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ----------------------
# Agregar oferta (solo empresas)
# ----------------------
@app.route('/agregar_oferta', methods=['GET','POST'])
@login_required
def agregar_oferta():
    if session.get('tipo') != 'empresa':
        flash("Acceso denegado.", "danger")
        return redirect(url_for('index'))

    usuario_id = session['usuario_id']
    if request.method == 'POST':
        titulo = request.form.get('titulo','').strip()
        descripcion = request.form.get('descripcion','').strip()

        if not titulo or not descripcion:
            flash("Título y descripción son obligatorios", "warning")
            return redirect(url_for('agregar_oferta'))

        conn = None
        cursor = None
        try:
            conn = conectar_bd()
            cursor = conn.cursor()
            # Usamos el usuario_id como id_empresa (según tu esquema: empresas.usuario_id)
            cursor.execute(
                "INSERT INTO ofertas (id_empresa, titulo, descripcion, fecha_creacion) VALUES (%s,%s,%s,%s)",
                (usuario_id, titulo, descripcion, datetime.now())
            )
            conn.commit()
            flash("Oferta publicada exitosamente", "success")
            return redirect(url_for('ver_ofertas'))
        except Exception as e:
            if conn:
                conn.rollback()
            flash(f"Error al agregar oferta: {e}", "danger")
            return redirect(url_for('agregar_oferta'))
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    return render_template('agregar_oferta.html')


# ----------------------
# Ver ofertas (feed)
# ----------------------
@app.route('/ver_ofertas')
@login_required
def ver_ofertas():
    conn = None
    cursor = None
    try:
        conn = conectar_bd_lector()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                o.id, 
                e.nombre_empresa, 
                o.titulo, 
                o.descripcion, 
                o.fecha_creacion
            FROM ofertas o
            JOIN empresas e ON o.id_empresa = e.usuario_id
            ORDER BY o.fecha_creacion DESC
        """)
        ofertas = cursor.fetchall()
        return render_template('ver_ofertas.html', ofertas=ofertas)
    except Exception as e:
        flash(f"Error al cargar ofertas: {e}", "danger")
        # si falla, enviamos al inicio según tipo
        if session.get('tipo') == 'empresa':
            return redirect(url_for('inicio_empresa'))
        else:
            return redirect(url_for('inicio_estudiante'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ----------------------
# Editar oferta
# -oferta
# ----------------------
@app.route('/editar_oferta/<int:id>', methods=['GET','POST'])
@login_required
def editar_oferta(id):
    if session.get('tipo') != 'empresa':
        flash("Acceso denegado.", "danger")
        return redirect(url_for('index'))

    conn = None
    cursor = None
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        if request.method == 'POST':
            titulo = request.form.get('titulo','').strip()
            descripcion = request.form.get('descripcion','').strip()

            if not titulo or not descripcion:
                flash("Título y descripción son obligatorios", "warning")
                return redirect(url_for('editar_oferta', id=id))

            cursor.execute("UPDATE ofertas SET titulo=%s, descripcion=%s WHERE id=%s AND id_empresa=%s",
                           (titulo, descripcion, id, session['usuario_id']))
            conn.commit()
            flash("Oferta actualizada correctamente.", "success")
            return redirect(url_for('ver_ofertas'))

        cursor.execute("SELECT titulo, descripcion FROM ofertas WHERE id=%s AND id_empresa=%s", (id, session['usuario_id']))
        oferta = cursor.fetchone()
        return render_template('agregar_oferta.html', oferta=oferta)
    except Exception as e:
        if conn:
            conn.rollback()
        flash(f"Error al editar oferta: {e}", "danger")
        return redirect(url_for('ver_ofertas'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ----------------------
# Eliminar oferta
# ----------------------
@app.route('/eliminar_oferta/<int:id>')
@login_required
def eliminar_oferta(id):
    if session.get('tipo') != 'empresa':
        flash("Acceso denegado.", "danger")
        return redirect(url_for('index'))

    conn = None
    cursor = None
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ofertas WHERE id=%s AND id_empresa=%s", (id, session['usuario_id']))
        conn.commit()
        flash("Oferta eliminada correctamente.", "success")
        return redirect(url_for('ver_ofertas'))
    except Exception as e:
        if conn:
            conn.rollback()
        flash(f"Error al eliminar oferta: {e}", "danger")
        return redirect(url_for('ver_ofertas'))
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ----------------------
# Tutorias (si decides crear tabla más adelante)
# ----------------------
# ----------------------
# Agregar tutoría (solo estudiantes)
# ----------------------
@app.route('/agregar_tutoria', methods=['GET','POST'])
@login_required
def agregar_tutoria():
    if session['tipo'] != 'estudiante':
        flash("Acceso denegado.", "danger")
        return redirect(url_for('index'))

    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        descripcion = request.form.get('descripcion', '').strip()

        if not titulo or not descripcion:
            flash("Título y descripción son obligatorios", "warning")
            return redirect(url_for('agregar_tutoria'))

        conn = conectar_bd()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO tutorias (estudiante_id, titulo, descripcion, fecha_publicacion) VALUES (%s,%s,%s,%s)",
                (session['usuario_id'], titulo, descripcion, datetime.now())
            )
            conn.commit()
            flash("Tutoría agregada exitosamente", "success")
            return redirect(url_for('ver_tutorias'))
        except Exception as e:
            conn.rollback()
            flash(f"Error al agregar tutoría: {e}", "danger")
            return redirect(url_for('agregar_tutoria'))
        finally:
            cursor.close()
            conn.close()

    return render_template('agregar_tutoria.html')


# ----------------------
# Ver tutorías (solo estudiantes)
# ----------------------
@app.route('/ver_tutorias')
@login_required
def ver_tutorias():
    if session['tipo'] != 'estudiante':
        flash("Acceso denegado.", "danger")
        return redirect(url_for('index'))

    conn = conectar_bd_lector()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, titulo, descripcion, fecha_publicacion
            FROM tutorias
            WHERE estudiante_id=%s
            ORDER BY fecha_publicacion DESC
        """, (session['usuario_id'],))
        tutorias = cursor.fetchall()
        return render_template('ver_tutorias.html', tutorias=tutorias)
    finally:
        cursor.close()
        conn.close()
# ----------------------
# Editar tutoría
# ----------------------
@app.route('/editar_tutoria/<int:id>', methods=['GET','POST'])
@login_required
def editar_tutoria(id):
    if session['tipo'] != 'estudiante':
        flash("Acceso denegado.", "danger")
        return redirect(url_for('index'))

    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT titulo, descripcion FROM tutorias WHERE id=%s AND estudiante_id=%s", 
                       (id, session['usuario_id']))
        tutoría = cursor.fetchone()
        if not tutoría:
            flash("Tutoría no encontrada o no tienes permisos", "warning")
            return redirect(url_for('ver_tutorias'))

        if request.method == 'POST':
            titulo = request.form.get('titulo', '').strip()
            descripcion = request.form.get('descripcion', '').strip()
            if not titulo or not descripcion:
                flash("Todos los campos son obligatorios", "warning")
                return redirect(url_for('editar_tutoria', id=id))

            cursor.execute(
                "UPDATE tutorias SET titulo=%s, descripcion=%s WHERE id=%s",
                (titulo, descripcion, id)
            )
            conn.commit()
            flash("Tutoría actualizada correctamente", "success")
            return redirect(url_for('ver_tutorias'))

        return render_template('editar_tutoria.html', tutoría=tutoría)
    finally:
        cursor.close()
        conn.close()


# ----------------------
# Eliminar tutoría
# ----------------------
@app.route('/eliminar_tutoria/<int:id>')
@login_required
def eliminar_tutoria(id):
    if session['tipo'] != 'estudiante':
        flash("Acceso denegado.", "danger")
        return redirect(url_for('index'))

    conn = conectar_bd()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM tutorias WHERE id=%s AND estudiante_id=%s", (id, session['usuario_id']))
        if cursor.rowcount == 0:
            flash("No se encontró la tutoría o no tienes permisos", "warning")
        else:
            conn.commit()
            flash("Tutoría eliminada correctamente", "success")
        return redirect(url_for('ver_tutorias'))
    finally:
        cursor.close()
        conn.close()
# Rutas ya presentes anteriormente (agregar/ver/editar/eliminar tutorías)
# Si no existe la tabla tutorias, las rutas devolverán errores — por eso en tu DB todavía no las uses.

# ----------------------
# Ejecutar app
# ----------------------
if __name__ == "__main__":
    app.run(debug=True)