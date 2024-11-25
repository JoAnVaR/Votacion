from flask import Blueprint, render_template, request, jsonify
from models import Estudiante, Candidato, Votacion
from extensions import db

votacion_bp = Blueprint('votacion', __name__)

@votacion_bp.route('/paso1', methods=['GET', 'POST'])
def paso1():
    return render_template('votacion/paso1.html')

@votacion_bp.route('/paso2', methods=['GET', 'POST'])
def paso2():
    return render_template('votacion/paso2.html')

@votacion_bp.route('/paso3', methods=['GET', 'POST'])
def paso3():
    return render_template('votacion/paso3.html')
