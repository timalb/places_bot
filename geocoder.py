from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import asyncio
import logging

class Geocoder:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="my_bot", timeout=10)

    async def geocode(self, address: str, max_retries: int = 3) -> tuple:
        for attempt in range(max_retries):
            try:
                logging.info(f"Attempting to geocode address: {address}")
                loop = asyncio.get_event_loop()
                location = await loop.run_in_executor(None, self.geolocator.geocode, address)
                if location:
                    logging.info(f"Successfully geocoded: {address} -> ({location.latitude}, {location.longitude})")
                    return (location.latitude, location.longitude)
                logging.warning(f"No results found for address: {address}")
            except GeocoderTimedOut:
                logging.warning(f"Timeout on attempt {attempt + 1} for address: {address}")
                if attempt == max_retries - 1:
                    logging.error(f"Geocoding failed after {max_retries} attempts for address: {address}")
                    return None
                await asyncio.sleep(1)
            except Exception as e:
                logging.error(f"Geocoding error for {address}: {e}", exc_info=True)
                return None
        return None 

    async def get_formatted_address(self, address: str) -> str:
        try:
            loop = asyncio.get_event_loop()
            location = await loop.run_in_executor(None, self.geolocator.geocode, address)
            if location:
                return location.address
            return None
        except Exception as e:
            logging.error(f"Error getting formatted address: {e}")
            return None 