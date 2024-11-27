import os
from datetime import timedelta

# Configuración base
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')

# Configuración de la base de datos
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'instance', 'votacion.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Configuración de seguridad
SECRET_KEY = 'tu_clave_secreta_aqui'  # Cambiar en producción
SESSION_COOKIE_SECURE = False  # Cambiar a True en producción
PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

# Configuración de archivos
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max-limit
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Configuración del sistema
ITEMS_PER_PAGE = 10
MAX_ESTUDIANTES_POR_MESA = 30
CONFIGURACION_FINALIZADA = False

# Estados del sistema
SISTEMA_BLOQUEADO = False
CALENDARIO_BLOQUEADO = False
FASE_ACTUAL = 1

