import sympy as sp

# ==========================================
# EJERCICIO 2
# GIMBAL LOCK - ZYZ
# ==========================================

# Variables simbólicas
phi, theta, psi = sp.symbols(
    'phi theta psi',
    real=True
)

# ==========================================
# MATRIZ Rz(phi)
# ==========================================

Rz_phi = sp.Matrix([
    [sp.cos(phi), -sp.sin(phi), 0],
    [sp.sin(phi),  sp.cos(phi), 0],
    [0,             0,          1]
])

# ==========================================
# MATRIZ Ry(theta)
# ==========================================

Ry_theta = sp.Matrix([
    [sp.cos(theta),  0, sp.sin(theta)],
    [0,               1, 0],
    [-sp.sin(theta), 0, sp.cos(theta)]
])

# ==========================================
# MATRIZ Rz(psi)
# ==========================================

Rz_psi = sp.Matrix([
    [sp.cos(psi), -sp.sin(psi), 0],
    [sp.sin(psi),  sp.cos(psi), 0],
    [0,             0,          1]
])

# ==========================================
# MATRIZ ZYZ
# ==========================================

R_ZYZ = Rz_phi * Ry_theta * Rz_psi

print("Matriz R_ZYZ:")
sp.pprint(sp.simplify(R_ZYZ))


# ==========================================
# GIMBAL LOCK: theta = 0
# ==========================================

R_singular = R_ZYZ.subs(theta, 0)

R_singular = sp.simplify(R_singular)

print("\nMatriz R_ZYZ cuando theta = 0:")
sp.pprint(R_singular)


# ==========================================
# MATRIZ ESPERADA
# Rz(phi + psi)
# ==========================================

R_expected = sp.Matrix([
    [sp.cos(phi + psi), -sp.sin(phi + psi), 0],
    [sp.sin(phi + psi),  sp.cos(phi + psi), 0],
    [0,                   0,                  1]
])

print("\n¿R_ZYZ(theta=0) = Rz(phi+psi)?")

print(
    sp.simplify(
        R_singular - R_expected
    ) == sp.zeros(3)
)


# ==========================================
# DERIVADAS PARCIALES
# ==========================================

dR_dphi = sp.diff(R_ZYZ, phi)

dR_dpsi = sp.diff(R_ZYZ, psi)


# Evaluamos theta = 0

dR_dphi_0 = sp.simplify(
    dR_dphi.subs(theta, 0)
)

dR_dpsi_0 = sp.simplify(
    dR_dpsi.subs(theta, 0)
)

print("\nDerivada respecto a phi en theta=0:")
sp.pprint(dR_dphi_0)

print("\nDerivada respecto a psi en theta=0:")
sp.pprint(dR_dpsi_0)


# ==========================================
# COMPROBACIÓN DEL GIMBAL LOCK
# ==========================================

diferencia = sp.simplify(
    dR_dphi_0 - dR_dpsi_0
)

print("\n¿Las derivadas son iguales?")

print(
    diferencia == sp.zeros(3)
)

print("\nDiferencia:")
sp.pprint(diferencia)
print("\n¿R_singular == R_expected?")
print(R_singular == R_expected)