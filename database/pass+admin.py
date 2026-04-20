import sqlite3
import os

# Use the correct path to your database
db_path = r'C:\Users\Zainab Motiwala\Desktop\ticket-booking-\database\train_management.db'

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List of tables to clear data from
clear_tables = ['PASSENGERS', 'ADMIN']

delete_tables = ['PASSENGER_PHONES', 'ADMIN_PHONES']

# Delete all records from the specified tables
for table in clear_tables:
    cursor.execute(f"DELETE FROM {table}")

# Drop the extra tables
for table in delete_tables:
    cursor.execute(f"DROP TABLE IF EXISTS {table}")

# Insert data into PASSENGERS table with multivalued phone numbers
passengers_data = [
    (1, 'John Smith', 'Male', '1985-03-12', 40, '123 Main St, Boston, MA', '+1-555-100-0000, +1-555-100-1111'),
    (2, 'Maria Garcia', 'Female', '1992-08-24', 32, '456 Oak Ave, Chicago, IL', '+1-555-200-0000, +1-555-200-1111'),
    (3, 'Robert Johnson', 'Male', '1978-05-17', 47, '789 Pine Rd, Seattle, WA', '+1-555-300-0000, +1-555-300-1111'),
    (4, 'Aisha Patel', 'Female', '1990-11-30', 34, '101 Cedar Ln, Austin, TX', '+1-555-400-0000, +1-555-400-1111')
]

cursor.executemany('''
INSERT INTO PASSENGERS (passenger_id, name, gender, dob, age, address, phone_no)
VALUES (?, ?, ?, ?, ?, ?, ?)
''', passengers_data)

# Insert data into ADMIN table (without phone numbers)
admin_data = [
    (101, 'Michael Brown', 'michael.brown@example.com', 'securePass123!'),
    (102, 'Jennifer Lee', 'jennifer.lee@example.com', 'Admin@456!'),
    (103, 'Carlos Rodriguez', 'carlos.r@example.com', 'SysAdmin789#')
]

cursor.executemany('''
INSERT INTO ADMIN (admin_id, admin_name, email, password)
VALUES (?, ?, ?, ?)
''', admin_data)

# Commit changes and close connection
conn.commit()
conn.close()

print("Data inserted successfully!")
