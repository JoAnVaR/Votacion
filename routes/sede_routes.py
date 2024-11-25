import sys
from pathlib import Path
from utils.decorators import check_configuracion_abierta


# Agregar el directorio raíz al PYTHONPATH
root_path = str(Path(__file__).parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from models import Sede, Mesa, Estudiante
from extensions import db

sede_bp = Blueprint('sede', __name__)

# Ruta para agregar sede
@sede_bp.route('/agregar_sede', methods=['GET', 'POST'])
@check_configuracion_abierta
def agregar_sede():
    if request.method == 'POST':
        nombre_sede = request.form['nombre_sede']
        direccion = request.form['direccion']
        nueva_sede = Sede(nombre=nombre_sede, direccion=direccion)
        db.session.add(nueva_sede)
        db.session.commit()
        return jsonify({
            'success': True,
            'sede': {
                'id': nueva_sede.id,
                'nombre': nueva_sede.nombre
            }
        })
    sedes = Sede.query.all()
    mesas = Mesa.query.all()
    return render_template('administrar_sedes_mesas.html', sedes=sedes, mesas=mesas)

# Ruta para agregar mesas
@sede_bp.route('/agregar_mesas', methods=['POST'])
@check_configuracion_abierta
def agregar_mesas():
    try:
        print("=== Inicio de agregar_mesas ===")
        print("Datos del formulario:", request.form)
        
        sede_id = request.form.get('sede_id')
        mesa_numero = request.form.get('mesa_numero')
        
        print(f"sede_id: {sede_id}, mesa_numero: {mesa_numero}")
        
        if not sede_id or not mesa_numero:
            print("Error: Datos faltantes")
            return jsonify({
                'success': False,
                'message': 'Sede y número de mesa son requeridos'
            }), 400
        
        sede_id = int(sede_id)
        mesa_numero = int(mesa_numero)
        
        print(f"Valores convertidos - sede_id: {sede_id}, mesa_numero: {mesa_numero}")
        
        # Verificar si la mesa ya existe
        mesa_existente = Mesa.query.filter_by(sede_id=sede_id, mesa_numero=mesa_numero).first()
        if mesa_existente:
            print(f"Error: Mesa {mesa_numero} ya existe en sede {sede_id}")
            return jsonify({
                'success': False,
                'message': 'El número de mesa ya existe para esta sede'
            }), 400

        nueva_mesa = Mesa(sede_id=sede_id, mesa_numero=mesa_numero)
        db.session.add(nueva_mesa)
        db.session.commit()
        
        print(f"Mesa agregada exitosamente - ID: {nueva_mesa.id}")
        
        return jsonify({
            'success': True,
            'mesa': {
                'id': nueva_mesa.id,
                'mesa_numero': nueva_mesa.mesa_numero
            }
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error inesperado: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error al agregar la mesa: {str(e)}'
        }), 500

# Ruta mesas existentes
@sede_bp.route('/mesas_existentes/<int:sede_id>', methods=['GET'])
def mesas_existentes(sede_id):
    try:
        print(f"\n=== Consultando mesas para sede {sede_id} ===")
        
        # Buscar la última mesa de esta sede
        ultima_mesa = Mesa.query.filter_by(sede_id=sede_id).order_by(Mesa.mesa_numero.desc()).first()
        
        # Determinar el siguiente número
        if ultima_mesa is None:
            siguiente_numero = 1
            print(f"No hay mesas para esta sede. Siguiente número: {siguiente_numero}")
        else:
            siguiente_numero = ultima_mesa.mesa_numero + 1
            print(f"Última mesa encontrada: {ultima_mesa.mesa_numero}")
            print(f"Siguiente número: {siguiente_numero}")
        
        # Preparar y enviar respuesta
        respuesta = {'siguiente_numero': siguiente_numero}
        print(f"Enviando respuesta: {respuesta}")
        
        return jsonify(respuesta)
        
    except Exception as e:
        print(f"Error en mesas_existentes: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@sede_bp.before_request
def before_request():
    print(f"Ruta llamada: {request.path}")

@sede_bp.route('/borrar_mesa/<int:mesa_id>', methods=['DELETE'])
@check_configuracion_abierta
def borrar_mesa(mesa_id):
    try:
        mesa = Mesa.query.get_or_404(mesa_id)
        db.session.delete(mesa)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Mesa eliminada exitosamente'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@sede_bp.route('/obtener_mesa_id', methods=['GET'])
def obtener_mesa_id():
    try:
        sede_id = request.args.get('sede_id', type=int)
        mesa_numero = request.args.get('mesa_numero', type=int)
        
        if not sede_id or not mesa_numero:
            return jsonify({'error': 'Faltan parámetros'}), 400
            
        mesa = Mesa.query.filter_by(
            sede_id=sede_id,
            mesa_numero=mesa_numero
        ).first()
        
        if mesa:
            return jsonify({
                'success': True,
                'mesa_id': mesa.id
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Mesa no encontrada'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@sede_bp.route('/borrar_sede/<int:sede_id>', methods=['DELETE'])
@check_configuracion_abierta
def borrar_sede(sede_id):
    try:
        print(f"Intentando borrar sede {sede_id}")
        sede = Sede.query.get_or_404(sede_id)
        
        # Verificar si la sede tiene mesas
        mesas_count = Mesa.query.filter_by(sede_id=sede_id).count()
        if mesas_count > 0:
            print(f"La sede {sede_id} tiene {mesas_count} mesas")
            return jsonify({
                'success': False,
                'message': 'No se puede eliminar la sede porque tiene mesas asociadas'
            }), 400
            
        print(f"Borrando sede {sede_id}")
        db.session.delete(sede)
        db.session.commit()
        print(f"Sede {sede_id} borrada exitosamente")
        
        return jsonify({
            'success': True,
            'message': 'Sede eliminada exitosamente'
        })
        
    except Exception as e:
        print(f"Error al borrar sede: {str(e)}")
        import traceback
        print(traceback.format_exc())
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500