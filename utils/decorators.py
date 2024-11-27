from functools import wraps
from flask import jsonify
from models import EventoCalendario
from datetime import datetime

def verificar_acceso_ruta(ruta=None):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if EventoCalendario.sistema_bloqueado():
                return jsonify({
                    'success': False,
                    'message': 'El sistema está bloqueado'
                }), 403
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
