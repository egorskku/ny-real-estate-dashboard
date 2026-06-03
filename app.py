import streamlit as st
import pandas as pd
import plotly.express as px

# =============================================================================
# UI CONFIGURATION & THEME (PRD Step 3: Dark Tech & Neon Green Aesthetic)
# =============================================================================
st.set_page_config(page_title="NY Real Estate Hub", layout="wide")

# Custom CSS to apply dark mode and vibrant neon green styling
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

# =============================================================================
# DATA PIPELINE (Step 1: Loading & Cleaning Real-World Dataset)
# =============================================================================
@st.cache_data
def load_ny_data():
    # Read the dataset file (Must be located in the same directory as app.py)
    df = pd.read_csv("NY-House-Dataset.csv")
    
    # CRITICAL FIX: Force coordinates to be numeric and drop any rows with failed parsing
    df['LATITUDE'] = pd.to_numeric(df['LATITUDE'], errors='coerce')
    df['LONGITUDE'] = pd.to_numeric(df['LONGITUDE'], errors='coerce')
    df['PRICE'] = pd.to_numeric(df['PRICE'], errors='coerce')
    df['PROPERTYSQFT'] = pd.to_numeric(df['PROPERTYSQFT'], errors='coerce')
    
    # Drop rows missing crucial visual/numerical elements
    df = df.dropna(subset=['LATITUDE', 'LONGITUDE', 'PRICE', 'PROPERTYSQFT'])
    df = df[(df['PRICE'] > 0) & (df['PROPERTYSQFT'] > 0)]
    
    # Outlier Removal: Cut off top 2% extreme luxury properties to preserve chart scales
    q_high = df['PRICE'].quantile(0.98)
    df = df[df['PRICE'] <= q_high]
    
    # Engineer a new metric for deep production evaluation
    df['PRICE_PER_SQFT'] = df['PRICE'] / df['PROPERTYSQFT']
    return df

try:
    df = load_ny_data()

    # =============================================================================
    # INTERACTIVE CONTROLS (Sidebar Configuration)
    # =============================================================================
    st.sidebar.title("🎛️ NY CONTROL PANEL")
    st.sidebar.markdown("---")

    # Control 1: Neighborhood / Borough Dropdown Filter
    available_localities = sorted(df['SUBLOCALITY'].dropna().unique())
    selected_locality = st.sidebar.selectbox("Select Neighborhood / Borough:", ["All New York"] + list(available_localities))

    # Control 2: Multi-select Filter for Property Structure Types
    property_types = sorted(df['TYPE'].unique())
    selected_types = st.sidebar.multiselect("Property Type:", property_types, default=property_types)

    # Apply initial segment filters to safely determine dynamic slider bounds
    working_df = df[df['TYPE'].isin(selected_types)]
    if selected_locality != "All New York":
        working_df = working_df[working_df['SUBLOCALITY'] == selected_locality]

    # Control 3: Dynamic Price Range Slider
    min_price = int(working_df['PRICE'].min()) if not working_df.empty else 0
    max_price = int(working_df['PRICE'].max()) if not working_df.empty else 10000000

    selected_budget = st.sidebar.slider(
        "Set Purchase Budget Range ($):", 
        min_value=min_price, 
        max_value=max_price, 
        value=(min_price, max_price)
    )

    # Final synchronized dataframe for active rendering
    filtered_df = working_df[(working_df['PRICE'] >= selected_budget[0]) & (working_df['PRICE'] <= selected_budget[1])]

    # =============================================================================
    # MAIN MONITOR & SUMMARY METRICS
    # =============================================================================
    st.title("🌆 Urban Real Estate \"Production\" Analysis Dashboard")
    st.markdown(f"**Target Area:** {selected_locality} | **Analyzing:** {len(filtered_df)} properties")
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    if not filtered_df.empty:
        # Calculate localized analytical aggregates
        avg_price = filtered_df['PRICE'].mean()
        avg_size = filtered_df['PROPERTYSQFT'].mean()
        avg_cost_sqft = filtered_df['PRICE_PER_SQFT'].mean()
        
        col1.metric("Average Property Price", f"${avg_price:,.0f}")
        col2.metric("Average Property Size", f"{avg_size:,.0f} Sq Ft")
        col3.metric("Avg Price per Sq Ft", f"${avg_cost_sqft:,.2f}")

        st.markdown("---")
        
        # =============================================================================
        # DASHBOARD VISUALIZATIONS (3 Core Interactive Charts)
        # =============================================================================
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            # Chart 1: Spatial Geospatial Distribution Map (FIXED HOVER DATA Syntax)
            st.subheader("📍 Spatial Price Distribution Map")
            fig_map = px.scatter_mapbox(
                filtered_df, lat="LATITUDE", lon="LONGITUDE", color="PRICE", size="PROPERTYSQFT",
                color_continuous_scale=px.colors.sequential.Electric, zoom=10, hover_name="LOCALITY",
                hover_data=["PRICE", "PROPERTYSQFT"]
            )
            fig_map.update_layout(
                mapbox_style="carto-darkmatter", margin={"r":0,"t":0,"l":0,"b":0}, 
                paper_bgcolor="#161B22", plot_bgcolor="#161B22", font_color="#FFFFFF"
            )
            st.plotly_chart(fig_map, use_container_width=True)

            # Chart 2: Categorical Structural Evaluation
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
            # Chart 3: Numerical Value Mechanics Correlation Plot
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
        st.warning("No properties match your current filter criteria settings.")

except FileNotFoundError:
    st.error("Data Error: The critical data file 'NY-House-Dataset.csv' was not discovered in the root environment.")
