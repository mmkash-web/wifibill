
import os
import base64
import requests
import logging
import routeros_api  # MikroTik API
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)

# Setup logging
logging.basicConfig(level=logging.INFO)

# Load API credentials from environment variables
API_USERNAME = os.getenv('API_USERNAME')
API_PASSWORD = os.getenv('API_PASSWORD')

# MikroTik Credentials
MIKROTIK_HOST = os.getenv('MIKROTIK_HOST')
MIKROTIK_USERNAME = os.getenv('MIKROTIK_USERNAME')
MIKROTIK_PASSWORD = os.getenv('MIKROTIK_PASSWORD')

# Check that required variables are set
if not all([API_USERNAME, API_PASSWORD, MIKROTIK_HOST, MIKROTIK_USERNAME, MIKROTIK_PASSWORD]):
    raise EnvironmentError("Required environment variables are missing.")

# Create Basic Auth token
credentials = f"{API_USERNAME}:{API_PASSWORD}"
encoded_credentials = base64.b64encode(credentials.encode()).decode()
basic_auth_token = f"Basic {encoded_credentials}"

# Define available packages
data_packages = {
    'data_1': ('2 HOURS UNLIMITED', 5),
    'data_2': ('12 HOURS UNLIMITED', 15),
    'data_3': ('24 HOURS UNLIMITED', 20),
    'data_4': ('4 DAYS UNLIMITED', 50),
    'data_5': ('8 DAYS UNLIMITED', 100),
    'data_6': ('1 MONTH UNLIMITED', 300)
}

# Route to display the main page
@app.route('/')
def index():
    return render_template('index.html', data_packages=data_packages)

# Route to handle package purchase
@app.route('/api/buy', methods=['POST'])
def buy_package():
    data = request.json
    package_name = data['packageName']
    amount = float(data['amount'])
    phone_number = data['phoneNumber']

    stk_push_url = "https://backend.payhero.co.ke/api/v2/payments"
    payload = {
        "amount": amount,
        "phone_number": phone_number,
        "channel_id": 852,
        "provider": "m-pesa",
        "external_reference": "INV-009",
        "callback_url": "https://wifipay-f445b267e0c4.herokuapp.com/payhero-callback"  # Change to your actual domain
    }
    headers = {"Authorization": basic_auth_token}

    logging.info(f"Initiating STK Push: {payload}")

    try:
        response = requests.post(stk_push_url, json=payload, headers=headers)
        response_json = response.json()

        logging.info(f"Response Status Code: {response.status_code}")
        logging.info(f"Response JSON: {response_json}")

        if response.status_code in [200, 201] and response_json.get('success'):
            return jsonify(success=True, message="STK push sent successfully.")
        else:
            message = response_json.get('error_message', 'Unknown error')
            logging.error(f"Payment failed: {message}")
            return jsonify(success=False, message=message)

    except Exception as e:
        logging.error(f"Exception occurred: {e}")
        return jsonify(success=False, message=str(e))


# Function to add user to MikroTik
def add_user_to_mikrotik(phone_number, package):
    """Connects to MikroTik and adds user to Hotspot"""
    try:
        logging.info(f"Connecting to MikroTik at {MIKROTIK_HOST} ...")
        connection = routeros_api.RouterOsApiPool(
            MIKROTIK_HOST, username=MIKROTIK_USERNAME, password=MIKROTIK_PASSWORD, plaintext_login=True
        )
        api = connection.get_api()

        # Convert phone number to username
        username = phone_number
        password = phone_number[-4:]  # Last 4 digits as password
        profile = package.replace(" ", "_")  # Use package name for profile

        # Add user to MikroTik Hotspot
        api.get_resource('/ip/hotspot/user').add(
            name=username,
            password=password,
            profile=profile,
            comment=f"Auto-added {package}"
        )

        logging.info(f"User {username} added to MikroTik with package {package}")
        connection.disconnect()
        return True

    except routeros_api.exceptions.RouterOsApiConnectionError as e:
        logging.error("Failed to connect to MikroTik. Check network, firewall, or API settings.")
        logging.error(f"Connection Error: {e}")
        return False
    except Exception as e:
        logging.error(f"Error adding user to MikroTik: {e}")
        return False


# Route to handle Payhero payment confirmation callback
@app.route('/payhero-callback', methods=['POST'])
def payhero_callback():
    """Handle Payhero payment confirmation."""
    data = request.json
    logging.info(f"Received Payhero callback: {data}")

    # Check for required fields in Payhero response
    required_fields = ['status', 'amount', 'phone_number']
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        logging.error(f"Missing required fields in Payhero response: {missing_fields}")
        return jsonify(success=False, message=f"Missing required fields: {', '.join(missing_fields)}")

    status = data.get('status')
    amount = data.get('amount')
    phone_number = data.get('phone_number')

    # Find package by amount
    package_name = None
    for key, value in data_packages.items():
        if value[1] == amount:
            package_name = value[0]
            break

    if not package_name:
        logging.error(f"No matching package for amount: {amount}")
        return jsonify(success=False, message="Invalid package.")

    if status == "SUCCESS":
        logging.info(f"Payment successful for {phone_number}, package: {package_name}")

        # Add user to MikroTik Hotspot
        if add_user_to_mikrotik(phone_number, package_name):
            return jsonify(success=True, message="User activated successfully.")
        else:
            return jsonify(success=False, message="MikroTik activation failed.")

    else:
        logging.error(f"Payment failed for {phone_number}, status: {status}")
        return jsonify(success=False, message="Payment verification failed.")


if __name__ == '__main__':
    app.run(debug=True)
