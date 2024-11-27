from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from models import EventoCalendario
from extensions import db
from datetime import datetime
from utils.calendar_mappings import ACTIVITY_ROUTES

calendario_bp = Blueprint('calendario', __name__)

@calendario_bp.route('/calendario-electoral')
def calendario_electoral():
    eventos = EventoCalendario.query.order_by(EventoCalendario.fase, EventoCalendario.orden).all()
    return render_template('calendario_electoral.html', 
                         eventos=eventos,
                         sistema_bloqueado=EventoCalendario.sistema_bloqueado())

@calendario_bp.route('/calendario/editar', methods=['POST'])
def editar_calendario():
    if request.method == 'POST':
        try:
            evento_id = request.form.get('evento_id')
            evento = EventoCalendario.query.get_or_404(evento_id)
            
            # Obtener y validar fechas
            fecha_inicio = datetime.strptime(request.form.get('fecha_inicio'), '%Y-%m-%d')
            fecha_fin = datetime.strptime(request.form.get('fecha_fin'), '%Y-%m-%d')
            
            if fecha_fin < fecha_inicio:
                return jsonify({
                    'success': False,
                    'message': 'La fecha de fin no puede ser anterior a la fecha de inicio'
                }), 400
            
            # Actualizar el evento
            evento.fecha_inicio = fecha_inicio
            evento.fecha_fin = fecha_fin
            evento.titulo = request.form.get('titulo')
            evento.descripcion = request.form.get('descripcion')
            
            # Actualizar estado automáticamente
            hoy = datetime.now()
            if hoy > fecha_fin:
                evento.estado = 'completado'
            elif hoy >= fecha_inicio and hoy <= fecha_fin:
                evento.estado = 'en-curso'
            else:
                evento.estado = 'pendiente'
            
            db.session.commit()
            return jsonify({'success': True})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
    
    return redirect(url_for('calendario.calendario_electoral'))

@calendario_bp.route('/calendario/guardar', methods=['POST'])
def guardar_calendario():
    if request.method == 'POST':
        try:
            datos = request.get_json()
            eventos = datos.get('eventos', [])
            
            for evento_data in eventos:
                evento = EventoCalendario.query.get(evento_data['id'])
                if evento:
                    evento.titulo = evento_data['titulo']
                    evento.descripcion = evento_data['descripcion']
                    evento.fecha_inicio = datetime.strptime(evento_data['fecha_inicio'], '%Y-%m-%d')
                    evento.fecha_fin = datetime.strptime(evento_data['fecha_fin'], '%Y-%m-%d')
                    
                    # Actualizar estado automáticamente
                    hoy = datetime.now()
                    if hoy > evento.fecha_fin:
                        evento.estado = 'completado'
                    elif hoy >= evento.fecha_inicio and hoy <= evento.fecha_fin:
                        evento.estado = 'en-curso'
                    else:
                        evento.estado = 'pendiente'
            
            db.session.commit()
            return jsonify({'success': True})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    return jsonify({'success': False, 'message': 'Método no permitido'}), 405

@calendario_bp.route('/calendario/finalizar-calendario', methods=['POST'])
def finalizar_calendario():
    try:
        # Marcar todos los eventos como completados
        eventos = EventoCalendario.query.all()
        for evento in eventos:
            evento.estado = 'completado'
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@calendario_bp.route('/verificar-fase', methods=['POST'])
def verificar_fase():
    data = request.get_json()
    fase = data.get('fase')
    
    eventos = EventoCalendario.query.filter_by(fase=fase).all()
    ahora = datetime.now()
    
    fase_activa = any(
        evento.fecha_inicio <= ahora <= evento.fecha_fin
        for evento in eventos
    )
    
    return jsonify({
        'activa': fase_activa
    })

@calendario_bp.route('/verificar-acceso', methods=['POST'])
def verificar_acceso():
    data = request.get_json()
    ruta = data.get('ruta')
    
    # Buscar la actividad correspondiente
    for actividad, rutas in ACTIVITY_ROUTES.items():
        if ruta in rutas:
            evento = EventoCalendario.query.filter_by(titulo=actividad).first()
            if evento:
                ahora = datetime.now()
                fecha_inicio = evento.fecha_inicio.replace(hour=0, minute=0, second=0)
                fecha_fin = evento.fecha_fin.replace(hour=23, minute=59, second=59)
                return jsonify({
                    'permitido': fecha_inicio <= ahora <= fecha_fin
                })
    
    return jsonify({'permitido': False})