import numpy as np
import time


class Transform3D:
    """
    Representa una transformación homogénea SE(3).

    R : matriz de rotación 3x3
    p : vector de traslación 3x1
    """

    def __init__(self, R, p):
        self.R = np.asarray(R, dtype=float)
        self.p = np.asarray(p, dtype=float)

        if self.R.shape != (3, 3):
            raise ValueError("R debe ser una matriz de 3x3")

        if self.p.shape != (3,):
            raise ValueError("p debe ser un vector de 3 elementos")

        # Construcción de la matriz homogénea 4x4
        self.T = np.eye(4)
        self.T[:3, :3] = self.R
        self.T[:3, 3] = self.p

    def inv_analytic(self):
        """
        Inversa analítica de una transformación SE(3):

        T^-1 = [ R^T   -R^T p ]
               [ 0        1   ]
        """

        R_T = self.R.T
        p_inv = -R_T @ self.p

        return Transform3D(R_T, p_inv)

    def inv_generic(self):
        """
        Inversa mediante np.linalg.inv().
        """

        T_inv = np.linalg.inv(self.T)

        return Transform3D(
            T_inv[:3, :3],
            T_inv[:3, 3]
        )


# ============================================================
# EJERCICIO 1
# Matriz de transformación obtenida analíticamente
# ============================================================

R = np.array([
    [0.5, 0.0, np.sqrt(3) / 2],
    [np.sqrt(3) / 2, 0.0, -0.5],
    [0.0, 1.0, 0.0]
])

p = np.array([
    0.2 + 0.1 * np.sqrt(3),
    0.2 * np.sqrt(3) - 0.1,
    0.1
])

T = Transform3D(R, p)

print("=" * 60)
print("MATRIZ DE TRANSFORMACIÓN T")
print("=" * 60)
print(T.T)


# ============================================================
# INVERSA ANALÍTICA
# ============================================================

T_inv_analytic = T.inv_analytic()

print("\n" + "=" * 60)
print("INVERSA ANALÍTICA")
print("=" * 60)
print(T_inv_analytic.T)


# ============================================================
# INVERSA GENÉRICA
# ============================================================

T_inv_generic = T.inv_generic()

print("\n" + "=" * 60)
print("INVERSA CON np.linalg.inv()")
print("=" * 60)
print(T_inv_generic.T)


# ============================================================
# VALIDACIÓN DE LA INVERSA ANALÍTICA
# E = T * T^-1 - I
# ============================================================

I = np.eye(4)

E = T.T @ T_inv_analytic.T - I

error_frobenius = np.linalg.norm(E, ord='fro')

print("\n" + "=" * 60)
print("VALIDACIÓN DE LA INVERSA ANALÍTICA")
print("=" * 60)
print("Matriz de error E = T*T^-1 - I:")
print(E)

print("\nNorma de Frobenius:")
print(error_frobenius)

if error_frobenius < 1e-14:
    print("\nVALIDACIÓN CORRECTA: ||E||_F < 1e-14")
else:
    print("\nVALIDACIÓN NO CUMPLE: ||E||_F >= 1e-14")


# ============================================================
# COMPARACIÓN ENTRE AMBAS INVERSAS
# ============================================================

diferencia = T_inv_analytic.T - T_inv_generic.T

error_diferencia = np.linalg.norm(diferencia, ord='fro')

print("\n" + "=" * 60)
print("COMPARACIÓN ENTRE INVERSAS")
print("=" * 60)
print("Diferencia entre inversa analítica y np.linalg.inv():")
print(diferencia)

print("\nNorma de la diferencia:")
print(error_diferencia)


# ============================================================
# BENCHMARK
# 100000 inversiones
# ============================================================

N = 100000

# ------------------------------------------------------------
# Tiempo de la inversa analítica
# ------------------------------------------------------------

inicio_analitico = time.perf_counter()

for _ in range(N):
    T.inv_analytic()

fin_analitico = time.perf_counter()

tiempo_analitico = fin_analitico - inicio_analitico


# ------------------------------------------------------------
# Tiempo de np.linalg.inv()
# ------------------------------------------------------------

inicio_generico = time.perf_counter()

for _ in range(N):
    T.inv_generic()

fin_generico = time.perf_counter()

tiempo_generico = fin_generico - inicio_generico


# ============================================================
# RESULTADOS DEL BENCHMARK
# ============================================================

reduccion = (
    (tiempo_generico - tiempo_analitico)
    / tiempo_generico
) * 100

print("\n" + "=" * 60)
print("BENCHMARK: 100000 INVERSIONES")
print("=" * 60)

print(f"Tiempo inversa analítica : {tiempo_analitico:.6f} s")
print(f"Tiempo np.linalg.inv()    : {tiempo_generico:.6f} s")

print(f"\nReducción porcentual del tiempo:")
print(f"{reduccion:.2f} %")


# ============================================================
# RESUMEN FINAL
# ============================================================

print("\n" + "=" * 60)
print("RESUMEN")
print("=" * 60)

print(f"Error de Frobenius      : {error_frobenius:.3e}")
print(f"Diferencia entre métodos: {error_diferencia:.3e}")
print(f"Tiempo analítico        : {tiempo_analitico:.6f} s")
print(f"Tiempo np.linalg.inv    : {tiempo_generico:.6f} s")
print(f"Reducción de tiempo     : {reduccion:.2f} %")