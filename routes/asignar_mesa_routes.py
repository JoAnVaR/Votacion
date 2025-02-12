from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from models import AsignacionMesa, Estudiante, Sede, Mesa, UserActivity
from sqlalchemy import text
from extensions import db
from utils.decorators import verificar_acceso_ruta, login_required
from sqlalchemy.sql import exists, and_
from datetime import datetime

asignar_mesa_bp = Blueprint('asignar_mesa', __name__)

# Ruta para asignar mesas
@asignar_mesa_bp.route('/asignar_mesas', methods=['GET', 'POST'])
@login_required
@verificar_acceso_ruta('asignar_mesa.asignar_mesas')
def asignar_mesas():
    if request.method == 'POST':
        try:
            grado_seccion = request.form.get('grado_seccion')
            mesa_numero = request.form.get('mesa_numero')
            sede_id = request.form.get('sede_id')

            if not all([grado_seccion, mesa_numero, sede_id]):
                return jsonify({
                    'success': False,
                    'message': 'Faltan datos requeridos'
                })

            grado, seccion = grado_seccion.split(' - ')

            # Verificar asignación existente
            asignacion_existente = AsignacionMesa.query.filter_by(
                grado=grado,
                seccion=seccion,
                sede_id=sede_id
            ).first()

            if asignacion_existente:
                return jsonify({
                    'success': False,
                    'message': 'Este grado y sección ya tiene una mesa asignada'
                })

            # Crear nueva asignación
            nueva_asignacion = AsignacionMesa(
                grado=grado,
                seccion=seccion,
                mesa_id=mesa_numero,
                mesa_numero=mesa_numero,
                sede_id=sede_id
            )
            
            db.session.add(nueva_asignacion)
            db.session.commit()

            # Registrar la actividad del usuario
            activity = UserActivity(user_id=session['user_id'], action='Mesa asignada: ' + mesa_numero, timestamp=datetime.now())
            db.session.add(activity)
            db.session.commit()

            # Calcular total de estudiantes
            total_estudiantes = Estudiante.query.filter_by(
                grado=grado,
                seccion=seccion,
                sede_id=sede_id
            ).count()

            return jsonify({
                'success': True,
                'message': 'Mesa asignada exitosamente',
                'data': {
                    'asignacion_id': nueva_asignacion.id,
                    'grado_seccion': f"{grado} - {seccion}",
                    'mesa_numero': mesa_numero,
                    'sede_id': sede_id
                }
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Error al realizar la asignación: {str(e)}'
            })

    # Obtener asignaciones existentes usando una subconsulta
    asignaciones_subquery = db.session.query(
        AsignacionMesa.grado,
        AsignacionMesa.seccion,
        AsignacionMesa.sede_id
    ).subquery()

    # Obtener grados y secciones no asignados
    grados_secciones = db.session.query(
        Estudiante.grado,
        Estudiante.seccion,
        Estudiante.sede_id
    ).filter(
        ~exists().where(
            and_(
                asignaciones_subquery.c.grado == Estudiante.grado,
                asignaciones_subquery.c.seccion == Estudiante.seccion,
                asignaciones_subquery.c.sede_id == Estudiante.sede_id
            )
        )
    ).distinct().all()

    grados_secciones = [
        {
            'grado_seccion': f"{gs.grado} - {gs.seccion}",
            'sede_id': gs.sede_id
        }
        for gs in grados_secciones
    ]

    sedes = Sede.query.all()
    mesas = Mesa.query.all()

    # Filtrar sedes que tienen grados disponibles
    sedes_con_grados = [s for s in sedes if any(gs['sede_id'] == s.id for gs in grados_secciones)]
    
    # Obtener asignaciones con total de estudiantes
    asignaciones = []
    totales_por_mesa = {}

    # Obtener todas las asignaciones y ordenarlas
    todas_asignaciones = AsignacionMesa.query.order_by(
        AsignacionMesa.mesa_numero,
        AsignacionMesa.grado,
        AsignacionMesa.seccion
    ).all()

    for asignacion in todas_asignaciones:
        sede = Sede.query.get(asignacion.sede_id)
        
        # Contar estudiantes para esta asignación
        total_estudiantes = Estudiante.query.filter_by(
            grado=asignacion.grado,
            seccion=asignacion.seccion,
            sede_id=asignacion.sede_id
        ).count()

        # Crear clave única para la mesa
        mesa_key = f"{sede.nombre}_{asignacion.mesa_numero}"
        
        # Inicializar o actualizar el total para esta mesa
        if mesa_key not in totales_por_mesa:
            totales_por_mesa[mesa_key] = {
                'total': 0,
                'grados': [],
                'sede_id': asignacion.sede_id,
                'mesa_numero': asignacion.mesa_numero
            }
        
        # Actualizar totales y grados para esta mesa
        totales_por_mesa[mesa_key]['total'] += total_estudiantes
        totales_por_mesa[mesa_key]['grados'].append(f"{asignacion.grado} - {asignacion.seccion}")
        
        asignaciones.append({
            'id': asignacion.id,
            'mesa_numero': asignacion.mesa_numero,
            'grado': asignacion.grado,
            'seccion': asignacion.seccion,
            'sede_nombre': sede.nombre,
            'total_estudiantes': total_estudiantes
        })

    return render_template('asignar_mesas.html',
                         sedes=sedes,
                         mesas=mesas,
                         grados_secciones=grados_secciones,
                         sedes_con_grados=sedes_con_grados,
                         asignaciones=asignaciones,
                         totales_por_mesa=totales_por_mesa)  # Agregamos los totales por mesa

# Ruta eliminar asignacion mesa
@asignar_mesa_bp.route('/eliminar_asignacion/<int:id>', methods=['POST'])
@login_required
@verificar_acceso_ruta('asignar_mesa.asignar_mesas')
def eliminar_asignacion(id):
    try:
        asignacion = AsignacionMesa.query.get_or_404(id)
        
        # Guardar los datos antes de eliminar
        grado = asignacion.grado
        seccion = asignacion.seccion
        sede_id = asignacion.sede_id
        mesa_numero = asignacion.mesa_numero
        
        # Eliminar la asignación
        db.session.delete(asignacion)
        db.session.commit()
        
        user = session.get('user')
        if user:
            username_to_delete = f"{grado} - {seccion}"
            # Registrar la actividad del usuario
            activity = UserActivity(user_id=user.id, action='Asignación de mesa eliminada: ' + username_to_delete, timestamp=datetime.now())
            db.session.add(activity)
            db.session.commit()
        
        return jsonify({
            'success': True,
            'grado': grado,
            'seccion': seccion,
            'sede_id': sede_id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400