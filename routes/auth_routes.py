from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from extensions import db
from models import User, UserActivity
from utils.decorators import  login_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.verify_password(password):
            session['user_id'] = user.id  # Guarda el ID del usuario en la sesión
            session['username'] = user.username  # Guarda el nombre de usuario en la sesión
            session['name'] = user.name  # Guarda el nombre de usuario en la sesión
            flash('Ingreso exitoso', 'success')
            
            # Registrar la actividad del usuario
            activity = UserActivity(user_id=user.id, action='Inicio de sesión')
            db.session.add(activity)
            db.session.commit()
            
            return redirect(url_for('index'))
        else:
            flash('Credenciales incorrectas', 'danger')
    return render_template('login.html')

@auth_bp.route('/add_user', methods=['GET', 'POST'])
@login_required
def add_user():
    if request.method == 'POST':
        name = request.form['name']
        username = request.form['username']
        password = request.form['password']
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('El nombre de usuario ya está en uso. Por favor, elige otro.', 'danger')
        else:
            new_user = User(name=name, username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            # Registrar la actividad del usuario
            activity = UserActivity(user_id=new_user.id, action='Usuario agregado: ' + username)
            db.session.add(activity)
            db.session.commit()
            activity = UserActivity(user_id=session['user_id'], action='Usuario agregado: ' + username)
            db.session.add(activity)
            db.session.commit()
            flash('Usuario agregado exitosamente', 'success')
            return redirect(url_for('auth.list_users'))  # Redirigir a la lista de usuarios
    return render_template('add_user.html')  # Pasar la lista de usuarios

@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)  # Elimina el ID del usuario de la sesión
    flash('Has cerrado sesión exitosamente.', 'success')
    return redirect(url_for('auth.login'))  # Redirige al login

@auth_bp.route('/configurar_usuario', methods=['GET', 'POST'])
@login_required
def configurar_usuario():
    if request.method == 'POST':
        # Aquí puedes manejar la lógica para actualizar la información del usuario
        activity = UserActivity(user_id=session['user_id'], action='Configuración de usuario actualizada')
        db.session.add(activity)
        db.session.commit()
        flash('Información del usuario actualizada exitosamente.', 'success')
        return redirect(url_for('index'))  # Redirige a la página principal
    return render_template('add_user.html')  # Asegúrate de tener este template

@auth_bp.route('/modify_user', methods=['POST'])
@login_required
def modify_user():
    existing_username = request.form['existing_username']
    new_password = request.form['new_password']
    
    user = User.query.filter_by(username=existing_username).first()
    if user:
        if new_password:
            user.set_password(new_password)  # Asegúrate de que este método esté en tu modelo
        db.session.commit()
        # Registrar la actividad del usuario
        activity = UserActivity(user_id=user.id, action='Usuario modificado: ' + existing_username)
        db.session.add(activity)
        db.session.commit()
        activity = UserActivity(user_id=session['user_id'], action='Usuario modificado: ' + existing_username)
        db.session.add(activity)
        db.session.commit()
        activity = UserActivity(user_id=user.id, action='Usuario modificado: ' + existing_username)
        db.session.add(activity)
        db.session.commit()
        flash('Información del usuario actualizada exitosamente.', 'success')
    else:
        flash('Usuario no encontrado.', 'danger')
    
    return redirect(url_for('auth.configurar_usuario'))  # Redirige a la configuración de usuario

@auth_bp.route('/delete_user', methods=['POST'])
@login_required
def delete_user():
    username_to_delete = request.form['existing_username']
    
    user = User.query.filter_by(username=username_to_delete).first()
    if user:
        # Registrar la actividad del usuario
        activity = UserActivity(user_id=user.id, action='Usuario eliminado: ' + username_to_delete)
        db.session.add(activity)
        db.session.commit()
        db.session.delete(user)
        db.session.commit()
        # Registrar la actividad del usuario
        activity = UserActivity(user_id=session['user_id'], action='Usuario eliminado: ' + username_to_delete)
        db.session.add(activity)
        db.session.commit()
        flash('Usuario eliminado exitosamente.', 'success')
    else:
        flash('Usuario no encontrado.', 'danger')
    
    return redirect(url_for('auth.configurar_usuario'))  # Redirige a la configuración de usuario

@auth_bp.route('/list_users', methods=['GET', 'POST'])
@login_required
def list_users():
    users = User.query.all()  # Obtener todos los usuarios
    print(f'Cantidad de usuarios recuperados: {len(users)}')  # Mensaje de depuración
    return render_template('add_user.html', users_list=users)  # Renderizar el template con la lista de usuarios
