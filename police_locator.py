import requests
import folium
from opencage.geocoder import OpenCageGeocode

OPENCAGE_KEY = "bbce6a89e66d4979b7a2530627cb2fab"


def find_police_stations(location: str, radius: int = 5000):

    try:
        
        geocoder = OpenCageGeocode(OPENCAGE_KEY)
        results = geocoder.geocode(location)

        if not results:
            return [], None, "Location not found."

        latitude = results[0]["geometry"]["lat"]
        longitude = results[0]["geometry"]["lng"]

        print(f"Location: {location}")
        print(f"Latitude: {latitude}")
        print(f"Longitude: {longitude}")

        
        overpass_servers = [
            "https://overpass-api.de/api/interpreter",
            "https://overpass.private.coffee/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter"
        ]

        
        overpass_query = f"""
        [out:json][timeout:20];
        (
            node["amenity"="police"](around:{radius},{latitude},{longitude});
            way["amenity"="police"](around:{radius},{latitude},{longitude});
        );
        out center;
        """

        headers = {
            "User-Agent": "PoliceStationFinder/1.0",
            "Accept": "application/json"
        }

        data = None

        
        for overpass_url in overpass_servers:

            try:
                print("------------------------------------")
                print("Trying:", overpass_url)

                response = requests.post(
                    overpass_url,
                    headers=headers,
                    data={"data": overpass_query},
                    timeout=30
                )

                print("Status Code:", response.status_code)

                
                if response.status_code == 200:

                    try:
                        data = response.json()
                        print("Overpass request successful.")
                        break

                    except ValueError:
                        print("Invalid JSON received.")
                        continue

                
                elif response.status_code in [429, 500, 502, 503, 504]:

                    print(
                        f"Overpass server returned "
                        f"{response.status_code}. Trying next server..."
                    )

                    continue

                else:

                    print(
                        f"Unexpected Overpass response: "
                        f"{response.status_code}"
                    )

                    continue

            except requests.exceptions.Timeout:

                print(
                    f"Timeout while connecting to "
                    f"{overpass_url}"
                )

                continue

            except requests.exceptions.RequestException as e:

                print(
                    f"Request failed for {overpass_url}: {e}"
                )

                continue

        
        if data is None:

            return (
                [],
                None,
                "Police station service is temporarily "
                "unavailable. Please try again."
            )

        
        map_location = folium.Map(
            location=[latitude, longitude],
            zoom_start=13
        )

        
        folium.Marker(
            [latitude, longitude],
            popup=f"Search Center: {location}",
            icon=folium.Icon(
                color="red",
                icon="home"
            )
        ).add_to(map_location)

        stations = []

        
        for place in data.get("elements", []):

            
            if "lat" in place and "lon" in place:

                lat = place["lat"]
                lon = place["lon"]

            
            elif "center" in place:

                lat = place["center"]["lat"]
                lon = place["center"]["lon"]

            else:
                continue

            tags = place.get("tags", {})

            name = tags.get(
                "name",
                "Unnamed Police Station"
            )

            stations.append(name)

            
            folium.Marker(
                [lat, lon],
                popup=name,
                tooltip=name,
                icon=folium.Icon(
                    color="blue",
                    icon="info-sign"
                )
            ).add_to(map_location)

        
        map_file = "templates/police_map.html"

        map_location.save(map_file)

        
        if not stations:

            return (
                [],
                map_file,
                "No police stations found within "
                f"{radius // 1000} km."
            )

        
        return stations, map_file, None

    
    except Exception as e:

        print("ERROR:", str(e))

        return (
            [],
            None,
            f"An error occurred: {str(e)}"
        )