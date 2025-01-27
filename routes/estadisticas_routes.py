from flask import Blueprint, render_template, jsonify
from models import Sede, Estudiante, Profesor, Mesa, AsignacionMesa, EventoCalendario
from sqlalchemy import func, exists, and_, select
from extensions import db
from datetime import datetime
from utils.decorators import verificar_acceso_ruta, login_required

estadisticas_bp = Blueprint('estadisticas', __name__)

@estadisticas_bp.route('/dashboard')
@login_required
def dashboard():
    # Estadísticas generales
    total_sedes = Sede.query.count()
    
    # Consulta para el total general de estudiantes
    total_estudiantes_general = db.session.query(func.count(Estudiante.id)).scalar()
    print(f"Total estudiantes general: {total_estudiantes_general}")
    
    # Obtener estudiantes por sede para el gráfico
    estudiantes_por_sede_query = db.session.query(
        Sede.nombre,
        func.count(Estudiante.id)
    ).outerjoin(
        Estudiante
    ).group_by(
        Sede.nombre
    ).all()

    sedes_nombres = [sede[0] for sede in estudiantes_por_sede_query]
    estudiantes_por_sede = [int(count) for _, count in estudiantes_por_sede_query]

    total_profesores = Profesor.query.count()
    total_mesas = Mesa.query.count()

    # Obtener información de sedes con sus estadísticas
    sedes_info = []
    sedes_query = Sede.query.all()
    
    for sede in sedes_query:
        # Obtener mesas de la sede ordenadas por número
        mesas = Mesa.query.filter_by(sede_id=sede.id).order_by(Mesa.mesa_numero).all()
        
        # Obtener estudiantes por grado para esta sede
        estudiantes_grado = db.session.query(
            Estudiante.grado,
            Estudiante.seccion,
            func.count(Estudiante.id)
        ).filter_by(
            sede_id=sede.id
        ).group_by(
            Estudiante.grado,
            Estudiante.seccion
        ).order_by(
            Estudiante.grado,
            Estudiante.seccion
        ).all()
        
        # Crear diccionario de grados
        grados_dict = {
            f"{grado}-{seccion}": int(total) 
            for grado, seccion, total in estudiantes_grado
        }
        
        # Renumerar las mesas para esta sede
        mesas_info = []
        for i, mesa in enumerate(mesas, 1):
            mesa_dict = {
                'id': mesa.id,
                'mesa_numero': i,  # Renumeramos localmente
                'sede_id': mesa.sede_id
            }
            mesas_info.append(mesa_dict)
        
        # Crear objeto sede con toda la información necesaria
        sede_dict = {
            'id': sede.id,
            'nombre': sede.nombre,
            'mesas': mesas_info,
            'grados': grados_dict
        }
        sedes_info.append(sede_dict)

    # Estudiantes por grado
    grados_query = db.session.query(
        Estudiante.grado,
        db.func.count(Estudiante.id).label('total')
    ).group_by(Estudiante.grado).order_by(Estudiante.grado).all()
    
    grados = [str(g[0]) for g in grados_query]
    estudiantes_por_grado = [int(g[1]) for g in grados_query]

    # Validaciones básicas
    estudiantes_sin_mesa = db.session.query(Estudiante).filter(
        ~exists().where(
            and_(
                AsignacionMesa.grado == Estudiante.grado,
                AsignacionMesa.seccion == Estudiante.seccion,
                AsignacionMesa.sede_id == Estudiante.sede_id
            )
        )
    ).count()

    profesores_sin_sede = Profesor.query.filter_by(sede_id=None).count()
    mesas_vacias = 0

    # Total de mesas
    total_mesas = Mesa.query.count()

    # Conteo de mesas sin asignaciones
    mesas_sin_asignaciones = 0
    estudiantes_por_mesa = {}
    
    for mesa in Mesa.query.all():
        # Verificar asignaciones para esta mesa
        asignaciones = AsignacionMesa.query.filter_by(
            mesa_numero=mesa.mesa_numero,
            sede_id=mesa.sede_id
        ).all()
        
        if not asignaciones:
            mesas_sin_asignaciones += 1
            print(f"DEBUG: Mesa {mesa.mesa_numero} en sede {mesa.sede_id} sin asignaciones")
            estudiantes_por_mesa[mesa.id] = 0
            continue
        
        # Contar estudiantes para las asignaciones existentes
        total_estudiantes = 0
        for asignacion in asignaciones:
            estudiantes = Estudiante.query.filter_by(
                sede_id=mesa.sede_id,
                grado=asignacion.grado,
                seccion=asignacion.seccion
            ).count()
            total_estudiantes += estudiantes
            
        estudiantes_por_mesa[mesa.id] = total_estudiantes
        print(f"DEBUG: Mesa {mesa.mesa_numero} (Sede {mesa.sede_id}): {total_estudiantes} estudiantes")

    # Agregar conteo de mesas y profesores por sede
    mesas_por_sede = []
    profesores_por_sede = []
    
    for sede in sedes_query:
        # Contar mesas por sede
        mesas_count = Mesa.query.filter_by(sede_id=sede.id).count()
        mesas_por_sede.append(mesas_count)
        
        # Contar profesores por sede
        profesores_count = Profesor.query.filter_by(sede_id=sede.id).count()
        profesores_por_sede.append(profesores_count)

    return render_template('dashboard_estadisticas.html',
        total_sedes=total_sedes,
        total_estudiantes=total_estudiantes_general,
        total_profesores=total_profesores,
        total_mesas=total_mesas,
        sedes=sedes_info,
        estudiantes_sin_mesa=estudiantes_sin_mesa,
        profesores_sin_sede=profesores_sin_sede,
        mesas_vacias=mesas_vacias,
        sedes_nombres=sedes_nombres,
        estudiantes_por_sede=estudiantes_por_sede,
        grados=grados,
        estudiantes_por_grado=estudiantes_por_grado,
        mesas_sin_asignaciones=mesas_sin_asignaciones,
        estudiantes_por_mesa=estudiantes_por_mesa,
        mesas_por_sede=mesas_por_sede,
        profesores_por_sede=profesores_por_sede
    )

@estadisticas_bp.route('/finalizar_configuracion', methods=['POST'])
@login_required
def finalizar_configuracion():
    try:
        # Verificar si hay errores pendientes
        estudiantes_sin_mesa = db.session.query(Estudiante).filter(
            ~exists().where(
                and_(
                    AsignacionMesa.grado == Estudiante.grado,
                    AsignacionMesa.seccion == Estudiante.seccion,
                    AsignacionMesa.sede_id == Estudiante.sede_id
                )
            )
        ).count()
        
        profesores_sin_sede = Profesor.query.filter_by(sede_id=None).count()
        
        if estudiantes_sin_mesa > 0 or profesores_sin_sede > 0:
            return jsonify({
                'success': False,
                'message': 'No se puede finalizar la configuración mientras haya errores pendientes'
            })

        # Actualizar estado de eventos fase 1
        eventos_fase1 = EventoCalendario.query.filter_by(fase=1).all()
        for evento in eventos_fase1:
            evento.estado = 'completado'
        
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Configuración finalizada exitosamente'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error al finalizar la configuración: {str(e)}'
        }) 