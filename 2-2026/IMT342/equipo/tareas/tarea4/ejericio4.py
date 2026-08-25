import numpy as np
import matplotlib.pyplot as plt


# ============================================================
# CLASE QUATERNION
# Convención interna: [w, x, y, z]
# ============================================================

class Quaternion:

    def __init__(self, w, x, y, z, normalize=True):
        self.q = np.array([w, x, y, z], dtype=float)

        if normalize:
            self.normalize()

    def normalize(self):
        norma = np.linalg.norm(self.q)

        if norma < 1e-15:
            raise ValueError("No se puede normalizar un cuaternión de norma cero.")

        self.q = self.q / norma
        return self

    @property
    def w(self):
        return self.q[0]

    @property
    def x(self):
        return self.q[1]

    @property
    def y(self):
        return self.q[2]

    @property
    def z(self):
        return self.q[3]

    @property
    def vector(self):
        return self.q[1:4]

    def __repr__(self):
        return (
            f"Quaternion("
            f"w={self.w:.6f}, "
            f"x={self.x:.6f}, "
            f"y={self.y:.6f}, "
            f"z={self.z:.6f})"
        )

    # --------------------------------------------------------
    # Producto de Hamilton
    # --------------------------------------------------------

    def __mul__(self, other):

        w1, x1, y1, z1 = self.q
        w2, x2, y2, z2 = other.q

        w = (
            w1*w2
            - x1*x2
            - y1*y2
            - z1*z2
        )

        x = (
            w1*x2
            + x1*w2
            + y1*z2
            - z1*y2
        )

        y = (
            w1*y2
            - x1*z2
            + y1*w2
            + z1*x2
        )

        z = (
            w1*z2
            + x1*y2
            - y1*x2
            + z1*w2
        )

        return Quaternion(w, x, y, z)

    # --------------------------------------------------------
    # Conjugado
    # --------------------------------------------------------

    def conjugate(self):

        return Quaternion(
            self.w,
            -self.x,
            -self.y,
            -self.z,
            normalize=False
        )

    # --------------------------------------------------------
    # Producto punto
    # --------------------------------------------------------

    def dot(self, other):

        return np.dot(self.q, other.q)

    # --------------------------------------------------------
    # from_axis_angle
    # --------------------------------------------------------

    @classmethod
    def from_axis_angle(cls, axis, angle):

        axis = np.asarray(axis, dtype=float)

        norma = np.linalg.norm(axis)

        if norma < 1e-15:
            raise ValueError("El eje no puede tener norma cero.")

        axis = axis / norma

        half = angle / 2.0

        w = np.cos(half)

        xyz = axis * np.sin(half)

        return cls(
            w,
            xyz[0],
            xyz[1],
            xyz[2]
        )

    # --------------------------------------------------------
    # from_euler_zyz
    # R = Rz(phi) Ry(theta) Rz(psi)
    # --------------------------------------------------------

    @classmethod
    def from_euler_zyz(cls, phi, theta, psi):

        qz_phi = cls.from_axis_angle(
            [0, 0, 1],
            phi
        )

        qy_theta = cls.from_axis_angle(
            [0, 1, 0],
            theta
        )

        qz_psi = cls.from_axis_angle(
            [0, 0, 1],
            psi
        )

        q = qz_phi * qy_theta * qz_psi

        q.normalize()

        return q

    # --------------------------------------------------------
    # rotate_vector
    # p' = q p q*
    # --------------------------------------------------------

    def rotate_vector(self, vector):

        vector = np.asarray(vector, dtype=float)

        if vector.shape != (3,):
            raise ValueError("El vector debe tener tres componentes.")

        p_quaternion = Quaternion(
            0,
            vector[0],
            vector[1],
            vector[2],
            normalize=False
        )

        result = self * p_quaternion * self.conjugate()

        return result.q[1:4]

    # --------------------------------------------------------
    # to_rotation_matrix
    # --------------------------------------------------------

    def to_rotation_matrix(self):

        w, x, y, z = self.q

        R = np.array([

            [
                1 - 2*(y*y + z*z),
                2*(x*y - z*w),
                2*(x*z + y*w)
            ],

            [
                2*(x*y + z*w),
                1 - 2*(x*x + z*z),
                2*(y*z - x*w)
            ],

            [
                2*(x*z - y*w),
                2*(y*z + x*w),
                1 - 2*(x*x + y*y)
            ]

        ])

        return R

    # --------------------------------------------------------
    # to_ros_msg
    # ROS utiliza x, y, z, w
    # --------------------------------------------------------

    def to_ros_msg(self):

        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "w": self.w
        }


# ============================================================
# SLERP
# ============================================================

def slerp(q0, q1, t):

    q0_array = q0.q.copy()
    q1_array = q1.q.copy()

    dot = np.dot(q0_array, q1_array)

    # --------------------------------------------------------
    # Corrección antipodal:
    # q y -q representan la misma orientación
    # --------------------------------------------------------

    if dot < 0.0:

        q1_array = -q1_array

        dot = -dot

    dot = np.clip(dot, -1.0, 1.0)

    # --------------------------------------------------------
    # Si están muy cerca:
    # utilizar LERP
    # --------------------------------------------------------

    if dot > 0.9995:

        resultado = (
            (1.0 - t) * q0_array
            + t * q1_array
        )

        resultado = resultado / np.linalg.norm(resultado)

        return Quaternion(
            resultado[0],
            resultado[1],
            resultado[2],
            resultado[3]
        )

    # --------------------------------------------------------
    # SLERP normal
    # --------------------------------------------------------

    omega = np.arccos(dot)

    sin_omega = np.sin(omega)

    factor0 = np.sin((1.0 - t) * omega) / sin_omega

    factor1 = np.sin(t * omega) / sin_omega

    resultado = (
        factor0 * q0_array
        + factor1 * q1_array
    )

    resultado = resultado / np.linalg.norm(resultado)

    return Quaternion(
        resultado[0],
        resultado[1],
        resultado[2],
        resultado[3]
    )


# ============================================================
# EJERCICIO 3
# POSES INICIAL Y FINAL ZYZ
# ============================================================

phi0 = np.deg2rad(0.0)
theta0 = np.deg2rad(30.0)
psi0 = np.deg2rad(0.0)

phi1 = np.deg2rad(90.0)
theta1 = np.deg2rad(60.0)
psi1 = np.deg2rad(45.0)


q0 = Quaternion.from_euler_zyz(
    phi0,
    theta0,
    psi0
)

q1 = Quaternion.from_euler_zyz(
    phi1,
    theta1,
    psi1
)


print("=" * 70)
print("EJERCICIO 3 - SLERP")
print("=" * 70)

print("\nCuaternión inicial:")
print(q0)

print("\nCuaternión final:")
print(q1)

print("\nProducto punto q0 · q1:")
print(q0.dot(q1))


# ============================================================
# INTERPOLACIÓN
# N = 100 PASOS
# ============================================================

N = 100

t_values = np.linspace(0.0, 1.0, N)

quaternions = []

for t in t_values:

    q = slerp(q0, q1, t)

    quaternions.append(q)


# ============================================================
# COMPROBACIÓN DE NORMA UNITARIA
# ============================================================

normas = np.array([
    np.linalg.norm(q.q)
    for q in quaternions
])

print("\nNorma mínima:")
print(np.min(normas))

print("\nNorma máxima:")
print(np.max(normas))

print("\nError máximo respecto a norma 1:")
print(np.max(np.abs(normas - 1.0)))


# ============================================================
# EJERCICIO 4
# MATRICES DE ROTACIÓN
# ============================================================

R_values = np.array([
    q.to_rotation_matrix()
    for q in quaternions
])


# ============================================================
# VALIDACIÓN DE LAS MATRICES DE ROTACIÓN
# R^T R = I
# det(R) = 1
# ============================================================

errores_ortogonalidad = []

determinantes = []

for R in R_values:

    error = np.linalg.norm(
        R.T @ R - np.eye(3),
        ord='fro'
    )

    errores_ortogonalidad.append(error)

    determinantes.append(np.linalg.det(R))


errores_ortogonalidad = np.array(
    errores_ortogonalidad
)

determinantes = np.array(
    determinantes
)


print("\n" + "=" * 70)
print("VALIDACIÓN DE SO(3)")
print("=" * 70)

print("\nError máximo de ortogonalidad:")
print(np.max(errores_ortogonalidad))

print("\nDeterminante mínimo:")
print(np.min(determinantes))

print("\nDeterminante máximo:")
print(np.max(determinantes))


# ============================================================
# VELOCIDAD ANGULAR
#
# [omega(tk)]x ≈
# ((R(tk+1)-R(tk))/dt) R(tk)^T
# ============================================================

# Para realizar la gráfica se toma un intervalo de tiempo
# normalizado de 1 segundo.

tiempo = np.linspace(
    0.0,
    1.0,
    N
)

dt = tiempo[1] - tiempo[0]

omega_values = []

for k in range(N - 1):

    Rk = R_values[k]

    Rk1 = R_values[k + 1]

    dR_dt = (
        Rk1 - Rk
    ) / dt

    omega_skew = (
        dR_dt @ Rk.T
    )

    # --------------------------------------------------------
    # Extraer omega de la matriz antisimétrica
    #
    # [  0    -wz    wy ]
    # [ wz     0    -wx ]
    # [-wy    wx     0  ]
    # --------------------------------------------------------

    wx = omega_skew[2, 1]

    wy = omega_skew[0, 2]

    wz = omega_skew[1, 0]

    omega = np.array([
        wx,
        wy,
        wz
    ])

    omega_values.append(omega)


omega_values = np.array(
    omega_values
)


# ============================================================
# MAGNITUD DE LA VELOCIDAD ANGULAR
# ============================================================

omega_norm = np.linalg.norm(
    omega_values,
    axis=1
)

tiempo_omega = tiempo[:-1]


print("\n" + "=" * 70)
print("VELOCIDAD ANGULAR")
print("=" * 70)

print("\nVelocidad angular mínima:")
print(np.min(omega_norm))

print("\nVelocidad angular máxima:")
print(np.max(omega_norm))

print("\nVelocidad angular promedio:")
print(np.mean(omega_norm))


# ============================================================
# ERROR DE CONSTANCIA DE LA VELOCIDAD ANGULAR
# ============================================================

omega_promedio = np.mean(omega_norm)

error_porcentual = (
    np.abs(omega_norm - omega_promedio)
    / omega_promedio
) * 100.0

error_maximo = np.max(
    error_porcentual
)


print("\nError máximo porcentual:")
print(error_maximo, "%")


if error_maximo < 0.5:

    print("\nRESULTADO:")
    print("La velocidad angular cumple el criterio de error < 0.5 %.")

else:

    print("\nRESULTADO:")
    print("La velocidad angular NO cumple el criterio de error < 0.5 %.")


# ============================================================
# GRÁFICA 1
# MAGNITUD DE VELOCIDAD ANGULAR VS TIEMPO
# ============================================================

plt.figure(figsize=(9, 5))

plt.plot(
    tiempo_omega,
    omega_norm,
    linewidth=2
)

plt.xlabel("Tiempo [s]")

plt.ylabel("||ω(t)|| [rad/s]")

plt.title(
    "Magnitud de la velocidad angular durante SLERP"
)

plt.grid(True)

plt.tight_layout()

plt.show()


# ============================================================
# GRÁFICA 2
# ERROR PORCENTUAL DE VELOCIDAD ANGULAR
# ============================================================

plt.figure(figsize=(9, 5))

plt.plot(
    tiempo_omega,
    error_porcentual,
    linewidth=2
)

plt.axhline(
    0.5,
    linestyle="--",
    label="Límite 0.5 %"
)

plt.xlabel("Tiempo [s]")

plt.ylabel("Error [%]")

plt.title(
    "Error porcentual de la magnitud de velocidad angular"
)

plt.legend()

plt.grid(True)

plt.tight_layout()

plt.show()


# ============================================================
# EJEMPLO DE ROTACIÓN DE UN VECTOR
# ============================================================

vector = np.array([
    1.0,
    0.0,
    0.0
])

vector_rotado = q0.rotate_vector(vector)

print("\n" + "=" * 70)
print("PRUEBA DE ROTACIÓN DE VECTOR")
print("=" * 70)

print("\nVector original:")
print(vector)

print("\nVector rotado con q0:")
print(vector_rotado)


# ============================================================
# EJEMPLO DE MENSAJE ROS
# ============================================================

print("\n" + "=" * 70)
print("REPRESENTACIÓN ROS")
print("=" * 70)

print(q0.to_ros_msg())