from flask import Flask
from models import ConfiguracionSistema

def create_app():
    app = Flask(__name__)
    
    # Configuración
    app.config['SECRET_KEY'] = 'tu_clave_secreta'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///votacion.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = 'static/uploads'
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
    
    @app.context_processor
    def inject_config():
        return {'config': ConfiguracionSistema.get_config()}
    
    return app