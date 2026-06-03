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

# Pre-initialize core DataFrames to guarantee they exist in memory
df = pd.DataFrame()
working_df = pd.DataFrame()
filtered_df = pd.DataFrame()

# =============================================================================
# SMART FILE PATH FINDER (Locates CSV anywhere in the repository)
# =============================================================================
target_file = "NY-House-Dataset.csv"
actual_path = None

# Search root directory first
if os.path.exists(target_file):
    actual_path = target_file
else:
    # Scan all directories and subfolders automatically
    for root, dirs, files in os.walk("."):
        if target_file in files:
            actual_path = os.path.join(root, target_file)
            break

# If found, read and process data safely
if actual_path is not None:
    raw_df = pd.read_csv(actual_path)
    
    # Force numeric conversion to prevent map/scatter math mismatch failures
    raw_df['LATITUDE'] = pd.to_numeric(raw_df['LATITUDE'], errors='coerce')
    raw_df['LONGITUDE'] = pd.to_numeric(raw_df['LONGITUDE'], errors='coerce')
    raw_df['PRICE'] = pd.to_numeric(raw_df['PRICE'], errors='coerce')
    raw_df['PROPERTYSQFT'] = pd.to_numeric(raw_df['PROPERTYSQFT'], errors='coerce')
    
    # Clean logic: drop rows missing vital positioning or values
    df = raw_df.dropna(subset=['LATITUDE', 'LONGITUDE', 'PRICE', 'PROPERTYSQFT']).copy()
    df = df[(df['PRICE'] > 0) & (df['PROPERTYSQFT'] > 10)]
    
    # Outlier Removal (Cuts top 2% ultra-luxury extreme properties to fix chart scaling)
    if not df.empty:
        q_high = df['PRICE'].quantile(0.98)
        df = df[df['PRICE'] <= q_high].copy()
        df['PRICE_PER_SQFT'] = df['PRICE'] / df['PROPERTYSQFT']
else:
    st.error(f"⚠️ Repository Setup Error: The data file '{target_file}' could not be located anywhere in your repository folders. Please double-check your uploaded files on GitHub.")
    st.stop()

# =============================================================================
# INTERACTIVE CONTROLS (Sidebar Configuration)
# =============================================================================
st.sidebar.title("🎛️ NY CONTROL PANEL")
st.sidebar.markdown("---")

if not df.empty:
    # 1. Locality Filter Setup
    available_localities = sorted(df['SUBLOCALITY'].dropna().unique())
    selected_locality = st.sidebar.selectbox("Select Neighborhood / Borough:", ["All New York"] + list(available_localities))

    # 2. Structure Type Filter Setup
    property_types = sorted(df['TYPE'].unique())
    selected_types = st.sidebar.multiselect("Property Type:", property_types, default=property_types)

    # Apply initial filter layers
    working_df = df[df['TYPE'].isin(selected_types)].copy()
    if selected_locality != "All New York":
        working_df = working_df[working_df['SUBLOCALITY'] == selected_locality].copy()

    # 3. Dynamic Price Budget Slider Bounds Setup
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

    #
