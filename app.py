import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Country Development Dashboard", layout="wide")

LIFE_GDP_URL = "https://ourworldindata.org/grapher/life-expectancy-vs-gdp-per-capita.csv"
POPULATION_URL = (
    "https://ourworldindata.org/grapher/population.csv"
    "?v=1&csvType=full&useColumnShortNames=false"
)


@st.cache_data
def load_data():
    """Load and prepare the Our World in Data datasets."""
    life_gdp = pd.read_csv(
        LIFE_GDP_URL,
        storage_options={"User-Agent": "Our World in Data data fetch/1.0"},
    )
    population = pd.read_csv(
        POPULATION_URL,
        storage_options={"User-Agent": "Our World in Data data fetch/1.0"},
    )

    # Identify OWID columns without relying on one exact column-name version.
    life_col = next(c for c in life_gdp.columns if "life expectancy" in c.lower())
    gdp_col = next(c for c in life_gdp.columns if "gdp per capita" in c.lower())
    pop_col = next(c for c in population.columns if "population" in c.lower())

    life_gdp = life_gdp.rename(
        columns={
            "Entity": "country",
            "Code": "code",
            "Year": "year",
            life_col: "lifeExp",
            gdp_col: "gdpPercap",
        }
    )

    population = population.rename(
        columns={
            "Entity": "country",
            "Code": "code",
            "Year": "year",
            pop_col: "pop",
        }
    )

    population = population[["country", "code", "year", "pop"]]

    df = life_gdp[
        ["country", "code", "year", "lifeExp", "gdpPercap"]
    ].merge(
        population,
        on=["country", "code", "year"],
        how="left",
    )

    # OWID's life-expectancy/GDP chart does not contain a continent column.
    # Gapminder is used only as a country-to-continent lookup so the
    # lab's required continent filter can be retained.
    continent_lookup = (
        px.data.gapminder()[["country", "continent"]]
        .drop_duplicates()
    )

    df = df.merge(continent_lookup, on="country", how="left")
    df["continent"] = df["continent"].fillna("Other/Region")

    df["year"] = pd.to_numeric(df["year"], errors="coerce")
    for col in ["lifeExp", "gdpPercap", "pop"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(
        subset=["year", "lifeExp", "gdpPercap", "pop"]
    ).copy()

    df["year"] = df["year"].astype(int)

    # The main chart uses a logarithmic GDP axis.
    df = df[df["gdpPercap"] > 0].copy()

    return df.sort_values(["year", "country"])


try:
    df = load_data()
except Exception as exc:
    st.error(
        "The dashboard could not load the Our World in Data files. "
        "Check your internet connection and try again."
    )
    st.exception(exc)
    st.stop()


st.title("Country Development Dashboard")
st.caption(
    "Our World in Data: Life Expectancy vs. GDP per Capita, "
    "with population data."
)

st.sidebar.header("Filters")

years = sorted(df["year"].unique())

selected_year = st.sidebar.select_slider(
    "Year",
    options=years,
    value=years[-1],
)

continents = sorted(df["continent"].dropna().unique())

selected_continents = st.sidebar.multiselect(
    "Continent",
    continents,
    default=continents,
)

pop_min = float(df["pop"].min())
pop_max = float(df["pop"].max())

population_threshold = st.sidebar.slider(
    "Minimum Population",
    min_value=pop_min,
    max_value=pop_max,
    value=pop_min,
    step=max((pop_max - pop_min) / 100, 1.0),
    format="%.0f",
)

filtered = df[
    (df["year"] == selected_year)
    & (df["continent"].isin(selected_continents))
    & (df["pop"] >= population_threshold)
].copy()

if filtered.empty:
    st.warning("No countries match the selected filters.")
    st.stop()


col1, col2, col3 = st.columns(3)

col1.metric(
    "Countries Shown",
    f'{filtered["country"].nunique()}',
)

# Task 4: change one KPI from average to median.
col2.metric(
    "Median Life Expectancy",
    f'{filtered["lifeExp"].median():.1f} Yrs',
)

col3.metric(
    "Total Population",
    f'{filtered["pop"].sum() / 1e9:.2f} B',
)


fig = px.scatter(
    filtered,
    x="gdpPercap",
    y="lifeExp",
    size="pop",
    color="continent",
    hover_name="country",
    log_x=True,
    size_max=60,
    title=f"GDP per Capita vs Life Expectancy - {selected_year}",
    labels={
        "gdpPercap": "GDP per Capita",
        "lifeExp": "Life Expectancy (Years)",
        "pop": "Population",
        "continent": "Continent",
    },
)

st.plotly_chart(fig, use_container_width=True)

st.subheader("Drill Down into a Country")

# Independent of the filters above.
all_countries = sorted(df["country"].dropna().unique())

country_pick = st.selectbox(
    "Choose a Country",
    all_countries,
)

country_hist = df[df["country"] == country_pick].sort_values("year")

fig2 = px.line(
    country_hist,
    x="year",
    y="lifeExp",
    markers=True,
    title=f"Life Expectancy over time - {country_pick}",
    labels={
        "year": "Year",
        "lifeExp": "Life Expectancy (Years)",
    },
)

st.plotly_chart(fig2, use_container_width=True)

st.caption(
    "Primary data source: Our World in Data. "
    "The continent lookup is retained only to preserve the lab's "
    "required filter structure."
)
