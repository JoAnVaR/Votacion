from flask import Blueprint, render_template, request, jsonify
from models import Estudiante, Sede
from extensions import db
from utils.decorators import verificar_acceso_ruta

estudiante_bp = Blueprint('estudiante', __name__)

@estudiante_bp.route('/registro-estudiante')
@verificar_acceso_ruta('estudiante.registro_estudiante')
def registro_estudiante():
    sedes = Sede.query.all()
    return render_template('registro_estudiante.html', sedes=sedes)
