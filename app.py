#Importacion y configuracion inicial
import os 
import csv
import random
import io

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_secreto'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///votacion.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
db = SQLAlchemy(app)

# Crear el directorio de subida si no existe 
if not os.path.exists(app.config['UPLOAD_FOLDER']): 
    os.makedirs(app.config['UPLOAD_FOLDER'])

#Context Processor para Enumerar
@app.context_processor
def utility_processor():
    def enumerar(iterable, start=0):
        return enumerate(iterable, start)
    return dict(enumerar=enumerar)

#Modelos de Base de Datos
class Estudiante(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_documento = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    grado = db.Column(db.String(20), nullable=False)
    seccion = db.Column(db.String(10), nullable=False)
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=False)
    es_candidato = db.Column(db.Boolean, default=False)
    sede = db.relationship('Sede', backref='estudiantes')

class Profesor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_documento = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    departamento = db.Column(db.String(100))

# Definición del modelo para la tabla de sedes
class Sede(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.String(200), nullable=False)

# Definición del modelo para la tabla de mesas
class Mesa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=False)
    mesa_numero = db.Column(db.Integer, nullable=False)
    sede = db.relationship('Sede', backref=db.backref('mesas', lazy=True))

class AsignacionMesa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    grado = db.Column(db.String(20), nullable=False)
    seccion = db.Column(db.String(10), nullable=False)
    mesa_numero = db.Column(db.String(20), nullable=False)
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=False)
    sede = db.relationship('Sede', backref=db.backref('asignaciones', lazy=True))

class Jurado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_documento = db.Column(db.String(20), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    tipo_persona = db.Column(db.String(20), nullable=False)  # Estudiante o Profesor
    id_mesa = db.Column(db.Integer, nullable=True)  # Eliminamos la ForeignKey a mesa
    sorteo = db.Column(db.Integer, nullable=False)
    activo = db.Column(db.Boolean, default=True)
    db.UniqueConstraint('numero_documento', 'sorteo', name='unique_sorteo_documento')

class Votacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_estudiante = db.Column(db.Integer, db.ForeignKey('estudiante.id'), nullable=False)
    id_mesa = db.Column(db.Integer, nullable=True)  # Eliminamos la ForeignKey a mesa
    fecha_hora = db.Column(db.DateTime, nullable=False)
    autorizado = db.Column(db.Boolean, nullable=False)
    estudiante = db.relationship('Estudiante', backref='votaciones')

class Testigo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_documento = db.Column(db.String(20), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    tipo_persona = db.Column(db.String(20), nullable=False)  # Estudiante o Profesor
    asignaciones = db.relationship('AsignacionTestigo', backref='testigo', lazy=True)

class AsignacionTestigo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_testigo = db.Column(db.Integer, db.ForeignKey('testigo.id'), nullable=False)
    mesa_numero = db.Column(db.String(20), nullable=False)  # Cambiamos a mesa_numero

    # Definir el modelo Candidato con el campo foto_path
class Candidato(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_documento = db.Column(db.String(80), unique=True, nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    grado = db.Column(db.String(80), nullable=False)
    seccion = db.Column(db.String(80), nullable=False)
    propuesta = db.Column(db.Text, nullable=False)
    foto_path = db.Column(db.String(200), nullable=True)  # Agregar el campo foto_path

class Reemplazo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jurado_original_id = db.Column(db.Integer, db.ForeignKey('jurado.id'), nullable=False)
    jurado_original = db.relationship('Jurado', foreign_keys=[jurado_original_id])
    jurado_reemplazo_id = db.Column(db.Integer, db.ForeignKey('jurado.id'), nullable=False)
    jurado_reemplazo = db.relationship('Jurado', foreign_keys=[jurado_reemplazo_id])
    razon = db.Column(db.String(255), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


# Funciones para Poblar la Base de Datos y Asignar Mesas

# Función para Poblar la Base de Datos
def poblar_base_de_datos():
    nombres_profesores = ["Prof. Juan", "Prof. Elena", "Prof. Roberto", "Prof. Sofía"]
    departamentos = ["Matemáticas", "Ciencias", "Historia", "Inglés"]
    for i in range(1, 20):  # Crear 20 profesores
        profesor = Profesor(
            numero_documento=f"P{i:03}",
            nombre=random.choice(nombres_profesores),
            departamento=random.choice(departamentos)
        )
        db.session.add(profesor)

    db.session.commit()
    print("Base de datos poblada con datos de prueba.")

# Función para realizar sorteo
def realizar_sorteo(fase, grado_especifico):
    candidatos = Estudiante.query.filter_by(es_candidato=True, grado=grado_especifico).all()
    candidatos_ids = [c.id for c in candidatos]
    estudiantes = Estudiante.query.filter(Estudiante.grado == grado_especifico, Estudiante.id.notin_(candidatos_ids)).all()
    profesores = Profesor.query.all()
    asignaciones_mesa = AsignacionMesa.query.all()

    sorteos = []
    remanentes = []
    seleccionados = set()
    mesas_asignadas = set()  # Nuevo conjunto para rastrear mesas asignadas

    # Crear un diccionario de estudiantes por seccion
    estudiantes_por_seccion = {}
    for estudiante in estudiantes:
        if estudiante.seccion not in estudiantes_por_seccion:
            estudiantes_por_seccion[estudiante.seccion] = []
        estudiantes_por_seccion[estudiante.seccion].append(estudiante)

    # Comprobar si hay suficientes secciones diferentes
    secciones = list(estudiantes_por_seccion.keys())
    if len(secciones) < 2:
        raise ValueError("No hay suficientes secciones diferentes para realizar el sorteo.")

    for asignacion in asignaciones_mesa:
        if asignacion.mesa_numero in mesas_asignadas:
            continue  # Saltar mesas duplicadas

        estudiantes_seleccionados = []
        secciones_disponibles = list(estudiantes_por_seccion.keys())

        # Seleccionar estudiantes de secciones diferentes
        while len(estudiantes_seleccionados) < 2 and secciones_disponibles:
            seccion = random.choice(secciones_disponibles)
            if estudiantes_por_seccion[seccion]:
                estudiante = random.choice(estudiantes_por_seccion[seccion])
                estudiantes_por_seccion[seccion].remove(estudiante)
                estudiantes_seleccionados.append(estudiante)
            if not estudiantes_por_seccion[seccion]:
                secciones_disponibles.remove(seccion)

        seleccionados.update(e.id for e in estudiantes_seleccionados)

        # Seleccionar un estudiante remanente de cualquier sección disponible
        remanente_disponible = [e for e in estudiantes if e.id not in seleccionados]
        remanente = random.choice(remanente_disponible)
        seleccionados.add(remanente.id)

        profesor_seleccionado = random.choice(profesores)

        sorteos.append({
            "grado": grado_especifico,
            "seccion": asignacion.seccion,
            "mesa_numero": asignacion.mesa_numero,
            "estudiantes": [{"id": e.id, "nombre": e.nombre, "numero_documento": e.numero_documento, "seccion": e.seccion} for e in estudiantes_seleccionados],
            "profesor": {"id": profesor_seleccionado.id, "nombre": profesor_seleccionado.nombre, "numero_documento": profesor_seleccionado.numero_documento},
            "remanente": {"id": remanente.id, "nombre": remanente.nombre, "numero_documento": remanente.numero_documento, "seccion": remanente.seccion}
        })
        remanentes.append({"id": remanente.id, "nombre": remanente.nombre, "numero_documento": remanente.numero_documento})
        mesas_asignadas.add(asignacion.mesa_numero)  # Añadir mesa al conjunto de mesas asignadas

    for sorteo in sorteos:
        for estudiante in sorteo["estudiantes"]:
            nuevo_jurado = Jurado(numero_documento=estudiante["numero_documento"], nombre=estudiante["nombre"], tipo_persona="Estudiante", id_mesa=sorteo["mesa_numero"], sorteo=fase)
            db.session.add(nuevo_jurado)
        profesor = sorteo["profesor"]
        nuevo_jurado = Jurado(numero_documento=profesor["numero_documento"], nombre=profesor["nombre"], tipo_persona="Profesor", id_mesa=sorteo["mesa_numero"], sorteo=fase)
        db.session.add(nuevo_jurado)

    for remanente in remanentes:
        nuevo_remanente = Jurado(numero_documento=remanente["numero_documento"], nombre=remanente["nombre"], tipo_persona="Estudiante", id_mesa=0, sorteo=fase)
        db.session.add(nuevo_remanente)

    db.session.commit()
    return sorteos, remanentes

# Función para realizar reemplazo
def reemplazar_jurado(jurado_id, remanente_id, razon):
    jurado = Jurado.query.get(jurado_id)
    remanente = Jurado.query.get(remanente_id)
    if jurado and jurado.activo and remanente and remanente.id_mesa == 0:  # Verificar que el remanente tiene id_mesa == 0
        # Marcar el jurado como inactivo
        jurado.activo = False
        db.session.add(jurado)
        
        # Marcar el remanente como el nuevo jurado
        remanente.id_mesa = jurado.id_mesa
        remanente.activo = True
        db.session.add(remanente)

        # Registrar el reemplazo
        reemplazo = Reemplazo(
            jurado_original_id=jurado.id,
            jurado_reemplazo_id=remanente.id,
            razon=razon,
            fecha=datetime.now()
        )
        db.session.add(reemplazo)
        db.session.commit()
        return remanente
    return None

# Función para verificar extensiones permitidas:
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


# Rutas y Vistas -----------------------------------------------------------------------------------------

# Ruta de Inicio
@app.route('/')
def index():
    return render_template('index.html')

# Ruta para Poblar Datos
@app.route('/poblar_datos')
def poblar_datos():
    poblar_base_de_datos()
    return redirect(url_for('index'))

# Ruta para agregar sede
@app.route('/agregar_sede', methods=['GET', 'POST'])
def agregar_sede():
    if request.method == 'POST':
        nombre_sede = request.form['nombre_sede']
        direccion = request.form['direccion']
        nueva_sede = Sede(nombre=nombre_sede, direccion=direccion)
        db.session.add(nueva_sede)
        db.session.commit()
        return redirect(url_for('agregar_sede'))
    sedes = Sede.query.all()
    mesas = Mesa.query.all()
    return render_template('administrar_sedes_mesas.html', sedes=sedes, mesas=mesas)

# Ruta para agregar mesas
@app.route('/agregar_mesas', methods=['GET', 'POST'])
def agregar_mesas():
    if request.method == 'POST':
        sede_id = int(request.form['sede_id'])

        # Obtener el número de mesa más alto en la sede
        mesas_existentes = Mesa.query.filter_by(sede_id=sede_id).order_by(Mesa.mesa_numero).all()
        if mesas_existentes:
            ultimo_numero = mesas_existentes[-1].mesa_numero
            nuevo_numero = ultimo_numero + 1
        else:
            nuevo_numero = 1

        nueva_mesa = Mesa(sede_id=sede_id, mesa_numero=nuevo_numero)
        db.session.add(nueva_mesa)
        db.session.commit()
        return redirect(url_for('agregar_mesas'))
    
    sedes = Sede.query.all()
    return render_template('administrar_sedes_mesas.html', sedes=sedes)

# Ruta mesas existentes
@app.route('/mesas_existentes/<int:sede_id>', methods=['GET'])
def mesas_existentes(sede_id):
    mesas = Mesa.query.filter_by(sede_id=sede_id).all()
    mesa_numeros = [mesa.mesa_numero for mesa in mesas]
    return jsonify(mesa_numeros)

# Ruta para Sorteo de Jurados
@app.route('/sorteo_jurados', methods=['GET', 'POST'])
def sorteo_jurados():
    # Verificar si los tres sorteos ya se han realizado
    fase_1_completado = Jurado.query.filter_by(sorteo=1).first() is not None
    fase_2_completado = Jurado.query.filter_by(sorteo=2).first() is not None
    fase_3_completado = Jurado.query.filter_by(sorteo=3).first() is not None
    sorteos_realizados = fase_1_completado and fase_2_completado and fase_3_completado

    sorteos = []  # Inicializamos sorteos
    remanentes = []  # Inicializamos remanentes
    jurados_definitivos = []  # Inicializamos jurados definitivos

    if request.method == 'POST' and not sorteos_realizados:
        try:
            grado_especifico = request.form['grado']
            session['grado'] = grado_especifico
        except KeyError:
            grado_especifico = session.get('grado', '')

        fase = request.form.get('fase')

        if fase == 'Iniciar Primer Sorteo' and not fase_1_completado:
            sorteos, remanentes = realizar_sorteo(1, grado_especifico)
            session['fase'] = 1
        elif fase == 'Realizar Segundo Sorteo' and session.get('fase') == 1 and not fase_2_completado:
            sorteos, remanentes = realizar_sorteo(2, grado_especifico)
            session['fase'] = 2
        elif fase == 'Realizar Sorteo Definitivo' and session.get('fase') == 2 and not fase_3_completado:
            sorteos, remanentes = realizar_sorteo(3, grado_especifico)
            session.pop('fase', None)

        # Guardar sorteos en la sesión para mostrarlos después
        session['sorteos'] = sorteos
        session['remanentes'] = remanentes

        # Redireccionamos para actualizar la página y mostrar los resultados
        return redirect(url_for('sorteo_jurados'))

    # Cargar datos de la sesión si existen
    sorteos = session.get('sorteos', [])
    remanentes = session.get('remanentes', [])
    fase = session.get('fase', 0)
    grado_especifico = session.get('grado', "")

    # Obtener la lista de jurados definitivos del último sorteo
    jurados_definitivos = Jurado.query.filter_by(activo=True, sorteo=3).all()

    # Pasar las variables a la plantilla
    return render_template('sorteo_jurados.html', grados=sorted(list(set(e.grado for e in Estudiante.query.all()))), sorteos=sorteos, remanentes=remanentes, fase=fase, grado=grado_especifico, sorteos_realizados=sorteos_realizados, jurados_definitivos=jurados_definitivos, fase_1_completado=fase_1_completado, fase_2_completado=fase_2_completado, fase_3_completado=fase_3_completado)

# Ruta para registro de estudiantes
@app.route('/registro_estudiante', methods=['GET', 'POST'])
def registro_estudiante():
    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file.filename.endswith('.csv'):
                try:
                    # Leer el archivo CSV con codificación latin1
                    file_stream = io.StringIO(file.stream.read().decode("latin1"))
                    csv_reader = csv.reader(file_stream, delimiter=',')
                    next(csv_reader)  # Saltar el encabezado
                    for row in csv_reader:
                        numero_documento, nombre, grado, seccion, sede_id = row
                        # Verificar si el número de documento ya existe
                        if Estudiante.query.filter_by(numero_documento=numero_documento).first():
                            flash(f"El número de documento '{numero_documento}' ya existe en la base de datos.", 'error')
                            continue
                        nuevo_estudiante = Estudiante(
                            numero_documento=numero_documento,
                            nombre=nombre,
                            grado=grado,
                            seccion=seccion,
                            sede_id=sede_id
                        )
                        db.session.add(nuevo_estudiante)
                    db.session.commit()
                    return redirect(url_for('registro_estudiante'))
                except UnicodeDecodeError:
                    flash('Error al leer el archivo CSV. Asegúrate de que el archivo está en el formato correcto y vuelve a intentarlo.', 'error')
            else:
                flash('Por favor, sube un archivo CSV válido (.csv)', 'error')
        else:
            numero_documento = request.form['numero_documento']
            nombre = request.form['nombre']
            grado = request.form['grado']
            seccion = request.form['seccion']
            sede_id = request.form['sede_id']
            # Verificar si el número de documento ya existe
            if Estudiante.query.filter_by(numero_documento=numero_documento).first():
                flash(f"El número de documento '{numero_documento}' ya existe en la base de datos.", 'error')
            else:
                nuevo_estudiante = Estudiante(
                    numero_documento=numero_documento,
                    nombre=nombre,
                    grado=grado,
                    seccion=seccion,
                    sede_id=sede_id
                )
                db.session.add(nuevo_estudiante)
                db.session.commit()

        return redirect(url_for('registro_estudiante'))

    total_estudiantes = Estudiante.query.count()
    totales_por_sede = db.session.query(
        Sede.nombre, db.func.count(Estudiante.id)
    ).join(Estudiante).group_by(Sede.nombre).all()
    totales_por_grado_seccion = db.session.query(
        Estudiante.grado, Estudiante.seccion, Sede.nombre, db.func.count(Estudiante.id)
    ).join(Sede).group_by(Estudiante.grado, Estudiante.seccion, Sede.nombre).order_by(db.func.count(Estudiante.id).desc()).all()

    sedes = Sede.query.all()
    return render_template('registro_estudiante.html', sedes=sedes, total_estudiantes=total_estudiantes, totales_por_sede=totales_por_sede, totales_por_grado_seccion=totales_por_grado_seccion)

# Ruta para descargar la plantilla
@app.route('/descargar_plantilla')
def descargar_plantilla():
    return send_file('plantilla_estudiantes.csv', as_attachment=True)

# Ruta para detallar estudiantes
@app.route('/detalle_grado_seccion/<grado>/<seccion>/<sede>', methods=['GET', 'POST'])
def detalle_grado_seccion(grado, seccion, sede):
    if request.method == 'POST':
        if 'modificar' in request.form:
            estudiante_id = request.form['estudiante_id']
            estudiante = Estudiante.query.get(estudiante_id)
            estudiante.nombre = request.form['nombre']
            estudiante.numero_documento = request.form['numero_documento']
            db.session.commit()
        elif 'eliminar' in request.form:
            estudiante_id = request.form['estudiante_id']
            estudiante = Estudiante.query.get(estudiante_id)
            db.session.delete(estudiante)
            db.session.commit()
        return redirect(url_for('detalle_grado_seccion', grado=grado, seccion=seccion, sede=sede))

    estudiantes = Estudiante.query.join(Sede).filter(
        Estudiante.grado == grado,
        Estudiante.seccion == seccion,
        Sede.nombre == sede
    ).all()

    return render_template('detalle_grado_seccion.html', estudiantes=estudiantes, grado=grado, seccion=seccion, sede=sede)

# Ruta para Reemplazo de Jurados
@app.route('/reemplazo_jurados', methods=['GET', 'POST'])
def reemplazo_jurados():
    if request.method == 'POST':
        jurado_id = request.form['jurado_id']
        remanente_id = request.form['remanente_id']
        razon = request.form['razon']

        # Llamar a la función de reemplazo
        resultado_reemplazo = reemplazar_jurado(jurado_id, remanente_id, razon)

        if resultado_reemplazo:
            flash("Reemplazo realizado con éxito.", "success")
        else:
            flash("Error al realizar el reemplazo. Verifica los datos e intenta de nuevo.", "error")
        
        return redirect(url_for('reemplazo_jurados'))

    # Obtener los jurados activos del sorteo final (fase 3) excluyendo remanentes (id_mesa != 0)
    jurados = Jurado.query.filter(Jurado.activo == True, Jurado.sorteo == 3, Jurado.id_mesa != 0).all()

    # Obtener los remanentes del sorteo final (fase 3) que son inactivos y tienen id_mesa == 0
    remanentes = Jurado.query.filter(Jurado.activo == True, Jurado.sorteo == 3, Jurado.id_mesa == 0).all()

    reemplazos = Reemplazo.query.all()

    return render_template('reemplazo_jurados.html', jurados=jurados, remanentes=remanentes, reemplazos=reemplazos)

# Ruta para Registro de Testigos
@app.route('/asignar_testigos', methods=['GET', 'POST'])
def asignar_testigos():
    testigos = Testigo.query.all()
    asignaciones = AsignacionTestigo.query.all()  # Usamos AsignacionTestigo

    if request.method == 'POST':
        if 'agregar_testigo' in request.form:
            numero_documento = request.form.get('numero_documento')
            nombre = request.form.get('nombre')
            tipo_persona = request.form.get('tipo_persona')
            nuevo_testigo = Testigo(
                numero_documento=numero_documento,
                nombre=nombre,
                tipo_persona=tipo_persona
            )
            db.session.add(nuevo_testigo)
            db.session.commit()
        elif 'asignar_testigo' in request.form:
            testigo_id = request.form.get('testigo_id')
            mesa_numero = request.form.get('mesa_numero')
            asignacion = AsignacionTestigo(id_testigo=testigo_id, mesa_numero=mesa_numero)
            db.session.add(asignacion)
            db.session.commit()
        return redirect(url_for('asignar_testigos'))

    return render_template('asignar_testigos.html', testigos=testigos, asignaciones=asignaciones)

# Ruta para asignar mesas
@app.route('/asignar_mesas', methods=['GET', 'POST'])
def asignar_mesas():
    grados_asignados = db.session.query(
        AsignacionMesa.grado, AsignacionMesa.seccion, AsignacionMesa.sede_id
    ).distinct().all()

    grados_secciones = db.session.query(
        (Estudiante.grado + ' - ' + Estudiante.seccion).label('grado_seccion'),
        Estudiante.sede_id
    ).distinct().all()

    grados_secciones = [
        gs for gs in grados_secciones
        if (gs.grado_seccion.split(' - ')[0], gs.grado_seccion.split(' - ')[1], gs.sede_id) not in grados_asignados
    ]

    sedes = Sede.query.all()
    mesas = Mesa.query.all()

    # Filtrar sedes que tienen grados disponibles
    sedes_con_grados = [s for s in sedes if any(gs.sede_id == s.id for gs in grados_secciones)]
    
    if request.method == 'POST':
        grado_seccion = request.form.get('grado_seccion')
        mesa_numero = request.form.get('mesa_numero')

        if grado_seccion is None or mesa_numero is None:
            flash('Por favor selecciona un grado, sección y una mesa', 'error')
            return redirect(url_for('asignar_mesas'))

        grado_seccion, sede_id = grado_seccion.split('|')
        grado, seccion = grado_seccion.split(' - ')

        asignacion_mesa = AsignacionMesa(grado=grado, seccion=seccion, mesa_numero=mesa_numero, sede_id=sede_id)
        db.session.add(asignacion_mesa)
        db.session.commit()

        return redirect(url_for('asignar_mesas'))

    # Ordenar asignaciones por mesa, grado y seccion
    asignaciones = db.session.query(
        AsignacionMesa.id, AsignacionMesa.grado, AsignacionMesa.seccion, AsignacionMesa.mesa_numero, Sede.nombre.label('sede_nombre')
    ).join(Sede, AsignacionMesa.sede_id == Sede.id).order_by(
        AsignacionMesa.mesa_numero, AsignacionMesa.grado, AsignacionMesa.seccion
    ).all()

    return render_template('asignar_mesas.html', sedes=sedes, sedes_con_grados=sedes_con_grados, grados_secciones=grados_secciones, mesas=mesas, asignaciones=asignaciones)

# Ruta eliminar asignacion mesa
@app.route('/eliminar_asignacion/<int:id>', methods=['POST'])
def eliminar_asignacion(id):
    asignacion = AsignacionMesa.query.get_or_404(id)
    db.session.delete(asignacion)
    db.session.commit()
    flash('Asignación eliminada correctamente', 'success')
    return redirect(url_for('asignar_mesas'))

# Ruta para Registro de Candidatos
@app.route('/registro_candidato', methods=['GET', 'POST'])
def registro_candidato():
    if request.method == 'POST':
        id_estudiante = request.form['id_estudiante']
        propuesta = request.form['propuesta']

        # Manejo de la subida de la foto
        file = request.files['foto']
        estudiante = Estudiante.query.get(id_estudiante)
        if file and allowed_file(file.filename):
            # Renombrar el archivo con el número de documento del estudiante
            filename = secure_filename(f"{estudiante.numero_documento}.{file.filename.rsplit('.', 1)[1].lower()}")
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Guardar el nuevo candidato en la base de datos
            nuevo_candidato = Candidato(
                numero_documento=estudiante.numero_documento, 
                nombre=estudiante.nombre, 
                grado=estudiante.grado, 
                seccion=estudiante.seccion, 
                propuesta=propuesta,
                foto_path=f"uploads/{filename}"  # Guardamos la ruta relativa de la foto en la base de datos
            )
            db.session.add(nuevo_candidato)
            estudiante.es_candidato = True
            db.session.commit()

            flash('Candidato registrado exitosamente')
            return redirect(url_for('registro_candidato'))
        else:
            flash('Archivo no permitido o no subido correctamente')
    
    # Manejar búsqueda
    search_query = request.args.get('search_query')
    if search_query:
        estudiantes = Estudiante.query.filter(Estudiante.es_candidato == False, 
                                              (Estudiante.nombre.contains(search_query) | 
                                               Estudiante.numero_documento.contains(search_query))).all()
    else:
        estudiantes = Estudiante.query.filter_by(es_candidato=False).all()
    
    candidatos = Candidato.query.all()  # Obtener la lista de candidatos registrados
    
    return render_template('registro_candidato.html', estudiantes=estudiantes, candidatos=candidatos, search_query=search_query)

# Ruta para eliminar de Candidatos
@app.route('/eliminar_candidato/<int:id>', methods=['POST'])
def eliminar_candidato(id):
    candidato = Candidato.query.get(id)
    if candidato:
        # Eliminar el candidato, pero mantener el estado de estudiante para permitir la reactivación
        estudiante = Estudiante.query.filter_by(numero_documento=candidato.numero_documento).first()
        if estudiante:
            estudiante.es_candidato = False
        
        db.session.delete(candidato)
        db.session.commit()
        flash('Candidato eliminado exitosamente')
    return redirect(url_for('registro_candidato'))

if __name__ == '__main__': 
    with app.app_context(): 
        #db.drop_all()  # Eliminar todas las tablas existentes 
        db.create_all()  # Crear todas las tablas con la estructura actualizada 
    app.run(debug=True)
