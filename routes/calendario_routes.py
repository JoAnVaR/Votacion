from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app, session
from models import EventoCalendario, Configuracion, UserActivity
from extensions import db
from datetime import datetime
from utils.calendar_mappings import ACTIVITY_ROUTES
from utils.decorators import verificar_acceso_ruta, login_required

calendario_bp = Blueprint('calendario', __name__)

@calendario_bp.route('/calendario-electoral')
@login_required
def calendario_electoral():
    eventos = EventoCalendario.query.order_by(EventoCalendario.fase, EventoCalendario.orden).all()
    config = Configuracion.query.first()
    sistema_bloqueado = config.configuracion_finalizada if config else False
    return render_template('calendario_electoral.html', 
                         eventos=eventos,
                         sistema_bloqueado=sistema_bloqueado)

@calendario_bp.route('/calendario/editar', methods=['POST'])
@login_required
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
    
    return redirect(url_for('calendario.calendario_electoral'))

@calendario_bp.route('/calendario/guardar', methods=['POST'])
@login_required
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
                    
                    # Parsear fecha de inicio con hora 00:00:00
                    fecha_inicio = datetime.strptime(evento_data['fecha_inicio'], '%Y-%m-%d').replace(hour=0, minute=0, second=0, microsecond=0)
                    
                    # Parsear fecha de fin con hora 23:59:59
                    fecha_fin = datetime.strptime(evento_data['fecha_fin_impreso'], '%Y-%m-%d').replace(hour=23, minute=59, second=59, microsecond=999999)
                    
                    evento.fecha_inicio = fecha_inicio
                    evento.fecha_fin = fecha_fin
                    evento.fecha_fin_impreso = fecha_fin
                    
                    # Actualizar estado automáticamente
                    hoy = datetime.now()
                    if hoy > evento.fecha_fin:
                        evento.estado = 'completado'
                    elif hoy >= evento.fecha_inicio and hoy <= evento.fecha_fin:
                        evento.estado = 'en-curso'
                    else:
                        evento.estado = 'pendiente'
            
            db.session.commit()
            
            # Registrar la actividad del usuario
            activity = UserActivity(user_id=session['user_id'], action='Calendario guardado', timestamp=datetime.now())
            db.session.add(activity)
            db.session.commit()
            
            return jsonify({'success': True})
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error al guardar el calendario: {str(e)}')
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    return jsonify({'success': False, 'message': 'Método no permitido'}), 405

@calendario_bp.route('/calendario/finalizar-calendario', methods=['POST'])
@login_required
@verificar_acceso_ruta('calendario.finalizar_calendario')
def finalizar_calendario():
    try:
        config = Configuracion.query.first()
        if not config:
            config = Configuracion()
            db.session.add(config)
        
        config.configuracion_finalizada = True
        config.fecha_finalizacion = datetime.now()
        
        # Actualizar estados de eventos
        eventos = EventoCalendario.query.all()
        hoy = datetime.now()
        for evento in eventos:
            if hoy > evento.fecha_fin:
                evento.estado = 'completado'
            elif hoy >= evento.fecha_inicio and hoy <= evento.fecha_fin:
                evento.estado = 'en-curso'
            else:
                evento.estado = 'pendiente'
        
        db.session.commit()

        # Registrar la actividad del usuario
        activity = UserActivity(user_id=session['user_id'], action='Calendario finalizado', timestamp=datetime.now())
        db.session.add(activity)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'calendario_bloqueado': True,
            'message': 'Calendario electoral finalizado exitosamente'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@calendario_bp.route('/verificar-fase', methods=['POST'])
@login_required
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
@login_required
def verificar_acceso():
    data = request.get_json()
    ruta = data.get('ruta')
    
    for actividad, rutas in ACTIVITY_ROUTES.items():
        if ruta in rutas:
            evento = EventoCalendario.query.filter_by(titulo=actividad).first()
            if evento:
                ahora = datetime.now()
                fecha_inicio = evento.fecha_inicio
                fecha_fin = evento.fecha_fin
                return jsonify({
                    'permitido': fecha_inicio <= ahora <= fecha_fin
                })
    
    return jsonify({'permitido': False})

@calendario_bp.route('/calendario/guardar_fecha_fin', methods=['POST'])
@login_required
def guardar_fecha_fin():
    if request.method == 'POST':
        try:
            datos = request.get_json()
            eventos = datos.get('eventos', [])
            
            for evento_data in eventos:
                evento = EventoCalendario.query.get(evento_data['id'])
                if evento:
                    evento.fecha_fin = datetime.now()
                    # Actualizar estado automáticamente
                    hoy = datetime.now()
                    if hoy > evento.fecha_fin:
                        evento.estado = 'completado'
                    elif hoy >= evento.fecha_inicio and hoy <= evento.fecha_fin:
                        evento.estado = 'en-curso'
                    else:
                        evento.estado = 'pendiente'
            
            db.session.commit()
            
            # Registrar la actividad del usuario
            activity = UserActivity(user_id=session['user_id'], action='Configuración guardada', timestamp=datetime.now())
            db.session.add(activity)
            db.session.commit()
            
            return jsonify({'success': True})
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error al guardar la configuración: {str(e)}')
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500

    return jsonify({'success': False, 'message': 'Método no permitido'}), 405