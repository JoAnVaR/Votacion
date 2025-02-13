import sys
from pathlib import Path
from utils.decorators import verificar_acceso_ruta, login_required
from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session
from models import Sede, Mesa, Estudiante, UserActivity
from extensions import db
from datetime import datetime

# Agregar el directorio raíz al PYTHONPATH
root_path = str(Path(__file__).parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

sede_bp = Blueprint('sede', __name__)

# Ruta para agregar sede
@sede_bp.route('/sede/agregar', methods=['GET', 'POST'])
@login_required
@verificar_acceso_ruta('sede.agregar_sede')
def agregar_sede(bloqueado=False):
    if request.method == 'POST':
        if bloqueado:
            return jsonify({
                'success': False,
                'message': 'La edición está bloqueada en este momento'
            }), 403
            
        nombre_sede = request.form['nombre_sede']
        direccion = request.form['direccion']
        nueva_sede = Sede(nombre=nombre_sede, direccion=direccion)
        db.session.add(nueva_sede)
        db.session.commit()

        # Registrar la actividad del usuario
        activity = UserActivity(user_id=session['user_id'], action='Sede agregada: ' + nueva_sede.nombre, timestamp=datetime.now())
        db.session.add(activity)
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
    return render_template('administrar_sedes_mesas.html', sedes=sedes, mesas=mesas, bloqueado=bloqueado)

# Ruta para agregar mesas
@sede_bp.route('/agregar_mesas', methods=['POST'])
@login_required
@verificar_acceso_ruta('sede.agregar_mesas')
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

        # Registrar la actividad del usuario
        activity = UserActivity(user_id=session['user_id'], action='Mesa agregada: ' + str(nueva_mesa.mesa_numero), timestamp=datetime.now())
        db.session.add(activity)
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
@login_required
@verificar_acceso_ruta('sede.ver_mesas_existentes')
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

@sede_bp.route('/borrar_mesa/<int:mesa_id>', methods=['POST'])
@login_required
@verificar_acceso_ruta('sede.borrar_mesa')
def borrar_mesa(mesa_id):
    try:
        print(f"=== Intentando borrar mesa {mesa_id} ===")
        print(f"Headers recibidos: {dict(request.headers)}")
        
        mesa = Mesa.query.get_or_404(mesa_id)
        print(f"Mesa encontrada: {mesa}")
        
        # Verificar si la mesa tiene estudiantes asignados
        estudiantes = Estudiante.query.filter_by(mesa_id=mesa_id).first()
        if estudiantes:
            print(f"Error: Mesa {mesa_id} tiene estudiantes asignados")
            return jsonify({
                'success': False,
                'message': 'No se puede eliminar la mesa porque tiene estudiantes asignados'
            }), 400
            
        db.session.delete(mesa)
        db.session.commit()

        # Registrar la actividad del usuario
        activity = UserActivity(user_id=session['user_id'], action='Mesa eliminada: ' + str(mesa.mesa_numero), timestamp=datetime.now())
        db.session.add(activity)
        db.session.commit() 

        print(f"Mesa {mesa_id} eliminada exitosamente")
        return jsonify({
            'success': True,
            'message': 'Mesa eliminada exitosamente'
        })
    except Exception as e:
        print(f"Error al borrar mesa {mesa_id}: {str(e)}")
        import traceback
        print(traceback.format_exc())
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@sede_bp.route('/obtener_mesa_id', methods=['GET'])
@login_required
@verificar_acceso_ruta('sede.obtener_mesa_id')
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

@sede_bp.route('/borrar_sede/<int:sede_id>', methods=['POST', 'DELETE'])
@login_required
@verificar_acceso_ruta('sede.borrar_sede')
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

        # Registrar la actividad del usuario
        activity = UserActivity(user_id=session['user_id'], action='Sede eliminada: ' + sede.nombre, timestamp=datetime.now())
        db.session.add(activity)
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

@sede_bp.route('/<int:sede_id>/mesas')
@login_required
@verificar_acceso_ruta('sede.ver_mesas')
def obtener_mesas_sede(sede_id):
    try:
        mesas = Mesa.query.filter_by(sede_id=sede_id).order_by(Mesa.mesa_numero).all()
        
        # Preparar los datos de las mesas
        mesas_data = []
        for i, mesa in enumerate(mesas):
            mesas_data.append({
                'id': mesa.id,
                'mesa_numero': mesa.mesa_numero,
                'es_ultima': (i == len(mesas) - 1)  # Solo la última mesa tendrá el botón de borrar
            })
            
        return jsonify({
            'success': True,
            'mesas': mesas_data
        })
    except Exception as e:
        print(f"Error al obtener mesas: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error al obtener las mesas'
        }), 500

# Agregar esta nueva ruta
@sede_bp.route('/obtener_sedes', methods=['GET'])
@login_required
@verificar_acceso_ruta('sede.obtener_sedes')
def obtener_sedes():
    try:
        sedes = Sede.query.all()
        return jsonify({
            'success': True,
            'sedes': [{'id': sede.id, 'nombre': sede.nombre} for sede in sedes]
        })
    except Exception as e:
        print(f"Error al obtener sedes: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error al obtener las sedes'
        }), 500

@sede_bp.route('/administrar_sedes_mesas', methods=['GET'])
@login_required
@verificar_acceso_ruta('sede.administrar_sedes_mesas')
def administrar_sedes_mesas():
    # Lógica para administrar sedes y mesas
    return render_template('administrar_sedes_mesas.html')

@sede_bp.before_request
@login_required
def before_request():
    print(f"Ruta llamada: {request.path}")
