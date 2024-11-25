from functools import wraps
from flask import flash, redirect, url_for
from models import ConfiguracionSistema

def check_configuracion_abierta(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        config = ConfiguracionSistema.get_config()
        if config.configuracion_finalizada:
            flash('La configuración del sistema está bloqueada.', 'warning')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function
