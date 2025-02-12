from extensions import db
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
# Modelos de Base de Datos
class Estudiante(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_documento = db.Column(db.String(20), unique=True, nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    grado = db.Column(db.Integer, nullable=False)
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
    asignaciones_testigos = db.relationship('AsignacionTestigo', back_populates='sede')
    configuraciones = db.relationship('ConfiguracionMesa', back_populates='sede')

# Definición del modelo para la tabla de mesas
class Mesa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=False)
    mesa_numero = db.Column(db.Integer, nullable=False)
    
    # Relaciones con back_populates
    sede = db.relationship('Sede', back_populates='mesas')
    estudiantes = db.relationship('Estudiante', back_populates='mesa')
    asignaciones = db.relationship('AsignacionMesa', back_populates='mesa')
    asignaciones_testigos = db.relationship('AsignacionTestigo', back_populates='mesa')
    configuraciones = db.relationship('ConfiguracionMesa', back_populates='mesa')
    
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
    tipo_persona = db.Column(db.String(20), nullable=False)
    persona_id = db.Column(db.Integer, nullable=True)
    mesa_id = db.Column(db.Integer, db.ForeignKey('mesa.id'), nullable=True)
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=True)
    es_remanente = db.Column(db.Boolean, default=False)
    disponible = db.Column(db.Boolean, default=True)
    sorteo = db.Column(db.Integer, nullable=True)
    activo = db.Column(db.Boolean, default=True)
    _numero_documento = db.Column('numero_documento', db.String(20), nullable=True)
    _nombre = db.Column('nombre', db.String(100), nullable=True)
    
    # Relaciones
    mesa = db.relationship('Mesa', backref='jurados')
    sede = db.relationship('Sede', backref='jurados')
    
    @property
    def id_mesa(self):
        return self.mesa_id
    
    @id_mesa.setter
    def id_mesa(self, value):
        self.mesa_id = value
    
    @property
    def nombre(self):
        if self._nombre:
            return self._nombre
        if not self.persona_id:
            return self._nombre or 'Sin Asignar'
        if self.tipo_persona == 'estudiante':
            estudiante = Estudiante.query.get(self.persona_id)
            return estudiante.nombre if estudiante else 'Desconocido'
        else:
            profesor = Profesor.query.get(self.persona_id)
            return profesor.nombre if profesor else 'Desconocido'
    
    @nombre.setter
    def nombre(self, value):
        self._nombre = value
    
    @property
    def numero_documento(self):
        if self._numero_documento:
            return self._numero_documento
        if not self.persona_id:
            return self._numero_documento or 'Sin Asignar'
        if self.tipo_persona == 'estudiante':
            estudiante = Estudiante.query.get(self.persona_id)
            return estudiante.numero_documento if estudiante else 'Desconocido'
        else:
            profesor = Profesor.query.get(self.persona_id)
            return profesor.numero_documento if profesor else 'Desconocido'
    
    @numero_documento.setter
    def numero_documento(self, value):
        self._numero_documento = value

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

class AsignacionTestigo(db.Model):
    __tablename__ = 'asignacion_testigo'
    id = db.Column(db.Integer, primary_key=True)
    numero_documento = db.Column(db.String(20), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=False)
    mesa_id = db.Column(db.Integer, db.ForeignKey('mesa.id'), nullable=False)
    candidato_id = db.Column(db.Integer, db.ForeignKey('candidato.id'), nullable=True)
    es_blanco = db.Column(db.Boolean, default=False)
    es_otro = db.Column(db.Boolean, default=False)
    fecha_asignacion = db.Column(db.DateTime, default=datetime.now)
    
    # Relaciones
    sede = db.relationship('Sede', back_populates='asignaciones_testigos')
    mesa = db.relationship('Mesa', back_populates='asignaciones_testigos')
    candidato = db.relationship('Candidato', backref='testigos')
    
    # Restricción única para evitar duplicados de testigo en la misma mesa
    __table_args__ = (
        db.UniqueConstraint('numero_documento', 'mesa_id', name='_testigo_mesa_uc'),
        db.CheckConstraint(
            '(candidato_id IS NOT NULL AND NOT es_blanco AND NOT es_otro) OR '
            '(candidato_id IS NULL AND es_blanco AND NOT es_otro) OR '
            '(candidato_id IS NULL AND NOT es_blanco AND es_otro)',
            name='_testigo_tipo_check'
        )
    )

class Candidato(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero_documento = db.Column(db.String(80), unique=True, nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    grado = db.Column(db.String(80), nullable=False)
    seccion = db.Column(db.String(80), nullable=False)
    propuesta = db.Column(db.Text, nullable=False)
    foto_path = db.Column(db.String(200), nullable=True)  # Agregar el campo foto_path

class ReemplazoJurado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jurado_original_id = db.Column(db.Integer, db.ForeignKey('jurado.id'), nullable=False)
    jurado_reemplazo_id = db.Column(db.Integer, db.ForeignKey('jurado.id'), nullable=True)
    mesa_id = db.Column(db.Integer, db.ForeignKey('mesa.id'), nullable=False)
    razon = db.Column(db.String(200), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.now)
    activo = db.Column(db.Boolean, default=True)
    
    # Relaciones
    jurado_original = db.relationship('Jurado', foreign_keys=[jurado_original_id])
    jurado_reemplazo = db.relationship('Jurado', foreign_keys=[jurado_reemplazo_id])
    mesa = db.relationship('Mesa')

class EventoCalendario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fase = db.Column(db.Integer, nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    fecha_inicio = db.Column(db.DateTime, nullable=False)
    fecha_fin = db.Column(db.DateTime, nullable=True)
    fecha_fin_impreso = db.Column(db.DateTime, nullable=True)
    descripcion = db.Column(db.Text, nullable=True)
    estado = db.Column(db.String(20), default='pendiente')
    orden = db.Column(db.Integer, nullable=False)
    
    @classmethod
    def sistema_bloqueado(cls):
        """Verifica si el sistema está bloqueado basado en las fechas de los eventos"""
        ultimo_evento = cls.query.order_by(cls.fecha_fin.desc()).first()
        if ultimo_evento:
            return datetime.now() > ultimo_evento.fecha_fin
        return False
    
    @classmethod
    def fase_actual(cls):
        """Determina la fase actual del proceso electoral"""
        ahora = datetime.now()
        evento_actual = cls.query.filter(
            cls.fecha_inicio <= ahora,
            cls.fecha_fin >= ahora
        ).first()
        return evento_actual.fase if evento_actual else None
    
    @classmethod
    def permitir_modificaciones(cls, modulo):
        """Verifica si se permiten modificaciones en un módulo específico"""
        ahora = datetime.now()
        evento = cls.query.filter_by(titulo=modulo).first()
        if evento:
            return evento.fecha_inicio <= ahora <= evento.fecha_fin
        return False
    
    @classmethod
    def crear_calendario_default(cls):
        fecha_base = datetime.now()
        
        eventos_default = [
            {
                'titulo': 'Registro de Sedes Educativas',
                'descripcion': 'Registro de las sedes educativas participantes y configuración de mesas de votación',
                'fase': 1,
                'orden': 1,
                'fecha_inicio': fecha_base.replace(hour=0, minute=0, second=0, microsecond=0),
                'fecha_fin': (fecha_base + timedelta(days=2)).replace(hour=23, minute=59, second=59, microsecond=999999),
                'fecha_fin_impreso': fecha_base + timedelta(days=2),
                'estado': 'pendiente'
            },
            {
                'titulo': 'Registro de Estudiantes',
                'descripcion': 'Registro de estudiantes habilitados para votar en el proceso electoral',
                'fase': 1,
                'orden': 2,
                'fecha_inicio': (fecha_base + timedelta(days=3)).replace(hour=0, minute=0, second=0, microsecond=0),
                'fecha_fin': (fecha_base + timedelta(days=5)).replace(hour=23, minute=59, second=59, microsecond=999999),
                'fecha_fin_impreso': fecha_base + timedelta(days=5),
                'estado': 'pendiente'
            },
            {
                'titulo': 'Registro de Profesores',
                'descripcion': 'Registro de profesores que actuarán como jurados de votación',
                'fase': 1,
                'orden': 3,
                'fecha_inicio': (fecha_base + timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0),
                'fecha_fin': (fecha_base + timedelta(days=8)).replace(hour=23, minute=59, second=59, microsecond=999999),
                'fecha_fin_impreso': fecha_base + timedelta(days=8),
                'estado': 'pendiente'
            },
            {
                'titulo': 'Conformación de Mesas de Votación',
                'descripcion': 'Asignación de estudiantes a mesas de votación según sede y grado',
                'fase': 1,
                'orden': 4,
                'fecha_inicio': (fecha_base + timedelta(days=9)).replace(hour=0, minute=0, second=0, microsecond=0),
                'fecha_fin': (fecha_base + timedelta(days=11)).replace(hour=23, minute=59, second=59, microsecond=999999),
                'fecha_fin_impreso': fecha_base + timedelta(days=11),
                'estado': 'pendiente'
            },
            {
                'titulo': 'Inscripción de Candidatos',
                'descripcion': 'Registro de estudiantes candidatos a personería estudiantil',
                'fase': 2,
                'orden': 1,
                'fecha_inicio': (fecha_base + timedelta(days=15)).replace(hour=0, minute=0, second=0, microsecond=0),
                'fecha_fin': (fecha_base + timedelta(days=17)).replace(hour=23, minute=59, second=59, microsecond=999999),
                'fecha_fin_impreso': fecha_base + timedelta(days=17),
                'estado': 'pendiente'
            },
            {
                'titulo': 'Designación de Jurados',
                'descripcion': 'Asignación de profesores como jurados en las mesas de votación',
                'fase': 2,
                'orden': 2,
                'fecha_inicio': (fecha_base + timedelta(days=12)).replace(hour=0, minute=0, second=0, microsecond=0),
                'fecha_fin': (fecha_base + timedelta(days=14)).replace(hour=23, minute=59, second=59, microsecond=999999),
                'fecha_fin_impreso': fecha_base + timedelta(days=14),
                'estado': 'pendiente'
            },
            {
            'titulo': 'Reemplazo de Jurados',
            'descripcion': 'Proceso de sustitución de jurados que presentan impedimentos justificados para ejercer su función durante la jornada electoral. Incluye el registro de la razón del reemplazo y la asignación del nuevo jurado.',
            'fase': 2,
            'orden': 3,
            'fecha_inicio': (fecha_base + timedelta(days=13)).replace(hour=0, minute=0, second=0, microsecond=0),
            'fecha_fin': (fecha_base + timedelta(days=16)).replace(hour=23, minute=59, second=59, microsecond=999999),
            'fecha_fin_impreso': (fecha_base + timedelta(days=16)), 
            'estado': 'pendiente'
        },
        {
            'titulo': 'Inscripción de Candidatos',
            'descripcion': 'Registro de estudiantes candidatos a personería estudiantil',
            'fase': 2,
            'orden': 4,
            'fecha_inicio': (fecha_base + timedelta(days=15)).replace(hour=0, minute=0, second=0, microsecond=0),
            'fecha_fin': (fecha_base + timedelta(days=17)).replace(hour=23, minute=59, second=59, microsecond=999999),
            'fecha_fin_impreso': (fecha_base + timedelta(days=17)),
            'estado': 'pendiente'
        },
            {
                'titulo': 'Registro de Testigos',
                'descripcion': 'Inscripción de testigos para garantizar la transparencia del proceso electoral',
                'fase': 2,
                'orden': 5,
                'fecha_inicio': (fecha_base + timedelta(days=18)).replace(hour=0, minute=0, second=0, microsecond=0),
                'fecha_fin': (fecha_base + timedelta(days=19)).replace(hour=23, minute=59, second=59, microsecond=999999),
                'fecha_fin_impreso': (fecha_base + timedelta(days=19)),
                'estado': 'pendiente'
            },
            {
                'titulo': 'Jornada de Votación',
                'descripcion': 'Proceso de votación electrónica para la elección del personero estudiantil',
                'fase': 3,
                'orden': 1,
                'fecha_inicio': (fecha_base + timedelta(days=20)).replace(hour=0, minute=0, second=0, microsecond=0),
                'fecha_fin': (fecha_base + timedelta(days=21)).replace(hour=23, minute=59, second=59, microsecond=999999),
                'fecha_fin_impreso': (fecha_base + timedelta(days=21)),
                'estado': 'pendiente'
            }
        ]
        
        for evento in eventos_default:
            if not EventoCalendario.query.filter_by(titulo=evento['titulo']).first():
                nuevo_evento = EventoCalendario(**evento)
                db.session.add(nuevo_evento)
        
        db.session.commit()

    @classmethod
    def get_config(cls):
        """Retorna la configuración del sistema basada en el estado de los eventos"""
        return {
            'sistema_bloqueado': cls.sistema_bloqueado(),
            'calendario_bloqueado': cls.sistema_bloqueado(),  # Para mantener compatibilidad con templates
            'fase_actual': cls.obtener_fase_actual()
        }

    @classmethod
    def obtener_fase_actual(cls):
        """Determina la fase actual basada en los eventos activos"""
        ahora = datetime.now()
        for fase in range(1, 4):  # Asumiendo que hay 3 fases
            eventos = cls.query.filter_by(fase=fase).all()
            if any(evento.fecha_inicio <= ahora <= evento.fecha_fin for evento in eventos):
                return fase
        return 1  # Fase por defecto

class Configuracion(db.Model):
    __tablename__ = 'configuracion'
    
    id = db.Column(db.Integer, primary_key=True)
    configuracion_finalizada = db.Column(db.Boolean, default=False)
    fecha_finalizacion = db.Column(db.DateTime, nullable=True)

    @staticmethod
    def sistema_bloqueado():
        config = Configuracion.query.first()
        return config is not None and config.configuracion_finalizada == True

class ConfiguracionSorteo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jurados_por_mesa = db.Column(db.Integer, nullable=False, default=3)
    porcentaje_remanentes = db.Column(db.Integer, nullable=False, default=12)
    grados_seleccionados = db.Column(db.String(100), nullable=False)  # Almacenados como string separado por comas
    fase_actual = db.Column(db.Integer, nullable=False, default=1)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.now)

class ConfiguracionMesa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sede_id = db.Column(db.Integer, db.ForeignKey('sede.id'), nullable=False)  # Relación con Sede
    mesa_id = db.Column(db.Integer, db.ForeignKey('mesa.id'), nullable=False)  # Relación con Mesa
    mac_equipo = db.Column(db.String(17), nullable=False)
    mac_votantes = db.Column(db.JSON, nullable=False)  # Usar JSON en lugar de PickleType

    # Relaciones
    sede = db.relationship('Sede', back_populates='configuraciones')
    mesa = db.relationship('Mesa', back_populates='configuraciones')

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)  # Nuevo campo para nombre
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    @classmethod
    def crear_usuario_default(cls):
        """Crea el primer usuario administrador"""
        if not cls.query.filter_by(username='admin').first():
            nuevo_usuario = cls(
                username='admin',
                name='Administrador',
                password_hash=generate_password_hash('admin')
            )
            db.session.add(nuevo_usuario)
            db.session.commit()


class UserActivity(db.Model):
    __tablename__ = 'user_activity'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref='activities')
