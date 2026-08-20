import numpy as np

# 1. Definición de las funciones de rotación (entradas en grados)
def rot_x(deg):
    rad = np.radians(deg)
    return np.array([
        [1, 0, 0],
        [0, np.cos(rad), -np.sin(rad)],
        [0, np.sin(rad), np.cos(rad)]
    ])

def rot_y(deg):
    rad = np.radians(deg)
    return np.array([
        [np.cos(rad), 0, np.sin(rad)],
        [0, 1, 0],
        [-np.sin(rad), 0, np.cos(rad)]
    ])

def rot_z(deg):
    rad = np.radians(deg)
    return np.array([
        [np.cos(rad), -np.sin(rad), 0],
        [np.sin(rad), np.cos(rad), 0],
        [0, 0, 1]
    ])

# 2. Cálculo numérico de la matriz ARB del Ejercicio 2
# Secuencia: Ry(-45) * Rx(45) * Rz(90)
R_x_45 = rot_x(45)
R_z_90 = rot_z(90)
R_y_minus_45 = rot_y(-45)

# Empleamos el operador '@' de NumPy para multiplicar matrices
ARB = R_y_minus_45 @ R_x_45 @ R_z_90

print("Matriz ARB:")
print(np.round(ARB, 4))
print("-" * 40)

# 3. Comprobación mediante la norma de Frobenius
I = np.eye(3)
frobenius_error = np.linalg.norm((ARB.T @ ARB) - I, 'fro')

print(f"Error de Norma de Frobenius: {frobenius_error}")
if frobenius_error < 1e-15:
    print("Validación de Ortogonalidad: EXITOSA (Error < 10^-15)")
else:
    print("Validación de Ortogonalidad: FALLIDA")
print("-" * 40)

# 4. Cálculo de Isometría (Conservación de Norma)
pB = np.array([[2], [-1], [4]])
pA = ARB @ pB

norm_pB = np.linalg.norm(pB)
norm_pA = np.linalg.norm(pA)
norm_difference = norm_pA - norm_pB

print(f"Norma del vector original ||pB||: {norm_pB:.6f}")
print(f"Norma del vector transformado ||pA||: {norm_pA:.6f}")
print(f"Diferencia ||pA|| - ||pB||: {norm_difference}")

if np.isclose(norm_difference, 0):
    print("Validación de Isometría: EXITOSA (La longitud del vector se conserva)")