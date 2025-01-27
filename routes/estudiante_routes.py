from flask import Blueprint, render_template, request, jsonify, send_file, render_template_string, session
from models import Estudiante, Sede, UserActivity
from extensions import db
from utils.decorators import verificar_acceso_ruta, login_required
import io
import csv
from sqlalchemy import func

estudiante_bp = Blueprint('estudiante', __name__)

@estudiante_bp.route('/registro-estudiante', methods=['GET', 'POST'])
@login_required
@verificar_acceso_ruta('estudiante.registro_estudiante')
def registro_estudiante():
    if request.method == 'POST':
        try:
            data = request.form
            print("Datos recibidos en el servidor:", data)  # Para depurar
            print(data)  # Para depurar los datos recibidos
            
            # Verificar si todos los campos requeridos están presentes
            required_fields = ['numero_documento', 'nombre', 'grado', 'seccion', 'sede_id']
            for field in required_fields:
                if field not in data:
                    print(f"Falta el campo requerido: {field}")  # Para depurar
                    return jsonify({'success': False, 'message': f'Falta el campo requerido: {field}'}), 400

            # Verificar si ya existe un estudiante con ese número de documento
            estudiante_existente = Estudiante.query.filter_by(
                numero_documento=data['numero_documento']
            ).first()
            
            if estudiante_existente:
                print("El estudiante ya existe en la base de datos.")  # Para depurar
                return jsonify({
                    'success': False,
                    'message': 'Ya existe un estudiante con ese número de documento'
                }), 400

            try:
                # Verificar si el número de documento es único
                if Estudiante.query.filter_by(numero_documento=data['numero_documento']).first():
                    print("El número de documento ya existe en la base de datos.")  # Para depurar
                    return jsonify({
                        'success': False,
                        'message': 'El número de documento ya existe en la base de datos'
                    }), 400
            except Exception as e:
                print(f"Error al verificar número de documento: {str(e)}")  # Para debugging
                return jsonify({
                    'success': False,
                    'message': f"Error al verificar número de documento: {str(e)}"
                }), 400

            print(f"Intentando registrar: {data['numero_documento']}")  # Para depurar antes de la inserción
            print("Intentando registrar estudiante:", data)  # Para depurar
            estudiante = Estudiante(
                numero_documento=data['numero_documento'],
                nombre=data['nombre'],
                grado=data['grado'],
                seccion=data['seccion'],
                sede_id=data['sede_id']
            )
            print("Estudiante creado:", estudiante)  # Para depurar
            db.session.add(estudiante)
            db.session.commit()

            # Registrar la actividad del usuario
            activity = UserActivity(user_id=session['user_id'], action='Estudiante registrado: ' + estudiante.numero_documento)
            db.session.add(activity)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Estudiante registrado exitosamente'
            })
            
        except Exception as e:
            db.session.rollback()
            print(f"Error al registrar estudiante: {str(e)}")  # Para debugging
            print("Error al registrar estudiante:", e)  # Para debugging
            return jsonify({
                'success': False,
                'message': f"Error al registrar estudiante: {str(e)}"
            }), 400
    
    # Si es GET, renderizar el template
    sedes = Sede.query.all()
    return render_template('registro_estudiante.html', sedes=sedes)

@estudiante_bp.route('/cargar-csv', methods=['POST'])
@login_required
def cargar_csv():
    try:
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No se seleccionó ningún archivo'
            })
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': 'No se seleccionó ningún archivo'
            })

        sedes = Sede.query.all()
        if not sedes:
            return jsonify({
                'success': False,
                'message': 'No hay sedes registradas. Por favor, registre al menos una sede primero.'
            })

        sedes_dict = {sede.nombre.lower(): sede.id for sede in sedes}

        if file and file.filename.endswith('.csv'):
            try:
                content = file.read()
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

                stream = io.StringIO(decoded_content)
                csv_input = csv.DictReader(stream)
                
                estudiantes_nuevos = []
                errores = []
                linea = 2

                for row in csv_input:
                    # Verificar que la sede existe
                    sede_nombre = row.get('sede', '').lower().strip()
                    if sede_nombre not in sedes_dict:
                        errores.append(f'Línea {linea}: La sede "{row.get("sede")}" no existe')
                        continue

                    # Verificar campos requeridos
                    campos_requeridos = ['numero_documento', 'nombre', 'grado', 'seccion', 'sede']
                    campos_faltantes = [campo for campo in campos_requeridos if not row.get(campo, '').strip()]
                    
                    if campos_faltantes:
                        errores.append(f'Línea {linea}: Faltan los campos: {", ".join(campos_faltantes)}')
                        continue

                    # Verificar si el estudiante ya existe
                    if Estudiante.query.filter_by(numero_documento=row['numero_documento'].strip()).first():
                        errores.append(f'Línea {linea}: Ya existe un estudiante con el documento {row["numero_documento"]}')
                        continue

                    try:
                        estudiante = Estudiante(
                            numero_documento=row['numero_documento'].strip(),
                            nombre=row['nombre'].strip(),
                            grado=row['grado'].strip(),
                            seccion=row['seccion'].strip(),
                            sede_id=sedes_dict[sede_nombre]  # Convertir nombre de sede a ID
                        )
                        estudiantes_nuevos.append(estudiante)
                    except Exception as e:
                        errores.append(f'Línea {linea}: {str(e)}')
                    
                    linea += 1

                if errores:
                    return jsonify({
                        'success': False,
                        'message': 'Se encontraron errores en el archivo CSV:\n' + '\n'.join(errores)
                    })

                if estudiantes_nuevos:
                    db.session.bulk_save_objects(estudiantes_nuevos)
                    db.session.commit()

                    # Registrar la actividad del usuario
                    activity = UserActivity(user_id=session['user_id'], action='Estudiante cargados CSV')
                    db.session.add(activity)
                    db.session.commit()

                    return jsonify({
                        'success': True,
                        'message': f'Se registraron {len(estudiantes_nuevos)} estudiantes exitosamente'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'No se encontraron estudiantes válidos para registrar'
                    })

            except Exception as e:
                db.session.rollback()
                return jsonify({
                    'success': False,
                    'message': f'Error al procesar el archivo: {str(e)}'
                })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@estudiante_bp.route('/descargar-plantilla-estudiante')
@login_required
def descargar_plantilla_estudiante():
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Cambiar sede_id por sede en los encabezados
    writer.writerow(['numero_documento', 'nombre', 'grado', 'seccion', 'sede'])
    
    # Ejemplo usando nombre de sede en lugar de ID
    writer.writerow(['12345678', 'Nombre Apellido', '11', 'A', 'Sede Principal'])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name='plantilla_estudiantes.csv'
    )

@estudiante_bp.route('/obtener_estadisticas')
@login_required
def obtener_estadisticas():
    try:
        # Obtener estadísticas de estudiantes por sede
        totales_por_sede = db.session.query(
            Sede.nombre,
            func.count(Estudiante.id).label('total')
        ).outerjoin(
            Estudiante, Sede.id == Estudiante.sede_id
        ).group_by(Sede.id, Sede.nombre).all()

        # Obtener total de estudiantes
        total_estudiantes = Estudiante.query.count()

        # Obtener totales por grado y sección
        totales_por_grado_seccion = db.session.query(
            Estudiante.grado,
            Estudiante.seccion,
            Sede.nombre,
            func.count(Estudiante.id).label('total')
        ).join(
            Sede, Estudiante.sede_id == Sede.id
        ).group_by(
            Estudiante.grado,
            Estudiante.seccion,
            Sede.nombre
        ).all()

        # Renderizar el template con las estadísticas
        html = render_template('estadisticas_partial.html',
                             total_estudiantes=total_estudiantes,
                             totales_por_sede=totales_por_sede,
                             totales_por_grado_seccion=totales_por_grado_seccion)

        return jsonify({
            'success': True,
            'html': html
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })

@estudiante_bp.route('/detalle-grado-seccion/<grado>/<seccion>/<sede>')
@login_required
@verificar_acceso_ruta('estudiante.detalle_grado_seccion')
def detalle_grado_seccion(grado, seccion, sede):
    try:
        # Obtener la sede_id basado en el nombre de la sede
        sede_obj = Sede.query.filter_by(nombre=sede).first()
        if not sede_obj:
            return jsonify({
                'success': False,
                'message': 'Sede no encontrada'
            }), 404

        # Obtener estudiantes del grado, sección y sede específicos
        estudiantes = Estudiante.query.filter_by(
            grado=grado,
            seccion=seccion,
            sede_id=sede_obj.id
        ).all()

        return render_template('detalle_grado_seccion.html',
                             estudiantes=estudiantes,
                             grado=grado,
                             seccion=seccion,
                             sede=sede,
                             config={'configuracion_finalizada': False})
    except Exception as e:
        print(f"Error en detalle_grado_seccion: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@estudiante_bp.route('/eliminar-estudiante', methods=['POST'])
@login_required
@verificar_acceso_ruta('estudiante.eliminar_estudiante')
def eliminar_estudiante():
    try:
        estudiante_id = request.form.get('estudiante_id')
        estudiante = Estudiante.query.get_or_404(estudiante_id)
        
        db.session.delete(estudiante)
        db.session.commit()

        # Registrar la actividad del usuario
        activity = UserActivity(user_id=session['user_id'], action='Estudiante eliminado: ' + estudiante.numero_documento)
        db.session.add(activity)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Estudiante eliminado exitosamente'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@estudiante_bp.route('/modificar-estudiante', methods=['POST'])
@login_required
@verificar_acceso_ruta('estudiante.modificar_estudiante')
def modificar_estudiante():
    try:
        estudiante_id = request.form.get('estudiante_id')
        numero_documento = request.form.get('numero_documento')
        nombre = request.form.get('nombre')

        estudiante = Estudiante.query.get_or_404(estudiante_id)
        estudiante.numero_documento = numero_documento
        estudiante.nombre = nombre

        db.session.commit()

        # Registrar la actividad del usuario
        activity = UserActivity(user_id=session['user_id'], action='Estudiante modificado: ' + estudiante.numero_documento)
        db.session.add(activity)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Estudiante modificado exitosamente'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500
