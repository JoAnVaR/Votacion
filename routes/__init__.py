from flask import Blueprint

# Importar todos los blueprints
from .sede_routes import sede_bp
from .estudiante_routes import estudiante_bp
from .profesor_routes import profesor_bp
from .asignar_mesa_routes import asignar_mesa_bp
from .candidato_routes import candidato_bp
from .jurado_routes import jurado_bp
from .testigo_routes import testigo_bp
from .votacion_routes import votacion_bp
from .estadisticas_routes import estadisticas_bp
from .calendario_routes import calendario_bp
from .auth_routes import auth_bp

# Lista de todos los blueprints para fácil importación
all_blueprints = [
    sede_bp,
    estudiante_bp,
    profesor_bp,
    asignar_mesa_bp,
    candidato_bp,
    jurado_bp,
    testigo_bp,
    votacion_bp,
    estadisticas_bp,
    calendario_bp,
    auth_bp
]