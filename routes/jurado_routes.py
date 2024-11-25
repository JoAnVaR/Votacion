from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import Jurado, Estudiante, Profesor, AsignacionMesa, Sede, Reemplazo
from sqlalchemy.sql import func
from datetime import datetime
import random
from extensions import db

jurado_bp = Blueprint('jurado', __name__)

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

# Ruta para Sorteo de Jurados
@jurado_bp.route('/sorteo_jurados', methods=['GET', 'POST'])
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

# Ruta para Reemplazo de Jurados
@jurado_bp.route('/reemplazo_jurados', methods=['GET', 'POST'])
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


    asignacion = AsignacionMesa.query.get_or_404(id)
    db.session.delete(asignacion)
    db.session.commit()
    flash('Asignación eliminada correctamente', 'success')
    return redirect(url_for('asignar_mesas'))


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
