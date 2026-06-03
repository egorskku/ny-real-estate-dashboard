import os
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st


# =============================================================================
# PAGE CONFIG
# =============================================================================
st.set_page_config(
    page_title="NY Real Estate Dashboard",
    page_icon="🏙️",
    layout="wide",
)


# =============================================================================
# CUSTOM CSS
# =============================================================================
st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(180deg, #0E1117 0%, #111827 100%);
        color: #F9FAFB;
    }

    section[data-testid="stSidebar"] {
        background-color: #111827 !important;
        border-right: 1px solid #1F2937;
    }

    h1 {
        color: #22C55E !important;
        font-weight: 800 !important;
        letter-spacing: -0.03em;
    }

    h2, h3 {
        color: #F9FAFB !important;
        font-weight: 700 !important;
    }

    .subtitle {
        font-size: 18px;
        color: #9CA3AF;
        margin-top: -10px;
        margin-bottom: 20px;
    }

    .dashboard-card {
        background-color: #111827;
        border: 1px solid #1F2937;
        border-radius: 18px;
        padding: 22px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.25);
        margin-bottom: 18px;
    }

    div[data-testid="metric-container"] {
        background-color: #111827;
        border: 1px solid #22C55E;
        padding: 18px;
        border-radius: 16px;
        box-shadow: 0 10px 25px rgba(34,197,94,0.08);
    }

    div[data-testid="stMetricValue"] {
        color: #22C55E !important;
        font-weight: 800;
    }

    div[data-testid="stMetricLabel"] {
        color: #D1D5DB !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #111827;
        border-radius: 12px;
        color: #D1D5DB;
        border: 1px solid #1F2937;
        padding: 10px 18px;
    }

    .stTabs [aria-selected="true"] {
        background-color: #22C55E !important;
        color: #031B0D !important;
        font-weight: 800;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# FILE SEARCH
# =============================================================================
TARGET_FILE = "NY-House-Dataset.csv"


def find_file(filename: str) -> Optional[str]:
    if os.path.exists(filename):
        return filename

    for root, dirs, files in os.walk("."):
        if filename in files:
            return os.path.join(root, filename)

    return None


csv_path = find_file(TARGET_FILE)

if csv_path is None:
    st.error(
        f"⚠️ Файл `{TARGET_FILE}` не найден. "
        "Загрузи его в GitHub-репозиторий рядом с `app.py`."
    )
    st.stop()


# =============================================================================
# DATA LOADING
# =============================================================================
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    raw_df = pd.read_csv(path)

    required_columns = [
        "LATITUDE",
        "LONGITUDE",
        "PRICE",
        "PROPERTYSQFT",
        "SUBLOCALITY",
        "TYPE",
        "LOCALITY",
    ]

    missing_columns = [
        column for column in required_columns
        if column not in raw_df.columns
    ]

    if missing_columns:
        st.error(
            "⚠️ В CSV не хватает колонок: "
            + ", ".join(missing_columns)
        )
        st.stop()

    numeric_columns = [
        "LATITUDE",
        "LONGITUDE",
        "PRICE",
        "PROPERTYSQFT",
    ]

    for column in numeric_columns:
        raw_df[column] = pd.to_numeric(raw_df[column], errors="coerce")

    cleaned_df = raw_df.dropna(
        subset=[
            "LATITUDE",
            "LONGITUDE",
            "PRICE",
            "PROPERTYSQFT",
            "SUBLOCALITY",
            "TYPE",
        ]
    ).copy()

    cleaned_df = cleaned_df[
        (cleaned_df["PRICE"] > 0)
        & (cleaned_df["PROPERTYSQFT"] > 10)
    ].copy()

    if cleaned_df.empty:
        return cleaned_df

    upper_price_limit = cleaned_df["PRICE"].quantile(0.98)
    cleaned_df = cleaned_df[
        cleaned_df["PRICE"] <= upper_price_limit
    ].copy()

    cleaned_df["PRICE_PER_SQFT"] = (
        cleaned_df["PRICE"] / cleaned_df["PROPERTYSQFT"]
    )

    cleaned_df = cleaned_df.replace(
        [float("inf"), -float("inf")],
        pd.NA
    )

    cleaned_df = cleaned_df.dropna(
        subset=["PRICE_PER_SQFT"]
    ).copy()

    return cleaned_df


df = load_data(csv_path)

if df.empty:
    st.error("⚠️ После очистки данных не осталось подходящих строк.")
    st.stop()


# =============================================================================
# SIDEBAR
# =============================================================================
st.sidebar.title("🎛️ Filters")
st.sidebar.caption("Control the real estate dataset")
st.sidebar.markdown("---")

available_localities = sorted(
    df["SUBLOCALITY"].dropna().unique().tolist()
)

property_types = sorted(
    df["TYPE"].dropna().unique().tolist()
)

selected_locality = st.sidebar.selectbox(
    "Neighborhood / Borough",
    ["All New York"] + available_localities,
)

selected_types = st.sidebar.multiselect(
    "Property Type",
    property_types,
    default=property_types,
)

if not selected_types:
    st.warning("⚠️ Выбери хотя бы один тип недвижимости.")
    st.stop()

working_df = df[df["TYPE"].isin(selected_types)].copy()

if selected_locality != "All New York":
    working_df = working_df[
        working_df["SUBLOCALITY"] == selected_locality
    ].copy()

if working_df.empty:
    st.warning("⚠️ Нет объектов под выбранные фильтры.")
    st.stop()

min_price = int(working_df["PRICE"].min())
max_price = int(working_df["PRICE"].max())

if min_price == max_price:
    max_price = min_price + 1

selected_budget = st.sidebar.slider(
    "Budget Range ($)",
    min_value=min_price,
    max_value=max_price,
    value=(min_price, max_price),
)

filtered_df = working_df[
    (working_df["PRICE"] >= selected_budget[0])
    & (working_df["PRICE"] <= selected_budget[1])
].copy()

if filtered_df.empty:
    st.warning("⚠️ Нет объектов в выбранном ценовом диапазоне.")
    st.stop()


# =============================================================================
# HEADER
# =============================================================================
st.title("🏙️ NY Real Estate Analytics Dashboard")

st.markdown(
    f"""
    <div class="subtitle">
        Target area: <b>{selected_locality}</b> · 
        Properties analyzed: <b>{len(filtered_df):,}</b>
    </div>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# METRICS
# =============================================================================
avg_price = filtered_df["PRICE"].mean()
median_price = filtered_df["PRICE"].median()
avg_sqft = filtered_df["PROPERTYSQFT"].mean()
avg_price_sqft = filtered_df["PRICE_PER_SQFT"].mean()

metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

metric_col1.metric(
    "Average Price",
    f"${avg_price:,.0f}",
)

metric_col2.metric(
    "Median Price",
    f"${median_price:,.0f}",
)

metric_col3.metric(
    "Average Size",
    f"{avg_sqft:,.0f} sqft",
)

metric_col4.metric(
    "Avg $ / sqft",
    f"${avg_price_sqft:,.0f}",
)

st.markdown("---")


# =============================================================================
# TABS
# =============================================================================
tab_map, tab_charts, tab_table = st.tabs(
    ["🗺️ Map", "📊 Charts", "📋 Data"]
)


# =============================================================================
# MAP TAB
# =============================================================================
with tab_map:
    st.subheader("Property Map")

    map_center_lat = filtered_df["LATITUDE"].mean()
    map_center_lon = filtered_df["LONGITUDE"].mean()

    fig_map = px.scatter_mapbox(
        filtered_df,
        lat="LATITUDE",
        lon="LONGITUDE",
        color="PRICE",
        size="PROPERTYSQFT",
        size_max=14,
        color_continuous_scale="Viridis",
        zoom=9,
        center={
            "lat": map_center_lat,
            "lon": map_center_lon,
        },
        hover_name="LOCALITY",
        hover_data={
            "PRICE": ":,.0f",
            "PROPERTYSQFT": ":,.0f",
            "PRICE_PER_SQFT": ":,.0f",
            "TYPE": True,
            "SUBLOCALITY": True,
            "LATITUDE": False,
            "LONGITUDE": False,
        },
    )

    fig_map.update_layout(
        mapbox_style="open-street-map",
        height=620,
        margin=dict(r=0, t=0, l=0, b=0),
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font_color="#F9FAFB",
    )

    st.plotly_chart(fig_map, use_container_width=True)


# =============================================================================
# CHARTS TAB
# =============================================================================
with tab_charts:
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Price Distribution by Property Type")

        fig_box = px.box(
            filtered_df,
            x="TYPE",
            y="PRICE",
            color="TYPE",
            color_discrete_sequence=px.colors.qualitative.Plotly,
        )

        fig_box.update_layout(
            height=520,
            paper_bgcolor="#111827",
            plot_bgcolor="#111827",
            font_color="#F9FAFB",
            showlegend=False,
            xaxis_title="Property Type",
            yaxis_title="Price ($)",
        )

        st.plotly_chart(fig_box, use_container_width=True)

    with chart_col2:
        st.subheader("Size vs Price")

        fig_scatter = px.scatter(
            filtered_df,
            x="PROPERTYSQFT",
            y="PRICE",
            color="PRICE_PER_SQFT",
            color_continuous_scale="Viridis",
            hover_name="LOCALITY",
            labels={
                "PROPERTYSQFT": "Size, sqft",
                "PRICE": "Price, $",
                "PRICE_PER_SQFT": "$ / sqft",
            },
        )

        fig_scatter.update_layout(
            height=520,
            paper_bgcolor="#111827",
            plot_bgcolor="#111827",
            font_color="#F9FAFB",
        )

        st.plotly_chart(fig_scatter, use_container_width=True)

    st.markdown("---")

    st.subheader("Top Neighborhoods by Average Price")

    neighborhood_df = (
        filtered_df
        .groupby("SUBLOCALITY", as_index=False)
        .agg(
            AVG_PRICE=("PRICE", "mean"),
            COUNT=("PRICE", "count"),
        )
        .sort_values("AVG_PRICE", ascending=False)
        .head(15)
    )

    fig_bar = px.bar(
        neighborhood_df,
        x="AVG_PRICE",
        y="SUBLOCALITY",
        orientation="h",
        text="COUNT",
        labels={
            "AVG_PRICE": "Average Price ($)",
            "SUBLOCALITY": "Neighborhood / Borough",
            "COUNT": "Listings",
        },
    )

    fig_bar.update_layout(
        height=600,
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font_color="#F9FAFB",
        yaxis=dict(autorange="reversed"),
    )

    st.plotly_chart(fig_bar, use_container_width=True)


# =============================================================================
# DATA TAB
# =============================================================================
with tab_table:
    st.subheader("Filtered Property Data")

    preview_columns = [
        "TYPE",
        "PRICE",
        "PROPERTYSQFT",
        "PRICE_PER_SQFT",
        "LOCALITY",
        "SUBLOCALITY",
        "LATITUDE",
        "LONGITUDE",
    ]

    available_preview_columns = [
        column for column in preview_columns
        if column in filtered_df.columns
    ]

    display_df = filtered_df[available_preview_columns].copy()

    st.dataframe(
        display_df,
        use_container_width=True,
        height=620,
    )

    csv_export = display_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="⬇️ Download filtered data as CSV",
        data=csv_export,
        file_name="filtered_ny_real_estate.csv",
        mime="text/csv",
    )
