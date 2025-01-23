from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import Jurado, Estudiante, Profesor, AsignacionMesa, ReemplazoJurado, Sede, ConfiguracionSorteo
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
    
    # Validar profesores - Solo filtrar por activo
    print("\n=== Verificando Profesores ===")
    profesores = Profesor.query.all()  # Removemos el filtro de sorteos previos
    print(f"Profesores disponibles para sorteo: {len(profesores)}")

    if not profesores:
        raise ValueError("No hay suficientes profesores disponibles para asignar como jurados.")

    # Obtener estudiantes - Solo filtrar candidatos y grados seleccionados
    estudiantes = Estudiante.query.filter(
        Estudiante.grado.in_(grados_seleccionados),
        Estudiante.es_candidato == False
    ).all()
    
    print(f"Estudiantes elegibles encontrados: {len(estudiantes)}")
    print("Grados de los estudiantes seleccionados:", set(e.grado for e in estudiantes))

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
    mesas_asignadas = set()  # Para llevar control de mesas ya asignadas

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
        mesa_key = (asignacion.mesa_numero, asignacion.sede_id)
        if mesa_key in mesas_asignadas:
            continue
        
        mesas_asignadas.add(mesa_key)  # Agregar la mesa a las asignadas
        
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
                id=None,  # Permitir que la base de datos asigne un nuevo ID
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
            id=None,  # Permitir que la base de datos asigne un nuevo ID
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
            id=None,  # Permitir que la base de datos asigne un nuevo ID
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
   
   # Definir ultima_fase aquí, antes de usarla
    if fase_3_completado:
        ultima_fase = 3
    elif fase_2_completado:
        ultima_fase = 2
    elif fase_1_completado:
        ultima_fase = 1
    else:
        ultima_fase = 0
    
    print(f"Estado de fases: Fase1={fase_1_completado}, Fase2={fase_2_completado}, Fase3={fase_3_completado}")

    if request.method == 'POST':
        print("\n=== PROCESANDO POST ===")
        try:
            accion = request.form.get('fase')
            
            # Si es segundo o tercer sorteo, obtener datos de ConfiguracionSorteo
            if accion in ['Realizar Segundo Sorteo', 'Realizar Sorteo Definitivo']:
                config_sorteo = ConfiguracionSorteo.query.first()
                if not config_sorteo:
                    raise ValueError("No se encontró la configuración del sorteo anterior")
                
                grados = config_sorteo.grados_seleccionados.split(',')
                jurados_por_mesa = config_sorteo.jurados_por_mesa
                porcentaje_remanentes = config_sorteo.porcentaje_remanentes
            else:
                # Para el primer sorteo, usar datos del formulario
                grados = request.form.getlist('grados')
                jurados_por_mesa = int(request.form.get('jurados_por_mesa', 3))
                porcentaje_remanentes = int(request.form.get('porcentaje_remanentes', 12))
            
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
            
            # Guardar configuración después del sorteo exitoso
            config_sorteo = ConfiguracionSorteo.query.first()
            if not config_sorteo:
                config_sorteo = ConfiguracionSorteo()
            
            config_sorteo.jurados_por_mesa = jurados_por_mesa
            config_sorteo.porcentaje_remanentes = porcentaje_remanentes
            config_sorteo.grados_seleccionados = ','.join(map(str, grados))
            config_sorteo.fase_actual = fase
            config_sorteo.fecha_actualizacion = datetime.now()
            
            db.session.add(config_sorteo)
            db.session.commit()
            
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
        for sede in sedes:  # Usar sedes en lugar de sedes_dict
            jurados_sede = Jurado.query.filter(
                Jurado.sorteo == ultima_fase,
                Jurado.sede_id == sede.id,
                Jurado.mesa_id != 0
            ).order_by(Jurado.mesa_id).all()
            
            # Agrupar por mesa
            mesas = {}
            for jurado in jurados_sede:
                if jurado.mesa_id not in mesas:
                    mesas[jurado.mesa_id] = {
                        'sede_id': sede.id,
                        'mesa_numero': jurado.mesa_id,
                        'estudiantes': [],
                        'profesor': None
                    }
                
                if jurado.tipo_persona == 'Estudiante':
                    estudiante = Estudiante.query.filter_by(
                        numero_documento=jurado.numero_documento
                    ).first()
                    
                    if estudiante:
                        mesas[jurado.mesa_id]['estudiantes'].append({
                            'id': estudiante.id,
                            'nombre': jurado.nombre,
                            'numero_documento': jurado.numero_documento,
                            'grado': estudiante.grado,
                            'seccion': estudiante.seccion,
                            'reemplazado': not jurado.activo
                        })
                else:  # Es profesor
                    profesor = Profesor.query.filter_by(
                        numero_documento=jurado.numero_documento
                    ).first()
                    
                    mesas[jurado.mesa_id]['profesor'] = {
                        'id': jurado.id,
                        'nombre': jurado.nombre,
                        'numero_documento': jurado.numero_documento,
                        'departamento': profesor.departamento if profesor else None,
                        'reemplazado': not jurado.activo  # Agregar estado de reemplazo para profesores
                    }
            
            # Agregar todas las mesas de esta sede a los sorteos
            sorteos.extend(mesas.values())

        # Obtener remanentes de la última fase
        remanentes = []
        remanentes_query = Jurado.query.filter(
            Jurado.sorteo == ultima_fase,
            Jurado.mesa_id == 0,  # Solo filtrar por remanentes (mesa_id = 0)
            # Removemos el filtro de activo=True para mostrar todos los remanentes originales
        ).all()
        
        for remanente in remanentes_query:
            estudiante = Estudiante.query.filter_by(
                numero_documento=remanente.numero_documento
            ).first()
            
            if estudiante:  # Verificar que se encontró el estudiante
                remanentes.append({
                    'id': remanente.id,
                    'nombre': remanente.nombre,
                    'numero_documento': remanente.numero_documento,
                    'grado': estudiante.grado,
                    'seccion': estudiante.seccion,
                    'activo': remanente.activo,
                    'usado': not remanente.activo  # True si el remanente ya fue usado
                })

        return render_template(
            'sorteo_jurados.html',
            sedes=sedes,
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
            fase_3_completado=fase_3_completado,
            config=ConfiguracionSorteo.query.first()
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
    
    if not jurado or not remanente:
        raise ValueError("Jurado o remanente no encontrado")
        
    if not jurado.activo:
        raise ValueError("El jurado ya ha sido reemplazado")
        
    if not remanente.activo:
        raise ValueError("El remanente ya ha sido utilizado")
    
    try:
        # Marcar el jurado original como inactivo
        jurado.activo = False
        
        # Crear un nuevo jurado con los datos del remanente
        nuevo_jurado = Jurado(
            numero_documento=remanente.numero_documento,
            nombre=remanente.nombre,
            tipo_persona=remanente.tipo_persona,
            sorteo=4,  # Indicar que es un reemplazo
            mesa_id=jurado.mesa_id,
            sede_id=jurado.sede_id,
            activo=True
        )
        
        # Marcar el remanente como inactivo
        remanente.activo = False
        
        # Primero guardar el nuevo jurado para obtener su ID
        db.session.add(nuevo_jurado)
        db.session.add(jurado)
        db.session.add(remanente)
        db.session.flush()  # Esto asigna el ID al nuevo_jurado
        
        # Ahora crear el registro de reemplazo con el ID del nuevo jurado
        nuevo_reemplazo = ReemplazoJurado(
            jurado_original_id=jurado.id,
            jurado_reemplazo_id=nuevo_jurado.id,
            mesa_id=jurado.mesa_id,
            razon=razon,
            fecha=datetime.now()
        )
        
        db.session.add(nuevo_reemplazo)
        db.session.commit()
        
        return nuevo_jurado
    except Exception as e:
        db.session.rollback()
        raise e

# Ruta para Reemplazo de Jurados
@jurado_bp.route('/reemplazo_jurados', methods=['GET', 'POST'])
@verificar_acceso_ruta('jurado.reemplazo_jurados')
def reemplazo_jurados():
    if request.method == 'POST':
        try:
            # Obtener datos
            if request.is_json:
                data = request.get_json()
                jurado_id = data.get('jurado_id')
                razon = data.get('razon')
                tipo_accion = data.get('tipo_accion', 'reemplazo')
                profesor_reemplazo_id = data.get('profesor_reemplazo_id')  # Nuevo campo
            else:
                jurado_id = request.form.get('jurado_id')
                razon = request.form.get('razon')
                tipo_accion = request.form.get('tipo_accion', 'reemplazo')
                profesor_reemplazo_id = request.form.get('profesor_reemplazo_id')  # Nuevo campo

            # Verificar jurado original
            jurado = Jurado.query.get(jurado_id)
            if not jurado:
                return jsonify({'success': False, 'message': 'Jurado no encontrado'}), 400

            if tipo_accion == 'reemplazo':
                if jurado.tipo_persona == 'Profesor':
                    # Validar que se haya seleccionado un profesor de reemplazo
                    if not profesor_reemplazo_id:
                        return jsonify({
                            'success': False,
                            'message': 'Debe seleccionar un profesor para reemplazar'
                        }), 400

                    # Obtener el profesor de reemplazo
                    profesor_reemplazo = Profesor.query.get(profesor_reemplazo_id)
                    if not profesor_reemplazo:
                        return jsonify({
                            'success': False,
                            'message': 'Profesor de reemplazo no encontrado'
                        }), 400

                    # Crear nuevo jurado con los datos del profesor de reemplazo
                    nuevo_jurado = Jurado(
                        numero_documento=profesor_reemplazo.numero_documento,
                        nombre=profesor_reemplazo.nombre,
                        tipo_persona='Profesor',
                        sorteo=4,  # Sorteo de reemplazos
                        mesa_id=jurado.mesa_id,
                        sede_id=jurado.sede_id,
                        activo=True
                    )
                    db.session.add(nuevo_jurado)
                    db.session.flush()  # Para obtener el ID del nuevo jurado

                    # Actualizar el jurado original
                    jurado.activo = False
                    db.session.add(jurado)

                    # Crear el registro de reemplazo
                    reemplazo = ReemplazoJurado(
                        jurado_original_id=jurado.id,
                        jurado_reemplazo_id=nuevo_jurado.id,
                        mesa_id=jurado.mesa_id,
                        razon=razon,
                        fecha=datetime.now()
                    )
                    db.session.add(reemplazo)
                    
                    # Asegurarnos de que todo se guarde
                    db.session.commit()

                    return jsonify({
                        'success': True,
                        'message': 'Reemplazo registrado correctamente'
                    })

                elif jurado.tipo_persona == 'Estudiante':
                    # Si es estudiante, usar remanente como antes
                    remanente = Jurado.query.filter(
                        Jurado.sorteo == 3,
                        Jurado.mesa_id == 0,
                        Jurado.activo == True,
                        ~Jurado.id.in_(
                            db.session.query(ReemplazoJurado.jurado_reemplazo_id)
                        )
                    ).first()
                    
                    if not remanente:
                        return jsonify({
                            'success': False,
                            'message': 'No hay remanentes disponibles'
                        }), 400
                    
                    
                    
                    nuevo_jurado = Jurado(
                    numero_documento=remanente.numero_documento,
                    nombre=remanente.nombre,
                    tipo_persona=remanente.tipo_persona,
                    sorteo=4,  # Indicar que es un reemplazo
                    mesa_id=jurado.mesa_id,
                    sede_id=jurado.sede_id,
                    activo=True
                    )

                    # Realizar el reemplazo
                    
                    db.session.add(nuevo_jurado)
                    db.session.flush()  # Para obtener el ID del nuevo jurado

                    remanente.activo = False
                    print(f"Marcando jurado {remanente.id} como inactivo")  # Mensaje de depuración
                    db.session.add(remanente)

                    # Actualizar el jurado original
                    jurado.activo = False
                    db.session.add(jurado)

                    reemplazo = ReemplazoJurado(
                        jurado_original_id=jurado.id,
                        jurado_reemplazo_id=nuevo_jurado.id,
                        mesa_id=jurado.mesa_id,
                        razon=razon,
                        fecha=datetime.now()
                    )
                    db.session.add(reemplazo)
                    db.session.commit()

                    return jsonify({
                        'success': True,
                        'message': 'Reemplazo registrado correctamente'
                    })

            elif tipo_accion == 'exoneracion':
                # Lógica para exonerar
                jurado.activo = False  # Marcar como inactivo
                db.session.add(jurado)
                db.session.commit()

                reemplazo = ReemplazoJurado(
                        jurado_original_id=jurado.id,
                        jurado_reemplazo_id='',
                        mesa_id=jurado.mesa_id,
                        razon=razon,
                        fecha=datetime.now()
                    )
                db.session.add(reemplazo)
                db.session.commit()

            return jsonify({
                    'success': True,
                    'message': 'Jurado exonerado correctamente'
                })

        except Exception as e:
            return jsonify({
                'success': False,
                'message': str(e)
            }), 400

    try:
        # Obtener jurados activos del sorteo 3 que no son remanentes
        jurados_query = db.session.query(Jurado).filter(
            Jurado.activo == True,
            Jurado.mesa_id != 0,
            Jurado.sorteo == 3
        ).all()

        jurados = []
        for jurado in jurados_query:
            jurado_info = {
                'id': jurado.id,
                'nombre': jurado.nombre,
                'numero_documento': jurado.numero_documento,
                'mesa_id': jurado.mesa_id,
                'tipo': jurado.tipo_persona
            }

            if jurado.tipo_persona == "Estudiante":
                estudiante = Estudiante.query.filter_by(
                    numero_documento=jurado.numero_documento
                ).first()
                if estudiante:
                    jurado_info['descripcion'] = f"{estudiante.grado}° {estudiante.seccion}"
            else:
                profesor = Profesor.query.filter_by(
                    numero_documento=jurado.numero_documento
                ).first()
                if profesor:
                    jurado_info['descripcion'] = f"Profesor - {profesor.departamento}"

            jurados.append(jurado_info)

        # Obtener reemplazos y exoneraciones
        reemplazos = db.session.query(ReemplazoJurado).order_by(ReemplazoJurado.fecha.desc()).all()
        reemplazos_info = []
        
        for reemplazo in reemplazos:
            info = {
                'fecha': reemplazo.fecha,
                'mesa_id': reemplazo.mesa_id,
                'razon': reemplazo.razon,
                'original': {
                    'nombre': reemplazo.jurado_original.nombre,
                    'documento': reemplazo.jurado_original.numero_documento,
                    'tipo': reemplazo.jurado_original.tipo_persona
                },
                'reemplazo': None
            }
            
            # Información adicional del jurado original
            if reemplazo.jurado_original.tipo_persona == "Estudiante":
                estudiante = Estudiante.query.filter_by(
                    numero_documento=reemplazo.jurado_original.numero_documento
                ).first()
                if estudiante:
                    info['original']['descripcion'] = f"{estudiante.grado}° {estudiante.seccion}"
            else:
                profesor = Profesor.query.filter_by(
                    numero_documento=reemplazo.jurado_original.numero_documento
                ).first()
                if profesor:
                    info['original']['descripcion'] = f"Profesor - {profesor.departamento}"
            
            # Información del reemplazo si existe
            if reemplazo.jurado_reemplazo:
                info['reemplazo'] = {
                    'nombre': reemplazo.jurado_reemplazo.nombre,
                    'documento': reemplazo.jurado_reemplazo.numero_documento,
                    'tipo': reemplazo.jurado_reemplazo.tipo_persona
                }
                
                if reemplazo.jurado_reemplazo.tipo_persona == "Estudiante":
                    estudiante = Estudiante.query.filter_by(
                        numero_documento=reemplazo.jurado_reemplazo.numero_documento
                    ).first()
                    if estudiante:
                        info['reemplazo']['descripcion'] = f"{estudiante.grado}° {estudiante.seccion}"
                else:
                    profesor = Profesor.query.filter_by(
                        numero_documento=reemplazo.jurado_reemplazo.numero_documento
                    ).first()
                    if profesor:
                        info['reemplazo']['descripcion'] = f"Profesor - {profesor.departamento}"
            
            reemplazos_info.append(info)

        # Contar remanentes disponibles
        remanentes_disponibles = db.session.query(Jurado).filter(
            Jurado.sorteo == 3,
            Jurado.mesa_id == 0,
            Jurado.activo == True,
            ~Jurado.id.in_(
                db.session.query(ReemplazoJurado.jurado_reemplazo_id).filter(
                    ReemplazoJurado.jurado_reemplazo_id != None
                )
            )
        ).count()
        
        # Contar total de remanentes
        total_remanentes = db.session.query(Jurado).filter(
            Jurado.sorteo == 3,
            Jurado.mesa_id == 0
        ).count()

        # Obtener todos los profesores ordenados por nombre
        profesores_disponibles = Profesor.query.order_by(Profesor.nombre).all()

        # Obtener números de documento de jurados actuales - CORREGIDO
        jurados_actuales_query = db.session.query(Jurado).filter(
            Jurado.tipo_persona == 'Profesor',
            Jurado.activo == True,
            Jurado.sorteo.in_([3, 4])
        ).all()
        
        # Convertir a lista de números de documento
        jurados_actuales = [j.numero_documento for j in jurados_actuales_query]

        return render_template(
            'reemplazo_jurados.html',
            jurados=jurados,
            reemplazos_info=reemplazos_info,
            remanentes_disponibles=remanentes_disponibles,
            total_remanentes=total_remanentes,
            profesores_disponibles=profesores_disponibles,
            jurados_actuales=jurados_actuales
        )
        
    except Exception as e:
        print(f"Error en reemplazo_jurados: {str(e)}")
        flash(f'Error al cargar la página: {str(e)}', 'error')
        return redirect(url_for('index'))

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

@jurado_bp.route('/buscar_profesores')
def buscar_profesores():
    try:
        query = request.args.get('q', '').lower()
        
        # Obtener los números de documento de profesores que ya son jurados activos
        jurados_activos = db.session.query(Jurado.numero_documento).filter(
            Jurado.tipo_persona == 'Profesor',
            Jurado.activo == True
        ).all()
        
        # Convertir a lista de números de documento
        documentos_usados = [j[0] for j in jurados_activos]
        
        # Buscar profesores disponibles
        profesores = Profesor.query.filter(
            Profesor.numero_documento.notin_(documentos_usados)
        ).filter(
            db.or_(
                Profesor.nombre.ilike(f'%{query}%'),
                Profesor.numero_documento.ilike(f'%{query}%')
            )
        ).all()
        
        # Formatear resultados
        resultados = [{
            'id': p.id,
            'nombre': p.nombre,
            'numero_documento': p.numero_documento,
            'departamento': p.departamento
        } for p in profesores]
        
        return jsonify({
            'success': True,
            'profesores': resultados
        })
        
    except Exception as e:
        print(f"Error en buscar_profesores: {str(e)}")  # Para debugging
        return jsonify({
            'success': False,
            'error': str(e),
            'profesores': []
        }), 200

