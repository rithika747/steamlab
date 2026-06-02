import streamlit as st
import pandas as pd
from iapws import IAPWS97
import plotly.graph_objects as go
import numpy as np


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



st.set_page_config(page_title="SteamLab", layout="wide")
st.title("🔥 SteamLab")
st.markdown("<h4 style='color: #FF6B35;'>Interactive Rankine cycle analyser — T-s diagrams, parametric studies & CO₂ estimation</h4>", unsafe_allow_html=True)

# --- Sidebar inputs ---
st.sidebar.header("Cycle Parameters")
P_boiler = st.sidebar.slider("Boiler Pressure (MPa)", 1.0, 20.0, 10.0, 0.1)
T_boiler_c = st.sidebar.slider("Boiler Temperature (°C)", 300.0, 600.0, 500.0, 1.0)
P_condenser = st.sidebar.slider("Condenser Pressure (MPa)", 0.01, 0.5, 0.1, 0.01)

st.sidebar.markdown("---")
P_boiler = st.sidebar.number_input("Or type Boiler Pressure (MPa)", value=P_boiler, step=0.1)
T_boiler_c = st.sidebar.number_input("Or type Boiler Temp (°C)", value=T_boiler_c, step=1.0)
P_condenser = st.sidebar.number_input("Or type Condenser Pressure (MPa)", value=P_condenser, step=0.01)

# --- Calculation ---
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
    valid = True
except:
    valid = False

if valid:
    # --- Metrics ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Thermal Efficiency", f"{efficiency:.2f}%")
    col2.metric("Carnot Limit", f"{carnot:.2f}%")
    col3.metric("Net Work", f"{W_net:.2f} kJ/kg")
    col4.metric("Turbine Outlet Quality", f"{quality:.3f}")

    if quality is not None and quality < 0.85:
        st.error(f"⚠️ Turbine outlet quality = {quality:.3f} — blade damage risk!")
    else:
        st.success(f"✅ Turbine outlet quality = {quality:.3f} — safe")

    # --- Saturation dome ---
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

    s_liq, s_vap, T_sat = get_saturation_dome()

    # --- State Points Table ---
    st.markdown("---")
    st.subheader("Cycle State Points")

    state2 = IAPWS97(P=P_boiler, s=s1)

    table_data = {
        "State": ["1 — Condenser Outlet", "2 — Pump Outlet", "3 — Boiler Outlet", "4 — Turbine Outlet"],
        "Description": ["Saturated liquid", "Compressed liquid", "Superheated steam", "Wet/dry steam"],
        "Temperature (K)": [f"{state1.T:.2f}", f"{state2.T:.2f}", f"{T_boiler:.2f}", f"{state4.T:.2f}"],
        "Pressure (MPa)": [f"{P_condenser:.3f}", f"{P_boiler:.2f}", f"{P_boiler:.2f}", f"{P_condenser:.3f}"],
        "Enthalpy (kJ/kg)": [f"{h1:.2f}", f"{h2:.2f}", f"{h3:.2f}", f"{h4:.2f}"],
        "Entropy (kJ/kg·K)": [f"{s1:.4f}", f"{s1:.4f}", f"{s3:.4f}", f"{s4:.4f}"],
}

    import pandas as pd
    st.dataframe(table_data, use_container_width=True)

    # --- Plots ---
    col_left, col_right = st.columns(2)

    with col_left:
        fig1 = go.Figure()
        fig1.add_trace(go.Scatter(x=s_liq, y=T_sat, mode='lines', name='Saturation dome', line=dict(color='royalblue')))
        fig1.add_trace(go.Scatter(x=s_vap, y=T_sat, mode='lines', showlegend=False, line=dict(color='royalblue')))
        s_cycle = [s1, s1, s3, s4, s1]
        T_cycle = [state1.T, state1.T, T_boiler, state1.T, state1.T]
        fig1.add_trace(go.Scatter(x=s_cycle, y=T_cycle, mode='lines+markers', name='Rankine cycle', line=dict(color='red'), marker=dict(size=8)))
        
        # Label the 4 state points
        
        state2 = IAPWS97(P=P_boiler, h=h2)
        h2_actual = state2.h
        s2_actual = state2.s
        T2_actual = state2.T

        fig1.add_trace(go.Scatter(
            x=[s1, s2_actual, s3, s4],
            y=[state1.T, T2_actual, T_boiler, state4.T],
            mode='markers+text',
            text=['<b>1</b><br>Condenser', '<b>2</b><br>Pump', '<b>3</b><br>Boiler', '<b>4</b><br>Turbine'],
            textposition=['bottom left', 'top left', 'top center', 'bottom right'],
            marker=dict(size=12, color='yellow', symbol='circle'),
            textfont=dict(size=10, color='yellow'),
            showlegend=False,
            hoverinfo='skip'
        ))   
        fig1.update_layout(title='T-s Diagram', xaxis_title='Entropy (kJ/kg·K)', yaxis_title='Temperature (K)', template='plotly_dark')
        st.plotly_chart(fig1, use_container_width=True)

    with col_right:
        pressures = np.linspace(1, 20, 50)
        effs, carnots = [], []
        T_cold = state1.T
        for P in pressures:
            try:
                h3_p = IAPWS97(P=P, T=T_boiler).h
                s3_p = IAPWS97(P=P, T=T_boiler).s
                h4_p = IAPWS97(P=P_condenser, s=s3_p).h
                h1_p = IAPWS97(P=P_condenser, x=0).h
                h2_p = h1_p + IAPWS97(P=P_condenser, x=0).v * (P - P_condenser) * 1000
                effs.append(((h3_p - h4_p) - (h2_p - h1_p)) / (h3_p - h2_p) * 100)
            except:
                effs.append(None)
            carnots.append((1 - T_cold / T_boiler) * 100)

    

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=list(pressures), y=effs, mode='lines', name='Rankine Cycle', line=dict(color='limegreen')))
        fig2.add_trace(go.Scatter(x=list(pressures), y=carnots, mode='lines', name='Carnot Limit', line=dict(color='red', dash='dash')))
        fig2.add_vline(x=P_boiler, line_dash='dot', line_color='royalblue', annotation_text=f'Current P = {P_boiler:.1f} MPa')
        fig2.update_layout(title=f'Efficiency vs Pressure | η = {efficiency:.2f}%', xaxis_title='Boiler Pressure (MPa)', yaxis_title='Thermal Efficiency (%)', template='plotly_dark')
        st.plotly_chart(fig2, use_container_width=True)

    

    # --- CO2 Estimator ---
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