from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import Jurado, Estudiante, Profesor, AsignacionMesa, Sede, Reemplazo
from sqlalchemy.sql import func
from datetime import datetime
import random
from extensions import db
from utils.decorators import verificar_acceso_ruta

jurado_bp = Blueprint('jurado', __name__)

# Función para realizar sorteo
def realizar_sorteo(fase, grados_seleccionados, jurados_por_mesa, porcentaje_remanentes):
    print("\n=== INICIANDO REALIZAR_SORTEO ===")
    print(f"Parámetros recibidos:")
    print(f"- Fase: {fase}")
    print(f"- Grados: {grados_seleccionados}")
    print(f"- Jurados por mesa: {jurados_por_mesa}")
    print(f"- Porcentaje remanentes: {porcentaje_remanentes}")
    
    # Validar profesores - Modificado para incluir todos los profesores sin importar la sede
    print("\n=== Verificando Profesores ===")
    profesores = Profesor.query.filter(
        ~Profesor.id.in_(
            db.session.query(Jurado.id).filter(
                Jurado.tipo_persona == "Profesor",
                Jurado.sorteo == fase
            )
        )
    ).all()
    print(f"Profesores disponibles para sorteo: {len(profesores)}")

    if not profesores:
        raise ValueError("No hay suficientes profesores disponibles para asignar como jurados.")

    # Obtener estudiantes
    estudiantes = Estudiante.query.filter(
        Estudiante.grado.in_(grados_seleccionados),
        Estudiante.es_candidato == False,
        ~Estudiante.id.in_(db.session.query(Jurado.id).filter(Jurado.tipo_persona == "Estudiante"))
    ).all()
    
    print(f"Estudiantes elegibles encontrados: {len(estudiantes)}")

    # Mejorar el manejo de asignaciones únicas por sede
    asignaciones_por_sede = db.session.query(
        AsignacionMesa.sede_id,
        AsignacionMesa.mesa_numero
    ).distinct().all()

    total_mesas = len(asignaciones_por_sede)
    if total_mesas == 0:
        raise ValueError("No hay mesas configuradas para realizar el sorteo.")

    sorteos_resultado = []
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
    total_mesas = len(asignaciones_por_sede)
    estudiantes_necesarios = total_mesas * jurados_por_mesa - total_mesas # Estudiantes necesarios por mesa
    total_estudiantes_disponibles = len(estudiantes)
    total_jurados = estudiantes_necesarios + len(profesores)

    # Calcular remanentes basado en el porcentaje especificado
    remanentes_necesarios = round((estudiantes_necesarios * porcentaje_remanentes) / 100)
    
    print(f"Estudiantes necesarios: {estudiantes_necesarios}")
    print(f"Total de estudiantes disponibles: {total_estudiantes_disponibles}")
    print(f"Remanentes necesarios: {remanentes_necesarios}")

    if total_estudiantes_disponibles < estudiantes_necesarios + remanentes_necesarios:
        raise ValueError("No hay suficientes estudiantes disponibles en los grados seleccionados. Por favor, seleccione grados adicionales.")

    for asignacion in asignaciones_por_sede:
        # Verificar que no se dupliquen las mesas asignadas por sede
        if (asignacion.mesa_numero, asignacion.sede_id) in mesas_asignadas:
            continue

        estudiantes_mesa = []
        profesor = random.choice(profesores)
        profesores.remove(profesor)  # Evitar duplicados
        
        # Seleccionar estudiantes de diferentes secciones
        secciones_disponibles = list(estudiantes_por_seccion.keys())
        for _ in range(jurados_por_mesa - 1):  # -1 porque ya tenemos al profesor
            if not secciones_disponibles:
                raise ValueError("No hay suficientes secciones diferentes para completar la mesa")
            
            seccion = random.choice(secciones_disponibles)
            if not estudiantes_por_seccion[seccion]:
                secciones_disponibles.remove(seccion)
                continue
                
            estudiante = random.choice(estudiantes_por_seccion[seccion])
            estudiantes_por_seccion[seccion].remove(estudiante)
            estudiantes_mesa.append(estudiante)
            
        # Guardar en la base de datos
        for estudiante in estudiantes_mesa:
            jurado = Jurado(
                id=estudiante.id,
                numero_documento=estudiante.numero_documento,
                nombre=estudiante.nombre,
                tipo_persona="Estudiante",
                sorteo=fase,
                id_mesa=asignacion.mesa_numero,
                sede_id=asignacion.sede_id,
                activo=True
            )
            db.session.add(jurado)
        
        # Agregar profesor como jurado
        jurado_profesor = Jurado(
            id=profesor.id,
            numero_documento=profesor.numero_documento,
            nombre=profesor.nombre,
            tipo_persona="Profesor",
            sorteo=fase,
            id_mesa=asignacion.mesa_numero,
            sede_id=asignacion.sede_id,
            activo=True
        )
        db.session.add(jurado_profesor)
        
        sorteos_resultado.append({
            'sede_id': asignacion.sede_id,
            'mesa_numero': asignacion.mesa_numero,
            'estudiantes': [{
                'id': e.id,
                'nombre': e.nombre,
                'numero_documento': e.numero_documento,
                'grado': e.grado,
                'seccion': e.seccion
            } for e in estudiantes_mesa],
            'profesor': {
                'id': profesor.id,
                'nombre': profesor.nombre,
                'numero_documento': profesor.numero_documento,
                'departamento': profesor.departamento
            }
        })
    
    # Después de asignar todos los jurados, procesar remanentes
    estudiantes_restantes = []
    for seccion, estudiantes in estudiantes_por_seccion.items():
        estudiantes_restantes.extend(estudiantes)
    
    # Seleccionar remanentes aleatoriamente
    remanentes_seleccionados = random.sample(estudiantes_restantes, min(remanentes_necesarios, len(estudiantes_restantes)))
    
    # Guardar remanentes en la base de datos
    for estudiante in remanentes_seleccionados:
        jurado_remanente = Jurado(
            id=estudiante.id,
            numero_documento=estudiante.numero_documento,
            nombre=estudiante.nombre,
            tipo_persona="Estudiante",
            sorteo=fase,
            id_mesa=0,  # 0 indica que es remanente
            sede_id=None,
            activo=True
        )
        db.session.add(jurado_remanente)
        remanentes.append({
            'id': estudiante.id,
            'nombre': estudiante.nombre,
            'numero_documento': estudiante.numero_documento,
            'grado': estudiante.grado,
            'seccion': estudiante.seccion
        })
    
    db.session.commit()
    return sorteos_resultado, remanentes

# Ruta para Sorteo de Jurados
@jurado_bp.route('/sorteo_jurados', methods=['GET', 'POST'])
@verificar_acceso_ruta('jurado.sorteo_jurados')
def sorteo_jurados():
    print("\n=== INICIO DE SORTEO JURADOS ===")
    
    # Verificar el estado de los sorteos
    fase_1_completado = Jurado.query.filter_by(sorteo=1).first() is not None
    fase_2_completado = Jurado.query.filter_by(sorteo=2).first() is not None
    fase_3_completado = Jurado.query.filter_by(sorteo=3).first() is not None
    
    print(f"Estado de fases: Fase1={fase_1_completado}, Fase2={fase_2_completado}, Fase3={fase_3_completado}")

    # Obtener grados seleccionados de la sesión o del formulario
    if request.method == 'POST':
        grados = request.form.getlist('grados')
        session['grados_seleccionados'] = grados
    else:
        grados = session.get('grados_seleccionados', [])

    if request.method == 'POST':
        print("\n=== PROCESANDO POST ===")
        try:
            jurados_por_mesa = int(request.form.get('jurados_por_mesa', 3))
            porcentaje_remanentes = int(request.form.get('porcentaje_remanentes', 12))
            accion = request.form.get('fase')
            
            print(f"Datos recibidos:")
            print(f"- Grados seleccionados: {grados}")
            print(f"- Jurados por mesa: {jurados_por_mesa}")
            print(f"- Porcentaje remanentes: {porcentaje_remanentes}")
            print(f"- Acción/Fase: {accion}")
            
            if not grados:
                raise ValueError("Debe seleccionar al menos un grado")
                
            # Determinar la fase según el botón presionado
            if accion == 'Iniciar Primer Sorteo':
                fase = 1
            elif accion == 'Realizar Segundo Sorteo':
                fase = 2
            elif accion == 'Realizar Sorteo Definitivo':
                fase = 3
            else:
                raise ValueError(f"Acción no válida: {accion}")
            
            print(f"\nIniciando sorteo fase {fase}")
            sorteos, remanentes = realizar_sorteo(fase, grados, jurados_por_mesa, porcentaje_remanentes)
            print(f"Sorteo completado. Resultados: {len(sorteos)} sorteos y {len(remanentes)} remanentes")
            
            # Guardar en sesión
            session['grados_seleccionados'] = grados
            session['jurados_por_mesa'] = jurados_por_mesa
            session['porcentaje_remanentes'] = porcentaje_remanentes
            
            return jsonify({
                'success': True,
                'message': f'{"Simulacro" if fase < 3 else "Sorteo"} {fase} realizado con éxito'
            })
            
        except Exception as e:
            print(f"ERROR: {str(e)}")
            return jsonify({
                'success': False,
                'message': str(e)
            }), 400

    # Limpiar las sesiones si no hay sorteos previos
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
    grados_seleccionados = session.get('grados_seleccionados', [])
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

    # Calcular total de mesas
    total_mesas = sum(len(sede.mesas) for sede in sedes)
    
    # Después de realizar el sorteo, obtener los resultados de la base de datos
    if fase_1_completado or fase_2_completado or fase_3_completado:
        # Obtener el último sorteo realizado
        ultima_fase = 3 if fase_3_completado else (2 if fase_2_completado else 1)
        
        sorteos = []
        # Obtener todas las sedes con sus jurados
        for sede in sedes_dict:
            jurados_sede = Jurado.query.filter(
                Jurado.sorteo == ultima_fase,
                Jurado.sede_id == sede['id'],
                Jurado.activo == True,
                Jurado.id_mesa != 0
            ).order_by(Jurado.id_mesa).all()
            
            # Agrupar por mesa
            mesas = {}
            for jurado in jurados_sede:
                if jurado.id_mesa not in mesas:
                    mesas[jurado.id_mesa] = {
                        'sede_id': sede['id'],
                        'mesa_numero': jurado.id_mesa,
                        'estudiantes': [],
                        'profesor': None
                    }
                
                if jurado.tipo_persona == 'Estudiante':
                    estudiante = Estudiante.query.get(jurado.id)
                    mesas[jurado.id_mesa]['estudiantes'].append({
                        'id': jurado.id,
                        'nombre': jurado.nombre,
                        'numero_documento': jurado.numero_documento,
                        'grado': estudiante.grado,
                        'seccion': estudiante.seccion
                    })
                else:
                    mesas[jurado.id_mesa]['profesor'] = {
                        'id': jurado.id,
                        'nombre': jurado.nombre,
                        'numero_documento': jurado.numero_documento
                    }
            
            sorteos.extend(mesas.values())
        
        # Obtener remanentes de la última fase
        remanentes = []
        remanentes_query = Jurado.query.filter(
            Jurado.sorteo == ultima_fase,
            Jurado.id_mesa == 0,
            Jurado.activo == True
        ).all()
        
        for remanente in remanentes_query:
            estudiante = Estudiante.query.get(remanente.id)
            remanentes.append({
                'id': remanente.id,
                'nombre': remanente.nombre,
                'numero_documento': remanente.numero_documento,
                'grado': estudiante.grado,
                'seccion': estudiante.seccion
            })
        
        return render_template(
            'sorteo_jurados.html',
            sedes=sedes_dict,
            grados=sorted(list(set(e.grado for e in Estudiante.query.all()))),
            total_mesas=total_mesas,
            sorteos=sorteos,
            remanentes=remanentes,
            fase=ultima_fase,
            grados_seleccionados=grados_seleccionados,
            jurados_por_mesa=jurados_por_mesa,
            porcentaje_remanentes=porcentaje_remanentes,
            fase_1_completado=fase_1_completado,
            fase_2_completado=fase_2_completado,
            fase_3_completado=fase_3_completado
        )
    else:
        sorteos = []

    return render_template(
        'sorteo_jurados.html',
        sedes=sedes_dict,
        grados=sorted(list(set(e.grado for e in Estudiante.query.all()))),
        total_mesas=total_mesas,
        sorteos=sorteos,
        remanentes=remanentes,
        fase=fase,
        grados_seleccionados=grados_seleccionados,
        jurados_por_mesa=jurados_por_mesa,
        porcentaje_remanentes=porcentaje_remanentes,
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

@jurado_bp.route('/numero_estudiantes')
@verificar_acceso_ruta('jurado.sorteo_jurados')
def numero_estudiantes():
    grados = request.args.getlist('grados[]')
    
    # Obtener estudiantes disponibles excluyendo candidatos y jurados existentes
    estudiantes = Estudiante.query.filter(
        Estudiante.grado.in_(grados),
        Estudiante.es_candidato == False,
        ~Estudiante.id.in_(
            db.session.query(Jurado.id).filter(
                Jurado.tipo_persona == "Estudiante"
            ).with_entities(Jurado.id)
        )
    ).count()
    
    print(f"Grados seleccionados: {grados}")  # Debug
    print(f"Estudiantes encontrados: {estudiantes}")  # Debug
    
    return jsonify({
        'numero_estudiantes': estudiantes
    })
