import os
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="NY Housing Market Analysis",
    page_icon="🏙️",
    layout="wide",
)


st.markdown(
    """
    <style>
    .stApp {
        background: #F7FAFC;
        color: #172033;
    }

    section[data-testid="stSidebar"] {
        background: #FFFFFF !important;
        border-right: 1px solid #E5E7EB;
    }

    h1 {
        color: #0F766E !important;
        font-weight: 900 !important;
        letter-spacing: -0.04em;
    }

    h2 {
        color: #172033 !important;
        font-weight: 800 !important;
        margin-top: 20px;
    }

    h3 {
        color: #334155 !important;
        font-weight: 700 !important;
    }

    .hero {
        background: linear-gradient(135deg, #DBEAFE 0%, #D1FAE5 100%);
        padding: 34px;
        border-radius: 28px;
        border: 1px solid #BFDBFE;
        margin-bottom: 26px;
        box-shadow: 0 18px 45px rgba(15, 118, 110, 0.10);
    }

    .hero-subtitle {
        font-size: 18px;
        color: #334155;
        max-width: 900px;
        line-height: 1.6;
    }

    .section-card {
        background: #FFFFFF;
        padding: 24px;
        border-radius: 24px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 14px 38px rgba(15, 23, 42, 0.06);
        margin-top: 22px;
        margin-bottom: 26px;
    }

    .explain {
        background: #F0F9FF;
        border-left: 5px solid #0EA5E9;
        padding: 14px 18px;
        border-radius: 14px;
        color: #334155;
        margin-bottom: 18px;
        font-size: 15px;
    }

    div[data-testid="metric-container"] {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        padding: 18px;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(15, 118, 110, 0.08);
    }

    div[data-testid="stMetricValue"] {
        color: #0F766E !important;
        font-weight: 900;
    }

    div[data-testid="stMetricLabel"] {
        color: #475569 !important;
    }

    .stDataFrame {
        border-radius: 18px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


TARGET_FILE = "NY-House-Dataset.csv"


def find_file(filename: str) -> Optional[str]:
    if os.path.exists(filename):
        return filename

    for root, dirs, files in os.walk("."):
        if filename in files:
            return os.path.join(root, filename)

    return None


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    required_columns = [
        "TYPE",
        "PRICE",
        "BEDS",
        "BATH",
        "PROPERTYSQFT",
        "LOCALITY",
        "SUBLOCALITY",
        "LATITUDE",
        "LONGITUDE",
        "ADDRESS",
    ]

    missing_columns = [col for col in required_columns if col not in df.columns]

    if missing_columns:
        st.error("Missing columns in CSV: " + ", ".join(missing_columns))
        st.stop()

    numeric_columns = [
        "PRICE",
        "BEDS",
        "BATH",
        "PROPERTYSQFT",
        "LATITUDE",
        "LONGITUDE",
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(
        subset=[
            "TYPE",
            "PRICE",
            "BEDS",
            "BATH",
            "PROPERTYSQFT",
            "LOCALITY",
            "SUBLOCALITY",
            "LATITUDE",
            "LONGITUDE",
        ]
    ).copy()

    # Automatic cleaning. The original CSV is not changed.
    df = df[df["PRICE"].between(50_000, 50_000_000)]
    df = df[df["PROPERTYSQFT"].between(100, 20_000)]
    df = df[df["BEDS"].between(0, 20)]
    df = df[df["BATH"].between(0, 20)]

    df["PRICE_PER_SQFT"] = df["PRICE"] / df["PROPERTYSQFT"]

    df = df.replace([float("inf"), -float("inf")], pd.NA)
    df = df.dropna(subset=["PRICE_PER_SQFT"]).copy()

    return df


csv_path = find_file(TARGET_FILE)

if csv_path is None:
    st.error(f"File `{TARGET_FILE}` was not found. Upload it next to `app.py`.")
    st.stop()

df = load_data(csv_path)

if df.empty:
    st.error("No valid data left after cleaning.")
    st.stop()


# SIDEBAR
st.sidebar.title("🏙️ Filters")
st.sidebar.caption("Control the housing market analysis")
st.sidebar.markdown("---")

localities = sorted(df["SUBLOCALITY"].dropna().unique())
property_types = sorted(df["TYPE"].dropna().unique())

selected_locality = st.sidebar.selectbox(
    "Neighborhood / Borough",
    ["All New York"] + list(localities),
)

selected_types = st.sidebar.multiselect(
    "Property Type",
    property_types,
    default=property_types,
)

selected_budget = st.sidebar.slider(
    "Budget Range ($)",
    min_value=int(df["PRICE"].min()),
    max_value=int(df["PRICE"].max()),
    value=(int(df["PRICE"].min()), int(df["PRICE"].max())),
)

selected_beds = st.sidebar.slider(
    "Bedrooms",
    min_value=int(df["BEDS"].min()),
    max_value=int(df["BEDS"].max()),
    value=(int(df["BEDS"].min()), int(df["BEDS"].max())),
)

selected_baths = st.sidebar.slider(
    "Bathrooms",
    min_value=int(df["BATH"].min()),
    max_value=int(df["BATH"].max()),
    value=(int(df["BATH"].min()), int(df["BATH"].max())),
)

if not selected_types:
    st.warning("Please select at least one property type.")
    st.stop()

filtered_df = df.copy()

if selected_locality != "All New York":
    filtered_df = filtered_df[filtered_df["SUBLOCALITY"] == selected_locality]

filtered_df = filtered_df[
    filtered_df["TYPE"].isin(selected_types)
    & filtered_df["PRICE"].between(selected_budget[0], selected_budget[1])
    & filtered_df["BEDS"].between(selected_beds[0], selected_beds[1])
    & filtered_df["BATH"].between(selected_baths[0], selected_baths[1])
].copy()

if filtered_df.empty:
    st.warning("No properties match the selected filters.")
    st.stop()


# HERO
st.markdown(
    """
    <div class="hero">
        <h1>🏙️ NY Housing Market Analysis</h1>
        <div class="hero-subtitle">
            This dashboard explores how location, property size, bedrooms, bathrooms,
            and property type shape real estate prices in New York.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# KPI CARDS
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

kpi1.metric("Properties", f"{len(filtered_df):,}")
kpi2.metric("Average Price", f"${filtered_df['PRICE'].mean():,.0f}")
kpi3.metric("Median Price", f"${filtered_df['PRICE'].median():,.0f}")
kpi4.metric("Average Size", f"{filtered_df['PROPERTYSQFT'].mean():,.0f} sqft")
kpi5.metric("Avg $ / sqft", f"${filtered_df['PRICE_PER_SQFT'].mean():,.0f}")


# MAP
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.header("📍 Where are expensive properties?")
st.markdown(
    """
    <div class="explain">
        Each point represents one property. Color shows price, and point size shows square footage.
        This helps identify where high-value properties are concentrated.
    </div>
    """,
    unsafe_allow_html=True,
)

fig_map = px.scatter_mapbox(
    filtered_df,
    lat="LATITUDE",
    lon="LONGITUDE",
    color="PRICE",
    size="PROPERTYSQFT",
    size_max=16,
    color_continuous_scale="Viridis",
    zoom=9,
    center={
        "lat": filtered_df["LATITUDE"].mean(),
        "lon": filtered_df["LONGITUDE"].mean(),
    },
    hover_name="ADDRESS",
    hover_data={
        "PRICE": ":,.0f",
        "PROPERTYSQFT": ":,.0f",
        "PRICE_PER_SQFT": ":,.0f",
        "TYPE": True,
        "BEDS": True,
        "BATH": True,
        "SUBLOCALITY": True,
        "LATITUDE": False,
        "LONGITUDE": False,
    },
)

fig_map.update_layout(
    mapbox_style="open-street-map",
    height=650,
    margin=dict(r=0, t=0, l=0, b=0),
)

st.plotly_chart(fig_map, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)


# SCATTER
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.header("📈 What drives price?")
st.markdown(
    """
    <div class="explain">
        This chart compares property size and market price. It supports the PRD goal
        of showing how square footage contributes to final market value.
    </div>
    """,
    unsafe_allow_html=True,
)

fig_scatter = px.scatter(
    filtered_df,
    x="PROPERTYSQFT",
    y="PRICE",
    color="PRICE_PER_SQFT",
    size="BEDS",
    color_continuous_scale="Teal",
    hover_name="ADDRESS",
    hover_data={
        "TYPE": True,
        "SUBLOCALITY": True,
        "BEDS": True,
        "BATH": True,
        "PRICE_PER_SQFT": ":,.0f",
    },
    labels={
        "PROPERTYSQFT": "Property Size (sqft)",
        "PRICE": "Market Price ($)",
        "PRICE_PER_SQFT": "$ per sqft",
    },
)

fig_scatter.update_layout(
    height=600,
    paper_bgcolor="white",
    plot_bgcolor="white",
)

st.plotly_chart(fig_scatter, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)


# NEIGHBORHOODS
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.header("🏘️ Which neighborhoods are most expensive?")
st.markdown(
    """
    <div class="explain">
        This comparison ranks neighborhoods by average property price using the filtered data.
    </div>
    """,
    unsafe_allow_html=True,
)

neighborhood_summary = (
    filtered_df.groupby("SUBLOCALITY", as_index=False)
    .agg(
        AVG_PRICE=("PRICE", "mean"),
        LISTINGS=("PRICE", "count"),
    )
    .sort_values("AVG_PRICE", ascending=False)
    .head(15)
)

fig_neighborhoods = px.bar(
    neighborhood_summary,
    x="AVG_PRICE",
    y="SUBLOCALITY",
    orientation="h",
    color="AVG_PRICE",
    color_continuous_scale="Teal",
    text="LISTINGS",
    labels={
        "AVG_PRICE": "Average Price ($)",
        "SUBLOCALITY": "Neighborhood / Borough",
        "LISTINGS": "Listings",
    },
)

fig_neighborhoods.update_layout(
    height=580,
    yaxis=dict(autorange="reversed"),
    paper_bgcolor="white",
    plot_bgcolor="white",
)

st.plotly_chart(fig_neighborhoods, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)


# PROPERTY TYPES
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.header("🏠 Which property types cost more?")
st.markdown(
    """
    <div class="explain">
        This chart compares average prices across property types, such as houses, condos, and co-ops.
    </div>
    """,
    unsafe_allow_html=True,
)

type_summary = (
    filtered_df.groupby("TYPE", as_index=False)
    .agg(
        AVG_PRICE=("PRICE", "mean"),
        LISTINGS=("PRICE", "count"),
    )
    .sort_values("AVG_PRICE", ascending=False)
)

fig_types = px.bar(
    type_summary,
    x="TYPE",
    y="AVG_PRICE",
    color="AVG_PRICE",
    color_continuous_scale="Blues",
    text="LISTINGS",
    labels={
        "TYPE": "Property Type",
        "AVG_PRICE": "Average Price ($)",
        "LISTINGS": "Listings",
    },
)

fig_types.update_layout(
    height=560,
    paper_bgcolor="white",
    plot_bgcolor="white",
    xaxis_tickangle=-35,
)

st.plotly_chart(fig_types, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)


# DATASET
st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.header("📋 Dataset")
st.markdown(
    """
    <div class="explain">
        This table shows the filtered dataset used in the visualizations.
        The CSV file is not manually edited; cleaning is applied inside the app.
    </div>
    """,
    unsafe_allow_html=True,
)

display_columns = [
    "TYPE",
    "PRICE",
    "BEDS",
    "BATH",
    "PROPERTYSQFT",
    "PRICE_PER_SQFT",
    "ADDRESS",
    "LOCALITY",
    "SUBLOCALITY",
    "LATITUDE",
    "LONGITUDE",
]

display_columns = [col for col in display_columns if col in filtered_df.columns]

st.dataframe(
    filtered_df[display_columns],
    use_container_width=True,
    height=520,
)

csv_export = filtered_df[display_columns].to_csv(index=False).encode("utf-8")

st.download_button(
    "⬇️ Download filtered dataset",
    data=csv_export,
    file_name="filtered_ny_housing_data.csv",
    mime="text/csv",
)

st.markdown("</div>", unsafe_allow_html=True)
