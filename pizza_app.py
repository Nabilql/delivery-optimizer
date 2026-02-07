import streamlit as st
import googlemaps
import pandas as pd
from datetime import datetime

# --- 1. CONFIGURATIE ---
# Jouw API Key uit de screenshots
API_KEY = 'AIzaSyBWa7fO-vuLHDE38VostjS877wU8igrn2I' 
gmaps = googlemaps.Client(key=API_KEY)

# Pagina-instellingen voor een professionele look
st.set_page_config(page_title="NYP Route Optimizer", page_icon="🍕", layout="wide")

# --- 2. HELPER FUNCTIES ---
def fix_adres(adres):
    """Data Cleaning: Voegt Barendrecht toe als de stad ontbreekt."""
    adres = adres.strip()
    if not adres: return None
    if "," not in adres:
        return f"{adres}, Barendrecht"
    return adres

def maak_maps_link(start, stops_lijst):
    """Genereert de URL voor Google Maps navigatie op de telefoon."""
    start_safe = start.replace(" ", "+")
    stops_safe = "/".join([s.replace(" ", "+") for s in stops_lijst])
    return f"https://www.google.com/maps/dir/{start_safe}/{stops_safe}/{start_safe}"

# --- 3. GEBRUIKERSINTERFACE (UI) ---
st.title("🍕 NYP Bezorg-Optimizer v3.0")
st.markdown("### Strategie: *Dichtbijste adres eerst*")

# Sidebar voor instellingen
st.sidebar.header("Locatie Instellingen")
start_punt = st.sidebar.text_input("Startlocatie (Winkel)", "Platehaven 5, Barendrecht")

# Hoofdscherm voor input
st.info("Tip: Typ stad erbij (bijv. ', Rotterdam') voor adressen buiten Barendrecht.")
adres_input = st.text_area("Voer adressen in (één per regel):", 
                            placeholder="Topaaslaan 33\nMeerleveld 11, Rotterdam\nSmitshoeksebaan 10",
                            height=150)

if st.button("🚀 Bereken Optimale Route", type="primary"):
    # Stap 1: Input verwerken en opschonen
    lijst = [line.strip() for line in adres_input.split('\n') if line.strip()]
    
    if not lijst:
        st.error("Voer eerst minimaal één adres in.")
    else:
        verwerkte_adressen = [fix_adres(a) for a in lijst]

        try:
            with st.spinner('Afstanden berekenen en route plannen...'):
                # Stap 2: Bereken afstanden vanaf de winkel (Nearest Neighbor logic)
                # 
                matrix_res = gmaps.distance_matrix(
                    origins=[start_punt],
                    destinations=verwerkte_adressen,
                    mode="driving",
                    region='nl'
                )

                # Afstanden koppelen aan adressen
                afstanden_data = []
                for i, adres in enumerate(verwerkte_adressen):
                    # We pakken de afstand in meters uit de API response
                    meters = matrix_res['rows'][0]['elements'][i]['distance']['value']
                    afstanden_data.append({"adres": adres, "meters": meters})

                # Stap 3: Sorteren op afstand (Greedy Algorithm)
                # We sorteren de lijst zodat de kleinste afstand bovenaan staat
                afstanden_data.sort(key=lambda x: x['meters'])
                gesorteerde_adressen = [item['adres'] for item in afstanden_data]

                # Stap 4: De definitieve route ophalen bij Google
                # We zetten optimize_waypoints=False omdat we ZELF al gesorteerd hebben!
                directions_res = gmaps.directions(
                    origin=start_punt,
                    destination=start_punt,
                    waypoints=gesorteerde_adressen,
                    optimize_waypoints=False,
                    mode="driving",
                    departure_time=datetime.now(),
                    region='nl'
                )

            if directions_res:
                route = directions_res[0]
                legs = route['legs']
                
                st.success(f"Route gepland voor {len(gesorteerde_adressen)} pizza's!")

                # Layout verdelen in twee kolommen
                col1, col2 = st.columns([1, 1])

                with col1:
                    st.subheader("📍 Rij-volgorde")
                    gevalideerde_stops = []
                    
                    for i, leg in enumerate(legs[:-1], 1): # De laatste leg is terug naar de winkel
                        adres_gevonden = leg['end_address']
                        afstand_tekst = leg['distance']['text']
                        tijd_tekst = leg['duration']['text']
                        
                        st.write(f"**{i}. {adres_gevonden}**")
                        st.caption(f"📏 {afstand_tekst} vanaf vorig punt | ⏱️ {tijd_tekst}")
                        gevalideerde_stops.append(adres_gevonden)
                    
                    # De Navigatie Link
                    maps_url = maak_maps_link(start_punt, gevalideerde_stops)
                    st.markdown(f"## [🗺️ Start Navigatie op Telefoon]({maps_url})")

                with col2:
                    st.subheader("🗺️ Kaartoverzicht")
                    # Data voorbereiden voor de kaart
                    map_points = []
                    # Voeg winkel toe
                    map_points.append({"lat": legs[0]['start_location']['lat'], 
                                       "lon": legs[0]['start_location']['lng'], "naam": "NYP"})
                    # Voeg alle stops toe
                    for leg in legs[:-1]:
                        map_points.append({"lat": leg['end_location']['lat'], 
                                           "lon": leg['end_location']['lng'], "naam": "Stop"})
                    
                    df = pd.DataFrame(map_points)
                    st.map(df) # Streamlit tekent de puntjes op de kaart

            else:
                st.error("Google kon geen route vinden. Check de spelling van je adressen.")

        except Exception as e:
            st.error(f"Er ging iets mis met de API: {e}")