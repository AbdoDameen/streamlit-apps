# Streamlit Apps

12 serious data web apps built with Streamlit and free public APIs.

Deployed at: https://share.streamlit.io/user/abdodameen

## Apps

| App | API | Description |
|---|---|---|
| [Sydney Weather](/sydney-weather) | Open-Meteo | Real-time weather with 7-day forecast |
| [SpaceX Launches](/spacex-launches) | SpaceX API | Launch history, vehicles, stats |
| [Country Explorer](/country-explorer) | REST Countries | Country data with pygwalker viz |
| [Bitcoin Dashboard](/bitcoin-dashboard) | CoinDesk | Live BTC price + pygwalker trends |
| [Flight Tracker](/flight-tracker) | OpenSky Network | Real-time ADS-B aircraft tracking |
| [Earthquake Monitor](/earthquake-monitor) | USGS | Live quakes with heatmap |
| [Global CO₂ Emissions](/global-co2-emissions) | World Bank | CO₂ data with pygwalker |
| [Stock Market Trends](/stock-market) | Alpha Vantage | Market movers and history |
| [NASA APOD](/nasa-apod) | NASA API | Daily astronomy picture |
| [Vehicle Safety Recalls](/vehicle-safety-recalls) | NHTSA | Recalls by make/model/year |
| [Train Schedules](/train-schedules) | transport.rest | Live European rail departures |
| [World Population & GDP](/world-population-gdp) | World Bank | Economic indicators + pygwalker |

## Deploy

Each subfolder is a standalone Streamlit app. To deploy:

1. Push this repo to GitHub
2. Go to share.streamlit.io
3. Connect your GitHub account
4. Deploy each subfolder individually:
   - Repo: `AbdoDameen/streamlit-apps`
   - Branch: `main`
   - Path: e.g. `sydney-weather/`
   - Python version: 3.11+
