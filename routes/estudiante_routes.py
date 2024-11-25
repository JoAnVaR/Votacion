from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, make_response
from models import Estudiante, Sede
import csv
import io
from extensions import db
from utils.decorators import check_configuracion_abierta
estudiante_bp = Blueprint('estudiante', __name__)

# Ruta para contar numero de estudiantes
@estudiante_bp.route('/numero_estudiantes', methods=['GET'])
def numero_estudiantes():
    grados = request.args.get('grados')
    if grados:
        grados_lista = grados.split(',')
        print(f"Grados recibidos: {grados_lista}")

        # Filtrar estudiantes por grados, excluyendo candidatos
        estudiantes = Estudiante.query.filter(
            Estudiante.grado.in_(grados_lista),
            Estudiante.es_candidato == False
        ).all()

        print(f"Estudiantes encontrados: {len(estudiantes)}")
        for estudiante in estudiantes:
            print(f"Estudiante: {estudiante.nombre}, Documento: {estudiante.numero_documento}, Grado: {estudiante.grado}")

        return jsonify({"numero_estudiantes": len(estudiantes)})

    return jsonify({"error": "Grados no especificados"}), 400

# Ruta para registro de estudiantes
@estudiante_bp.route('/registro_estudiante', methods=['GET', 'POST'])
@check_configuracion_abierta
def registro_estudiante():
    if request.method == 'GET':
        # Obtener todas las sedes para el select
        sedes = Sede.query.all()
        return render_template('registro_estudiante.html', sedes=sedes)
    
    try:
        numero_documento = request.form['numero_documento']
        
        # Verificar si ya existe
        if Estudiante.query.filter_by(numero_documento=numero_documento).first():
            return jsonify({
                'success': False,
                'message': f"El número de documento '{numero_documento}' ya existe"
            })

        nuevo_estudiante = Estudiante(
            numero_documento=numero_documento,
            nombre=request.form['nombre'],
            grado=request.form['grado'],
            seccion=request.form['seccion'],
            sede_id=request.form['sede_id']
        )
        
        db.session.add(nuevo_estudiante)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Estudiante registrado exitosamente'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

# Ruta para descargar la plantilla
@estudiante_bp.route('/descargar_plantilla')
def descargar_plantilla():
    return send_file('plantilla_estudiantes.csv', as_attachment=True)

# Ruta para descargar la plantilla de estudiantes
@estudiante_bp.route('/descargar_plantilla_estudiante')
def descargar_plantilla_estudiante():
    # Crear un StringIO para escribir el CSV
    si = io.StringIO()
    writer = csv.writer(si)
    
    # Escribir los encabezados
    writer.writerow(['numero_documento', 'nombre', 'grado', 'seccion', 'sede'])
    
    # Obtener todas las sedes para el ejemplo
    sedes = Sede.query.all()
    sede_ejemplo = sedes[0].nombre if sedes else ''
    
    # Escribir una fila de ejemplo
    writer.writerow(['12345678', 'Nombre Ejemplo', '1', 'A o 1', sede_ejemplo])
    
    # Preparar la respuesta
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=plantilla_estudiantes.csv"
    output.headers["Content-type"] = "text/csv"
    return output

# Ruta para detallar estudiantes
@estudiante_bp.route('/detalle_grado_seccion/<grado>/<seccion>/<sede>')
def detalle_grado_seccion(grado, seccion, sede):
    try:
        estudiantes = Estudiante.query.join(Sede).filter(
            Estudiante.grado == grado,
            Estudiante.seccion == seccion,
            Sede.nombre == sede
        ).order_by(Estudiante.numero_documento).all()
        
        return render_template(
            'detalle_grado_seccion.html',
            estudiantes=estudiantes,
            grado=grado,
            seccion=seccion,
            sede=sede
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error al obtener detalles: {str(e)}'
        }), 500

@estudiante_bp.route('/cargar_csv', methods=['POST'])
def cargar_csv():
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
            
            estudiantes_nuevos = []
            errores = []
            linea = 2  # Empezamos en 2 porque la línea 1 son los encabezados

            for row in csv_input:
                # Verificar que la sede existe
                sede_nombre = row.get('sede', '').lower().strip()
                if sede_nombre not in sedes_dict:
                    errores.append(f'Línea {linea}: La sede "{row.get("sede")}" no existe')
                    continue

                # Verificar que todos los campos requeridos estén presentes y no estén vacíos
                campos_requeridos = ['numero_documento', 'nombre', 'grado', 'seccion', 'sede']
                campos_faltantes = [campo for campo in campos_requeridos if not row.get(campo, '').strip()]
                
                if campos_faltantes:
                    errores.append(f'Línea {linea}: Faltan los campos: {", ".join(campos_faltantes)}')
                    continue

                # Verificar si el estudiante ya existe
                if Estudiante.query.filter_by(numero_documento=row['numero_documento'].strip()).first():
                    errores.append(f'Línea {linea}: Ya existe un estudiante con el documento {row["numero_documento"]}')
                    continue

                estudiante = Estudiante(
                    numero_documento=row['numero_documento'].strip(),
                    nombre=row['nombre'].strip(),
                    grado=row['grado'].strip(),
                    seccion=row['seccion'].strip(),
                    sede_id=sedes_dict[sede_nombre]
                )
                estudiantes_nuevos.append(estudiante)
                linea += 1

            if errores:
                return jsonify({
                    'success': False,
                    'message': 'Se encontraron errores en el archivo CSV:\n' + '\n'.join(errores)
                })

            # Si no hay errores, guardar todos los estudiantes
            if estudiantes_nuevos:
                db.session.bulk_save_objects(estudiantes_nuevos)
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
                'message': f'Error al procesar el archivo: {str(e)}\nPor favor, asegúrese de que el archivo esté en formato CSV válido y use codificación UTF-8.'
            })

    return jsonify({
        'success': False,
        'message': 'Formato de archivo no válido. Por favor, use un archivo CSV'
    })

@estudiante_bp.route('/obtener_estadisticas')
def obtener_estadisticas():
    try:
        # Total de estudiantes
        total_estudiantes = Estudiante.query.count()
        
        # Totales por sede
        totales_por_sede = db.session.query(
            Sede.nombre, 
            db.func.count(Estudiante.id)
        ).join(
            Sede, 
            Estudiante.sede_id == Sede.id
        ).group_by(
            Sede.nombre
        ).all()
        
        # Totales por grado y sección
        totales_por_grado_seccion = db.session.query(
            Estudiante.grado,
            Estudiante.seccion,
            Sede.nombre,
            db.func.count(Estudiante.id)
        ).join(
            Sede,
            Estudiante.sede_id == Sede.id
        ).group_by(
            Estudiante.grado,
            Estudiante.seccion,
            Sede.nombre
        ).order_by(
            Sede.nombre,
            db.cast(Estudiante.grado, db.Integer),  # Convertir a número para ordenar
            Estudiante.seccion
        ).all()
        
        # Renderizar el template parcial
        html = render_template(
            'estadisticas_partial.html',
            total_estudiantes=total_estudiantes,
            totales_por_sede=totales_por_sede,
            totales_por_grado_seccion=totales_por_grado_seccion
        )
        
        return jsonify({'html': html})
        
    except Exception as e:
        print(f"Error en obtener_estadisticas: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al obtener estadísticas: {str(e)}'
        }), 500

@estudiante_bp.route('/modificar_estudiante', methods=['POST'])
@check_configuracion_abierta
def modificar_estudiante():
    try:
        print("Iniciando modificación de estudiante")
        print("Datos recibidos:", request.form)
        
        estudiante_id = request.form.get('estudiante_id')
        nuevo_documento = request.form.get('numero_documento')
        nuevo_nombre = request.form.get('nombre')
        
        if not all([estudiante_id, nuevo_documento, nuevo_nombre]):
            return jsonify({
                'success': False,
                'message': 'Faltan datos requeridos'
            }), 400

        estudiante = Estudiante.query.get_or_404(estudiante_id)
        print(f"Estudiante encontrado: {estudiante.nombre}")
        
        # Verificar si el nuevo número de documento ya existe
        if nuevo_documento != estudiante.numero_documento:
            existe = Estudiante.query.filter(
                Estudiante.numero_documento == nuevo_documento,
                Estudiante.id != estudiante.id
            ).first()
            
            if existe:
                return jsonify({
                    'success': False,
                    'message': f'El número de documento {nuevo_documento} ya existe'
                }), 400
        
        # Actualizar datos
        estudiante.nombre = nuevo_nombre
        estudiante.numero_documento = nuevo_documento
        
        print(f"Actualizando estudiante a: {nuevo_nombre}, {nuevo_documento}")
        
        db.session.commit()
        print("Cambios guardados exitosamente")
        
        return jsonify({
            'success': True,
            'message': 'Estudiante actualizado exitosamente',
            'estudiante': {
                'id': estudiante.id,
                'nombre': estudiante.nombre,
                'numero_documento': estudiante.numero_documento
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error al modificar estudiante: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'Error al modificar estudiante: {str(e)}'
        }), 500

@estudiante_bp.route('/eliminar_estudiante', methods=['POST'])
@check_configuracion_abierta
def eliminar_estudiante():
    try:
        estudiante_id = request.form['estudiante_id']
        estudiante = Estudiante.query.get_or_404(estudiante_id)
        db.session.delete(estudiante)
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
