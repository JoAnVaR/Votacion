from flask import render_template
from config import create_app
from extensions import db
from routes import all_blueprints

app = create_app()

# Inicializar la base de datos con la app
db.init_app(app)

# Registrar todos los blueprints
for blueprint in all_blueprints:
    app.register_blueprint(blueprint)

# Ruta de Inicio
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__': 
    with app.app_context():
        db.create_all()
    app.run(host='192.168.1.40', port=5000, debug=True)