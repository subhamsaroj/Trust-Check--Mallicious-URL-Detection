import phonenumbers
from phonenumbers import geocoder, carrier
from opencage.geocoder import OpenCageGeocode
import folium

Key = "bbce6a89e66d4979b7a2530627cb2fab"  

def lookup_number(number: str):
    """
    Lookup phone number details and generate mylocation.html map.
    """
    try:
        parsed_number = phonenumbers.parse(number)

        
        number_location = geocoder.description_for_number(parsed_number, "en")
        service_provider = carrier.name_for_number(parsed_number, "en")

        
        geocode = OpenCageGeocode(Key)
        results = geocode.geocode(str(number_location))
        if not results:
            raise ValueError("Location not found")

        lat = results[0]['geometry']['lat']
        lng = results[0]['geometry']['lng']

        
        map_location = folium.Map(location=[lat, lng], zoom_start=9)
        folium.Marker([lat, lng], popup=number_location).add_to(map_location)
        map_location.save("templates/mylocation.html")

        return {
            "phone": number,
            "location": number_location,
            "provider": service_provider,
            "latitude": lat,
            "longitude": lng
        }
    except Exception as e:
        return {"error": str(e)}
