import os
from flask import Flask, render_template
from routes import all_blueprints
from extensions import db
from models import EventoCalendario, ConfiguracionSistema
import json

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

# Registrar todos los blueprints
for blueprint in all_blueprints:
    app.register_blueprint(blueprint)

@app.context_processor
def inject_config():
    """Inyecta la configuración del sistema en todos los templates"""
    config = ConfiguracionSistema.get_config()
    eventos = EventoCalendario.query.all()
    config_data = {
        'sistema_bloqueado': EventoCalendario.sistema_bloqueado(),
        'fase_actual': EventoCalendario.obtener_fase_actual(),
        'configuracion_finalizada': config.configuracion_finalizada,
        'calendario_bloqueado': config.calendario_bloqueado,
        'fecha_finalizacion': config.fecha_finalizacion.strftime('%d/%m/%Y %H:%M') if config.fecha_finalizacion else None,
        'preparacion_finalizada': False
    }
    return {
        'config': config_data,
        'config_json': json.dumps(config_data, default=str)
    }

@app.route('/')
def index():
    return render_template('index.html')

# Inicializar la base de datos
with app.app_context():
    db.create_all()
    EventoCalendario.crear_calendario_default()
    ConfiguracionSistema.get_config()  # Asegura que existe la configuración inicial

if __name__ == '__main__':
    app.run(debug=True)