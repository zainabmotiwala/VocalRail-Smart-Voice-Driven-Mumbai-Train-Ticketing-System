import sqlite3
import random
from datetime import datetime, timedelta

# Connect to SQLite database
conn = sqlite3.connect('train_management.db')
cursor = conn.cursor()

# Define the Harbour line stations
harbour_stations = [
    "chhatrapati shivaji terminus", "masjid", "sandhurst road", "dockyard road", 
    "reay road", "cotton green", "sewri", "wadala", "guru tegh bahadur nagar", 
    "chunabhatti", "kurla", "tilak nagar", "chembur", "govandi", "mankhurd", 
    "vashi", "sanpada", "juinagar", "nerul", "seawood darave", "belapur",    
    "kharghar", "panvel"
]

# Define routes (one for each direction on Harbour line)
routes = [
    {
        'route_id': 1,
        'source': 'Chhatrapati Shivaji Terminus',
        'destination': 'Panvel',
        'distance': 50.0,
        'type': 'SLOW'
    },
    {
        'route_id': 2,
        'source': 'Panvel',
        'destination': 'Chhatrapati Shivaji Terminus',
        'distance': 50.0,
        'type': 'SLOW'
    }
]

# Sample data for CST to Panvel trains based on website
# This is a small sample; in the actual script we'll generate 318 entries
sample_cst_to_panvel_trains = [
    {'departure': '04:08', 'arrival': '05:47'},
    {'departure': '04:32', 'arrival': '06:10'},
    {'departure': '05:22', 'arrival': '07:00'},
    {'departure': '05:45', 'arrival': '07:20'},
    # More entries will be added to reach 318 trains
]

# Sample data for Panvel to CST trains
sample_panvel_to_cst_trains = [
    {'departure': '04:15', 'arrival': '05:55'},
    {'departure': '04:40', 'arrival': '06:15'},
    {'departure': '05:10', 'arrival': '06:48'},
    {'departure': '05:37', 'arrival': '07:15'},
    # More entries will be added to reach 318 trains
]

# Generate more train timings to reach 318 trains
def generate_train_timings(initial_sample, count, direction):
    all_trains = initial_sample.copy()
    current_time = datetime.strptime('07:30', '%H:%M')
    end_time = datetime.strptime('23:59', '%H:%M')
    
    # Calculate average journey time from samples
    total_minutes = 0
    for train in initial_sample:
        dep = datetime.strptime(train['departure'], '%H:%M')
        arr = datetime.strptime(train['arrival'], '%H:%M')
        journey_time = (arr - dep).seconds // 60
        total_minutes += journey_time
    
    avg_journey_minutes = total_minutes // len(initial_sample)
    
    # Add variation to journey times
    while len(all_trains) < count:
        # Add some randomness to departure interval (4-15 minutes between trains)
        interval = random.randint(4, 15)
        current_time += timedelta(minutes=interval)
        
        if current_time > end_time:
            # Restart from early morning if we've gone past midnight
            current_time = datetime.strptime('04:00', '%H:%M') + timedelta(minutes=random.randint(0, 60))
        
        # Calculate arrival with slight variation in journey time
        variation = random.randint(-10, 10)
        arrival_time = current_time + timedelta(minutes=avg_journey_minutes + variation)
        
        all_trains.append({
            'departure': current_time.strftime('%H:%M'),
            'arrival': arrival_time.strftime('%H:%M')
        })
    
    # Ensure we have exactly the count requested
    return all_trains[:count]

# Generate 159 trains in each direction (total 318)
cst_to_panvel_trains = generate_train_timings(sample_cst_to_panvel_trains, 159, 'cst-to-panvel')
panvel_to_cst_trains = generate_train_timings(sample_panvel_to_cst_trains, 159, 'panvel-to-cst')

# Clear existing data if any
cursor.execute("DELETE FROM STATIONS")
cursor.execute("DELETE FROM NORMAL_TRAIN")
cursor.execute("DELETE FROM AC_TRAIN")
cursor.execute("DELETE FROM TRAINS")
cursor.execute("DELETE FROM ROUTE")
cursor.execute("DELETE FROM FAST_ROUTE")
cursor.execute("DELETE FROM SLOW_ROUTE")

# Insert route data
for route in routes:
    # Insert into ROUTE table
    cursor.execute('''
        INSERT INTO ROUTE (route_no, source, destination, distance, type)
        VALUES (?, ?, ?, ?, ?)
    ''', (route['route_id'], route['source'], route['destination'], route['distance'], route['type']))
    
    # Insert into SLOW_ROUTE
    cursor.execute('''
        INSERT INTO SLOW_ROUTE (route_no, duration, stations)
        VALUES (?, ?, ?)
    ''', (route['route_id'], 90, len(harbour_stations)))  # Average 90 minutes, 23 stations

# Insert CST to Panvel train data
train_id = 1
for idx, train in enumerate(cst_to_panvel_trains):
    train_no = 10001 + idx
    train_code = f"HAR{str(idx+1).zfill(3)}"
    
    # Randomly decide if this is a NORMAL or AC train
    train_type = random.choice(['NORMAL', 'AC'])
    no_of_coaches = random.randint(12, 15)
    
    # Insert into TRAINS table
    cursor.execute('''
        INSERT INTO TRAINS (train_id, route_id, source, destination, 
                          departure_time, arrival_time, no_of_coaches, type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (train_id, 1, 'Chhatrapati Shivaji Terminus', 'Panvel', 
          train['departure'], train['arrival'], no_of_coaches, train_type))
    
    # Insert into NORMAL_TRAIN or AC_TRAIN based on train type
    if train_type == 'NORMAL':
        # Insert for First class
        cursor.execute('''
            INSERT INTO NORMAL_TRAIN (train_id, fare, class)
            VALUES (?, ?, ?)
        ''', (train_id, random.uniform(100.0, 200.0), 'First'))
        
        # Insert for Second class
        cursor.execute('''
            INSERT INTO NORMAL_TRAIN (train_id, fare, class)
            VALUES (?, ?, ?)
        ''', (train_id, random.uniform(50.0, 100.0), 'Second'))
    else:  # AC
        cursor.execute('''
            INSERT INTO AC_TRAIN (train_id, fare)
            VALUES (?, ?)
        ''', (train_id, random.uniform(250.0, 500.0)))
    
    train_id += 1

# Insert Panvel to CST train data
for idx, train in enumerate(panvel_to_cst_trains):
    train_no = 20001 + idx
    train_code = f"HAR{str(idx+159).zfill(3)}"
    
    # Randomly decide if this is a NORMAL or AC train
    train_type = random.choice(['NORMAL', 'AC'])
    no_of_coaches = random.randint(12, 15)
    
    # Insert into TRAINS table
    cursor.execute('''
        INSERT INTO TRAINS (train_id, route_id, source, destination, 
                          departure_time, arrival_time, no_of_coaches, type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (train_id, 2, 'Panvel', 'Chhatrapati Shivaji Terminus', 
          train['departure'], train['arrival'], no_of_coaches, train_type))
    
    # Insert into NORMAL_TRAIN or AC_TRAIN based on train type
    if train_type == 'NORMAL':
        # Insert for First class
        cursor.execute('''
            INSERT INTO NORMAL_TRAIN (train_id, fare, class)
            VALUES (?, ?, ?)
        ''', (train_id, random.uniform(100.0, 200.0), 'First'))
        
        # Insert for Second class
        cursor.execute('''
            INSERT INTO NORMAL_TRAIN (train_id, fare, class)
            VALUES (?, ?, ?)
        ''', (train_id, random.uniform(50.0, 100.0), 'Second'))
    else:  # AC
        cursor.execute('''
            INSERT INTO AC_TRAIN (train_id, fare)
            VALUES (?, ?)
        ''', (train_id, random.uniform(250.0, 500.0)))
    
    train_id += 1

# Insert station data
for idx, station_name in enumerate(harbour_stations):
    station_code = f"H{str(idx+1).zfill(2)}"
    
    # Insert stations for both routes (CST to Panvel)
    cursor.execute('''
        INSERT INTO STATIONS (station_code, route_id, name)
        VALUES (?, ?, ?)
    ''', (station_code, 1, station_name.title()))
    
    # Insert stations for Panvel to CST route
    cursor.execute('''
        INSERT INTO STATIONS (station_code, route_id, name)
        VALUES (?, ?, ?)
    ''', (f"{station_code}R", 2, station_name.title()))

# Commit changes
conn.commit()

# Verify data was inserted
print("Data insertion complete. Verifying data...")

# Check trains
cursor.execute("SELECT COUNT(*) FROM TRAINS")
train_count = cursor.fetchone()[0]
print(f"Number of trains: {train_count}")

# Check stations
cursor.execute("SELECT COUNT(*) FROM STATIONS")
station_count = cursor.fetchone()[0]
print(f"Number of stations: {station_count}")

# Sample data from tables
print("\nSample trains:")
cursor.execute("SELECT train_id, route_id, source, destination, departure_time, arrival_time FROM TRAINS LIMIT 5")
for row in cursor.fetchall():
    print(row)

print("\nSample stations:")
cursor.execute("SELECT station_code, route_id, name FROM STATIONS LIMIT 10")
for row in cursor.fetchall():
    print(row)

conn.close()