import os

import pandas as pd
import plotly.express as px
import streamlit as st


# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="NY Real Estate Hub",
    layout="wide"
)


# =============================================================================
# CUSTOM CSS THEME
# =============================================================================
st.markdown(
    """
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
    """,
    unsafe_allow_html=True
)


# =============================================================================
# FIND CSV FILE
# =============================================================================
TARGET_FILE = "NY-House-Dataset.csv"


def find_file(filename: str) -> str | None:
    """
    Search for a file in the current repository.
    Returns the path if found, otherwise None.
    """
    if os.path.exists(filename):
        return filename

    for root, dirs, files in os.walk("."):
        if filename in files:
            return os.path.join(root, filename)

    return None


csv_path = find_file(TARGET_FILE)

if csv_path is None:
    st.error(
        f"⚠️ Repository Setup Error: The file '{TARGET_FILE}' was not found. "
        "Please make sure it is uploaded to your GitHub repository."
    )
    st.stop()


# =============================================================================
# LOAD DATA
# =============================================================================
try:
    raw_df = pd.read_csv(csv_path)
except Exception as error:
    st.error(f"❌ Could not read CSV file: {error}")
    st.stop()


# =============================================================================
# VALIDATE REQUIRED COLUMNS
# =============================================================================
required_columns = [
    "LATITUDE",
    "LONGITUDE",
    "PRICE",
    "PROPERTYSQFT",
    "SUBLOCALITY",
    "TYPE",
    "LOCALITY",
]

missing_columns = [col for col in required_columns if col not in raw_df.columns]

if missing_columns:
    st.error(
        "❌ Your CSV file is missing these required columns: "
        + ", ".join(missing_columns)
    )
    st.stop()


# =============================================================================
# CLEAN DATA
# =============================================================================
df = raw_df.copy()

numeric_columns = ["LATITUDE", "LONGITUDE", "PRICE", "PROPERTYSQFT"]

for column in numeric_columns:
    df[column] = pd.to_numeric(df[column], errors="coerce")

df = df.dropna(
    subset=[
        "LATITUDE",
        "LONGITUDE",
        "PRICE",
        "PROPERTYSQFT",
        "SUBLOCALITY",
        "TYPE",
    ]
).copy()

df = df[
    (df["PRICE"] > 0)
    & (df["PROPERTYSQFT"] > 10)
    & (df["LATITUDE"].between(-90, 90))
    & (df["LONGITUDE"].between(-180, 180))
].copy()

if df.empty:
    st.error("❌ The dataset became empty after cleaning. Check your CSV values.")
    st.stop()

# Remove extreme luxury outliers for better chart scaling
price_limit = df["PRICE"].quantile(0.98)
df = df[df["PRICE"] <= price_limit].copy()

df["PRICE_PER_SQFT"] = df["PRICE"] / df["PROPERTYSQFT"]

if df.empty:
    st.error("❌ No valid data left after removing outliers.")
    st.stop()


# =============================================================================
# SIDEBAR FILTERS
# =============================================================================
st.sidebar.title("🎛️ NY CONTROL PANEL")
st.sidebar.markdown("---")

available_localities = sorted(df["SUBLOCALITY"].dropna().unique().tolist())

selected_locality = st.sidebar.selectbox(
    "Select Neighborhood / Borough:",
    ["All New York"] + available_localities
)

property_types = sorted(df["TYPE"].dropna().unique().tolist())

selected_types = st.sidebar.multiselect(
    "Property Type:",
    property_types,
    default=property_types
)

if not selected_types:
    st.warning("⚠️ Please select at least one property type in the sidebar.")
    st.stop()

working_df = df[df["TYPE"].isin(selected_types)].copy()

if selected_locality != "All New York":
    working_df = working_df[working_df["SUBLOCALITY"] == selected_locality].copy()

if working_df.empty:
    st.warning("⚠️ No properties match the selected locality and property type.")
    st.stop()

min_price = int(working_df["PRICE"].min())
max_price = int(working_df["PRICE"].max())

if min_price == max_price:
    max_price = min_price + 1

selected_budget = st.sidebar.slider(
    "Set Purchase Budget Range ($):",
    min_value=min_price,
    max_value=max_price,
    value=(min_price, max_price)
)

filtered_df = working_df[
    (working_df["PRICE"] >= selected_budget[0])
    & (working_df["PRICE"] <= selected_budget[1])
].copy()


# =============================================================================
# MAIN DASHBOARD
# =============================================================================
st.title('🌆 Urban Real Estate "Production" Analysis Dashboard')

st.markdown(
    f"""
    **Target Area:** {selected_locality}  
    **Analyzing:** {len(filtered_df):,} properties
    """
)

st.markdown("---")

if filtered_df.empty:
    st.info(
        "⚠️ No properties match your current filters. "
        "Try increasing the budget range or selecting more property types."
    )
    st.stop()


# =============================================================================
# METRICS
# =============================================================================
col1, col2, col3 = st.columns(3)

avg_price = filtered_df["PRICE"].mean()
avg_size = filtered_df["PROPERTYSQFT"].mean()
avg_cost_sqft = filtered_df["PRICE_PER_SQFT"].mean()

col1.metric("Average Property Price", f"${avg_price:,.0f}")
col2.metric("Average Property Size", f"{avg_size:,.0f} Sq Ft")
col3.metric("Avg Price per Sq Ft", f"${avg_cost_sqft:,.2f}")

st.markdown("---")


# =============================================================================
# CHARTS
# =============================================================================
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("📍 Spatial Price Distribution Map")

    fig_map = px.scatter_mapbox(
        filtered_df,
        lat="LATITUDE",
        lon="LONGITUDE",
        color="PRICE",
        color_continuous_scale=px.colors.sequential.Electric,
        zoom=10,
        hover_name="LOCALITY",
        hover_data={
            "PRICE": ":,.0f",
            "PROPERTYSQFT": ":,.0f",
            "LATITUDE": False,
            "LONGITUDE": False,
        },
    )

    fig_map.update_traces(marker=dict(size=8))

    fig_map.update_layout(
        mapbox_style="open-street-map",
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor="#161B22",
        plot_bgcolor="#161B22",
        font_color="#FFFFFF",
    )

    st.plotly_chart(fig_map, use_container_width=True)

    st.subheader("📊 Price Distribution by Property Type")

    fig_box = px.box(
        filtered_df,
        x="TYPE",
        y="PRICE",
        color="TYPE",
        color_discrete_sequence=px.colors.qualitative.Neon,
    )

    fig_box.update_layout(
        paper_bgcolor="#11151C",
        plot_bgcolor="#11151C",
        font_color="#FFFFFF",
        showlegend=False,
        xaxis_title="Property Type",
        yaxis_title="Price ($)",
    )

    st.plotly_chart(fig_box, use_container_width=True)


with chart_col2:
    st.subheader("📉 Size vs Market Price Correlation")

    fig_corr = px.scatter(
        filtered_df,
        x="PROPERTYSQFT",
        y="PRICE",
        color="PRICE_PER_SQFT",
        color_continuous_scale="Viridis",
        hover_name="LOCALITY",
        labels={
            "PROPERTYSQFT": "Property Size (Sq Ft)",
            "PRICE": "Market Price ($)",
            "PRICE_PER_SQFT": "Price per Sq Ft",
        },
    )

    fig_corr.update_layout(
        paper_bgcolor="#11151C",
        plot_bgcolor="#11151C",
        font_color="#FFFFFF",
    )

    st.plotly_chart(fig_corr, use_container_width=True)

    st.subheader("🏙️ Average Price by Neighborhood")

    neighborhood_df = (
        filtered_df.groupby("SUBLOCALITY", as_index=False)["PRICE"]
        .mean()
        .sort_values("PRICE", ascending=False)
        .head(15)
    )

    fig_bar = px.bar(
        neighborhood_df,
        x="PRICE",
        y="SUBLOCALITY",
        orientation="h",
        labels={
            "PRICE": "Average Price ($)",
            "SUBLOCALITY": "Neighborhood / Borough",
        },
    )

    fig_bar.update_layout(
        paper_bgcolor="#11151C",
        plot_bgcolor="#11151C",
        font_color="#FFFFFF",
        yaxis=dict(autorange="reversed"),
    )

    st.plotly_chart(fig_bar, use_container_width=True)


# =============================================================================
# DATA PREVIEW
# =============================================================================
st.markdown("---")
st.subheader("📋 Filtered Property Data Preview")

preview_columns = [
    "TYPE",
    "PRICE",
    "PROPERTYSQFT",
    "PRICE_PER_SQFT",
    "LOCALITY",
    "SUBLOCALITY",
]

existing_preview_columns = [
    col for col in preview_columns if col in filtered_df.columns
]

st.dataframe(
    filtered_df[existing_preview_columns].head(100),
    use_container_width=True
)
