from iapws import IAPWS97

print("=== Rankine Cycle Efficiency Calculator ===")
P_boiler = float(input("Enter boiler pressure (MPa): "))
T_boiler = float(input("Enter boiler temperature (°C): ")) + 273.15
P_condenser = float(input("Enter condenser pressure (MPa): "))

# --- State 3: Boiler outlet (superheated steam) ---
state3 = IAPWS97(P=P_boiler, T=T_boiler)
h3 = state3.h
s3 = state3.s

# --- State 1: Condenser outlet (saturated liquid) ---
state1 = IAPWS97(P=P_condenser, x=0)
h1 = state1.h
s1 = state1.s

# --- State 4: Turbine outlet (isentropic expansion) ---
state4 = IAPWS97(P=P_condenser, s=s3)
h4 = state4.h

# --- Turbine Quality Warning ---
if state4.x is not None and state4.x < 0.85:
    print(f"⚠️  WARNING: Turbine outlet quality = {state4.x:.3f} — blade damage risk!")
else:
    print(f"✅ Turbine outlet quality = {state4.x:.3f} — safe")


# --- State 2: Pump outlet (isentropic compression) ---
v1 = state1.v
pump_work = v1 * (P_boiler - P_condenser) * 1000
h2 = h1 + pump_work

# --- Cycle Performance ---
W_turbine = h3 - h4
W_pump = h2 - h1
Q_in = h3 - h2
W_net = W_turbine - W_pump
efficiency = (W_net / Q_in) * 100

print(f"\nh1: {h1:.2f}, h2: {h2:.2f}, h3: {h3:.2f}, h4: {h4:.2f}")
print(f"Turbine work: {W_turbine:.2f} kJ/kg")
print(f"Pump work: {W_pump:.2f} kJ/kg")
print(f"Heat input: {Q_in:.2f} kJ/kg")
print(f"Net work: {W_net:.2f} kJ/kg")
print(f"Thermal efficiency: {efficiency:.2f}%")

# --- CO2 Emissions Estimator ---
print("\n=== CO2 Emissions Estimator ===")
print("Select fuel type:")
print("1. Coal")
print("2. Natural Gas")
print("3. Nuclear")
fuel = input("Enter 1, 2 or 3: ")

# kg CO2 per kWh of heat input (emission factors)
emission_factors = {
    "1": ("Coal", 0.340),
    "2": ("Natural Gas", 0.200),
    "3": ("Nuclear", 0.012)
}

fuel_name, ef = emission_factors[fuel]

# CO2 per kWh of electricity output
co2_per_kwh = ef / (efficiency / 100)

print(f"\nFuel: {fuel_name}")
print(f"Cycle efficiency: {efficiency:.2f}%")
print(f"CO2 emissions: {co2_per_kwh:.3f} kg CO2 per kWh of electricity")

if fuel == "1":
    print("⚠️  High emissions — coal is the dirtiest power source")
elif fuel == "2":
    print("⚡ Moderate emissions — gas is cleaner but still fossil fuel")
else:
    print("✅ Near-zero emissions — nuclear is the cleanest thermal cycle")

import matplotlib.pyplot as plt
import numpy as np

# --- T-s Diagram ---
# Saturation dome
sat_temps = np.linspace(273.16, 647, 200)
s_liq, s_vap = [], []
for T in sat_temps:
    sat = IAPWS97(T=T, x=0)
    sat_v = IAPWS97(T=T, x=1)
    s_liq.append(sat.s)
    s_vap.append(sat_v.s)

# Cycle state points (s, T)
s_points = [s1, s1, s3, s3, s1]
T_points = [state1.T, state1.T, T_boiler, state4.T, state1.T]

plt.figure(figsize=(8, 6))
plt.plot(s_liq, sat_temps, 'b-', label='Saturation dome')
plt.plot(s_vap, sat_temps, 'b-')
plt.plot(s_points, T_points, 'r-o', label='Rankine cycle')
plt.xlabel("Entropy (kJ/kg·K)")
plt.ylabel("Temperature (K)")
plt.title("Rankine Cycle T-s Diagram")
plt.legend()
plt.grid(True)
plt.show()

# --- Parametric Study: Efficiency vs Boiler Pressure ---
pressures = np.linspace(1, 20, 50)
efficiencies = []
carnot_effs = []

for P in pressures:
    try:
        h3_p = IAPWS97(P=P, T=T_boiler).h
        s3_p = IAPWS97(P=P, T=T_boiler).s
        h4_p = IAPWS97(P=P_condenser, s=s3_p).h
        h2_p = h1 + IAPWS97(P=P_condenser, x=0).v * (P - P_condenser) * 1000
        eff = ((h3_p - h4_p) - (h2_p - h1)) / (h3_p - h2_p) * 100
        efficiencies.append(eff)
    except:
        efficiencies.append(None)

    carnot = (1 - state1.T / T_boiler) * 100
    carnot_effs.append(carnot)

plt.figure(figsize=(8, 6))
plt.plot(pressures, efficiencies, 'g-', label='Rankine Cycle')
plt.plot(pressures, carnot_effs, 'r--', label='Carnot Limit')
plt.xlabel("Boiler Pressure (MPa)")
plt.ylabel("Thermal Efficiency (%)")
plt.title(f"Efficiency vs Boiler Pressure (T_boiler = {T_boiler - 273.15:.0f}°C)")
plt.legend()
plt.grid(True)
plt.show()