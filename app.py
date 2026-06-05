import os
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st


st.set_page_config(
    page_title="NY Real Estate Dashboard",
    page_icon="🏙️",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background: #F6F8FB;
        color: #111827;
    }

    section[data-testid="stSidebar"] {
        background: #FFFFFF !important;
        border-right: 1px solid #E5E7EB;
    }

    h1 {
        color: #0F766E !important;
        font-weight: 850 !important;
    }

    h2, h3 {
        color: #111827 !important;
    }

    .hero {
        background: linear-gradient(135deg, #E0F2FE, #DCFCE7);
        padding: 28px;
        border-radius: 24px;
        border: 1px solid #D1FAE5;
        margin-bottom: 24px;
    }

    .hero-text {
        font-size: 18px;
        color: #374151;
    }

    div[data-testid="metric-container"] {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        padding: 18px;
        border-radius: 18px;
        box-shadow: 0 8px 24px rgba(15, 118, 110, 0.08);
    }

    div[data-testid="stMetricValue"] {
        color: #0F766E !important;
        font-weight: 800;
    }

    .info-box {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-left: 5px solid #0EA5E9;
        padding: 16px 18px;
        border-radius: 14px;
        margin-bottom: 16px;
        color: #374151;
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
            "PRICE",
            "BEDS",
            "BATH",
            "PROPERTYSQFT",
            "LATITUDE",
            "LONGITUDE",
            "TYPE",
            "LOCALITY",
            "SUBLOCALITY",
        ]
    ).copy()

    # Automatic cleaning for strange real-world outliers
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


# Sidebar
st.sidebar.title("🏙️ Filters")
st.sidebar.caption("Adjust the real estate analysis")
st.sidebar.markdown("---")

localities = sorted(df["SUBLOCALITY"].dropna().unique())
types = sorted(df["TYPE"].dropna().unique())

selected_locality = st.sidebar.selectbox(
    "Neighborhood / Borough",
    ["All New York"] + list(localities),
)

selected_types = st.sidebar.multiselect(
    "Property Type",
    types,
    default=types,
)

min_price = int(df["PRICE"].min())
max_price = int(df["PRICE"].max())

selected_budget = st.sidebar.slider(
    "Budget Range ($)",
    min_value=min_price,
    max_value=max_price,
    value=(min_price, max_price),
)

bedroom_range = st.sidebar.slider(
    "Bedrooms",
    min_value=int(df["BEDS"].min()),
    max_value=int(df["BEDS"].max()),
    value=(int(df["BEDS"].min()), int(df["BEDS"].max())),
)

bathroom_range = st.sidebar.slider(
    "Bathrooms",
    min_value=int(df["BATH"].min()),
    max_value=int(df["BATH"].max()),
    value=(int(df["BATH"].min()), int(df["BATH"].max())),
)

filtered_df = df.copy()

if selected_locality != "All New York":
    filtered_df = filtered_df[filtered_df["SUBLOCALITY"] == selected_locality]

filtered_df = filtered_df[
    filtered_df["TYPE"].isin(selected_types)
    & filtered_df["PRICE"].between(selected_budget[0], selected_budget[1])
    & filtered_df["BEDS"].between(bedroom_range[0], bedroom_range[1])
    & filtered_df["BATH"].between(bathroom_range[0], bathroom_range[1])
].copy()

if filtered_df.empty:
    st.warning("No properties match your filters. Try changing the sidebar filters.")
    st.stop()


# Header
st.markdown(
    """
    <div class="hero">
        <h1>NY Real Estate Analytics Dashboard</h1>
        <div class="hero-text">
            Explore how location, property size, bedrooms, bathrooms, and property type affect housing prices in New York.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# Metrics
col1, col2, col3, col4, col5 = st.columns(5)

col1.metric("Properties", f"{len(filtered_df):,}")
col2.metric("Average Price", f"${filtered_df['PRICE'].mean():,.0f}")
col3.metric("Median Price", f"${filtered_df['PRICE'].median():,.0f}")
col4.metric("Average Size", f"{filtered_df['PROPERTYSQFT'].mean():,.0f} sqft")
col5.metric("Avg $ / sqft", f"${filtered_df['PRICE_PER_SQFT'].mean():,.0f}")


tab_overview, tab_map, tab_analysis, tab_data = st.tabs(
    ["📌 Overview", "🗺️ Map", "📊 Analysis", "📋 Data"]
)


with tab_overview:
    st.markdown(
        """
        <div class="info-box">
        <b>What this page shows:</b> a quick summary of the filtered real estate market.
        It helps answer: which neighborhoods and property types are most expensive?
        </div>
        """,
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)

    with left:
        neighborhood_summary = (
            filtered_df.groupby("SUBLOCALITY", as_index=False)
            .agg(
                AVG_PRICE=("PRICE", "mean"),
                LISTINGS=("PRICE", "count"),
            )
            .sort_values("AVG_PRICE", ascending=False)
            .head(10)
        )

        fig_neighborhoods = px.bar(
            neighborhood_summary,
            x="AVG_PRICE",
            y="SUBLOCALITY",
            orientation="h",
            text="LISTINGS",
            color="AVG_PRICE",
            color_continuous_scale="Teal",
            labels={
                "AVG_PRICE": "Average Price ($)",
                "SUBLOCALITY": "Neighborhood",
                "LISTINGS": "Listings",
            },
            title="Top 10 Neighborhoods by Average Price",
        )

        fig_neighborhoods.update_layout(
            yaxis=dict(autorange="reversed"),
            height=520,
            paper_bgcolor="white",
            plot_bgcolor="white",
        )

        st.plotly_chart(fig_neighborhoods, use_container_width=True)

    with right:
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
            title="Average Price by Property Type",
        )

        fig_types.update_layout(
            height=520,
            paper_bgcolor="white",
            plot_bgcolor="white",
            xaxis_tickangle=-35,
        )

        st.plotly_chart(fig_types, use_container_width=True)


with tab_map:
    st.markdown(
        """
        <div class="info-box">
        <b>What this map shows:</b> each point is a property. 
        Color shows price, and point size shows property square footage.
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
        size_max=15,
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
            "BEDS": True,
            "BATH": True,
            "TYPE": True,
            "SUBLOCALITY": True,
            "LATITUDE": False,
            "LONGITUDE": False,
        },
        title="Spatial Distribution of Property Prices",
    )

    fig_map.update_layout(
        mapbox_style="open-street-map",
        height=680,
        margin=dict(r=0, t=40, l=0, b=0),
    )

    st.plotly_chart(fig_map, use_container_width=True)


with tab_analysis:
    st.markdown(
        """
        <div class="info-box">
        <b>What this page shows:</b> relationships between price, size, bedrooms, bathrooms, and property type.
        This is the main analysis section.
        </div>
        """,
        unsafe_allow_html=True,
    )

    row1_col1, row1_col2 = st.columns(2)

    with row1_col1:
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
                "PRICE": "Price ($)",
                "PRICE_PER_SQFT": "$ per sqft",
            },
            title="Property Size vs Market Price",
        )

        fig_scatter.update_layout(
            height=540,
            paper_bgcolor="white",
            plot_bgcolor="white",
        )

        st.plotly_chart(fig_scatter, use_container_width=True)

    with row1_col2:
        fig_box = px.box(
            filtered_df,
            x="TYPE",
            y="PRICE",
            color="TYPE",
            color_discrete_sequence=px.colors.qualitative.Set2,
            labels={
                "TYPE": "Property Type",
                "PRICE": "Price ($)",
            },
            title="Price Distribution by Property Type",
        )

        fig_box.update_layout(
            height=540,
            paper_bgcolor="white",
            plot_bgcolor="white",
            showlegend=False,
            xaxis_tickangle=-35,
        )

        st.plotly_chart(fig_box, use_container_width=True)

    row2_col1, row2_col2 = st.columns(2)

    with row2_col1:
        bedroom_summary = (
            filtered_df.groupby("BEDS", as_index=False)
            .agg(
                AVG_PRICE=("PRICE", "mean"),
                LISTINGS=("PRICE", "count"),
            )
            .sort_values("BEDS")
        )

        fig_beds = px.line(
            bedroom_summary,
            x="BEDS",
            y="AVG_PRICE",
            markers=True,
            text="LISTINGS",
            labels={
                "BEDS": "Bedrooms",
                "AVG_PRICE": "Average Price ($)",
                "LISTINGS": "Listings",
            },
            title="Average Price by Number of Bedrooms",
        )

        fig_beds.update_layout(
            height=480,
            paper_bgcolor="white",
            plot_bgcolor="white",
        )

        st.plotly_chart(fig_beds, use_container_width=True)

    with row2_col2:
        bathroom_summary = (
            filtered_df.groupby("BATH", as_index=False)
            .agg(
                AVG_PRICE=("PRICE", "mean"),
                LISTINGS=("PRICE", "count"),
            )
            .sort_values("BATH")
        )

        fig_baths = px.line(
            bathroom_summary,
            x="BATH",
            y="AVG_PRICE",
            markers=True,
            text="LISTINGS",
            labels={
                "BATH": "Bathrooms",
                "AVG_PRICE": "Average Price ($)",
                "LISTINGS": "Listings",
            },
            title="Average Price by Number of Bathrooms",
        )

        fig_baths.update_layout(
            height=480,
            paper_bgcolor="white",
            plot_bgcolor="white",
        )

        st.plotly_chart(fig_baths, use_container_width=True)


with tab_data:
    st.markdown(
        """
        <div class="info-box">
        <b>What this table shows:</b> the filtered dataset used to build the charts above.
        The original CSV is not manually edited; cleaning happens automatically in the app.
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
        height=620,
    )

    csv_export = filtered_df[display_columns].to_csv(index=False).encode("utf-8")

    st.download_button(
        "⬇️ Download filtered data",
        data=csv_export,
        file_name="filtered_ny_real_estate.csv",
        mime="text/csv",
    )
