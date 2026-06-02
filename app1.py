import streamlit as st
import pandas as pd
from iapws import IAPWS97
import plotly.graph_objects as go
import numpy as np

# 1. Page Configuration & Custom Dark Theme
st.set_page_config(page_title="SteamLab", layout="wide")
st.markdown("""
<style>
    [data-testid="stSidebar"] { border-right: 1px solid #30363d; }
    html, body, [class*="css"] { color: #e6edf3; font-family: -apple-system, sans-serif; }
    [data-testid="stMetric"] { border: 1px solid #30363d; border-radius: 8px; padding: 12px; }
    [data-testid="stMetricValue"] { color: #00b4d8 !important; }
    .stSlider [data-baseweb="slider"] [role="slider"] { background-color: #00b4d8; }
    .stSelectbox, .stNumberInput { border: 1px solid #30363d; border-radius: 6px; }
    .stSuccess { background-color: #0d2b1d; border: 1px solid #238636; color: #3fb950; }
    .stError { background-color: #2d1117; border: 1px solid #f85149; color: #f85149; }
</style>
""", unsafe_allow_html=True)

st.title("🔥 SteamLab")
st.markdown("<h4 style='color: #FF6B35;'>Interactive Rankine cycle analyser — T-s diagrams & CO₂ estimation</h4>", unsafe_allow_html=True)

# 2. Sidebar Core Inputs (Native Session State Synchronization)
st.sidebar.header("Cycle Parameters")
if "P_master" not in st.session_state: st.session_state["P_master"] = 10.0
if "T_master" not in st.session_state: st.session_state["T_master"] = 540.0
if "Cond_master" not in st.session_state: st.session_state["Cond_master"] = 0.04

p_slide = st.sidebar.slider("Boiler Pressure (MPa)", 1.0, 30.0, step=0.1, key="psl", value=st.session_state["P_master"])
t_slide = st.sidebar.slider("Boiler Temperature (°C)", 300.0, 600.0, step=1.0, key="tsl", value=st.session_state["T_master"])
c_slide = st.sidebar.slider("Condenser Pressure (MPa)", 0.005, 0.5, step=0.001, key="csl", value=st.session_state["Cond_master"])
st.sidebar.markdown("---")
p_num = st.sidebar.number_input("Or type Boiler Pressure (MPa)", 1.0, 30.0, step=0.1, key="pnm", value=st.session_state["P_master"])
t_num = st.sidebar.number_input("Or type Boiler Temp (°C)", 300.0, 600.0, step=1.0, key="tnm", value=st.session_state["T_master"])
c_num = st.sidebar.number_input("Or type Condenser Pressure (MPa)", 0.005, 0.5, step=0.001, key="cnm", value=st.session_state["Cond_master"])

# Track which input device changed and resolve to master variables
P_boiler = p_num if st.session_state.get("pnm") != st.session_state["P_master"] else p_slide
T_boiler_c = t_num if st.session_state.get("tnm") != st.session_state["T_master"] else t_slide
P_condenser = c_num if st.session_state.get("cnm") != st.session_state["Cond_master"] else c_slide

st.session_state["P_master"], st.session_state["T_master"], st.session_state["Cond_master"] = P_boiler, T_boiler_c, P_condenser

# 3. Thermodynamic Calculations Pipeline
T_boiler = T_boiler_c + 273.15
valid = False

try:
    state1 = IAPWS97(P=P_condenser, x=0)
    state3 = IAPWS97(P=P_boiler, T=T_boiler)
    state4 = IAPWS97(P=P_condenser, s=state3.s)
    
    try: quality = state4.x
    except: quality = 1.0  # Safe exit if expanded state lands outside vapor dome
    
    w_pump = state1.v * (P_boiler - P_condenser) * 1000
    h2 = state1.h + w_pump
    state2 = IAPWS97(P=P_boiler, h=h2)
    
    W_net = (state3.h - state4.h) - w_pump
    Q_in = state3.h - h2
    efficiency = (W_net / Q_in) * 100
    carnot = (1 - state1.T / T_boiler) * 100
    valid = True if Q_in > 0 and W_net > 0 else False
except:
    valid = False

# 4. Main Page Rendering
if valid:
    # Key Performance Metric Cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Thermal Efficiency", f"{efficiency:.2f}%")
    col2.metric("Carnot Limit", f"{carnot:.2f}%")
    col3.metric("Net Work", f"{W_net:.2f} kJ/kg")
    
    if quality < 0.999:
        col4.metric("Turbine Outlet Quality", f"{quality:.3f}")
        if quality < 0.85: st.error(f"⚠️ Turbine outlet quality = {quality:.3f} — blade damage risk!")
        else: st.success(f"✅ Turbine outlet quality = {quality:.3f} — safe")
    else:
        col4.metric("Turbine Outlet Quality", "Superheated")
        st.success("✅ Turbine expands into pure superheated gas — completely safe")

    # Cycle State Points Data Grid
    st.markdown("---")
    st.subheader("Cycle State Points")
    st.dataframe({
        "State": ["1 — Condenser Outlet", "2 — Pump Outlet", "3 — Boiler Outlet", "4 — Turbine Outlet"],
        "Description": ["Saturated liquid", "Compressed liquid", "Superheated vapor", "Wet Vapor" if quality < 0.999 else "Superheated vapor"],
        "Temperature (K)": [f"{state1.T:.2f}", f"{state2.T:.2f}", f"{T_boiler:.2f}", f"{state4.T:.2f}"],
        "Pressure (MPa)": [f"{P_condenser:.3f}", f"{P_boiler:.2f}", f"{P_boiler:.2f}", f"{P_condenser:.3f}"],
        "Enthalpy (kJ/kg)": [f"{state1.h:.2f}", f"{state2.h:.2f}", f"{state3.h:.2f}", f"{state4.h:.2f}"],
        "Entropy (kJ/kg·K)": [f"{state1.s:.4f}", f"{state2.s:.4f}", f"{state3.s:.4f}", f"{state4.s:.4f}"],
    }, use_container_width=True)

    # 5. Visual Interactive Plotting Panel
    col_left, col_right = st.columns(2)
    with col_left:
        fig1 = go.Figure()
        
        # Draw background saturation dome
        temps = np.linspace(273.16, 647.09, 150)
        s_liq = [IAPWS97(T=t, x=0).s for t in temps]
        s_vap = [IAPWS97(T=t, x=1).s for t in temps]
        fig1.add_trace(go.Scatter(x=s_liq, y=temps, mode='lines', name='Vapor Dome', line=dict(color='royalblue')))
        fig1.add_trace(go.Scatter(x=s_vap, y=temps, mode='lines', showlegend=False, line=dict(color='royalblue')))
        
        # Calculate precise heat addition line trace
        if P_boiler < 22.064:
            # Subcritical phase boiling plateau trace
            T_boil = IAPWS97(P=P_boiler, x=0).T
            s_boil_liq = IAPWS97(P=P_boiler, x=0).s
            s_boil_vap = IAPWS97(P=P_boiler, x=1).s
            
            s_profile = [state2.s, s_boil_liq, s_boil_vap, state3.s]
            T_profile = [state2.T, T_boil, T_boil, T_boiler]
        else:
            # Supercritical single-phase continuous heating trace
            T_super = np.linspace(state2.T, T_boiler, 40)
            s_profile = [IAPWS97(P=P_boiler, T=t).s for t in T_super]
            T_profile = list(T_super)

        # Plot full closed cycle loops
        fig1.add_trace(go.Scatter(x=s_profile, y=T_profile, mode='lines', name='Boiler Path', line=dict(color='red', width=2.5)))
        fig1.add_trace(go.Scatter(x=[state3.s, state4.s], y=[T_boiler, state4.T], mode='lines', name='Turbine', line=dict(color='red', width=2.5), showlegend=False))
        fig1.add_trace(go.Scatter(x=[state4.s, state1.s], y=[state4.T, state1.T], mode='lines', name='Condenser', line=dict(color='red', width=2.5), showlegend=False))
        fig1.add_trace(go.Scatter(x=[state1.s, state2.s], y=[state1.T, state2.T], mode='lines', name='Pump', line=dict(color='red', width=2.5), showlegend=False))

        # Overlay yellow stage identifier marks
        fig1.add_trace(go.Scatter(
            x=[state1.s, state2.s, state3.s, state4.s], y=[state1.T, state2.T, T_boiler, state4.T],
            mode='markers+text', text=['<b>1</b>', '<b>2</b>', '<b>3</b>', '<b>4</b>'],
            textposition=['bottom left', 'top left', 'top right', 'bottom right'],
            marker=dict(size=12, color='yellow', line=dict(color='black', width=1)),
            textfont=dict(color='yellow'), showlegend=False
        ))
        fig1.update_layout(title='T-s Diagram', xaxis_title='Entropy (kJ/kg·K)', yaxis_title='Temperature (K)', template='plotly_dark')
        st.plotly_chart(fig1, use_container_width=True)

    with col_right:
        # Generate Parametric Curve (Efficiency vs Pressure)
        pressures = np.linspace(1, 30, 40)
        effs, carnots = [], []
        for P in pressures:
            try:
                h3_p = IAPWS97(P=P, T=T_boiler).h
                s3_p = IAPWS97(P=P, T=T_boiler).s
                h4_p = IAPWS97(P=P_condenser, s=s3_p).h
                w_pump_p = IAPWS97(P=P_condenser, x=0).v * (P - P_condenser) * 1000
                effs.append(((h3_p - h4_p) - w_pump_p) / (h3_p - (state1.h + w_pump_p)) * 100)
            except:
                effs.append(None)
            carnots.append((1 - state1.T / T_boiler) * 100)

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=list(pressures), y=effs, mode='lines', name='Rankine Cycle', line=dict(color='limegreen')))
        fig2.add_trace(go.Scatter(x=list(pressures), y=carnots, mode='lines', name='Carnot Limit', line=dict(color='red', dash='dash')))
        fig2.add_vline(x=P_boiler, line_dash='dot', line_color='royalblue', annotation_text=f'Current P = {P_boiler:.1f} MPa')
        fig2.update_layout(title=f'Efficiency Analysis | η = {efficiency:.2f}%', xaxis_title='Boiler Pressure (MPa)', yaxis_title='Thermal Efficiency (%)', template='plotly_dark')
        st.plotly_chart(fig2, use_container_width=True)

    # 6. Environmental Emission Panel
    st.markdown("---")
    st.subheader("🌍 CO₂ Emissions Estimator")
    fuel = st.selectbox("Select fuel type", ["Coal", "Natural Gas", "Nuclear"])
    ef = {"Coal": 0.340, "Natural Gas": 0.200, "Nuclear": 0.012}[fuel]
    co2 = ef / (efficiency / 100)
    
    st.metric("CO₂ Footprint Intensity", f"{co2:.3f} kg CO₂ per kWh of electricity")
    if fuel == "Coal": st.warning("⚠️ High emissions — coal is the dirtiest power source")
    elif fuel == "Natural Gas": st.info("⚡ Moderate emissions — gas is cleaner but still fossil fuel")
    else: st.success("✅ Near-zero emissions — nuclear is the cleanest thermal cycle")
else:
    st.error("Thermodynamic state out of bounds. Please adjust cycle parameters safely.")
