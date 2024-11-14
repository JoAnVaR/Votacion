import csv
import random

# Generar datos
datos = []
sede_id_dict = {1: [1, 2, 3, 4, 5], 2: [6, 7, 8, 9, 10, 11]}
nombres = [
    "Juan Carlos Pérez García", "Ana María García López", "Pedro Martínez", 
    "María Rodríguez", "Luis Alberto Hernández Rivera", "Carla López", 
    "José González", "Laura Ramírez", "Antonio Díaz", "Elena Sánchez", 
    "Lucas Fernández", "Sofía Castro", "Daniel Morales", "Martina Paredes", 
    "David Ruiz", "Valentina Suárez", "Emilio González", "Mía Torres", 
    "Diego Rojas", "Isabella Moreno", "Samuel Herrera", "Renata Mendoza"
]

for grado in range(1, 12):
    for seccion in [1, 2]:
        sede_id = 2 if grado >= 6 else 1
        for i in range(20, 31):  # entre 20 a 30 estudiantes
            numero_documento = ''.join(["%s" % n for n in [random.randint(0, 9) for i in range(10)]])
            nombre = random.choice(nombres)
            datos.append([numero_documento, nombre, grado, seccion, sede_id])

# Escribir archivo CSV
with open('listado_estudiantes.csv', 'w', newline='') as archivo_csv:
    escritor_csv = csv.writer(archivo_csv)
    escritor_csv.writerow(['numero_documento', 'nombre', 'grado', 'seccion', 'sede_id'])
    escritor_csv.writerows(datos)

print("Archivo CSV generado exitosamente.")
