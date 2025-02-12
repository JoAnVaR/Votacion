from flask import Blueprint, render_template, request, jsonify, session
from models import Sede, Mesa, ConfiguracionMesa, db, UserActivity  # Asegúrate de que estos modelos existan
from datetime import datetime

config_mesas_bp = Blueprint('config_mesas', __name__)

@config_mesas_bp.route('/configurar_mesa', methods=['GET', 'POST'])
def configurar_mesa():
    if request.method == 'POST':
        try:
            sede_id = int(request.form['sede'])
            mesa_id = int(request.form['mesa'])
            mac_equipo = request.form['mac_equipo']
            mac_votantes = request.form.getlist('mac_votante[]')

            # Validar que los campos no estén vacíos
            errores = []
            if not sede_id:
                errores.append('La sede es obligatoria.')
            if not mesa_id:
                errores.append('La mesa es obligatoria.')
            if not mac_equipo:
                errores.append('La MAC del equipo es obligatoria.')
            if not mac_votantes:
                errores.append('Las MACs de votantes son obligatorias.')

            if errores:
                return jsonify({'error': errores}), 400

            # Validar si la MAC del equipo ya existe
            if ConfiguracionMesa.query.filter_by(mac_equipo=mac_equipo).first():
                return jsonify({'error': [f'La MAC del equipo ya está en uso.']}), 400

            # Validar si alguna de las MACs de votantes ya existe
            configuraciones = ConfiguracionMesa.query.all()
            for mac in mac_votantes:
                if any(mac in votantes for votantes in [config.mac_votantes for config in configuraciones]):
                    return jsonify({'error': [f'La MAC del votante {mac} ya está en uso.']}), 400
        
            # Obtener los objetos de Sede y Mesa
            sede_obj = Sede.query.get(sede_id)  # Asegúrate de que `sede_id` sea un entero
            mesa_obj = Mesa.query.get(mesa_id)  # Asegúrate de que `mesa_id` sea un entero

            # Crear una nueva configuración
            nueva_configuracion = ConfiguracionMesa(
                sede=sede_obj,
                mesa=mesa_obj,
                mac_equipo=mac_equipo,
                mac_votantes=mac_votantes
            )
            db.session.add(nueva_configuracion)
            db.session.commit()

            # Registrar la actividad del usuario
            activity = UserActivity(user_id=session['user_id'], action='configurar_mesa' + str(mesa_id), timestamp=datetime.now())
            db.session.add(activity)
            db.session.commit()

            return jsonify({'message': 'Configuración guardada exitosamente.'}), 200
        except Exception as e:
            print(f'Ocurrió un error: {str(e)}')  # Mensaje de depuración
            return jsonify({'error': f'Ocurrió un error: {str(e)}'}), 500

    # Método GET
    sedes = Sede.query.all()
    sede_id = int(request.args.get('sede_id', 0))  # Asegúrate de obtener el sede_id primero
    mesas = Mesa.query.filter_by(sede_id=sede_id).all()  # Filtrar por sede
    configuraciones = ConfiguracionMesa.query.all()
    equipos = ConfiguracionMesa.query.all()

    # Obtener las configuraciones existentes para la sede seleccionada
    print(f'Verificando configuraciones para sede_id: {sede_id}')  # Mensaje de depuración
    configuraciones_existentes = ConfiguracionMesa.query.filter_by(sede_id=sede_id).all()
    mesas_configuradas = [config.mesa_id for config in configuraciones_existentes]

    # Filtrar las mesas disponibles
    mesas_disponibles = [mesa for mesa in mesas if mesa.id not in mesas_configuradas]
    print(f'Mesas disponibles después del filtrado: {mesas_disponibles}')  # Mensaje de depuración

    return render_template('configurar_mesa.html', sedes=sedes, mesas=mesas_disponibles, configuraciones=configuraciones, equipos=equipos)

@config_mesas_bp.route('/mesas/<int:sede_id>', methods=['GET'])
def cargarMesas(sede_id):
    try:
        print(f'ID de sede recibido: {sede_id}')
        mesas = Mesa.query.filter_by(sede_id=sede_id).all()
        print(f'Respuesta de mesas: {mesas}')
        print(f'Mesas encontradas para sede_id {sede_id}: {len(mesas)}')  # Mensaje de depuración
        
        configuraciones_existentes = ConfiguracionMesa.query.filter_by(sede_id=sede_id).all()
        mesas_configuradas = [config.mesa_id for config in configuraciones_existentes]
        
        mesas_disponibles = [mesa for mesa in mesas if mesa.id not in mesas_configuradas]
        print(f'Mesas disponibles para sede_id {sede_id}: {mesas_disponibles}')  # Mensaje de depuración

        return jsonify({'mesas': [{'id': mesa.id, 'numero': mesa.mesa_numero} for mesa in mesas_disponibles]}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@config_mesas_bp.route('/equipos', methods=['GET'])
def listar_equipos():
    try:
        configuraciones = ConfiguracionMesa.query.all()
        if configuraciones:
            return jsonify({'equipos': [{ 
                'id': config.id,
                'sede': config.sede.nombre,
                'mesa': config.mesa.mesa_numero,
                'mac_equipo': config.mac_equipo,
                'mac_votantes': config.mac_votantes
            } for config in configuraciones]}), 200
        else:
            return jsonify({'equipos': []}), 200  # Devolver lista vacía
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@config_mesas_bp.route('/configurar_mesa/eliminar/<int:config_id>', methods=['DELETE'])
def eliminar_configuracion(config_id):
    try:
        configuracion = ConfiguracionMesa.query.get(config_id)
        if configuracion:
            db.session.delete(configuracion)
            db.session.commit()
            return jsonify({'message': 'Configuración eliminada exitosamente.'}), 200

            # Registrar la actividad del usuario
            activity = UserActivity(user_id=session['user_id'], action='eliminar_configuracion' + str(config_id), timestamp=datetime.now())
            db.session.add(activity)
            db.session.commit() 
        else:
            return jsonify({'error': 'Configuración no encontrada.'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500