import streamlit as st
import pandas as pd
import plotly.express as px
import os

# =============================================================================
# UI CONFIGURATION & THEME (PRD Step 3: Dark Tech & Neon Green Aesthetic)
# =============================================================================
st.set_page_config(page_title="NY Real Estate Hub", layout="wide")

st.markdown("""
    <style>
    .stApp { 
        background-color: #0E1117; 
        color: #FFFFFF; 
    }
    section[data-testid="stSidebar"] { 
        background-color: #161B22 !important; 
    }
    h1, h2, h3 { 
        color: #00FF66 !important; 
        font-family: 'Courier New', monospace; 
    }
    div[data-testid="metric-container"] { 
        background-color: #1F242D; 
        border: 1px solid #00FF66; 
        padding: 15px; 
        border-radius: 8px; 
    }
    div[data-testid="stMetricValue"] { 
        color: #00FF66 !important; 
    }
    </style>
""", unsafe_with_html=True)

# PRE-INITIALIZE VARIABLES TO PREVENT ANY NAME_ERRORS
df = pd.DataFrame()
working_df = pd.DataFrame()
filtered_df = pd.DataFrame()

filename = "NY-House-Dataset.csv"

# =============================================================================
# SAFE DATA LOADING
# =============================================================================
if os.path.exists(filename):
    raw_df = pd.read_csv(filename)
    
    # Force numeric conversion safely
    raw_df['LATITUDE'] = pd.to_numeric(raw_df['LATITUDE'], errors='coerce')
    raw_df['LONGITUDE'] = pd.to_numeric(raw_df['LONGITUDE'], errors='coerce')
    raw_df['PRICE'] = pd.to_numeric(raw_df['PRICE'], errors='coerce')
    raw_df['PROPERTYSQFT'] = pd.to_numeric(raw_df['PROPERTYSQFT'], errors='coerce')
    
    # Clean logic
    df = raw_df.dropna(subset=['LATITUDE', 'LONGITUDE', 'PRICE', 'PROPERTYSQFT']).copy()
    df = df[(df['PRICE'] > 0) & (df['PROPERTYSQFT'] > 10)]
    
    # Anti-outlier
    if not df.empty:
        q_high = df['PRICE'].quantile(0.98)
        df = df[df['PRICE'] <= q_high].copy()
        df['PRICE_PER_SQFT'] = df['PRICE'] / df['PROPERTYSQFT']
else:
    st.error(f"Critical Error: Source dataset file '{filename}' was not found.")
    st.stop()

# =============================================================================
# INTERACTIVE CONTROLS (Sidebar Configuration)
# =============================================================================
st.sidebar.title("🎛️ NY CONTROL PANEL")
st.sidebar.markdown("---")

if not df.empty:
    # 1. Locality Filter
    available_localities = sorted(df['SUBLOCALITY'].dropna().unique())
    selected_locality = st.sidebar.selectbox("Select Neighborhood / Borough:", ["All New York"] + list(available_localities))

    # 2. Type Filter
    property_types = sorted(df['TYPE'].unique())
    selected_types = st.sidebar.multiselect("Property Type:", property_types, default=property_types)

    # Apply structural filtration
    working_df = df[df['TYPE'].isin(selected_types)].copy()
    if selected_locality != "All New York":
        working_df = working_df[working_df['SUBLOCALITY'] == selected_locality].copy()

    # 3. Dynamic Price Slider Setup
    if not working_df.empty:
        min_price = int(working_df['PRICE'].min())
        max_price = int(working_df['PRICE'].max())
    else:
        min_price, max_price = 0, 10000000

    if min_price == max_price:
        max_price += 1

    selected_budget = st.sidebar.slider(
        "Set Purchase Budget Range ($):", 
        min_value=min_price, 
        max_value=max_price, 
        value=(min_price, max_price)
    )

    # Final safe definition
    filtered_df = working_df[(working_df['PRICE'] >= selected_budget[0]) & (working_df['PRICE'] <= selected_budget[1])].copy()
else:
    selected_locality = "All New York"

# =============================================================================
# MAIN MONITOR & SUMMARY METRICS
# =============================================================================
st.title("🌆 Urban Real Estate \"Production\" Analysis Dashboard")
st.markdown(f"**Target Area:** {selected_locality} | **Analyzing:** {len(filtered_df)} properties")
st.markdown("---")

if not filtered_df.empty:
    col1, col2, col3 = st.columns(3)
    avg_price = filtered_df['PRICE'].mean()
    avg_size = filtered_df['PROPERTYSQFT'].mean()
    avg_cost_sqft = filtered_df['PRICE_PER_SQFT'].mean()
    
    col1.metric("Average Property Price", f"${avg_price:,.0f}")
    col2.metric("Average Property Size", f"{avg_size:,.0f} Sq Ft")
    col3.metric("Avg Price per Sq Ft", f"${avg_cost_sqft:,.2f}")

    st.markdown("---")
    
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("📍 Spatial Price Distribution Map")
        fig_map = px.scatter_mapbox(
            filtered_df, lat="LATITUDE", lon="LONGITUDE", color="PRICE",
            color_continuous_scale=px.colors.sequential.Electric, zoom=10, hover_name="LOCALITY",
            hover_data=["PRICE", "PROPERTYSQFT"]
        )
        fig_map.update_traces(marker=dict(size=8))
        fig_map.update_layout(
            mapbox_style="open-street-map", margin={"r":0,"t":0,"l":0,"b":0}, 
            paper_bgcolor="#161B22", plot_bgcolor="#161B22", font_color="#FFFFFF"
        )
        st.plotly_chart(fig_map, use_container_width=True)

        st.subheader("📊 Price Distribution by Property Type")
        fig_box = px.box(
            filtered_df, x="TYPE", y="PRICE", color="TYPE", 
            color_discrete_sequence=px.colors.qualitative.Neon
        )
        fig_box.update_layout(
            paper_bgcolor="#11151C", plot_bgcolor="#11151C", 
            font_color="#FFFFFF", showlegend=False
        )
        st.plotly_chart(fig_box, use_container_width=True)

    with chart_col2:
        st.subheader("📉 Size vs Market Price Correlation")
        fig_corr = px.scatter(
            filtered_df, x="PROPERTYSQFT", y="PRICE", color="PRICE_PER_SQFT", 
            color_continuous_scale="Viridis",
            labels={"PROPERTYSQFT": "Property Size (Sq Ft)", "PRICE": "Market Price ($)"}
        )
        fig_corr.update_layout(
            paper_bgcolor="#11151C", plot_bgcolor="#11151C", font_color="#FFFFFF"
        )
        st.plotly_chart(fig_corr, use_container_width=True)
else:
    st.info("⚠️ No properties match your current filter criteria settings. Please broaden your budget range or select additional property types in the control panel.")
