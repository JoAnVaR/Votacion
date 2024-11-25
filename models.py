from extensions import db
from datetime import datetime
# Modelos de Base de Datos
class Estudiante(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_documento = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    grado = db.Column(db.String(20), nullable=False)
    seccion = db.Column(db.String(10), nullable=False)
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=False)
    mesa_id = db.Column(db.Integer, db.ForeignKey('mesa.id'), nullable=True)
    es_candidato = db.Column(db.Boolean, default=False)
    
    # Relaciones con back_populates
    sede = db.relationship('Sede', back_populates='estudiantes')
    mesa = db.relationship('Mesa', back_populates='estudiantes')

class Profesor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_documento = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    departamento = db.Column(db.String(100), nullable=False)
    titulo = db.Column(db.String(50), nullable=False)
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=False)
    sede = db.relationship('Sede', backref='profesores')

# Definición del modelo para la tabla de sedes
class Sede(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.String(200), nullable=False)
    
    # Relaciones con back_populates
    estudiantes = db.relationship('Estudiante', back_populates='sede')
    mesas = db.relationship('Mesa', back_populates='sede', cascade='all, delete-orphan')
    asignaciones = db.relationship('AsignacionMesa', back_populates='sede')

# Definición del modelo para la tabla de mesas
class Mesa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=False)
    mesa_numero = db.Column(db.Integer, nullable=False)
    
    # Relaciones con back_populates
    sede = db.relationship('Sede', back_populates='mesas')
    estudiantes = db.relationship('Estudiante', back_populates='mesa')
    asignaciones = db.relationship('AsignacionMesa', back_populates='mesa')
    
    __table_args__ = (db.UniqueConstraint('sede_id', 'mesa_numero', name='_sede_mesa_uc'),)

class AsignacionMesa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    grado = db.Column(db.String(20), nullable=False)
    seccion = db.Column(db.String(10), nullable=False)
    mesa_numero = db.Column(db.String(20), nullable=False)
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=False)
    mesa_id = db.Column(db.Integer, db.ForeignKey('mesa.id'), nullable=False)
    
    # Relaciones con back_populates
    sede = db.relationship('Sede', back_populates='asignaciones')
    mesa = db.relationship('Mesa', back_populates='asignaciones')

class Jurado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_documento = db.Column(db.String(20), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    tipo_persona = db.Column(db.String(20), nullable=False)
    id_mesa = db.Column(db.Integer, nullable=True)
    sorteo = db.Column(db.Integer, nullable=False)
    activo = db.Column(db.Boolean, default=True)
    
    # Agregar relación con Mesa usando sede_id y mesa_numero
    sede_id = db.Column(db.Integer, nullable=True)
    mesa_numero = db.Column(db.Integer, nullable=True)
    __table_args__ = (
        db.ForeignKeyConstraint(
            ['sede_id', 'mesa_numero'],
            ['mesa.sede_id', 'mesa.mesa_numero'],
            ondelete='SET NULL'
        ),
        db.UniqueConstraint('numero_documento', 'sorteo', name='unique_sorteo_documento')
    )

class Votacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_estudiante = db.Column(db.Integer, db.ForeignKey('estudiante.id', ondelete='CASCADE'), nullable=False)
    id_mesa = db.Column(db.Integer, nullable=True)
    fecha_hora = db.Column(db.DateTime, nullable=False)
    autorizado = db.Column(db.Boolean, nullable=False)
    estudiante = db.relationship('Estudiante', backref='votaciones')
    
    # Agregar relación con Mesa
    sede_id = db.Column(db.Integer, nullable=True)
    mesa_numero = db.Column(db.Integer, nullable=True)
    __table_args__ = (
        db.ForeignKeyConstraint(
            ['sede_id', 'mesa_numero'],
            ['mesa.sede_id', 'mesa.mesa_numero'],
            ondelete='SET NULL'
        ),
    )

class Testigo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_documento = db.Column(db.String(20), nullable=False, unique=True)
    nombre = db.Column(db.String(100), nullable=False)
    tipo_persona = db.Column(db.String(20), nullable=False)  # Estudiante o Profesor
    id_candidato = db.Column(db.Integer, db.ForeignKey('candidato.id'), nullable=True)
    asignaciones = db.relationship('AsignacionTestigo', backref='testigo', lazy=True)  # Cambiamos a 'testigo'

class AsignacionTestigo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_testigo = db.Column(db.Integer, db.ForeignKey('testigo.id'), nullable=False)
    id_sede = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=False)
    mesa_numero = db.Column(db.String(20), nullable=False)
    # No necesitamos redefinir aquí el backref, solo en el modelo Testigo
    sede = db.relationship('Sede', backref='asignaciones_testigos')


# Definir el modelo Candidato con el campo foto_path
class Candidato(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_documento = db.Column(db.String(80), unique=True, nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    grado = db.Column(db.String(80), nullable=False)
    seccion = db.Column(db.String(80), nullable=False)
    propuesta = db.Column(db.Text, nullable=False)
    foto_path = db.Column(db.String(200), nullable=True)  # Agregar el campo foto_path

class Reemplazo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jurado_original_id = db.Column(db.Integer, db.ForeignKey('jurado.id'), nullable=False)
    jurado_original = db.relationship('Jurado', foreign_keys=[jurado_original_id])
    jurado_reemplazo_id = db.Column(db.Integer, db.ForeignKey('jurado.id'), nullable=False)
    jurado_reemplazo = db.relationship('Jurado', foreign_keys=[jurado_reemplazo_id])
    razon = db.Column(db.String(255), nullable=False)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class ConfiguracionSistema(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    configuracion_finalizada = db.Column(db.Boolean, default=False)
    fecha_finalizacion = db.Column(db.DateTime)
    limite_estudiantes_por_mesa = db.Column(db.Integer, default=30)
    permitir_modificaciones = db.Column(db.Boolean, default=True)

    @staticmethod
    def get_config():
        config = ConfiguracionSistema.query.first()
        if not config:
            config = ConfiguracionSistema()
            db.session.add(config)
            db.session.commit()
        return config