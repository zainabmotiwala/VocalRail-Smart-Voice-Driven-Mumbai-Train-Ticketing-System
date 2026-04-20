import sqlite3

# Connect to SQLite database (it will be created if it doesn't exist)
conn = sqlite3.connect('train_management.db')
cursor = conn.cursor()

# Create tables with modifications
cursor.executescript('''
-- Create ADMIN table
CREATE TABLE ADMIN (
    admin_id INTEGER PRIMARY KEY,
    admin_name TEXT NOT NULL,
    email TEXT,
    password TEXT NOT NULL
);

-- Modified TRAINS table as per requirement #2
CREATE TABLE TRAINS (
    train_id INTEGER PRIMARY KEY,
    route_id INTEGER,
    source TEXT,
    destination TEXT,
    departure_time TEXT,
    arrival_time TEXT,
    no_of_coaches INTEGER,
    type TEXT CHECK (type IN ('NORMAL', 'AC'))
);

-- Create NORMAL train type table (subclass of TRAINS)
CREATE TABLE NORMAL_TRAIN (
    train_id INTEGER,
    fare REAL,
    class TEXT CHECK (class IN ('First', 'Second')),
    PRIMARY KEY (train_id, class),
    FOREIGN KEY (train_id) REFERENCES TRAINS(train_id)
);

-- Create AC train type table (subclass of TRAINS)
CREATE TABLE AC_TRAIN (
    train_id INTEGER PRIMARY KEY,
    fare REAL,
    FOREIGN KEY (train_id) REFERENCES TRAINS(train_id)
);

-- Create ROUTE table
CREATE TABLE ROUTE (
    route_no INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    distance REAL,
    destination TEXT NOT NULL,
    type TEXT CHECK (type IN ('FAST', 'SLOW'))
);

-- Create FAST route type table (subclass of ROUTE)
CREATE TABLE FAST_ROUTE (
    route_no INTEGER PRIMARY KEY,
    duration INTEGER,
    stations INTEGER,
    FOREIGN KEY (route_no) REFERENCES ROUTE(route_no)
);

-- Create SLOW route type table (subclass of ROUTE)
CREATE TABLE SLOW_ROUTE (
    route_no INTEGER PRIMARY KEY,
    duration INTEGER,
    stations INTEGER,
    FOREIGN KEY (route_no) REFERENCES ROUTE(route_no)
);

-- Create PASSENGERS table
CREATE TABLE PASSENGERS (
    passenger_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    gender TEXT,
    dob TEXT,
    age INTEGER,
    phone_no TEXT,
    address TEXT
);

-- Create STATIONS table as per requirement #3
CREATE TABLE STATIONS (
    station_code TEXT PRIMARY KEY,
    route_id INTEGER,
    name TEXT NOT NULL,
    FOREIGN KEY (route_id) REFERENCES TRAINS(route_id)
);
''')

# Commit changes
conn.commit()

# Verify tables were created
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print("Database modified successfully with the following tables:")
for table in tables:
    print(f"- {table[0]}")

conn.close()