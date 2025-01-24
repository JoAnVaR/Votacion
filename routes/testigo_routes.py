from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models import Testigo, AsignacionTestigo, Candidato, Sede, Mesa, Configuracion
from sqlalchemy.exc import IntegrityError
import csv
import io
from extensions import db
from utils.decorators import verificar_acceso_ruta

testigo_bp = Blueprint('testigo', __name__)

# Ruta para Registro de Testigos
@testigo_bp.route('/registro-testigos', methods=['GET', 'POST'])
@verificar_acceso_ruta('testigo.registro_testigos')
def registro_testigos():
    testigos = Testigo.query.all()
    asignaciones = AsignacionTestigo.query.all()
    candidatos = Candidato.query.all()
    sedes = Sede.query.all()
    config = Configuracion.query.first()  # Obtener configuración

    if request.method == 'POST':
        if config and config.configuracion_finalizada:  # Verificar si el sistema está bloqueado
            flash("Error: El sistema está bloqueado. No se pueden realizar modificaciones.", "error")
            return redirect(url_for('testigo.registro_testigos'))

        try:
            # Lógica para agregar testigos
            numero_documento = request.form.get('numero_documento')
            nombre = request.form.get('nombre')
            tipo_persona = request.form.get('tipo_persona')
            id_candidato = request.form.get('id_candidato')
            nuevo_testigo = Testigo(
                numero_documento=numero_documento,
                nombre=nombre,
                tipo_persona=tipo_persona,
                id_candidato=id_candidato
            )
            db.session.add(nuevo_testigo)
            db.session.commit()
            flash("Testigo agregado con éxito.", "success")
        except IntegrityError:
            db.session.rollback()
            flash("Error: El número de documento ya existe.", "error")

    elif 'registro_testigo' in request.form:
        if config and config.configuracion_finalizada:  # Verificar si el sistema está bloqueado
            flash("Error: El sistema está bloqueado. No se pueden realizar modificaciones.", "error")
            return redirect(url_for('testigo.registro_testigos'))

        testigo_id = request.form.get('testigo_id')
        id_sede = request.form.get('id_sede')
        mesas_seleccionadas = request.form.getlist('mesas')

        for mesa_numero in mesas_seleccionadas:
            asignacion = AsignacionTestigo(id_testigo=testigo_id, id_sede=id_sede, mesa_numero=mesa_numero)
            db.session.add(asignacion)
        db.session.commit()
        flash("Testigo asignado con éxito a las mesas seleccionadas.", "success")

    return render_template('registro_testigos.html', testigos=testigos, asignaciones=asignaciones, candidatos=candidatos, sedes=sedes, config=config)

# Ruta para obtener las mesas de una sede
@testigo_bp.route('/get_mesas/<int:sede_id>')
def get_mesas(sede_id):
    mesas = Mesa.query.filter_by(sede_id=sede_id).all()
    return jsonify([{'mesa_numero': mesa.mesa_numero} for mesa in mesas])

# Ruta para eliminar una asignación de testigo
@testigo_bp.route('/eliminar_asignacion/_testigo<int:asignacion_id>', methods=['POST'])
def eliminar_asignacion_testigo(asignacion_id):
    asignacion = AsignacionTestigo.query.get(asignacion_id)
    if asignacion:
        db.session.delete(asignacion)
        db.session.commit()
        flash("Asignación eliminada con éxito.", "success")
    else:
        flash("Error: Asignación no encontrada.", "error")
    return redirect(url_for('testigo.registro_testigos'))


