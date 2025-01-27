from flask import Blueprint, render_template, request, jsonify, send_file, make_response, session
from models import Profesor, Sede, UserActivity
import csv
import io
from extensions import db
from utils.decorators import verificar_acceso_ruta, login_required


profesor_bp = Blueprint('profesor', __name__)

@profesor_bp.route('/registro-profesor', methods=['GET', 'POST'])
@login_required
@verificar_acceso_ruta('profesor.registro_profesor')
def registro_profesor():
    if request.method == 'POST':
        try:
            if 'file' in request.files:
                file = request.files['file']
                if file.filename == '':
                    return jsonify({
                        'success': False,
                        'message': 'No se seleccionó ningún archivo'
                    })

                # Verificar si hay sedes registradas
                sedes = Sede.query.all()
                if not sedes:
                    return jsonify({
                        'success': False,
                        'message': 'No hay sedes registradas. Por favor, registre al menos una sede primero.'
                    })

                # Crear un diccionario de nombres de sedes y sus IDs
                sedes_dict = {sede.nombre.lower(): sede.id for sede in sedes}

                if file and file.filename.endswith('.csv'):
                    try:
                        # Leer el contenido del archivo
                        content = file.read()
                        
                        # Intentar diferentes codificaciones
                        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
                        decoded_content = None
                        
                        for encoding in encodings:
                            try:
                                decoded_content = content.decode(encoding)
                                break
                            except UnicodeDecodeError:
                                continue
                        
                        if decoded_content is None:
                            return jsonify({
                                'success': False,
                                'message': 'No se pudo decodificar el archivo. Por favor, guárdelo como UTF-8 o ISO-8859-1.'
                            })

                        # Procesar el CSV
                        stream = io.StringIO(decoded_content)
                        csv_input = csv.DictReader(stream)
                        
                        profesores_nuevos = []
                        errores = []
                        linea = 2  # Empezamos en 2 porque la línea 1 son los encabezados

                        for row in csv_input:
                            # Verificar que la sede existe
                            sede_nombre = row.get('sede', '').lower().strip()
                            if sede_nombre not in sedes_dict:
                                errores.append(f'Línea {linea}: La sede "{row.get("sede")}" no existe')
                                continue

                            # Verificar campos requeridos
                            campos_requeridos = ['numero_documento', 'nombre', 'departamento', 'titulo', 'sede']
                            campos_faltantes = [campo for campo in campos_requeridos if not row.get(campo, '').strip()]
                            
                            if campos_faltantes:
                                errores.append(f'Línea {linea}: Faltan los campos: {", ".join(campos_faltantes)}')
                                continue

                            # Verificar si el profesor ya existe
                            if Profesor.query.filter_by(numero_documento=row['numero_documento'].strip()).first():
                                errores.append(f'Línea {linea}: Ya existe un profesor con el documento {row["numero_documento"]}')
                                continue

                            profesor = Profesor(
                                numero_documento=row['numero_documento'].strip(),
                                nombre=row['nombre'].strip(),
                                departamento=row['departamento'].strip(),
                                titulo=row['titulo'].strip(),
                                sede_id=sedes_dict[sede_nombre]
                            )
                            profesores_nuevos.append(profesor)
                            linea += 1

                        if errores:
                            return jsonify({
                                'success': False,
                                'message': 'Se encontraron errores en el archivo CSV:\n' + '\n'.join(errores)
                            })

                        # Si no hay errores, guardar todos los profesores
                        if profesores_nuevos:
                            db.session.bulk_save_objects(profesores_nuevos)
                            db.session.commit()

                            # Registrar la actividad del usuario
                            activity = UserActivity(user_id=session['user_id'], action='Profesor registrado: ' + profesor.numero_documento)
                            db.session.add(activity)
                            db.session.commit()

                            return jsonify({
                                'success': True,
                                'message': f'Se registraron {len(profesores_nuevos)} profesores exitosamente'
                            })
                        else:
                            return jsonify({
                                'success': False,
                                'message': 'No se encontraron profesores válidos para registrar'
                            })

                    except Exception as e:
                        db.session.rollback()
                        return jsonify({
                            'success': False,
                            'message': f'Error al procesar el archivo: {str(e)}\nPor favor, asegúrese de que el archivo esté en formato CSV válido y use codificación UTF-8.'
                        })

                return jsonify({
                    'success': False,
                    'message': 'Formato de archivo no válido. Por favor, use un archivo CSV'
                })

            else:
                # Registro individual
                numero_documento = request.form['numero_documento']
                
                # Verificar si ya existe
                if Profesor.query.filter_by(numero_documento=numero_documento).first():
                    return jsonify({
                        'success': False,
                        'message': 'Ya existe un profesor con ese número de documento'
                    })

                nuevo_profesor = Profesor(
                    numero_documento=numero_documento,
                    nombre=request.form['nombre'],
                    departamento=request.form['departamento'],
                    titulo=request.form['titulo'],
                    sede_id=request.form['sede_id']
                )
                db.session.add(nuevo_profesor)
                db.session.commit()

                # Registrar la actividad del usuario
                activity = UserActivity(user_id=session['user_id'], action='Profesor registrado: ' + nuevo_profesor.numero_documento)
                db.session.add(activity)
                db.session.commit()

                return jsonify({
                    'success': True,
                    'message': 'Profesor registrado exitosamente'
                })

        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Error al procesar la solicitud: {str(e)}'
            }), 500

    # GET request
    sedes = Sede.query.all()
    return render_template('registro_profesor.html', sedes=sedes)

@profesor_bp.route('/descargar_plantilla_profesor')
@login_required
def descargar_plantilla_profesor():
    # Crear un StringIO para escribir el CSV
    si = io.StringIO()
    writer = csv.writer(si)
    
    # Escribir los encabezados
    writer.writerow(['numero_documento', 'nombre', 'departamento', 'titulo', 'sede'])
    
    # Obtener todas las sedes para el ejemplo
    sedes = Sede.query.all()
    sede_ejemplo = sedes[0].nombre if sedes else ''
    
    # Escribir una fila de ejemplo
    writer.writerow(['12345678', 'Nombre Ejemplo', 'Departamento Ejemplo', 'Título Ejemplo', sede_ejemplo])
    
    # Preparar la respuesta
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=plantilla_profesores.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@profesor_bp.route('/eliminar_profesor/<int:id>', methods=['POST'])
@login_required
def eliminar_profesor(id):
    try:
        profesor = Profesor.query.get_or_404(id)
        db.session.delete(profesor)
        db.session.commit()

        # Registrar la actividad del usuario
        activity = UserActivity(user_id=session['user_id'], action='Profesor eliminado: ' + profesor.numero_documento)
        db.session.add(activity)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Profesor eliminado exitosamente'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Error al eliminar profesor: {str(e)}'
        }), 500

@profesor_bp.route('/modificar_profesor/<int:id>', methods=['GET', 'POST'])
@login_required
@verificar_acceso_ruta('profesor.modificar_profesor')
def modificar_profesor(id):
    profesor = Profesor.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            # Verificar si el nuevo número de documento ya existe
            nuevo_documento = request.form['numero_documento']
            if nuevo_documento != profesor.numero_documento:
                profesor_existente = Profesor.query.filter_by(numero_documento=nuevo_documento).first()
                if profesor_existente:
                    return jsonify({
                        'success': False,
                        'message': 'Ya existe un profesor con ese número de documento'
                    })

            profesor.nombre = request.form['nombre']
            profesor.numero_documento = nuevo_documento
            profesor.departamento = request.form['departamento']
            profesor.titulo = request.form['titulo']
            profesor.sede_id = request.form['sede_id']

            db.session.commit()

            # Registrar la actividad del usuario
            activity = UserActivity(user_id=session['user_id'], action='Profesor modificado: ' + profesor.numero_documento)
            db.session.add(activity)
            db.session.commit()

            return jsonify({
                'success': True,
                'message': 'Profesor modificado exitosamente',
                'profesor': {
                    'id': profesor.id,
                    'nombre': profesor.nombre,
                    'numero_documento': profesor.numero_documento
                }
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'message': f'Error al modificar profesor: {str(e)}'
            }), 500

    # GET request
    sedes = Sede.query.all()
    return render_template('modificar_profesor.html', profesor=profesor, sedes=sedes)

@profesor_bp.route('/obtener_estadisticas_profesores')
@login_required
def obtener_estadisticas():
    try:
        # Total de profesores
        total_profesores = Profesor.query.count()
        
        # Totales por sede
        totales_por_sede = db.session.query(
            Sede.nombre,
            db.func.count(Profesor.id).label('total')
        ).outerjoin(
            Profesor,
            Sede.id == Profesor.sede_id
        ).group_by(Sede.nombre).all()

        # Totales por departamento
        totales_por_departamento = db.session.query(
            Profesor.departamento,
            Sede.nombre,
            db.func.count(Profesor.id).label('total')
        ).join(
            Sede,
            Profesor.sede_id == Sede.id
        ).group_by(
            Profesor.departamento,
            Sede.nombre
        ).all()

        html = render_template(
            'estadisticas_profesores_partial.html',
            total_profesores=total_profesores,
            totales_por_sede=totales_por_sede,
            totales_por_departamento=totales_por_departamento
        )

        return jsonify({
            'success': True,
            'html': html
        })

    except Exception as e:
        print(f"Error en obtener_estadisticas: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@profesor_bp.route('/detalle_sede/<sede>')
@login_required
def detalle_sede(sede):
    try:
        profesores = Profesor.query.join(Sede).filter(
            Sede.nombre == sede
        ).all()
        
        return render_template(
            'detalle_sede.html',
            sede=sede,
            profesores=profesores
        )
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@profesor_bp.route('/actualizar_profesor', methods=['POST'])
@login_required
@verificar_acceso_ruta('profesor.actualizar_profesor')
def actualizar_profesor():
    try:
        profesor_id = request.form['profesor_id']
        profesor = Profesor.query.get_or_404(profesor_id)
        
        nuevo_documento = request.form['numero_documento']
        if nuevo_documento != profesor.numero_documento:
            existe = Profesor.query.filter_by(numero_documento=nuevo_documento).first()
            if existe:
                return jsonify({
                    'success': False,
                    'message': 'Ya existe un profesor con ese número de documento'
                })

        profesor.numero_documento = nuevo_documento
        profesor.nombre = request.form['nombre']
        profesor.departamento = request.form['departamento']
        profesor.titulo = request.form['titulo']
        
        db.session.commit()

        # Registrar la actividad del usuario
        activity = UserActivity(user_id=session['user_id'], action='Profesor modificado: ' + profesor.numero_documento)
        db.session.add(activity)
        db.session.commit()

        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@profesor_bp.route('/borrar_profesor', methods=['POST'])
@login_required
@verificar_acceso_ruta('profesor.borrar_profesor')
def borrar_profesor():
    try:
        profesor_id = request.form['profesor_id']
        profesor = Profesor.query.get_or_404(profesor_id)
        db.session.delete(profesor)
        db.session.commit()

        # Registrar la actividad del usuario
        activity = UserActivity(user_id=session['user_id'], action='Profesor eliminado: ' + profesor.numero_documento)
        db.session.add(activity)
        db.session.commit()

        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500