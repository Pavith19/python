import mysql.connector
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO
import time
import threading
import random
import math
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Database details (Replace with your actual credentials)
DB_HOST = "car-management-db.crikk8q000mv.eu-north-1.rds.amazonaws.com"
DB_PORT = 3306
DB_USERNAME = "admin"
DB_PASSWORD = "Pavistar66"
DB_DATABASE = "carcare_db"

class OBDSimulator:
    def __init__(self):
        self.is_running = False
        self.data_thread = None
        self.time_counter = 0

        # Initialize car state
        self.car_state = {
            'engine_running': False,
            'accelerating': False,
            'braking': False,
            'current_speed': 0,
            'target_speed': 0
        }

        # Initialize sensor values
        self.sensor_values = {
            'engine_temp': 20,      # Start cold
            'rpm': 0,
            'speed': 0,
            'air_temp': 25,
            'engine_load': 0,
            'battery_voltage': 12.4,
            'coolant_temp': 20,
            'fuel_pressure': 0,
            'throttle_pos': 0
        }

        # Initialize update timers
        self.last_updates = {
            'engine_temp': datetime.now(),
            'rpm': datetime.now(),
            'speed': datetime.now(),
            'air_temp': datetime.now(),
            'engine_load': datetime.now(),
            'battery_voltage': datetime.now(),
            'coolant_temp': datetime.now(),
            'fuel_pressure': datetime.now(),
            'throttle_pos': datetime.now()
        }

    def should_update(self, sensor, interval):
        now = datetime.now()
        if (now - self.last_updates[sensor]) >= timedelta(seconds=interval):
            self.last_updates[sensor] = now
            return True
        return False

    def connect(self):
        try:
            print("Starting simulator...")
            self.is_running = True
            if self.data_thread is None or not self.data_thread.is_alive():
                self.data_thread = threading.Thread(target=self.stream_data)
                self.data_thread.start()
            return True
        except Exception as e:
            print(f"Simulation error: {str(e)}")
            return False

    def disconnect(self):
        print("Stopping simulator...")
        self.is_running = False
        # No need to join here as the thread will exit on its own when is_running is False

    def start_engine(self):
        self.car_state['engine_running'] = True
        self.sensor_values['rpm'] = 800  # Idle RPM
        self.sensor_values['fuel_pressure'] = 380

    def simulate_driving_behavior(self):
        # Randomly change driving behavior every 10-15 seconds
        if self.time_counter % random.randint(10, 15) == 0:
            if random.random() < 0.3:  # 30% chance to brake
                self.car_state['braking'] = True
                self.car_state['accelerating'] = False
                self.car_state['target_speed'] = max(0, self.sensor_values['speed'] - random.randint(20, 40))
            elif random.random() < 0.7:  # 40% chance to accelerate
                self.car_state['accelerating'] = True
                self.car_state['braking'] = False
                self.car_state['target_speed'] = min(120, self.sensor_values['speed'] + random.randint(20, 40))
            else:  # 30% chance to maintain speed
                self.car_state['accelerating'] = False
                self.car_state['braking'] = False

    def update_speed_and_rpm(self):
        if not self.car_state['engine_running']:
            self.start_engine()

        current_speed = self.sensor_values['speed']
        target_speed = self.car_state['target_speed']

        # Update speed
        if self.should_update('speed', 5):
            if current_speed < target_speed:
                self.sensor_values['speed'] = min(target_speed, current_speed + random.uniform(5, 10))
            elif current_speed > target_speed:
                self.sensor_values['speed'] = max(target_speed, current_speed - random.uniform(5, 10))

        # Update RPM based on speed and acceleration
        if self.should_update('rpm', 5):
            if self.car_state['accelerating']:
                base_rpm = 800 + (self.sensor_values['speed'] * 30)
                self.sensor_values['rpm'] = min(6000, base_rpm + random.uniform(200, 500))
            elif self.car_state['braking']:
                self.sensor_values['rpm'] = max(800, 800 + (self.sensor_values['speed'] * 25))
            else:
                self.sensor_values['rpm'] = 800 + (self.sensor_values['speed'] * 28)

    def update_temperatures(self):
        # Update engine temperature
        if self.should_update('engine_temp', 2):
            if self.sensor_values['engine_temp'] < 110:  # Warming up
                self.sensor_values['engine_temp'] += random.uniform(0.5, 1.5)
            else:  # Normal operation fluctuation
                self.sensor_values['engine_temp'] += random.uniform(-1.5, 0.5)

        # Update coolant temperature
        if self.should_update('coolant_temp', 2):
            self.sensor_values['coolant_temp'] = self.sensor_values['engine_temp'] + random.uniform(-2, 2)

        # Update air temperature
        if self.should_update('air_temp', 3):
            self.sensor_values['air_temp'] += random.uniform(-0.3, 0.3)

    def update_engine_metrics(self):
        # Update engine load
        if self.should_update('engine_load', 3):
            speed_factor = self.sensor_values['speed'] / 140
            rpm_factor = (self.sensor_values['rpm'] - 800) / 5200
            self.sensor_values['engine_load'] = ((speed_factor + rpm_factor) / 2) * 100

        # Update throttle position
        if self.should_update('throttle_pos', 2):
            if self.car_state['accelerating']:
                self.sensor_values['throttle_pos'] = min(100, self.sensor_values['engine_load'] + 20)
            elif self.car_state['braking']:
                self.sensor_values['throttle_pos'] = max(0, self.sensor_values['engine_load'] - 20)
            else:
                self.sensor_values['throttle_pos'] = self.sensor_values['engine_load']

        # Update fuel pressure
        if self.should_update('fuel_pressure', 5):
            base_pressure = 380
            load_factor = self.sensor_values['engine_load'] / 100
            self.sensor_values['fuel_pressure'] = base_pressure + (load_factor * 70) + random.uniform(-5, 5)

        # Update battery voltage
        if self.should_update('battery_voltage', 4):
            if self.sensor_values['rpm'] > 1000:
                self.sensor_values['battery_voltage'] = 14.2 + random.uniform(-0.2, 0.2)
            else:
                self.sensor_values['battery_voltage'] = 12.6 + random.uniform(-0.2, 0.2)

    def generate_data(self):
        self.time_counter += 1

        # Simulate driving behavior
        self.simulate_driving_behavior()

        # Update vehicle parameters
        self.update_speed_and_rpm()
        self.update_temperatures()
        self.update_engine_metrics()

        # Round all values for consistency
        return {
            'engine_temp': round(self.sensor_values['engine_temp'], 1),
            'rpm': round(self.sensor_values['rpm']),
            'speed': round(self.sensor_values['speed']),
            'air_temp': round(self.sensor_values['air_temp'], 1),
            'engine_load': round(self.sensor_values['engine_load'], 1),
            'battery_voltage': round(self.sensor_values['battery_voltage'], 1),
            'coolant_temp': round(self.sensor_values['coolant_temp'], 1),
            'fuel_pressure': round(self.sensor_values['fuel_pressure']),
            'throttle_pos': round(self.sensor_values['throttle_pos'], 1)
        }

    def stream_data(self):
        while self.is_running:
            try:
                data = self.generate_data()
                # Add DTC codes to the data
                data['dtc_codes'] = dtc_simulator.update_codes()
                print("Emitting data:", data)
                socketio.emit('sensor_data', data)
                time.sleep(1)  # Base update interval
            except Exception as e:
                print(f"Error streaming data: {str(e)}")
                self.is_running = False

class DTCSimulator:
    def __init__(self):
         # Initialize DTC related attributes with categories and priorities
        self.dtc_codes = {
            'confirmed': [],  # Initialize empty lists
            'pending': []
        }
          # Database connection
        try:
            self.conn = mysql.connector.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USERNAME,
                password=DB_PASSWORD,
                database=DB_DATABASE
            )
            self.cursor = self.conn.cursor()
        except mysql.connector.Error as err:
            print(f"Database connection error: {err}")
            self.conn = None  # Set to None if connection fails
            self.cursor = None

        initial_codes = {  # Define initial codes
            'confirmed': ['P0100', 'C1223'],
            'pending': ['C1222', 'U0107'],
        }

        for status, codes in initial_codes.items():
            for code in codes:
                dtc_details = self.get_dtc_details(code)  # Fetch details
                if dtc_details:
                    self.dtc_codes[status].append({
                        'code': code,
                        **dtc_details  # Merge details into the code dictionary
                    })
                else:
                    print(f"Failed to retrieve details for initial code {code}")
                    #add defaults if cant get
                    self.dtc_codes[status].append({
                        'code': code,
                        'description': 'Description not found',
                        'system': 'System not found',
                        'priority': 'Priority not found',
                        'solution': 'Solution not found'
                    })

        # Available DTC codes pool for simulation (4 from each category)
        self.available_dtc_codes = [
            # Powertrain (P) - Usually Urgent
            {'code': 'P0102'},
            {'code': 'P0305'},
            {'code': 'P0496'},
          

            # Body (B) - Usually Low to Moderate
            {'code': 'B1205'},
            {'code': 'B1206'},
            {'code': 'B1207'},

            # Chassis (C) - Usually Moderate to Urgent
            {'code': 'C1206'},
            {'code': 'C1215'},
            {'code': 'C1221'},

            # Network (U) - Usually Moderate
            {'code': 'U0101'},
            {'code': 'U0121'},
            {'code': 'U0137'}
        ]


        self.last_pending_update = datetime.now()
        self.last_confirm_update = datetime.now()

        # Database connection
        try:
            self.conn = mysql.connector.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USERNAME,
                password=DB_PASSWORD,
                database=DB_DATABASE
            )
            self.cursor = self.conn.cursor()
        except mysql.connector.Error as err:
            print(f"Database connection error: {err}")
            self.conn = None  # Set to None if connection fails
            self.cursor = None

    def get_dtc_details(self, code):
        """Fetches DTC details from the database."""
        if self.conn is None or self.cursor is None:
            print("No database connection available.")
            return None

        try:
            self.cursor.execute("SELECT description, category, priority, solution FROM dtc_codes WHERE code = %s", (code,))
            result = self.cursor.fetchone()
            if result:
                description, category, priority, solution = result
                return {
                    'description': description,
                    'system': category,  # 'category' in DB maps to 'system' in your structure
                    'priority': priority,
                    'solution': solution
                }
            else:
                print(f"DTC code {code} not found in database.")
                return None
        except mysql.connector.Error as err:
            print(f"Database query error: {err}")
            return None

    def update_codes(self):
        now = datetime.now()

        # Add new pending codes every 30 seconds
        if (now - self.last_pending_update) >= timedelta(seconds=35):
            self.last_pending_update = now
            if len(self.available_dtc_codes) > 0 and len(self.dtc_codes['pending']) < 8:  # Limit pending codes
                new_code_data = self.available_dtc_codes.pop(random.randint(0, len(self.available_dtc_codes) - 1))
                dtc_details = self.get_dtc_details(new_code_data['code'])
                if dtc_details:
                    new_code_data.update(dtc_details)  # Merge details
                    self.dtc_codes['pending'].append(new_code_data)
                    print(f"Added new pending code: {new_code_data['code']}")
                else:
                    print(f"Failed to retrieve details for {new_code_data['code']}")
                    # Handle error gracefully by adding default values
                    new_code_data['description'] = 'Description not found';
                    new_code_data['system'] = 'System not found';
                    new_code_data['priority'] = 'Priority not found';
                    new_code_data['solution'] = 'Solution not found';
                    self.dtc_codes['pending'].append(new_code_data)

        # Move pending to confirmed every 35 seconds
        if (now - self.last_confirm_update) >= timedelta(seconds=35):
            self.last_confirm_update = now
            if len(self.dtc_codes['pending']) > 0:
                code_to_confirm = self.dtc_codes['pending'].pop(0)
                dtc_details = self.get_dtc_details(code_to_confirm['code'])  # Fetch details again

                if dtc_details:
                    code_to_confirm.update(dtc_details)
                    self.dtc_codes['confirmed'].append(code_to_confirm)
                    print(f"Moved code to confirmed: {code_to_confirm['code']}")
                else:
                    print(f"Failed to retrieve details for {code_to_confirm['code']} on confirmation.")
                    # Handle error gracefully by adding default values
                    code_to_confirm['description'] = 'Description not found';
                    code_to_confirm['system'] = 'System not found';
                    code_to_confirm['priority'] = 'Priority not found';
                    code_to_confirm['solution'] = 'Solution not found';
                    self.dtc_codes['confirmed'].append(code_to_confirm)

        return self.dtc_codes


    def remove_confirmed_code(self, code_to_remove):
        """Removes a specific confirmed code."""
        for i, code_data in enumerate(self.dtc_codes['confirmed']):
            if code_data['code'] == code_to_remove:
                del self.dtc_codes['confirmed'][i]
                print(f"Removed confirmed code: {code_to_remove}")
                return  # Exit after removing the code

# Modify the existing simulator instance and add DTC simulator
simulator = OBDSimulator()
dtc_simulator = DTCSimulator()

# Replace the existing stream_data method in OBDSimulator (already done above)
OBDSimulator.stream_data = simulator.stream_data

@socketio.on('connect')
def handle_connect():
    print("Client connected")
    success = simulator.connect()
    socketio.emit('connection_status', {'connected': success})
    print(f"Sent connection status: {success}")

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected")
    simulator.disconnect()

@socketio.on('remove_dtc')  # Listen for the 'remove_dtc' event
def handle_remove_dtc(data):
    code_to_remove = data.get('code')
    if code_to_remove:
        dtc_simulator.remove_confirmed_code(code_to_remove)

if __name__ == '__main__':
    print("Starting server...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
