import sqlite3
import speech_recognition as sr
import pyttsx3
import datetime
import re
from difflib import get_close_matches
import time

class TrainVoiceAssistant:
    def __init__(self, db_path='train_management.db'):
        # Initialize the speech recognizer
        self.recognizer = sr.Recognizer()
        
        # Initialize text-to-speech engine
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 180)  # Speed of speech
        
        # Database connection
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
        # Store all station names for matching
        self.all_stations = self._get_all_stations()
        
        # Define time regex pattern
        self.time_pattern = r'\b([0-9]{1,2}):?([0-9]{2})?\s*(am|pm|AM|PM)?\b|\b([0-9]{1,2})\s*(am|pm|AM|PM)\b'
        
    def _connect_db(self):
        """Connect to the database"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
    
    def _close_db(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
    
    def _get_all_stations(self):
        """Get all station names from the database for matching"""
        self._connect_db()
        self.cursor.execute("SELECT DISTINCT name FROM STATIONS")
        stations = [station[0].lower() for station in self.cursor.fetchall()]
        self._close_db()
        return stations
        
    def speak(self, text):
        """Convert text to speech"""
        print(f"Assistant: {text}")
        self.engine.say(text)
        self.engine.runAndWait()
    
    def listen(self):
        """Listen for speech input and convert to text"""
        with sr.Microphone() as source:
            self.speak("I'm listening. Please speak.")
            print("Listening...")
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = self.recognizer.listen(source, timeout=10)
                print("Processing speech...")
                text = self.recognizer.recognize_google(audio)
                print(f"You said: {text}")
                return text.lower()
            except sr.WaitTimeoutError:
                self.speak("I didn't hear anything. Please try again.")
                return None
            except sr.UnknownValueError:
                self.speak("I couldn't understand what you said. Please try again.")
                return None
            except Exception as e:
                self.speak(f"Sorry, there was an error: {str(e)}")
                return None
    
    def extract_info(self, text):
        """Extract source, destination, time, train type, and class from speech"""
        info = {
            'source': None,
            'destination': None,
            'time': None,
            'train_type': None,
            'class': None
        }
        
        # Extract time using regex
        time_matches = re.findall(self.time_pattern, text)
        if time_matches:
            for match in time_matches:
                if match[0]:  # HH:MM format
                    hour = int(match[0])
                    minute = int(match[1]) if match[1] else 0
                    period = match[2].lower() if match[2] else None
                else:  # H AM/PM format
                    hour = int(match[3])
                    minute = 0
                    period = match[4].lower() if match[4] else None
                
                # Convert to 24-hour format if period is specified
                if period in ['pm', 'PM'] and hour < 12:
                    hour += 12
                elif period in ['am', 'AM'] and hour == 12:
                    hour = 0
                
                info['time'] = f"{hour:02d}:{minute:02d}"
                break
        
        # Extract train type (NORMAL or AC)
        if 'ac' in text or 'air conditioned' in text or 'air-conditioned' in text:
            info['train_type'] = 'AC'
        elif 'normal' in text or 'regular' in text or 'non ac' in text or 'non-ac' in text:
            info['train_type'] = 'NORMAL'
        
        # Extract class (First or Second)
        if 'first class' in text or '1st class' in text:
            info['class'] = 'First'
        elif 'second class' in text or '2nd class' in text:
            info['class'] = 'Second'
        
        # Extract stations (source and destination)
        words = text.split()
        for i, word in enumerate(words):
            # Check for words that indicate source/destination
            if i < len(words) - 1:
                if word == 'from':
                    potential_source = words[i+1].lower()
                    matched_source = self._match_station(potential_source)
                    if matched_source:
                        info['source'] = matched_source
                elif word == 'to':
                    potential_dest = words[i+1].lower()
                    matched_dest = self._match_station(potential_dest)
                    if matched_dest:
                        info['destination'] = matched_dest
                        
        # If we couldn't find source/destination with 'from/to' keywords, search for station names directly
        if not info['source'] or not info['destination']:
            for station in self.all_stations:
                if station.lower() in text:
                    if not info['source']:
                        info['source'] = station
                    elif not info['destination'] and station != info['source']:
                        info['destination'] = station
                        break
        
        return info
    
    def _match_station(self, potential_station):
        """Match a potential station name to a valid station in our database"""
        # Try to find closest match
        matches = get_close_matches(potential_station, self.all_stations, n=1, cutoff=0.6)
        if matches:
            return matches[0]
        return None
    
    def search_trains(self, info):
        """Search for trains based on extracted information"""
        self._connect_db()
        
        query = """
        SELECT t.train_id, t.source, t.destination, t.departure_time, t.arrival_time, 
               t.type AS train_type,
               CASE 
                   WHEN t.type = 'NORMAL' THEN (
                       SELECT n.fare FROM NORMAL_TRAIN n 
                       WHERE n.train_id = t.train_id AND n.class = ?
                   )
                   WHEN t.type = 'AC' THEN (
                       SELECT a.fare FROM AC_TRAIN a 
                       WHERE a.train_id = t.train_id
                   )
               END AS fare,
               CASE 
                   WHEN t.type = 'NORMAL' THEN ?
                   ELSE 'AC'
               END AS class
        FROM TRAINS t
        WHERE 1=1
        """
        
        params = []
        if info['class'] == 'First' or info['class'] == 'Second':
            params.append(info['class'])
        else:
            params.append('Second')  # Default to Second class
        
        params.append(info['class'] if info['class'] else 'Second')
        
        # Add source condition if available
        if info['source']:
            query += " AND LOWER(t.source) = LOWER(?)"
            params.append(info['source'])
        
        # Add destination condition if available
        if info['destination']:
            query += " AND LOWER(t.destination) = LOWER(?)"
            params.append(info['destination'])
        
        # Add train type condition if available
        if info['train_type']:
            query += " AND t.type = ?"
            params.append(info['train_type'])
            
        # Time filtering
        if info['time']:
            # Parse the requested time
            requested_time = datetime.datetime.strptime(info['time'], '%H:%M')
            
            # Add 20 minutes
            time_plus_20 = requested_time + datetime.timedelta(minutes=20)
            
            # Subtract 20 minutes
            time_minus_20 = requested_time - datetime.timedelta(minutes=20)
            
            query += " AND t.departure_time BETWEEN ? AND ?"
            params.append(time_minus_20.strftime('%H:%M'))
            params.append(time_plus_20.strftime('%H:%M'))
            
        # Order by departure time
        query += " ORDER BY t.departure_time LIMIT 5"
        
        self.cursor.execute(query, params)
        trains = self.cursor.fetchall()
        
        self._close_db()
        return trains
    
    def format_train_results(self, trains):
        """Format the train search results for speech output"""
        if not trains:
            return "I couldn't find any trains matching your criteria."
        
        result = f"I found {len(trains)} trains for you:\n\n"
        
        for i, train in enumerate(trains, 1):
            train_id, source, destination, departure, arrival, train_type, fare, train_class = train
            result += (f"Train {i}: From {source} to {destination}, "
                     f"Departure at {departure}, Arrival at {arrival}, "
                     f"{train_type} type, {train_class} class, Fare ₹{fare:.2f}\n\n")
        
        return result
    
    def book_ticket(self, train_details):
        """Handle ticket booking flow"""
        self.speak("Would you like to book a ticket for this train? Please say yes or no.")
        response = self.listen()
        
        if response and ('yes' in response.lower() or 'sure' in response.lower() or 'book' in response.lower()):
            self.speak("Great! To book a ticket, I'll need your name.")
            time.sleep(0.5)
            name = self.listen()
            
            if name:
                self.speak(f"Thank you, {name}. Your ticket is being processed.")
                time.sleep(1)
                self.speak("Your booking has been confirmed! The e-ticket will be sent to your registered email address.")
                return True
        else:
            self.speak("No problem. Is there anything else I can help you with?")
            return False
        
    def confirm_info(self, info):
        """Confirm the extracted information with the user"""
        confirmation_text = "I understood the following details: "
        
        if info['source']:
            confirmation_text += f"From {info['source']}. "
        else:
            confirmation_text += "I couldn't understand your source station. "
            
        if info['destination']:
            confirmation_text += f"To {info['destination']}. "
        else:
            confirmation_text += "I couldn't understand your destination station. "
            
        if info['time']:
            confirmation_text += f"Around {info['time']}. "
        
        if info['train_type']:
            confirmation_text += f"{info['train_type']} train. "
            
        if info['class']:
            confirmation_text += f"{info['class']} class. "
            
        confirmation_text += "Is this correct? Please say yes or no."
        
        self.speak(confirmation_text)
        response = self.listen()
        
        return response and ('yes' in response.lower() or 'correct' in response.lower() or 'right' in response.lower())
        
    def ask_missing_info(self, info):
        """Ask for missing information"""
        if not info['source']:
            self.speak("Could you please tell me your departure station?")
            response = self.listen()
            if response:
                potential_source = response.lower()
                matched_source = self._match_station(potential_source)
                if matched_source:
                    info['source'] = matched_source
        
        if not info['destination']:
            self.speak("Could you please tell me your destination station?")
            response = self.listen()
            if response:
                potential_dest = response.lower()
                matched_dest = self._match_station(potential_dest)
                if matched_dest:
                    info['destination'] = matched_dest
        
        if not info['time']:
            self.speak("What time would you like to travel?")
            response = self.listen()
            if response:
                time_matches = re.findall(self.time_pattern, response)
                if time_matches:
                    for match in time_matches:
                        if match[0]:  # HH:MM format
                            hour = int(match[0])
                            minute = int(match[1]) if match[1] else 0
                            period = match[2].lower() if match[2] else None
                        else:  # H AM/PM format
                            hour = int(match[3])
                            minute = 0
                            period = match[4].lower() if match[4] else None
                        
                        # Convert to 24-hour format if period is specified
                        if period in ['pm', 'PM'] and hour < 12:
                            hour += 12
                        elif period in ['am', 'AM'] and hour == 12:
                            hour = 0
                        
                        info['time'] = f"{hour:02d}:{minute:02d}"
                        break
        
        return info
    
    def start(self):
        """Start the voice assistant"""
        self.speak("Hello! I'm your train assistant. How can I help you find a train today?")
        
        while True:
            # Listen for command
            command = self.listen()
            
            if not command:
                continue
            
            # Check for exit command
            if 'exit' in command or 'quit' in command or 'bye' in command or 'goodbye' in command:
                self.speak("Thank you for using the train assistant. Goodbye!")
                break
            
            # Extract information from speech
            info = self.extract_info(command)
            
            # Ask for missing information
            if not info['source'] or not info['destination']:
                info = self.ask_missing_info(info)
            
            # Confirm the extracted information
            if not self.confirm_info(info):
                self.speak("Let's try again. Please provide your travel details.")
                continue
            
            # Search for trains based on the extracted information
            self.speak("Searching for trains. Please wait a moment.")
            trains = self.search_trains(info)
            
            # Format and speak the results
            results = self.format_train_results(trains)
            self.speak(results)
            
            # If trains were found, offer to book a ticket
            if trains:
                self.book_ticket(trains[0])  # Offer to book the first train
            
            # Ask if the user wants to search for more trains
            self.speak("Would you like to search for another train?")
            response = self.listen()
            
            if not response or not ('yes' in response.lower() or 'sure' in response.lower() or 'search' in response.lower()):
                self.speak("Thank you for using the train assistant. Goodbye!")
                break


if __name__ == "__main__":
    assistant = TrainVoiceAssistant()
    assistant.start()