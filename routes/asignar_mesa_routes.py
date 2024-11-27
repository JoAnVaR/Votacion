from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import AsignacionMesa, Estudiante, Sede, Mesa
from sqlalchemy import text
from extensions import db
from utils.decorators import verificar_acceso_ruta

asignar_mesa_bp = Blueprint('asignar_mesa', __name__)

# Ruta para asignar mesas
@asignar_mesa_bp.route('/asignar_mesas', methods=['GET', 'POST'])
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

            # Separar grado y sección
            grado, seccion = grado_seccion.split(' - ')

            # Buscar la mesa
            mesa = Mesa.query.filter_by(
                sede_id=sede_id,
                mesa_numero=mesa_numero
            ).first()

            if not mesa:
                return jsonify({
                    'success': False,
                    'message': 'Mesa no encontrada'
                })

            # Verificar si ya existe una asignación para este grado y sección
            asignacion_existente = AsignacionMesa.query.filter_by(
                grado=grado,
                seccion=seccion,
                sede_id=sede_id
            ).first()

            if asignacion_existente:
                # Actualizar la asignación existente
                asignacion_existente.mesa_id = mesa.id
                asignacion_existente.mesa_numero = mesa_numero
            else:
                # Crear nueva asignación
                nueva_asignacion = AsignacionMesa(
                    grado=grado,
                    seccion=seccion,
                    mesa_id=mesa.id,
                    mesa_numero=mesa_numero,
                    sede_id=sede_id
                )
                db.session.add(nueva_asignacion)

            db.session.commit()

            return jsonify({
                'success': True,
                'message': 'Asignación realizada exitosamente'
            })

        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Error al realizar la asignación: {str(e)}'
            })

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
    
    # Obtener asignaciones con total de estudiantes
    asignaciones = []
    totales_por_mesa = {}  # Diccionario para almacenar totales por mesa

    for asignacion in AsignacionMesa.query.all():
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
@verificar_acceso_ruta('asignar_mesa.eliminar_asignacion')
def eliminar_asignacion(id):
    try:
        asignacion = AsignacionMesa.query.get_or_404(id)
        db.session.delete(asignacion)
        db.session.commit()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True})
        
        flash('Asignación eliminada correctamente', 'success')
        return redirect(url_for('asignar_mesa.asignar_mesas'))
        
    except Exception as e:
        db.session.rollback()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': False,
                'message': str(e)
            })
        
        flash('Error al eliminar la asignación', 'error')
        return redirect(url_for('asignar_mesa.asignar_mesas'))