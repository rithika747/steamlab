import streamlit as st
import pandas as pd
from iapws import IAPWS97
import plotly.graph_objects as go
import numpy as np

# Page Configuration 
st.set_page_config(page_title="SteamLab", layout="wide")

st.markdown("""
<style>
    /* Sidebar */
    [data-testid="stSidebar"] {
        border-right: 1px solid #30363d;
    }
    
    /* All text */
    html, body, [class*="css"] {
        color: #e6edf3;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    /* Metric cards */
    [data-testid="stMetric"] {
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px;
    }
    
    /* Metric value color */
    [data-testid="stMetricValue"] {
        color: #00b4d8 !important;
    }
    
    /* Slider color */
    .stSlider [data-baseweb="slider"] [role="slider"] {
        background-color: #00b4d8;
    }
    
    /* Buttons and selectbox */
    .stSelectbox, .stNumberInput {
        border: 1px solid #30363d;
        border-radius: 6px;
    }

    /* Success/error banners */
    .stSuccess {
        background-color: #0d2b1d;
        border: 1px solid #238636;
        color: #3fb950;
    }
    .stError {
        background-color: #2d1117;
        border: 1px solid #f85149;
        color: #f85149;
    }
    
    /* Divider */
    hr {
        border-color: #30363d;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔥 SteamLab")
st.markdown("<h4 style='color: #FF6B35;'>Interactive Rankine cycle analyser — T-s diagrams, parametric studies & CO₂ estimation</h4>", unsafe_allow_html=True)

# Sidebar Inputs 
st.sidebar.header("Cycle Parameters")
P_boiler = st.sidebar.slider("Boiler Pressure (MPa)", 1.0, 20.0, 10.0, 0.1)
T_boiler_c = st.sidebar.slider("Boiler Temperature (°C)", 300.0, 600.0, 500.0, 1.0)
P_condenser = st.sidebar.slider("Condenser Pressure (MPa)", 0.01, 0.5, 0.1, 0.01)

st.sidebar.markdown("---")
P_boiler = st.sidebar.number_input("Or type Boiler Pressure (MPa)", value=P_boiler, step=0.1)
T_boiler_c = st.sidebar.number_input("Or type Boiler Temp (°C)", value=T_boiler_c, step=1.0)
P_condenser = st.sidebar.number_input("Or type Condenser Pressure (MPa)", value=P_condenser, step=0.01)

# Thermodynamic Calculations
T_boiler = T_boiler_c + 273.15
valid = False

try:
    # State 1: Condenser Outlet / Pump Inlet (Saturated Liquid at P_condenser)
    state1 = IAPWS97(P=P_condenser, x=0)
    h1, s1 = state1.h, state1.s
    
    # State 3: Boiler Outlet / Turbine Inlet (Superheated Steam at P_boiler, T_boiler)
    state3 = IAPWS97(P=P_boiler, T=T_boiler)
    h3, s3 = state3.h, state3.s
    
    # State 4: Turbine Outlet / Condenser Inlet (Isentropic Expansion: s4 = s3 at P_condenser)
    state4 = IAPWS97(P=P_condenser, s=s3)
    h4, s4 = state4.h, state4.s
    quality = state4.x
    
    # State 2: Pump Outlet / Boiler Inlet (Compressed Liquid)
    # Re-calculating using standard open-system pump work formula: w_pump = v1 * (P_boiler - P_condenser)
    w_pump = state1.v * (P_boiler - P_condenser) * 1000
    h2 = h1 + w_pump
    state2_actual = IAPWS97(P=P_boiler, h=h2)
    s2_actual = state2_actual.s
    T2_actual = state2_actual.T
    
    # Performance Parameters
    W_net = (h3 - h4) - w_pump
    Q_in = h3 - h2
    efficiency = (W_net / Q_in) * 100
    carnot = (1 - state1.T / T_boiler) * 100
    
    if Q_in > 0 and W_net > 0:
        valid = True
except:
    valid = False

if valid:
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Thermal Efficiency", f"{efficiency:.2f}%")
    col2.metric("Carnot Limit", f"{carnot:.2f}%")
    col3.metric("Net Work", f"{W_net:.2f} kJ/kg")
    col4.metric("Turbine Outlet Quality", f"{quality:.3f}")

    if quality is not None and quality < 0.85:
        st.error(f"⚠️ Turbine outlet quality = {quality:.3f} — blade damage risk!")
    else:
        st.success(f"✅ Turbine outlet quality = {quality:.3f} — safe")

    # Saturation Dome
    def get_saturation_dome():
        temps = np.linspace(273.16, 647.09, 200)
        s_liq_arr, s_vap_arr, T_sat_arr = [], [], []
        for T in temps:
            try:
                s_liq_arr.append(IAPWS97(T=T, x=0).s)
                s_vap_arr.append(IAPWS97(T=T, x=1).s)
                T_sat_arr.append(T)
            except:
                pass
        return s_liq_arr, s_vap_arr, T_sat_arr

    s_liq, s_vap, T_sat = get_saturation_dome()

    # State Points Table
    st.markdown("---")
    st.subheader("Cycle State Points")

    table_data = {
        "State": ["1 — Condenser Outlet", "2 — Pump Outlet", "3 — Boiler Outlet", "4 — Turbine Outlet"],
        "Description": ["Saturated liquid", "Compressed liquid", "Superheated steam", "Wet/dry steam" if quality is not None else "Superheated steam"],
        "Temperature (K)": [f"{state1.T:.2f}", f"{T2_actual:.2f}", f"{T_boiler:.2f}", f"{state4.T:.2f}"],
        "Pressure (MPa)": [f"{P_condenser:.3f}", f"{P_boiler:.2f}", f"{P_boiler:.2f}", f"{P_condenser:.3f}"],
        "Enthalpy (kJ/kg)": [f"{h1:.2f}", f"{h2:.2f}", f"{h3:.2f}", f"{h4:.2f}"],
        "Entropy (kJ/kg·K)": [f"{s1:.4f}", f"{s2_actual:.4f}", f"{s3:.4f}", f"{s4:.4f}"],
    }
    st.dataframe(table_data, use_container_width=True)

    # PLots
    col_left, col_right = st.columns(2)

    with col_left:
        fig1 = go.Figure()
        
        # 1. Plot the Saturation Dome background
        fig1.add_trace(go.Scatter(x=s_liq, y=T_sat, mode='lines', name='Saturation dome', line=dict(color='royalblue')))
        fig1.add_trace(go.Scatter(x=s_vap, y=T_sat, mode='lines', showlegend=False, line=dict(color='royalblue')))
        
        # 2. Extract specific actual fluid properties for the boiler paths
        state2_actual = IAPWS97(P=P_boiler, h=h2)
        s2_actual = state2_actual.s
        T2_actual = state2_actual.T

        state_sat_liq = IAPWS97(P=P_boiler, x=0)
        T_sat_boiler = state_sat_liq.T
        
        # 3. Mathematically generate the true Boiler Heating Profiles
        if P_boiler < 22.06:
            # Subcritical Path: Sensible heating -> Horizontal boiling plateau -> Superheating
            T_sensible = np.linspace(T2_actual, T_sat_boiler, 20)
            s_sensible = [IAPWS97(P=P_boiler, T=t).s for t in T_sensible]
            
            x_boil = np.linspace(0, 1, 20)
            s_boiling = [IAPWS97(P=P_boiler, x=x).s for x in x_boil]
            T_boiling = [T_sat_boiler] * 20
            
            T_superheat = np.linspace(T_sat_boiler, T_boiler, 20)
            s_superheat = [IAPWS97(P=P_boiler, T=t).s for t in T_superheat]
            
            s_boiler_profile = np.concatenate([s_sensible, s_boiling, s_superheat])
            T_boiler_profile = np.concatenate([T_sensible, T_boiling, T_superheat])
            # Sort both arrays together by ascending entropy to eliminate the zigzag loop
            sort_indices = np.argsort(s_boiler_profile)
            s_boiler_profile = s_boiler_profile[sort_indices]
            T_boiler_profile = T_boiler_profile[sort_indices]
        else:
            # Supercritical Path: Continuous upward fluid expansion past the critical ceiling
            T_supercritical = np.linspace(T2_actual, T_boiler, 50)
            s_boiler_profile = [IAPWS97(P=P_boiler, T=t).s for t in T_supercritical]
            T_boiler_profile = T_supercritical

        # 4. Plot the Four Separate Cycle Tracks to Prevent Coordinate Cross-Jumps
        # Segment A: The Boiler Curve (State 2 -> State 3)
        fig1.add_trace(go.Scatter(
            x=list(s_boiler_profile), 
            y=list(T_boiler_profile), 
            mode='lines', 
            name='Rankine cycle', 
            line=dict(color='red', width=2.5),
            legendgroup="cycle"
        ))
        
        # Segment B: Turbine Expansion (State 3 -> State 4)
        fig1.add_trace(go.Scatter(
            x=[s3, s4], 
            y=[T_boiler, state4.T], 
            mode='lines', 
            line=dict(color='red', width=2.5),
            showlegend=False,
            legendgroup="cycle"
        ))
        
        # Segment C: Condenser Rejection (State 4 -> State 1)
        fig1.add_trace(go.Scatter(
            x=[s4, s1], 
            y=[state4.T, state1.T], 
            mode='lines', 
            line=dict(color='red', width=2.5),
            showlegend=False,
            legendgroup="cycle"
        ))
        
        # Segment D: Pump Compression (State 1 -> State 2)
        fig1.add_trace(go.Scatter(
            x=[s1, s2_actual], 
            y=[state1.T, T2_actual], 
            mode='lines', 
            line=dict(color='red', width=2.5),
            showlegend=False,
            legendgroup="cycle"
        ))

        # 5. Overlay the clean, yellow component marker dots with clockwise label formatting
        fig1.add_trace(go.Scatter(
            x=[s1, s2_actual, s3, s4],
            y=[state1.T, T2_actual, T_boiler, state4.T],
            mode='markers+text',
            text=['<b>1</b><br>Condenser Outlet', '<b>2</b><br>Pump Outlet', '<b>3</b><br>Boiler Outlet', '<b>4</b><br>Turbine Outlet'],
            textposition=['bottom left', 'top left', 'top right', 'bottom right'],
            marker=dict(size=12, color='yellow', symbol='circle', line=dict(color='black', width=1)),
            textfont=dict(size=10, color='yellow'),
            showlegend=False,
            hoverinfo='skip'
        ))   
        
        # 6. Apply dark theme styling configuration
        fig1.update_layout(
            title='T-s Diagram', 
            xaxis_title='Entropy (kJ/kg·K)', 
            yaxis_title='Temperature (K)', 
            template='plotly_dark'
        )
        st.plotly_chart(fig1, use_container_width=True)

    with col_right:
        # Parametric Study Plot 
        pressures = np.linspace(1, 20, 50)
        effs, carnots = [], []
        T_cold = state1.T
        
        for P in pressures:
            try:
                h3_p = IAPWS97(P=P, T=T_boiler).h
                s3_p = IAPWS97(P=P, T=T_boiler).s
                h4_p = IAPWS97(P=P_condenser, s=s3_p).h
                h1_p = IAPWS97(P=P_condenser, x=0).h
                w_pump_p = IAPWS97(P=P_condenser, x=0).v * (P - P_condenser) * 1000
                h2_p = h1_p + w_pump_p
                effs.append(((h3_p - h4_p) - w_pump_p) / (h3_p - h2_p) * 100)
            except:
                effs.append(None)
            carnots.append((1 - T_cold / T_boiler) * 100)

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=list(pressures), y=effs, mode='lines', name='Rankine Cycle', line=dict(color='limegreen')))
        fig2.add_trace(go.Scatter(x=list(pressures), y=carnots, mode='lines', name='Carnot Limit', line=dict(color='red', dash='dash')))
        fig2.add_vline(x=P_boiler, line_dash='dot', line_color='royalblue', annotation_text=f'Current P = {P_boiler:.1f} MPa')
        fig2.update_layout(title=f'Efficiency vs Pressure | η = {efficiency:.2f}%', xaxis_title='Boiler Pressure (MPa)', yaxis_title='Thermal Efficiency (%)', template='plotly_dark')
        st.plotly_chart(fig2, use_container_width=True)

    # CO2 Estimator
    st.markdown("---")
    st.subheader("🌍 CO₂ Emissions Estimator")
    fuel = st.selectbox("Select fuel type", ["Coal", "Natural Gas", "Nuclear"])
    emission_factors = {"Coal": 0.340, "Natural Gas": 0.200, "Nuclear": 0.012}
    ef = emission_factors[fuel]
    co2 = ef / (efficiency / 100)
    st.metric("CO₂ Emissions", f"{co2:.3f} kg CO₂ per kWh of electricity")
    if fuel == "Coal":
        st.warning("⚠️ High emissions — coal is the dirtiest power source")
    elif fuel == "Natural Gas":
        st.info("⚡ Moderate emissions — gas is cleaner but still fossil fuel")
    else:
        st.success("✅ Near-zero emissions — nuclear is the cleanest thermal cycle")

else:
    st.error("Invalid inputs — try reducing boiler temperature or adjusting pressures.")