import os
import base64
import requests
import logging
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

# Check that environment variables are set
if not all([API_USERNAME, API_PASSWORD]):
    raise EnvironmentError("Required environment variables are not set.")

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
        "callback_url": "https://softcash.co.ke/billing/callbackurl.php"
    }
    headers = {"Authorization": basic_auth_token}

    logging.info(f"Initiating STK Push: {payload}")

    try:
        response = requests.post(stk_push_url, json=payload, headers=headers)
        response_json = response.json()

        logging.info(f"Response Status Code: {response.status_code}")
        logging.info(f"Response JSON: {response_json}")

        if response.status_code in [200, 201] and response_json.get('success'):
            return jsonify(success=True)
        else:
            message = response_json.get('error_message', 'Unknown error')
            logging.error(f"Payment failed: {message}")
            return jsonify(success=False, message=message)

    except Exception as e:
        logging.error(f"Exception occurred: {e}")
        return jsonify(success=False, message=str(e))

if __name__ == '__main__':
    app.run(debug=True)