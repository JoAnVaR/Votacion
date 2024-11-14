import csv
import random

# Generar datos
datos = []
departamentos = ["Matemáticas", "Ciencias", "Historia", "Lenguaje", "Educación Física", "Arte", "Música"]
titulos = ["Profesor", "Maestro", "Licenciado", "Doctor", "Magister"]
nombres = [
    "Juan Carlos Pérez García", "Ana María García López", "Pedro Martínez", 
    "María Rodríguez", "Luis Alberto Hernández Rivera", "Carla López", 
    "José González", "Laura Ramírez", "Antonio Díaz", "Elena Sánchez", 
    "Lucas Fernández", "Sofía Castro", "Daniel Morales", "Martina Paredes", 
    "David Ruiz", "Valentina Suárez", "Emilio González", "Mía Torres", 
    "Diego Rojas", "Isabella Moreno", "Samuel Herrera", "Renata Mendoza"
]

sede_ids = [1, 2]  # IDs de las sedes disponibles

for i in range(25):  # Generar datos para 25 profesores
    numero_documento = ''.join(["%s" % n for n in [random.randint(0, 9) for i in range(10)]])
    nombre = random.choice(nombres)
    departamento = random.choice(departamentos)
    titulo = random.choice(titulos)
    sede_id = random.choice(sede_ids)
    datos.append([numero_documento, nombre, departamento, titulo, sede_id])

# Escribir archivo CSV
with open('listado_profesores.csv', 'w', newline='') as archivo_csv:
    escritor_csv = csv.writer(archivo_csv)
    escritor_csv.writerow(['numero_documento', 'nombre', 'departamento', 'titulo', 'sede_id'])
    escritor_csv.writerows(datos)

print("Archivo CSV generado exitosamente.")
