import os
from flask import Flask, render_template, json, session, redirect, url_for, g
from functools import wraps
from routes import all_blueprints
from extensions import db
from models import EventoCalendario, User
from datetime import datetime

app = Flask(__name__, instance_relative_config=True)
app.config.from_object('config')


# Asegurarse que la carpeta instance existe
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

# Crear directorio de uploads si no existe
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db.init_app(app)

with app.app_context():
    db.create_all()
    print("Base de datos inicializada")
    User.crear_usuario_default()
    print("Usuario administrador creado")

# Registrar todos los blueprints
for blueprint in all_blueprints:
    app.register_blueprint(blueprint)

@app.before_request
def before_request():
    g.user = None
    if 'user_id' in session:
        g.user = db.session.get(User, session['user_id'])

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_config():
    """Inyecta la configuración del sistema en todos los templates"""
    sistema_bloqueado = EventoCalendario.sistema_bloqueado()
    config = {
        'sistema_bloqueado': sistema_bloqueado,
        'calendario_bloqueado': sistema_bloqueado,
        'fase_actual': EventoCalendario.obtener_fase_actual(),
        'configuracion_finalizada': sistema_bloqueado,
        'fecha_finalizacion': datetime.now() if sistema_bloqueado else None
    }
    return {
        'config': config,
        'config_json': json.dumps(config, default=str)
    }

@app.route('/')
@login_required
def index():
    return render_template('index.html', title='Inicio')

# Inicializar la base de datos
with app.app_context():
    db.create_all()
    print("Base de datos inicializada")
    EventoCalendario.crear_calendario_default()
    print("Calendario por defecto creado")

@app.context_processor
def utility_processor():
    return {
        'now': datetime.now
    }

if __name__ == '__main__':
    app.run(debug=True)