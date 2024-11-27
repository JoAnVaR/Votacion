from flask import Blueprint, render_template, request, jsonify, session, flash, redirect, url_for
from models import Estudiante, Candidato, Votacion, Mesa, AsignacionMesa
from extensions import db
from datetime import datetime
from utils.decorators import fase_requerida

votacion_bp = Blueprint('votacion', __name__)

@votacion_bp.route('/paso1', methods=['GET', 'POST'])
@fase_requerida(3)
def paso1():
    if request.method == 'POST':
        documento = request.form.get('documento')
        estudiante = Estudiante.query.filter_by(numero_documento=documento).first()
        
        if not estudiante:
            flash('Documento no encontrado', 'error')
            return redirect(url_for('votacion.paso1'))
            
        # Verificar si el estudiante ya votó
        if Votacion.query.filter_by(estudiante_id=estudiante.id).first():
            flash('Este estudiante ya ha votado', 'error')
            return redirect(url_for('votacion.paso1'))
            
        session['votante_id'] = estudiante.id
        return redirect(url_for('votacion.paso2'))
        
    return render_template('votacion/paso1.html')

@votacion_bp.route('/paso2', methods=['GET', 'POST'])
def paso2():
    if 'votante_id' not in session:
        return redirect(url_for('votacion.paso1'))
        
    if request.method == 'POST':
        candidato_id = request.form.get('candidato_id')
        if not candidato_id:
            flash('Debe seleccionar un candidato', 'error')
            return redirect(url_for('votacion.paso2'))
            
        session['candidato_id'] = candidato_id
        return redirect(url_for('votacion.paso3'))
        
    candidatos = Candidato.query.all()
    return render_template('votacion/paso2.html', candidatos=candidatos)

@votacion_bp.route('/paso3', methods=['GET', 'POST'])
def paso3():
    if 'votante_id' not in session or 'candidato_id' not in session:
        return redirect(url_for('votacion.paso1'))
        
    if request.method == 'POST':
        try:
            votacion = Votacion(
                estudiante_id=session['votante_id'],
                candidato_id=session['candidato_id'],
                fecha=datetime.now()
            )
            db.session.add(votacion)
            db.session.commit()
            
            # Limpiar sesión
            session.pop('votante_id', None)
            session.pop('candidato_id', None)
            
            flash('Voto registrado exitosamente', 'success')
            return redirect(url_for('votacion.paso1'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error al registrar el voto', 'error')
            return redirect(url_for('votacion.paso3'))
            
    candidato = Candidato.query.get(session['candidato_id'])
    return render_template('votacion/paso3.html', candidato=candidato)
