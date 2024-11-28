from functools import wraps
from flask import jsonify, request
from models import Configuracion, EventoCalendario
from datetime import datetime
from utils.calendar_mappings import ACTIVITY_ROUTES

def verificar_acceso_ruta(ruta=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            config = Configuracion.query.first()
            if config and config.configuracion_finalizada:
                # Si es una solicitud AJAX, devolver respuesta JSON
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({
                        'success': False,
                        'message': 'Esta sección no está disponible en este momento'
                    }), 403
                
                # Para solicitudes normales, permitir el acceso pero con elementos deshabilitados
                return f(*args, **kwargs)
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
