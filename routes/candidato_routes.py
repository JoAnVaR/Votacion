from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from extensions import db
from models import Candidato, Estudiante
from werkzeug.utils import secure_filename
import os

candidato_bp = Blueprint('candidato', __name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

# Ruta para Registro de Candidatos
@candidato_bp.route('/registro_candidato', methods=['GET', 'POST'])
def registro_candidato():
    if request.method == 'POST':
        id_estudiante = request.form['id_estudiante']
        propuesta = request.form['propuesta']

        # Manejo de la subida de la foto
        file = request.files['foto']
        estudiante = Estudiante.query.get(id_estudiante)
        if file and allowed_file(file.filename):
            # Renombrar el archivo con el número de documento del estudiante
            filename = secure_filename(f"{estudiante.numero_documento}.{file.filename.rsplit('.', 1)[1].lower()}")
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

            # Guardar el nuevo candidato en la base de datos
            nuevo_candidato = Candidato(
                numero_documento=estudiante.numero_documento, 
                nombre=estudiante.nombre, 
                grado=estudiante.grado, 
                seccion=estudiante.seccion, 
                propuesta=propuesta,
                foto_path=f"uploads/{filename}"  # Guardamos la ruta relativa de la foto en la base de datos
            )
            db.session.add(nuevo_candidato)
            estudiante.es_candidato = True
            db.session.commit()

            flash('Candidato registrado exitosamente')
            return redirect(url_for('registro_candidato'))
        else:
            flash('Archivo no permitido o no subido correctamente')
    
    # Manejar búsqueda
    search_query = request.args.get('search_query')
    if search_query:
        estudiantes = Estudiante.query.filter(Estudiante.es_candidato == False, 
                                              (Estudiante.nombre.contains(search_query) | 
                                               Estudiante.numero_documento.contains(search_query))).all()
    else:
        estudiantes = Estudiante.query.filter_by(es_candidato=False).all()
    
    candidatos = Candidato.query.all()  # Obtener la lista de candidatos registrados
    
    return render_template('registro_candidato.html', estudiantes=estudiantes, candidatos=candidatos, search_query=search_query)

# Ruta para eliminar de Candidatos
@candidato_bp.route('/eliminar_candidato/<int:id>', methods=['POST'])
def eliminar_candidato(id):
    candidato = Candidato.query.get(id)
    if candidato:
        # Eliminar el archivo de la foto
        if candidato.foto_path:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], candidato.foto_path.split('/')[-1])
            if os.path.exists(file_path):
                os.remove(file_path)

        # Eliminar el candidato, pero mantener el estado de estudiante para permitir la reactivación
        estudiante = Estudiante.query.filter_by(numero_documento=candidato.numero_documento).first()
        if estudiante:
            estudiante.es_candidato = False

        db.session.delete(candidato)
        db.session.commit()
        flash('Candidato eliminado exitosamente')
    return redirect(url_for('registro_candidato'))
