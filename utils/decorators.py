from functools import wraps
from flask import jsonify, request, flash, redirect, url_for
from models import Configuracion, EventoCalendario
from datetime import datetime
from utils.calendar_mappings import ACTIVITY_ROUTES

def verificar_acceso_ruta(ruta=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            config = Configuracion.query.first()
            if config and config.configuracion_finalizada:
                # Verificar si la ruta está permitida según el calendario
                for actividad, rutas in ACTIVITY_ROUTES.items():
                    if ruta in rutas:
                        evento = EventoCalendario.query.filter_by(titulo=actividad).first()
                        if evento:
                            ahora = datetime.now()
                            fecha_inicio = evento.fecha_inicio.replace(hour=0, minute=0, second=0)
                            fecha_fin = evento.fecha_fin.replace(hour=23, minute=59, second=59)
                            
                            if fecha_inicio <= ahora <= fecha_fin:
                                return f(*args, **kwargs)
                
                # Si no está permitido
                if request.method == 'POST':
                    return jsonify({
                        'success': False,
                        'message': 'Esta sección no está disponible en este momento'
                    }), 403
                
                # Para solicitudes GET, redirigir al index
                #flash('Esta sección no está disponible en este momento según el calendario electoral.', 'warning')
                #return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def fase_requerida(fase_numero):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            eventos = EventoCalendario.query.filter_by(fase=fase_numero).all()
            ahora = datetime.now()
            fase_activa = any(
                evento.fecha_inicio <= ahora <= evento.fecha_fin
                for evento in eventos
            )
            if not fase_activa:
                return jsonify({
                    'success': False,
                    'message': f'La fase {fase_numero} no está activa'
                }), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
