import os
import csv
import random
import io
import json

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.sql import func

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_secreto'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///votacion.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
db = SQLAlchemy(app)

# Crear el directorio de subida si no existe 
if not os.path.exists(app.config['UPLOAD_FOLDER']): 
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Context Processor para Enumerar
@app.context_processor
def utility_processor():
    def enumerar(iterable, start=0):
        return enumerate(iterable, start)
    return dict(enumerar=enumerar)

# Modelos de Base de Datos
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
    departamento = db.Column(db.String(100), nullable=False)
    titulo = db.Column(db.String(50), nullable=False)
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=False)
    sede = db.relationship('Sede', backref='profesores')

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
    numero_documento = db.Column(db.String(20), nullable=False, unique=True)
    nombre = db.Column(db.String(100), nullable=False)
    tipo_persona = db.Column(db.String(20), nullable=False)  # Estudiante o Profesor
    id_candidato = db.Column(db.Integer, db.ForeignKey('candidato.id'), nullable=True)
    asignaciones = db.relationship('AsignacionTestigo', backref='testigo', lazy=True)  # Cambiamos a 'testigo'

class AsignacionTestigo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_testigo = db.Column(db.Integer, db.ForeignKey('testigo.id'), nullable=False)
    id_sede = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=False)
    mesa_numero = db.Column(db.String(20), nullable=False)
    # No necesitamos redefinir aquí el backref, solo en el modelo Testigo
    sede = db.relationship('Sede', backref='asignaciones_testigos')


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

# Función para realizar sorteo
def realizar_sorteo(fase, grados_seleccionados, jurados_por_mesa, porcentaje_remanentes):
    estudiantes = Estudiante.query.filter(
        Estudiante.grado.in_(grados_seleccionados),
        Estudiante.es_candidato == False
    ).all()

    profesores = Profesor.query.all()
    asignaciones_mesa = AsignacionMesa.query.all()

    # Filtrar las asignaciones de mesas para que no se repitan en la misma sede
    asignaciones_unicas = {}
    for asignacion in asignaciones_mesa:
        if asignacion.sede_id not in asignaciones_unicas:
            asignaciones_unicas[asignacion.sede_id] = set()
        if asignacion.mesa_numero not in asignaciones_unicas[asignacion.sede_id]:
            asignaciones_unicas[asignacion.sede_id].add(asignacion.mesa_numero)

    # Crear una lista de asignaciones únicas
    asignaciones_mesa_unicas = []
    for sede, mesas in asignaciones_unicas.items():
        for mesa in mesas:
            asignaciones_mesa_unicas.append(next(a for a in asignaciones_mesa if a.sede_id == sede and a.mesa_numero == mesa))

    # Actualización del print para mostrar asignaciones únicas
    print(f"Asignaciones de mesas únicas: {len(asignaciones_mesa_unicas)}")

    sorteos = []
    remanentes = []
    seleccionados = set()
    mesas_asignadas = set()

    estudiantes_por_seccion = {}
    for estudiante in estudiantes:
        if estudiante.seccion not in estudiantes_por_seccion:
            estudiantes_por_seccion[estudiante.seccion] = []
        estudiantes_por_seccion[estudiante.seccion].append(estudiante)

    secciones = list(estudiantes_por_seccion.keys())
    if len(secciones) < 2:
        raise ValueError("No hay suficientes secciones diferentes para realizar el sorteo.")

    # Calcular correctamente los estudiantes necesarios
    total_mesas = len(asignaciones_mesa_unicas)
    estudiantes_necesarios = total_mesas * jurados_por_mesa - total_mesas # Estudiantes necesarios por mesa
    total_estudiantes_disponibles = len(estudiantes)
    total_jurados = estudiantes_necesarios + len(profesores)

    # Calcular remanentes basado en el porcentaje especificado
    remanentes_necesarios = round((total_estudiantes_disponibles * porcentaje_remanentes) / 100)
    
    print(f"Estudiantes necesarios: {estudiantes_necesarios}")
    print(f"Total de estudiantes disponibles: {total_estudiantes_disponibles}")
    print(f"Remanentes necesarios: {remanentes_necesarios}")

    if total_estudiantes_disponibles < estudiantes_necesarios + remanentes_necesarios:
        raise ValueError("No hay suficientes estudiantes disponibles en los grados seleccionados. Por favor, seleccione grados adicionales.")

    for asignacion in asignaciones_mesa_unicas:
        # Verificar que no se dupliquen las mesas asignadas por sede
        if (asignacion.mesa_numero, asignacion.sede_id) in mesas_asignadas:
            continue

        estudiantes_seleccionados = []
        secciones_disponibles = list(estudiantes_por_seccion.keys())

        while len(estudiantes_seleccionados) < (jurados_por_mesa - 1) and secciones_disponibles:
            seccion = random.choice(secciones_disponibles)
            if estudiantes_por_seccion[seccion]:
                estudiante = random.choice(estudiantes_por_seccion[seccion])
                estudiantes_por_seccion[seccion].remove(estudiante)
                estudiantes_seleccionados.append(estudiante)
            if not estudiantes_por_seccion[seccion]:
                secciones_disponibles.remove(seccion)

        seleccionados.update(e.id for e in estudiantes_seleccionados)

        remanente_disponible = [e for e in estudiantes if e.id not in seleccionados]
        if remanente_disponible:
            remanente = random.choice(remanente_disponible)
            seleccionados.add(remanente.id)
        else:
            remanente = None

        profesor_seleccionado = random.choice(profesores) if profesores else None

        sorteos.append({
            "mesa_numero": asignacion.mesa_numero,
            "sede_id": asignacion.sede_id,
            "estudiantes": [{"id": e.id, "numero_documento": e.numero_documento, "nombre": e.nombre, "grado": e.grado, "seccion": e.seccion} for e in estudiantes_seleccionados],
            "profesor": {"id": profesor_seleccionado.id, "numero_documento": profesor_seleccionado.numero_documento, "nombre": profesor_seleccionado.nombre} if profesor_seleccionado else None,
            "remanente": {"id": remanente.id, "numero_documento": remanente.numero_documento, "nombre": remanente.nombre, "grado": remanente.grado, "seccion": remanente.seccion} if remanente else None
        })
        mesas_asignadas.add((asignacion.mesa_numero, asignacion.sede_id))

    # Asignar remanentes según el porcentaje especificado
    remanente_disponible = [e for e in estudiantes if e.id not in seleccionados]
    for _ in range(remanentes_necesarios):
        if remanente_disponible:
            remanente = random.choice(remanente_disponible)
            seleccionados.add(remanente.id)
            remanentes.append({"id": remanente.id, "numero_documento": remanente.numero_documento, "nombre": remanente.nombre})
            remanente_disponible.remove(remanente)

    for sorteo in sorteos:
        for estudiante in sorteo["estudiantes"]:
            nuevo_jurado = Jurado(numero_documento=estudiante["numero_documento"], nombre=estudiante["nombre"], tipo_persona="Estudiante", id_mesa=sorteo["mesa_numero"], sorteo=fase)
            db.session.add(nuevo_jurado)
        profesor = sorteo["profesor"]
        if profesor:
            nuevo_jurado = Jurado(numero_documento=profesor["numero_documento"], nombre=profesor["nombre"], tipo_persona="Profesor", id_mesa=sorteo["mesa_numero"], sorteo=fase)
            db.session.add(nuevo_jurado)

    for remanente in remanentes:
        nuevo_remanente = Jurado(numero_documento=remanente["numero_documento"], nombre=remanente["nombre"], tipo_persona="Estudiante", id_mesa=0, sorteo=fase)
        db.session.add(nuevo_remanente)

    db.session.commit()
    return sorteos, remanentes

# Rutas y Vistas -----------------------------------------------------------------------------------------

# Ruta de Inicio
@app.route('/')
def index():
    return render_template('index.html')

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
    fase_1_completado = Jurado.query.filter_by(sorteo=1).first() is not None
    fase_2_completado = Jurado.query.filter_by(sorteo=2).first() is not None
    fase_3_completado = Jurado.query.filter_by(sorteo=3).first() is not None
    sorteos_realizados = fase_1_completado and fase_2_completado and fase_3_completado

    sorteos = []
    remanentes = []
    jurados_definitivos = []

    if request.method == 'POST' and not sorteos_realizados:
        try:
            grados_seleccionados = request.form.getlist('grados')
            jurados_por_mesa = int(request.form['jurados_por_mesa'])
            porcentaje_remanentes = int(request.form['porcentaje_remanentes'])
            session['grados'] = grados_seleccionados
            session['jurados_por_mesa'] = jurados_por_mesa
            session['porcentaje_remanentes'] = porcentaje_remanentes
        except KeyError:
            grados_seleccionados = session.get('grados', [])
            jurados_por_mesa = session.get('jurados_por_mesa', 3)
            porcentaje_remanentes = session.get('porcentaje_remanentes', 12)

        fase = request.form.get('fase')

        try:
            if fase == 'Iniciar Primer Sorteo' and not fase_1_completado:
                sorteos, remanentes = realizar_sorteo(1, grados_seleccionados, jurados_por_mesa, porcentaje_remanentes)
                session['fase'] = 1
            elif fase == 'Realizar Segundo Sorteo' and session.get('fase') == 1 and not fase_2_completado:
                sorteos, remanentes = realizar_sorteo(2, grados_seleccionados, jurados_por_mesa, porcentaje_remanentes)
                session['fase'] = 2
            elif fase == 'Realizar Sorteo Definitivo' and session.get('fase') == 2 and not fase_3_completado:
                sorteos, remanentes = realizar_sorteo(3, grados_seleccionados, jurados_por_mesa, porcentaje_remanentes)
                session.pop('fase', None)

            session['sorteos'] = sorteos
            session['remanentes'] = remanentes

            return redirect(url_for('sorteo_jurados'))
        except ValueError as e:
            flash(str(e), 'error')
            return redirect(url_for('sorteo_jurados'))

    # Limpiar las sesiones si la base de datos está vacía
    if not fase_1_completado and not fase_2_completado and not fase_3_completado:
        session.pop('sorteos', None)
        session.pop('remanentes', None)
        session.pop('fase', None)
        session.pop('grados', None)
        session.pop('jurados_por_mesa', None)
        session.pop('porcentaje_remanentes', None)

    sorteos = session.get('sorteos', [])
    remanentes = session.get('remanentes', [])
    fase = session.get('fase', 0)
    grados_seleccionados = session.get('grados', [])
    jurados_por_mesa = session.get('jurados_por_mesa', 3)
    porcentaje_remanentes = session.get('porcentaje_remanentes', 12)

    jurados_definitivos = Jurado.query.filter_by(activo=True, sorteo=3).all()

    # Serializar las sedes a diccionarios
    sedes = Sede.query.all()
    sedes_dict = []
    for sede in sedes:
        sede_dict = {"id": sede.id, "nombre": sede.nombre, "mesas": [a.mesa_numero for a in sede.asignaciones] if sede.asignaciones else []}
        if None not in sede_dict.values():  # Asegurarnos de que no haya valores None
            sedes_dict.append(sede_dict)

    return render_template(
        'sorteo_jurados.html',
        sedes=sedes_dict,
        grados=sorted(list(set(e.grado for e in Estudiante.query.all()))),
        sorteos=sorteos,
        remanentes=remanentes,
        fase=fase,
        grados_seleccionados=grados_seleccionados,
        jurados_por_mesa=jurados_por_mesa,
        porcentaje_remanentes=porcentaje_remanentes,
        sorteos_realizados=sorteos_realizados,
        jurados_definitivos=jurados_definitivos,
        fase_1_completado=fase_1_completado,
        fase_2_completado=fase_2_completado,
        fase_3_completado=fase_3_completado
    )

# Ruta para contar numero de estudiantes
@app.route('/numero_estudiantes', methods=['GET'])
def numero_estudiantes():
    grados = request.args.get('grados')
    if grados:
        grados_lista = grados.split(',')
        print(f"Grados recibidos: {grados_lista}")

        # Filtrar estudiantes por grados, excluyendo candidatos
        estudiantes = Estudiante.query.filter(
            Estudiante.grado.in_(grados_lista),
            Estudiante.es_candidato == False
        ).all()

        print(f"Estudiantes encontrados: {len(estudiantes)}")
        for estudiante in estudiantes:
            print(f"Estudiante: {estudiante.nombre}, Documento: {estudiante.numero_documento}, Grado: {estudiante.grado}")

        return jsonify({"numero_estudiantes": len(estudiantes)})

    return jsonify({"error": "Grados no especificados"}), 400

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

# Ruta para registro de profesores
@app.route('/registro_profesor', methods=['GET', 'POST'])
def registro_profesor():
    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']
            if file.filename.endswith('.csv'):
                try:
                    stream = io.StringIO(file.stream.read().decode("latin1"), newline=None)
                    csv_input = csv.reader(stream)
                    for row in csv_input:
                        if row:  # Evitar filas vacías
                            numero_documento, nombre, departamento, titulo, sede_id = row
                            nuevo_profesor = Profesor(
                                numero_documento=numero_documento,
                                nombre=nombre,
                                departamento=departamento,
                                titulo=titulo,
                                sede_id=sede_id
                            )
                            db.session.add(nuevo_profesor)
                    db.session.commit()
                    flash('Profesores cargados exitosamente')
                except Exception as e:
                    flash(f'Error al procesar el archivo CSV: {str(e)}')
                return redirect(url_for('registro_profesor'))
        else:
            numero_documento = request.form['numero_documento']
            nombre = request.form['nombre']
            departamento = request.form['departamento']
            titulo = request.form['titulo']
            sede_id = request.form['sede_id']

            nuevo_profesor = Profesor(
                numero_documento=numero_documento,
                nombre=nombre,
                departamento=departamento,
                titulo=titulo,
                sede_id=sede_id
            )
            db.session.add(nuevo_profesor)
            db.session.commit()

            flash('Profesor registrado exitosamente')
            return redirect(url_for('registro_profesor'))

    sedes = Sede.query.all()

    for sede in sedes: 
        sede.profesores = Profesor.query.filter_by(sede_id=sede.id).order_by(Profesor.numero_documento).all()

    return render_template('registro_profesor.html', sedes=sedes)

# Ruta para descargar la plantilla profesor
@app.route('/descargar_plantilla_profesor')
def descargar_plantilla_profesor():
    return send_file('plantilla_profesores.csv', as_attachment=True)

# Ruta para detallar profesor
@app.route('/eliminar_profesor/<int:id>', methods=['POST'])
def eliminar_profesor(id):
    profesor = Profesor.query.get(id)
    if profesor:
        db.session.delete(profesor)
        db.session.commit()
        flash('Profesor eliminado exitosamente')
    return redirect(url_for('registro_profesor'))

# Ruta para modificar profesor
@app.route('/modificar_profesor/<int:id>', methods=['GET', 'POST'])
def modificar_profesor(id):
    profesor = Profesor.query.get(id)
    if request.method == 'POST':
        profesor.nombre = request.form['nombre']
        profesor.numero_documento = request.form['numero_documento']
        profesor.departamento = request.form['departamento']
        profesor.titulo = request.form['titulo']
        profesor.sede_id = request.form['sede_id']

        db.session.commit()
        flash('Profesor modificado exitosamente')
        return redirect(url_for('registro_profesor'))

    sedes = Sede.query.all()
    return render_template('modificar_profesor.html', profesor=profesor, sedes=sedes)

# Ruta para Reemplazo de Jurados
@app.route('/reemplazo_jurados', methods=['GET', 'POST'])
def reemplazo_jurados():
    if request.method == 'POST':
        jurado_id = request.form['jurado_id']
        razon = request.form['razon']

        # Obtener un remanente aleatorio
        remanente = Jurado.query.filter(Jurado.activo == True, Jurado.sorteo == 3, Jurado.id_mesa == 0).order_by(func.random()).first()

        if remanente:
            # Llamar a la función de reemplazo
            resultado_reemplazo = reemplazar_jurado(jurado_id, remanente.id, razon)

            if resultado_reemplazo:
                flash("Reemplazo realizado con éxito.", "success")
            else:
                flash("Error al realizar el reemplazo. Verifica los datos e intenta de nuevo.", "error")
        else:
            flash("No hay remanentes disponibles para reemplazo.", "error")
        
        return redirect(url_for('reemplazo_jurados'))

    # Obtener los jurados activos del sorteo final (fase 3) excluyendo remanentes (id_mesa != 0)
    jurados = Jurado.query.filter(Jurado.activo == True, Jurado.sorteo == 3, Jurado.id_mesa != 0).all()

    reemplazos = Reemplazo.query.all()

    return render_template('reemplazo_jurados.html', jurados=jurados, reemplazos=reemplazos)

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
        # Eliminar el archivo de la foto
        if candidato.foto_path:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], candidato.foto_path.split('/')[-1])
            if os.path.exists(file_path):
                os.remove(file_path)

        # Eliminar el candidato, pero mantener el estado de estudiante para permitir la reactivación
        estudiante = Estudiante.query.filter_by(numero_documento=candidato.numero_documento).first()
        if estudiante:
            estudiante.es_candidato = False

        db.session.delete(candidato)
        db.session.commit()
        flash('Candidato eliminado exitosamente')
    return redirect(url_for('registro_candidato'))

# Ruta para Registro de Testigos
@app.route('/asignar_testigos', methods=['GET', 'POST'])
def asignar_testigos():
    testigos = Testigo.query.all()
    asignaciones = AsignacionTestigo.query.all()
    candidatos = Candidato.query.all()
    sedes = Sede.query.all()

    if request.method == 'POST':
        if 'agregar_testigo' in request.form:
            numero_documento = request.form.get('numero_documento')
            nombre = request.form.get('nombre')
            tipo_persona = request.form.get('tipo_persona')
            id_candidato = request.form.get('id_candidato')
            nuevo_testigo = Testigo(
                numero_documento=numero_documento,
                nombre=nombre,
                tipo_persona=tipo_persona,
                id_candidato=id_candidato
            )
            try:
                db.session.add(nuevo_testigo)
                db.session.commit()
                flash("Testigo agregado con éxito.", "success")
            except IntegrityError:
                db.session.rollback()
                flash("Error: El número de documento ya existe.", "error")
        elif 'asignar_testigo' in request.form:
            testigo_id = request.form.get('testigo_id')
            id_sede = request.form.get('id_sede')
            mesas_seleccionadas = request.form.getlist('mesas')

            for mesa_numero in mesas_seleccionadas:
                asignacion = AsignacionTestigo(id_testigo=testigo_id, id_sede=id_sede, mesa_numero=mesa_numero)
                db.session.add(asignacion)
            db.session.commit()
            flash("Testigo asignado con éxito a las mesas seleccionadas.", "success")
        return redirect(url_for('asignar_testigos'))

    return render_template('asignar_testigos.html', testigos=testigos, asignaciones=asignaciones, candidatos=candidatos, sedes=sedes)


# Ruta para obtener las mesas de una sede
@app.route('/get_mesas/<int:sede_id>')
def get_mesas(sede_id):
    mesas = Mesa.query.filter_by(sede_id=sede_id).all()
    return jsonify([{'mesa_numero': mesa.mesa_numero} for mesa in mesas])

# Ruta para eliminar una asignación de testigo
@app.route('/eliminar_asignacion/_testigo<int:asignacion_id>', methods=['POST'])
def eliminar_asignacion_testigo(asignacion_id):
    asignacion = AsignacionTestigo.query.get(asignacion_id)
    if asignacion:
        db.session.delete(asignacion)
        db.session.commit()
        flash("Asignación eliminada con éxito.", "success")
    else:
        flash("Error: Asignación no encontrada.", "error")
    return redirect(url_for('asignar_testigos'))


if __name__ == '__main__': 
    app.run(host='192.168.1.40', port=5000)
    with app.app_context(): 
        # db.drop_all()  # Eliminar todas las tablas existentes si es necesario
        db.create_all()  # Crear todas las tablas con la estructura actualizada 
    app.run(debug=True)
