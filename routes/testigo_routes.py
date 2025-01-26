from flask import Blueprint, request, jsonify, url_for, send_file, render_template, make_response
from models import db, AsignacionTestigo, Sede, Mesa, Candidato
import csv
import io
from utils.decorators import verificar_acceso_ruta

testigo_bp = Blueprint('testigo', __name__)

@testigo_bp.route('/registro-testigo', methods=['GET', 'POST'])
@verificar_acceso_ruta('testigo.registro_testigo')
def registro_testigo():
    if request.method == 'POST':
        if 'file' in request.files:
            # Procesar archivo CSV
            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'message': 'No se seleccionó ningún archivo'})
            
            try:
                # Leer el archivo CSV
                stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
                csv_reader = csv.DictReader(stream)
                
                for row in csv_reader:
                    testigo = AsignacionTestigo(
                        numero_documento=str(row['numero_documento']),
                        nombre=row['nombre'],
                        sede_id=int(row['sede_id']),
                        mesa_id=int(row['mesa_id']),
                        candidato_id=int(row['candidato_id']) if row.get('candidato_id') else None,
                        es_blanco=row.get('es_blanco', '').lower() == 'true',
                        es_otro=row.get('es_otro', '').lower() == 'true'
                    )
                    db.session.add(testigo)
                db.session.commit()
                return jsonify({'success': True, 'message': 'Testigos registrados exitosamente'})
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Error al procesar el archivo: {str(e)}'})
        else:
            # Registro individual
            try:
                numero_documento = request.form.get('numero_documento')
                nombre = request.form.get('nombre')
                sede_id = request.form.get('sede_id')
                mesas_ids = request.form.getlist('mesas_ids[]')
                candidato_id = request.form.get('candidato_id')
                es_blanco = request.form.get('es_blanco') == 'true'
                es_otro = request.form.get('es_otro') == 'true'
                
                # Validar que solo se seleccione una opción
                opciones_seleccionadas = sum([1 for x in [candidato_id, es_blanco, es_otro] if x])
                if opciones_seleccionadas != 1:
                    return jsonify({'success': False, 'message': 'Debe seleccionar exactamente una opción: candidato, voto en blanco u otro'})
                
                for mesa_id in mesas_ids:
                    testigo = AsignacionTestigo(
                        numero_documento=numero_documento,
                        nombre=nombre,
                        sede_id=sede_id,
                        mesa_id=mesa_id,
                        candidato_id=candidato_id if candidato_id else None,
                        es_blanco=es_blanco,
                        es_otro=es_otro
                    )
                    db.session.add(testigo)
                db.session.commit()
                return jsonify({'success': True, 'message': 'Testigo registrado exitosamente'})
            except Exception as e:
                db.session.rollback()
                return jsonify({'success': False, 'message': f'Error al registrar el testigo: {str(e)}'})
    
    # GET: Mostrar formulario
    sedes = Sede.query.all()
    candidatos = Candidato.query.all()
    return render_template('registro_testigos.html', sedes=sedes, candidatos=candidatos)

@testigo_bp.route('/obtener-mesas/<int:sede_id>')
def obtener_mesas(sede_id):
    try:
        mesas = Mesa.query.filter_by(sede_id=sede_id).all()
        return jsonify({
            'success': True,
            'mesas': [{
                'id': mesa.id,
                'numero': mesa.mesa_numero
            } for mesa in mesas]
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@testigo_bp.route('/descargar_plantilla_testigos')
def descargar_plantilla_testigos():
    # Crear un StringIO para escribir el CSV
    si = io.StringIO()
    writer = csv.writer(si)
    
    # Escribir los encabezados específicos para testigos
    writer.writerow(['numero_documento', 'nombre', 'sede', 'mesa', 'tipo_testigo'])
    
    # Obtener todas las sedes para el ejemplo
    sedes = Sede.query.all()
    sede_ejemplo = sedes[0].nombre if sedes else ''
    
    # Escribir una fila de ejemplo para testigos
    writer.writerow(['12345678', 'Nombre Testigo', sede_ejemplo, 'Mesa 1', 'Candidato'])
    
    # Preparar la respuesta
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=plantilla_testigos.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@testigo_bp.route('/testigos/obtener_estadisticas')
def obtener_estadisticas():
    try:
        print("Obteniendo estadísticas de testigos...")  # Debug
        # Obtener estadísticas por sede
        estadisticas_sede = db.session.query(
            Sede.nombre,
            db.func.count(db.distinct(AsignacionTestigo.numero_documento)).label('total_testigos'),
            db.func.count(AsignacionTestigo.id).label('total_asignaciones')
        ).outerjoin(AsignacionTestigo, Sede.id == AsignacionTestigo.sede_id).group_by(Sede.id, Sede.nombre).all()
        
        print(f"Estadísticas obtenidas: {estadisticas_sede}")  # Debug
        
        # Formatear los resultados
        sedes_data = []
        total_testigos = 0
        total_asignaciones = 0
        
        for sede_nombre, testigos, asignaciones in estadisticas_sede:
            total_testigos += testigos
            total_asignaciones += asignaciones
            sedes_data.append({
                'nombre': sede_nombre,
                'total_testigos': testigos,
                'total_asignaciones': asignaciones
            })
        
        result = {
            'success': True,
            'total_testigos': total_testigos,
            'total_asignaciones': total_asignaciones,
            'por_sede': sedes_data
        }
        print(f"Resultado final: {result}")  # Debug
        return jsonify(result)
    except Exception as e:
        print(f"Error en obtener_estadisticas: {str(e)}")  # Para debug
        return jsonify({'success': False, 'message': str(e)}), 500

@testigo_bp.route('/testigos/detalle_sede/<string:sede>')
def detalle_sede(sede):
    try:
        print(f"Obteniendo detalle para sede: {sede}")  # Debug
        # Obtener todos los testigos de la sede
        testigos = db.session.query(
            AsignacionTestigo.numero_documento,
            AsignacionTestigo.nombre,
            Candidato.nombre.label('candidato_nombre'),
            AsignacionTestigo.es_blanco,
            AsignacionTestigo.es_otro,
            db.func.group_concat(Mesa.mesa_numero).label('mesas')
        ).join(
            Sede, AsignacionTestigo.sede_id == Sede.id
        ).outerjoin(
            Candidato, AsignacionTestigo.candidato_id == Candidato.id
        ).join(
            Mesa, AsignacionTestigo.mesa_id == Mesa.id
        ).filter(
            Sede.nombre == sede
        ).group_by(
            AsignacionTestigo.numero_documento,
            AsignacionTestigo.nombre,
            Candidato.nombre,
            AsignacionTestigo.es_blanco,
            AsignacionTestigo.es_otro
        ).all()

        print(f"Testigos encontrados: {testigos}")  # Debug

        # Formatear los resultados
        testigos_data = []
        for t in testigos:
            tipo = 'Candidato: ' + t.candidato_nombre if t.candidato_nombre else ('Voto en Blanco' if t.es_blanco else 'Otro')
            testigos_data.append({
                'numero_documento': t.numero_documento,
                'nombre': t.nombre,
                'tipo': tipo,
                'mesas': str(t.mesas).split(',') if t.mesas else []
            })

        result = {
            'success': True,
            'testigos': testigos_data
        }
        print(f"Resultado final: {result}")  # Debug
        return jsonify(result)
    except Exception as e:
        print(f"Error en detalle_sede: {str(e)}")  # Para debug
        return jsonify({'success': False, 'message': str(e)}), 500

@testigo_bp.route('/testigos/eliminar/<string:numero_documento>', methods=['DELETE'])
def eliminar_testigo(numero_documento):
    try:
        print(f"Eliminando testigo con documento: {numero_documento}")  # Debug
        # Buscar todas las asignaciones del testigo
        asignaciones = AsignacionTestigo.query.filter_by(numero_documento=numero_documento).all()
        
        if not asignaciones:
            return jsonify({'success': False, 'message': 'No se encontró el testigo'}), 404
        
        # Eliminar todas las asignaciones
        for asignacion in asignaciones:
            db.session.delete(asignacion)
        
        db.session.commit()
        print(f"Testigo eliminado exitosamente")  # Debug
        return jsonify({'success': True, 'message': 'Testigo eliminado exitosamente'})
    except Exception as e:
        db.session.rollback()
        print(f"Error al eliminar testigo: {str(e)}")  # Debug
        return jsonify({'success': False, 'message': str(e)}), 500