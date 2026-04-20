import speech_recognition as sr
import pyttsx3
import re
import logging
import datetime
import time
from difflib import get_close_matches
import sqlite3

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MumbaiTrainAssistant:
    def __init__(self):
        # Initialize text-to-speech engine
        self.engine = pyttsx3.init()
        self.setup_voice()
        
        # Initialize speech recognizer
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = 4000
        
        # Mumbai local train lines
        self.train_lines = {
            "western": ["churchgate", "marine lines", "charni road", "grant road", "mumbai central", 
                       "mahalaxmi", "lower parel", "elphinstone", "dadar", "matunga", "mahim", 
                       "bandra", "santacruz", "vile parle", "andheri", "jogeshwari", 
                       "goregaon", "malad", "kandivali", "borivali", "dahisar", "mira road", 
                       "bhayander", "naigaon", "vasai road", "nalla sopara", "virar"],
            
            "central": ["chhatrapati shivaji terminus", "masjid", "sandhurst road", "byculla", "chinchpokli",
                      "currey road", "parel", "dadar", "matunga", "sion", "kurla", "vidyavihar", 
                      "ghatkopar", "vikhroli", "kanjurmarg", "bhandup", "nahur", "mulund", 
                      "thane", "kalva", "mumbra", "diva", "kopar", "dombivli", "thakurli", 
                      "kalyan", "shahad", "ambivli", "titwala", "kasara"],
            
            "harbour": ["chhatrapati shivaji terminus", "masjid", "sandhurst road", "dockyard road", 
                       "reay road", "cotton green", "sewri", "wadala", "guru tegh bahadur nagar", 
                       "chunabhatti", "kurla", "tilak nagar", "chembur", "govandi", "mankhurd", 
                       "vashi", "sanpada", "juinagar", "nerul", "seawood darave", "belapur",    
                       "kharghar", "panvel"]
        }
        
        # Station aliases and corrections
        self.station_aliases = {
            "seawoods": "seawood darave",
            "cst": "chhatrapati shivaji terminus",
            "vt": "chhatrapati shivaji terminus",
            "darave": "seawood darave",
            "parel lower": "lower parel",
            "gtb" : "guru tegh bahadur nagar",
            "road": "road",  # Placeholder to prevent partial matches with "road"
        }
        
        # Session data to remember user preferences
        self.session = {
            "last_source": None,
            "last_destination": None,
            "preferred_line": None,
            "active_query": False  # Flag to track if we're in the middle of a query
        }
    
    def setup_voice(self):
        """Configure the text-to-speech engine with optimal settings."""
        # Set speech properties
        self.engine.setProperty('rate', 170)  # Adjust speed
        self.engine.setProperty('volume', 1.0)  # Max volume
        
        # Select a more natural voice (preferably female)
        voices = self.engine.getProperty('voices')
        female_voices = [v for v in voices if "female" in v.name.lower()]
        
        if female_voices:
            self.engine.setProperty('voice', female_voices[0].id)
            logger.info(f"Using voice: {female_voices[0].name}")
        else:
            # If no female voice found, use the first available voice
            self.engine.setProperty('voice', voices[0].id)
            logger.info(f"Using voice: {voices[0].name}")
    
    def speak(self, text):
        """Convert text to speech and play it."""
        print(f"Bot: {text}")
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            logger.error(f"Speech error: {e}")
            print("Speech error occurred, continuing in text mode")
    
    def listen(self):
        """Capture user's speech and convert it to text."""
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print("Listening...")
            recognizer.adjust_for_ambient_noise(source)
            try:
                audio = recognizer.listen(source, timeout=5)
                user_input = recognizer.recognize_google(audio)
                print("You:", user_input)
                return user_input.lower()
            except sr.UnknownValueError:
                self.speak("I didn't quite catch that. Could you say it again?")
                return self.listen()  # Retry listening
            except sr.RequestError:
                self.speak("I'm having trouble connecting. Please try again later.")
                return None
            except sr.WaitTimeoutError:
                self.speak("I didn't hear anything. Let's try again.")
                return self.listen()  # Retry listening
    
    def get_normalized_station_name(self, station_name):
        """Normalize station name by checking against aliases."""
        station_lower = station_name.lower()
        
        # Check direct match in aliases
        if station_lower in self.station_aliases:
            return self.station_aliases[station_lower]
        
        # Check for matches in actual station names
        for line_stations in self.train_lines.values():
            if station_lower in line_stations:
                return station_lower
        
        # No direct match found, return None
        return None
    
    def get_closest_station(self, user_input, line=None):
        """Find the closest matching station from user input."""
        # First check for direct matches or aliases
        normalized = self.get_normalized_station_name(user_input)
        if normalized:
            return normalized
        
        # If no direct match, use difflib to find closest
        if line and line in self.train_lines:
            stations = self.train_lines[line]
        else:
            # Combine all stations from all lines
            stations = self.get_all_stations()
        
        # Get close matches
        matches = get_close_matches(user_input.lower(), stations, n=1, cutoff=0.6)
        
        if matches:
            return matches[0]
        return None
    
    def get_all_stations(self):
        """Get a list of all stations across all lines."""
        all_stations = []
        for line_stations in self.train_lines.values():
            all_stations.extend(line_stations)
        return list(set(all_stations))  # Remove duplicates
    
    def determine_line(self, source, destination):
        """Determine which line the journey is on."""
        for line, stations in self.train_lines.items():
            if source in stations and destination in stations:
                return line
        return None
    
    def find_station_in_text(self, text):
        """Find stations mentioned in the text using more robust matching."""
        text_lower = text.lower()
        found_stations = []
        
        # First, check for station aliases
        for alias, full_name in self.station_aliases.items():
            if alias in text_lower:
                # Make sure we're matching complete words
                for word in text_lower.split():
                    if word == alias or word.startswith(alias + " ") or word.endswith(" " + alias):
                        found_stations.append((full_name, text_lower.find(alias)))
        
        # Then check for actual station names
        for station in self.get_all_stations():
            if station in text_lower:
                # Ensure we're matching complete station names to avoid partial matches
                for segment in text_lower.split():
                    if segment == station or station in segment:
                        found_stations.append((station, text_lower.find(station)))
        
        # Sort by position and remove duplicates
        found_stations.sort(key=lambda x: x[1])
        
        # Remove duplicates while preserving order
        unique_stations = []
        seen = set()
        for station, pos in found_stations:
            if station not in seen:
                unique_stations.append((station, pos))
                seen.add(station)
        
        return unique_stations
    
    def extract_details(self, text):
        """Extract source, destination, and time from user input."""
        source = None
        destination = None
        time = None
        
        # Find stations mentioned in the text
        stations_found = self.find_station_in_text(text)
        
        # Extract stations based on context clues
        if stations_found:
            text_lower = text.lower()
            
            # If we have at least two stations
            if len(stations_found) >= 2:
                # Check if there's a clear "from X to Y" pattern
                from_idx = text_lower.find("from")
                to_idx = text_lower.find("to")
                
                if from_idx != -1 and to_idx != -1 and from_idx < to_idx:
                    # Find stations that follow "from" and "to"
                    for station, pos in stations_found:
                        if from_idx < pos < to_idx:
                            source = station
                        elif pos > to_idx:
                            destination = station
                            break
                
                # If the pattern doesn't match or we still don't have source/destination
                if not source or not destination:
                    # Use the first two stations mentioned
                    source = stations_found[0][0]
                    destination = stations_found[1][0]
            
            # If we have only one station
            elif len(stations_found) == 1:
                station = stations_found[0][0]
                from_idx = text_lower.find("from")
                to_idx = text_lower.find("to")
                
                if from_idx != -1 and from_idx < stations_found[0][1]:
                    source = station
                elif to_idx != -1 and to_idx < stations_found[0][1]:
                    destination = station
                else:
                    # Default behavior: if we can't tell if it's source or destination, assume destination
                    destination = station
        
        # Fallback to regex patterns if we couldn't extract stations
        if not source:
            source_match = re.search(r'from\s+([\w\s]+?)(?:\s+to|\s+at|$)', text, re.IGNORECASE)
            if source_match:
                source_input = source_match.group(1).strip()
                source = self.get_closest_station(source_input)
        
        if not destination:
            dest_match = re.search(r'to\s+([\w\s]+?)(?:\s+at|$|\s+by)', text, re.IGNORECASE)
            if dest_match:
                dest_input = dest_match.group(1).strip()
                destination = self.get_closest_station(dest_input)
        
        # Extract time (handles Indian time formats like "10:30", "10.30", "10 30")
        time_patterns = [
            r'at\s+(\d{1,2}(?:[:\.]\d{2})?\s*(?:am|pm)?)',  # 10:30 am, 10.30 pm
            r'at\s+(\d{1,2}\s+\d{2})',  # 10 30
            r'(\d{1,2}[:\.]\d{2}\s*(?:am|pm)?)',  # 10:30am without "at"
            r'(\d{1,2}\s*(?:am|pm))',  # 1 pm without "at"
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                time = match.group(1).strip()
                break
        
        # Debug logging
        logger.info(f"Extracted details - Source: {source}, Destination: {destination}, Time: {time}")
        
        return source, destination, time
    
    def process_user_response(self, response):
        """Process yes/no responses and other common phrases."""
        response = response.lower()
        
        # Check for affirmative responses
        if any(word in response for word in ["yes", "yeah", "sure", "okay", "ok", "yep", "yup"]):
            return "yes"
        
        # Check for negative responses
        if any(word in response for word in ["no", "nope", "nah", "not", "don't", "cant"]):
            return "no"
        
        # Check for exit commands
        if any(word in response for word in ["exit", "quit", "stop", "bye", "goodbye"]):
            return "exit"
        
        # Otherwise return the original response
        return response
    
    def handle_query_complete(self):
        """Handle the end of a query session."""
        self.speak("Would you like to check another train?")
        response = self.listen()
        processed_response = self.process_user_response(response)
        
        if processed_response == "yes":
            # Reset for a new query but keep the session data
            self.session["active_query"] = False
            return True
        elif processed_response == "exit":
            self.speak("Goodbye! Safe travels!")
            return False
        else:
            # Assume no if not clearly yes
            self.speak("Thank you for using Mumbai Train Assistant. Have a great day!")
            return False
    
    def handle_partial_query(self, text):
        """Handle partial queries like 'I want to go to Andheri'."""
        destination = None
        
        # Try to extract destination from partial query
        dest_match = re.search(r'(?:go|travel)\s+to\s+([\w\s]+)(?:\s+|$)', text, re.IGNORECASE)
        if dest_match:
            dest_input = dest_match.group(1).strip()
            destination = self.get_closest_station(dest_input)
            
            if destination and self.session["last_source"]:
                # We have a source from previous query and a new destination
                self.speak(f"Do you want to go from {self.session['last_source']} to {destination}?")
                response = self.listen()
                if self.process_user_response(response) == "yes":
                    return self.session["last_source"], destination, None
        
        # If we couldn't extract enough info, treat as a new query
        return None, None, None
        
    def run(self):
        """Main method to run the assistant."""
        self.speak("Hello! I'm here to help you find Mumbai local trains. Just tell me your journey details.")
        
        while True:
            user_text = self.listen()
            if user_text is None:
                continue
            
            # Log raw input for debugging
            logger.info(f"Raw user input: {user_text}")
            
            # Process the response first
            processed_response = self.process_user_response(user_text)
            
            if processed_response == "exit":
                self.speak("Goodbye! Safe travels!")
                break
            
            # Check for simple greeting
            if user_text.lower() in ["hello", "hi", "hey"]:
                self.speak("Hello! How can I help you with Mumbai local trains today?")
                continue
            
            # Extract details from the user's query
            source, destination, time = self.extract_details(user_text)
            
            # Handle partial queries by checking session data
            if not source and not destination and "go" in user_text.lower():
                source, destination, time = self.handle_partial_query(user_text)
            
            # Mark that we're starting a query
            self.session["active_query"] = True
            
            # Only ask for missing details
            if not source:
                self.speak("Which station are you traveling from?")
                source_input = self.listen()
                if source_input:
                    source = self.get_closest_station(source_input)
                    if source:
                        self.speak(f"Got it, {source}.")
                    else:
                        self.speak("I couldn't recognize that station. Let's try again.")
                        continue
            
            if not destination:
                self.speak(f"Which station do you want to go to from {source}?")
                dest_input = self.listen()
                if dest_input:
                    destination = self.get_closest_station(dest_input)
                    if destination:
                        self.speak(f"Got it, {destination}.")
                    else:
                        self.speak("I couldn't recognize that station. Let's try again.")
                        continue
            
            # Only try to determine line if we have both source and destination
            if source and destination:
                # Determine line if possible
                line = self.determine_line(source, destination)
                if not line:
                    self.speak(f"I'm not sure if there's a direct train from {source} to {destination}. You might need to change lines.")
            
            if not time:
                self.speak("What time do you plan to travel?")
                time_input = self.listen()
                if time_input:
                    # Extract time from the response
                    time_match = re.search(r'(\d{1,2}(?:[:\.]\d{2})?\s*(?:am|pm)?)', time_input, re.IGNORECASE)
                    if time_match:
                        time = time_match.group(1).strip()
                        self.speak(f"Got it, {time}.")
                    else:
                        # Default to current time + 30 minutes if not understood
                        now = datetime.datetime.now()
                        later = now + datetime.timedelta(minutes=30)
                        time = later.strftime("%I:%M %p")
                        self.speak(f"I'll check trains leaving soon, around {time}.")
            
            # Remember these preferences for the session
            self.session["last_source"] = source
            self.session["last_destination"] = destination
            
            # Find and speak train information
            train_info = self.find_trains(source, destination, time)
            self.speak(train_info)
            
            # Ask if the user needs another query
            if not self.handle_query_complete():
                break
    
    def find_trains(self, source, destination, time):
        """Find train information."""
        line = self.determine_line(source, destination)
        
        if not line:
            return f"I couldn't find a direct train from {source} to {destination}. You might need to change lines."
        
        # Use the database function to find real train data
        result = get_train_details(source, destination, time)
        
        # If no results were found, provide a fallback response
        
        
        return result

def get_train_details(source, destination, time=None):
    conn = sqlite3.connect('database/train_management.db')
    cursor = conn.cursor()

    query = '''
    SELECT train_id, route_no, departure_time, arrival_time, type, no_of_coaches
    FROM TRAINS
    WHERE source = ? AND destination = ?
    '''
    
    params = [source, destination]
    
    # Add time filter if provided
    if time:
        # Convert 12-hour format to 24-hour if needed
        if "pm" in time.lower() and not time.startswith("12"):
            hour = int(time.split(':')[0])
            time = f"{hour+12}:{time.split(':')[1]}" if ':' in time else f"{hour+12}:00"
        time = time.replace("am", "").replace("pm", "").strip()
        query += " AND departure_time >= ?"
        params.append(time)
    
    # Order by next available train
    query += " ORDER BY departure_time ASC"
    
    cursor.execute(query, params)
    trains = cursor.fetchall()
    conn.close()
    
    if not trains:
        return f"No trains found from {source} to {destination}"
    
    # Format results
    result = f"Found {len(trains)} trains from {source} to {destination}:"
    for train in trains:
        train_id, route_no, departure, arrival, train_type, coaches = train
        result += f"\n• Train {train_id} ({train_type}): Departs {departure}, Arrives {arrival}, {coaches} coaches"
    
    return result


if __name__ == "__main__":
    assistant = MumbaiTrainAssistant()
    try:
        assistant.run()
    except KeyboardInterrupt:
        print("\nProgram terminated by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print("An error occurred. Please restart the program.")