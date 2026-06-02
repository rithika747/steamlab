from iapws import IAPWS97
import matplotlib.pyplot as plt
import matplotlib.widgets as widgets
import numpy as np

# --- Initial values ---
P_boiler_init = 10.0
T_boiler_init = 500.0
P_condenser_init = 0.1

def calculate_cycle(P_boiler, T_boiler_c, P_condenser):
    T_boiler = T_boiler_c + 273.15
    try:
        state3 = IAPWS97(P=P_boiler, T=T_boiler)
        state1 = IAPWS97(P=P_condenser, x=0)
        state4 = IAPWS97(P=P_condenser, s=state3.s)
        h1, s1 = state1.h, state1.s
        h3, s3 = state3.h, state3.s
        h4, s4 = state4.h, state4.s
        h2 = h1 + state1.v * (P_boiler - P_condenser) * 1000
        W_net = (h3 - h4) - (h2 - h1)
        Q_in = h3 - h2
        efficiency = (W_net / Q_in) * 100
        carnot = (1 - state1.T / T_boiler) * 100
        quality = state4.x
        return efficiency, carnot, quality, s1, s3, s4, state1.T, T_boiler, state3.T
    except:
        return None

def get_saturation_dome():
    temps = np.linspace(273.16, 647, 200)
    s_liq, s_vap, T_sat = [], [], []
    for T in temps:
        try:
            s_liq.append(IAPWS97(T=T, x=0).s)
            s_vap.append(IAPWS97(T=T, x=1).s)
            T_sat.append(T)
        except:
            pass
    return s_liq, s_vap, T_sat

# --- Setup figure ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))
plt.subplots_adjust(bottom=0.35)

s_liq, s_vap, T_sat = get_saturation_dome()

# Slider axes
ax_pboiler = plt.axes([0.15, 0.22, 0.50, 0.03])
ax_tboiler = plt.axes([0.15, 0.16, 0.50, 0.03])
ax_pcond   = plt.axes([0.15, 0.10, 0.50, 0.03])

s_pboiler = widgets.Slider(ax_pboiler, 'Boiler Pressure (MPa)', 1, 20, valinit=P_boiler_init)
s_tboiler = widgets.Slider(ax_tboiler, 'Boiler Temp (°C)', 300, 600, valinit=T_boiler_init)
s_pcond   = widgets.Slider(ax_pcond, 'Condenser Pressure (MPa)', 0.01, 0.5, valinit=P_condenser_init)

# Text box axes (to the right of sliders)
ax_tbox_p  = plt.axes([0.84, 0.22, 0.08, 0.03])
ax_tbox_t  = plt.axes([0.84, 0.16, 0.08, 0.03])
ax_tbox_pc = plt.axes([0.84, 0.10, 0.08, 0.03])

tbox_p  = widgets.TextBox(ax_tbox_p,  '', initial=str(P_boiler_init))
tbox_t  = widgets.TextBox(ax_tbox_t,  '', initial=str(T_boiler_init))
tbox_pc = widgets.TextBox(ax_tbox_pc, '', initial=str(P_condenser_init))

def submit_p(text):
    try: s_pboiler.set_val(float(text))
    except: pass

def submit_t(text):
    try: s_tboiler.set_val(float(text))
    except: pass

def submit_pc(text):
    try: s_pcond.set_val(float(text))
    except: pass

tbox_p.on_submit(submit_p)
tbox_t.on_submit(submit_t)
tbox_pc.on_submit(submit_pc)

def update(val):
    P_boiler = s_pboiler.val
    T_boiler_c = s_tboiler.val
    P_condenser = s_pcond.val

    result = calculate_cycle(P_boiler, T_boiler_c, P_condenser)
    if result is None:
        return

    efficiency, carnot, quality, s1, s3, s4, T1, T_boiler, T3 = result

    # --- T-s diagram ---
    ax1.cla()
    ax1.plot(s_liq, T_sat, 'b-')
    ax1.plot(s_vap, T_sat, 'b-', label='Saturation dome')
    s_cycle = [s1, s1, s3, s4, s1]
    T_cycle = [T1, T1, T_boiler, T1, T1]
    ax1.plot(s_cycle, T_cycle, 'r-o', label='Rankine cycle')
    ax1.set_xlabel("Entropy (kJ/kg·K)")
    ax1.set_ylabel("Temperature (K)")
    ax1.legend()
    ax1.grid(True)

    # Quality warning
    if quality is not None and quality < 0.85:
        ax1.set_facecolor('#ffe6e6')
        ax1.set_title(f"T-s Diagram  ⚠️ Quality = {quality:.2f} — blade damage risk!", color='red')
    else:
        ax1.set_facecolor('white')
        if quality:
            ax1.set_title(f"T-s Diagram   Quality = {quality:.2f}")

    # --- Parametric plot ---
    ax2.cla()
    pressures = np.linspace(1, 20, 50)
    effs, carnots = [], []
    T_boiler_k = T_boiler_c + 273.15
    T_cold = IAPWS97(P=P_condenser, x=0).T
    for P in pressures:
        try:
            h3_p = IAPWS97(P=P, T=T_boiler_k).h
            s3_p = IAPWS97(P=P, T=T_boiler_k).s
            h4_p = IAPWS97(P=P_condenser, s=s3_p).h
            h1_p = IAPWS97(P=P_condenser, x=0).h
            h2_p = h1_p + IAPWS97(P=P_condenser, x=0).v * (P - P_condenser) * 1000
            effs.append(((h3_p - h4_p) - (h2_p - h1_p)) / (h3_p - h2_p) * 100)
        except:
            effs.append(None)
        carnots.append((1 - T_cold / T_boiler_k) * 100)

    ax2.plot(pressures, effs, 'g-', label='Rankine Cycle')
    ax2.plot(pressures, carnots, 'r--', label='Carnot Limit')
    ax2.axvline(x=P_boiler, color='blue', linestyle=':', label=f'Current P = {P_boiler:.1f} MPa')
    ax2.set_xlabel("Boiler Pressure (MPa)")
    ax2.set_ylabel("Thermal Efficiency (%)")
    ax2.set_title(f"Efficiency vs Pressure | η = {efficiency:.2f}%")
    ax2.legend()
    ax2.grid(True)

    fig.canvas.draw_idle()

s_pboiler.on_changed(update)
s_tboiler.on_changed(update)
s_pcond.on_changed(update)

update(None)
plt.suptitle("Rankine Cycle Analyser", fontsize=14, fontweight='bold')
plt.show()