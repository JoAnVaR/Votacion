from flask import Blueprint, render_template, jsonify
from models import Sede, Estudiante, Profesor, Mesa, AsignacionMesa, EventoCalendario
from sqlalchemy import func, exists, and_, select
from extensions import db
from datetime import datetime

estadisticas_bp = Blueprint('estadisticas', __name__)

@estadisticas_bp.route('/dashboard')
def dashboard():
    # Estadísticas generales
    total_sedes = Sede.query.count()
    total_estudiantes = Estudiante.query.count()
    total_profesores = Profesor.query.count()
    total_mesas = Mesa.query.count()

    # Obtener información de sedes con sus estadísticas
    sedes = []
    sedes_query = Sede.query.all()
    sedes_nombres = [sede.nombre for sede in sedes_query]

    # Preparar información detallada de cada sede
    for sede in sedes_query:
        # Obtener mesas de la sede
        mesas = Mesa.query.filter_by(sede_id=sede.id).all()
        
        # Obtener estudiantes por grado en esta sede
        estudiantes_grado = db.session.query(
            Estudiante.grado,
            db.func.count(Estudiante.id)
        ).filter_by(sede_id=sede.id).group_by(Estudiante.grado).all()
        
        grados_dict = {str(grado): total for grado, total in estudiantes_grado}
        
        sede_info = {
            'nombre': sede.nombre,
            'mesas': mesas,
            'grados': grados_dict
        }
        sedes.append(sede_info)

    # Estudiantes por sede
    estudiantes_por_sede = []
    for sede in sedes_query:
        total = Estudiante.query.filter_by(sede_id=sede.id).count()
        estudiantes_por_sede.append(total)

    # Estudiantes por grado (general)
    grados_query = db.session.query(
        Estudiante.grado,
        db.func.count(Estudiante.id).label('total')
    ).group_by(Estudiante.grado).order_by(Estudiante.grado).all()
    
    grados = [str(g[0]) for g in grados_query]
    estudiantes_por_grado = [int(g[1]) for g in grados_query]

    # Mesas por sede
    mesas_por_sede = []
    for sede in sedes_query:
        total_mesas = Mesa.query.filter_by(sede_id=sede.id).count()
        mesas_por_sede.append(int(total_mesas))

    # Profesores por sede
    profesores_por_sede = []
    for sede in sedes_query:
        total_profesores_sede = Profesor.query.filter_by(sede_id=sede.id).count()
        profesores_por_sede.append(int(total_profesores_sede))

    # Agregar profesores sin sede al gráfico (opcional)
    profesores_sin_sede = Profesor.query.filter_by(sede_id=None).count()
    if profesores_sin_sede > 0:
        sedes_nombres.append("Sin Sede")
        profesores_por_sede.append(int(profesores_sin_sede))

    # Conteo de estudiantes por mesa
    estudiantes_por_mesa = {}
    estudiantes_por_mesa_query = db.session.query(
        AsignacionMesa.mesa_id,
        db.func.count(Estudiante.id).label('total')
    ).join(
        Estudiante,
        and_(
            Estudiante.grado == AsignacionMesa.grado,
            Estudiante.seccion == AsignacionMesa.seccion,
            Estudiante.sede_id == AsignacionMesa.sede_id
        )
    ).group_by(AsignacionMesa.mesa_id).all()

    for mesa_id, total in estudiantes_por_mesa_query:
        estudiantes_por_mesa[mesa_id] = total

    # Validaciones
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
    mesas_vacias = Mesa.query.filter(~Mesa.id.in_(
        db.session.query(AsignacionMesa.mesa_id)
    )).count()

    # Ejecutar todas las validaciones
    mesas_sobrecargadas = validar_estudiantes_por_mesa()
    mesas_con_grados_dispersos = validar_grados_por_mesa()
    mesas_desbalanceadas = validar_distribucion_estudiantes()

    # Actualizar hay_errores para incluir las nuevas validaciones
    hay_errores = (
        estudiantes_sin_mesa > 0 or 
        profesores_sin_sede > 0 or 
        mesas_vacias > 0 or 
        len(mesas_sobrecargadas) > 0 or 
        len(mesas_con_grados_dispersos) > 0 or 
        len(mesas_desbalanceadas) > 0
    )

    # Conteo total de mesas (incluyendo todas las mesas)
    total_mesas = Mesa.query.count()
    
    # Conteo de mesas sin asignaciones
    mesas_sin_asignaciones = Mesa.query.filter(~Mesa.id.in_(
        db.session.query(AsignacionMesa.mesa_id)
    )).count()

    return render_template('dashboard_estadisticas.html',
        total_sedes=total_sedes,
        total_estudiantes=total_estudiantes,
        total_profesores=total_profesores,
        total_mesas=total_mesas,
        sedes=sedes,
        estudiantes_sin_mesa=estudiantes_sin_mesa,
        profesores_sin_sede=profesores_sin_sede,
        mesas_vacias=mesas_vacias,
        hay_errores=hay_errores,
        estudiantes_por_mesa=estudiantes_por_mesa,
        # Datos para los gráficos
        sedes_nombres=sedes_nombres,
        estudiantes_por_sede=estudiantes_por_sede,
        grados=grados,
        estudiantes_por_grado=estudiantes_por_grado,
        mesas_por_sede=mesas_por_sede,
        profesores_por_sede=profesores_por_sede,
        mesas_sobrecargadas=mesas_sobrecargadas,
        mesas_con_grados_dispersos=mesas_con_grados_dispersos,
        mesas_desbalanceadas=mesas_desbalanceadas,
        mesas_sin_asignaciones=mesas_sin_asignaciones
    )

@estadisticas_bp.route('/finalizar_configuracion', methods=['POST'])
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

        # Verificar si todos los eventos de la fase 1 han terminado
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

def validar_estudiantes_por_mesa():
    # Máximo de estudiantes permitidos por mesa
    MAX_ESTUDIANTES_POR_MESA = 30
    
    mesas_sobrecargadas = db.session.query(
        AsignacionMesa.mesa_id,
        Mesa.mesa_numero,
        Sede.nombre.label('sede_nombre'),
        db.func.count(Estudiante.id).label('total')
    ).join(
        Mesa, AsignacionMesa.mesa_id == Mesa.id
    ).join(
        Sede, Mesa.sede_id == Sede.id
    ).join(
        Estudiante,
        and_(
            Estudiante.grado == AsignacionMesa.grado,
            Estudiante.seccion == AsignacionMesa.seccion
        )
    ).group_by(
        AsignacionMesa.mesa_id
    ).having(
        db.func.count(Estudiante.id) > MAX_ESTUDIANTES_POR_MESA
    ).all()
    
    return mesas_sobrecargadas 

def validar_grados_por_mesa():
    mesas_con_grados_dispersos = db.session.query(
        Mesa.id,
        Mesa.mesa_numero,
        Sede.nombre.label('sede_nombre'),
        db.func.min(Estudiante.grado).label('grado_min'),
        db.func.max(Estudiante.grado).label('grado_max')
    ).join(
        AsignacionMesa, Mesa.id == AsignacionMesa.mesa_id
    ).join(
        Sede, Mesa.sede_id == Sede.id
    ).join(
        Estudiante,
        and_(
            Estudiante.grado == AsignacionMesa.grado,
            Estudiante.seccion == AsignacionMesa.seccion
        )
    ).group_by(Mesa.id).having(
        db.func.max(Estudiante.grado) - db.func.min(Estudiante.grado) > 1
    ).all()
    
    return mesas_con_grados_dispersos 

def validar_distribucion_estudiantes():
    # Primero obtener el conteo por mesa
    subquery = db.session.query(
        AsignacionMesa.mesa_id,
        db.func.count(Estudiante.id).label('estudiantes_count')
    ).join(
        Estudiante,
        and_(
            Estudiante.grado == AsignacionMesa.grado,
            Estudiante.seccion == AsignacionMesa.seccion,
            Estudiante.sede_id == AsignacionMesa.sede_id
        )
    ).group_by(AsignacionMesa.mesa_id).subquery()

    # Luego calcular el promedio
    promedio = db.session.query(
        db.func.avg(subquery.c.estudiantes_count)
    ).scalar() or 0

    # Encontrar mesas con desviación significativa
    mesas_desbalanceadas = db.session.query(
        Mesa.id,
        Mesa.mesa_numero,
        Sede.nombre.label('sede_nombre'),
        db.func.count(Estudiante.id).label('total')
    ).join(
        AsignacionMesa, Mesa.id == AsignacionMesa.mesa_id
    ).join(
        Sede, Mesa.sede_id == Sede.id
    ).join(
        Estudiante,
        and_(
            Estudiante.grado == AsignacionMesa.grado,
            Estudiante.seccion == AsignacionMesa.seccion,
            Estudiante.sede_id == AsignacionMesa.sede_id
        )
    ).group_by(
        Mesa.id,
        Mesa.mesa_numero,
        Sede.nombre
    ).having(
        db.func.abs(db.func.count(Estudiante.id) - promedio) > 5
    ).all()
    
    return mesas_desbalanceadas 