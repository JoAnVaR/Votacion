from flask import Blueprint, flash, redirect, render_template, request, jsonify, current_app, url_for
from extensions import db
from models import Candidato, Estudiante
from werkzeug.utils import secure_filename
import os
from routes.calendario_routes import verificar_acceso
from utils.decorators import verificar_acceso_ruta

candidato_bp = Blueprint('candidato', __name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

# Ruta para Registro de Candidatos
@candidato_bp.route('/registro-candidato', methods=['GET', 'POST'])
def registro_candidato():
    if request.method == 'POST':
        try:
            # Verificar acceso aquí
            if not verificar_acceso():
                return jsonify({
                    'success': False,
                    'message': 'No tienes permiso para realizar esta acción'
                }), 403
                
            id_estudiante = request.form['id_estudiante']
            propuesta = request.form['propuesta']
            file = request.files['foto']
            estudiante = Estudiante.query.get(id_estudiante)
            
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{estudiante.numero_documento}.{file.filename.rsplit('.', 1)[1].lower()}")
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)

                nuevo_candidato = Candidato(
                    numero_documento=estudiante.numero_documento, 
                    nombre=estudiante.nombre, 
                    grado=estudiante.grado, 
                    seccion=estudiante.seccion, 
                    propuesta=propuesta,
                    foto_path=f"uploads/{filename}"
                )
                db.session.add(nuevo_candidato)
                estudiante.es_candidato = True
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'message': 'Candidato registrado exitosamente'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Archivo no permitido o no subido correctamente'
                })
                
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': str(e)
            }), 500
    
    estudiantes = Estudiante.query.filter_by(es_candidato=False).all()
    candidatos = Candidato.query.all()
    return render_template('registro_candidato.html', estudiantes=estudiantes, candidatos=candidatos)

# Ruta para eliminar de Candidatos
@candidato_bp.route('/eliminar_candidato/<int:id>', methods=['POST'])
def eliminar_candidato(id):
    try:
        candidato = Candidato.query.get(id)
        if candidato:
            # Eliminar el archivo de la foto
            if candidato.foto_path:
                # Construir la ruta completa del archivo
                file_path = os.path.join(current_app.root_path, 'static', candidato.foto_path)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Error al eliminar archivo: {str(e)}")

            # Eliminar el candidato y actualizar el estado del estudiante
            estudiante = Estudiante.query.filter_by(numero_documento=candidato.numero_documento).first()
            if estudiante:
                estudiante.es_candidato = False

            db.session.delete(candidato)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Candidato eliminado exitosamente'
            })
        return jsonify({
            'success': False,
            'message': 'Candidato no encontrado'
        }), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error al eliminar candidato: {str(e)}'
        }), 500

def verificar_acceso(ruta=None):
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json()
            ruta = data.get('ruta')
        else:
            ruta = 'candidato.registro_candidato'
    return True  # Aquí va tu lógica de verificación
