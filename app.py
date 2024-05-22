from flask import Flask, request, jsonify, render_template, session, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image, ImageDraw, ImageFont
import random
import string
import io
import requests

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with a secure secret key

# VoIP.ms API credentials
VOIP_MS_API_URL = "https://voip.ms/api/v1/rest.php"
VOIP_MS_API_USERNAME = "VOIP_MS_API_USERNAME"
VOIP_MS_API_PASSWORD = "VOIP_MS_API_PASSWORD"

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    company_name = db.Column(db.String(100))
    street_address = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    state = db.Column(db.String(50), nullable=False)
    country = db.Column(db.String(50), nullable=False)  # Added country column
    zip_code = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@app.route('/')
def home():
    return "Welcome to Your VOIP COMPANY"

@app.route('/get_account_info', methods=['GET'])
def get_account_info():
    params = {
        'api_username': VOIP_MS_API_USERNAME,
        'api_password': VOIP_MS_API_PASSWORD,
        'method': 'getAccountInfo'
    }
    response = requests.get(VOIP_MS_API_URL, params=params)
    return jsonify(response.json())

@app.route('/get_balance', methods=['GET'])
def get_balance():
    params = {
        'api_username': VOIP_MS_API_USERNAME,
        'api_password': VOIP_MS_API_PASSWORD,
        'method': 'getBalance'
    }
    response = requests.get(VOIP_MS_API_URL, params=params)
    return jsonify(response.json())

@app.route('/get_cdr', methods=['GET'])
def get_cdr():
    params = {
        'api_username': VOIP_MS_API_USERNAME,
        'api_password': VOIP_MS_API_PASSWORD,
        'method': 'getCDR',
        'from': '2023-01-01',
        'to': '2023-12-31'
    }
    response = requests.get(VOIP_MS_API_URL, params=params)
    return jsonify(response.json())

@app.route('/captcha')
def captcha():
    try:
        # Generate a random string
        letters = string.ascii_uppercase + string.digits
        captcha_text = ''.join(random.choice(letters) for i in range(6))
        
        # Store the captcha text in session
        session['captcha_text'] = captcha_text

        # Create an image with the captcha text
        img = Image.new('RGB', (200, 60), color = (255, 255, 255))
        fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 32)
        d = ImageDraw.Draw(img)
        d.text((10, 10), captcha_text, font=fnt, fill=(0, 0, 0))

        # Save the image to a bytes buffer
        buf = io.BytesIO()
        img.save(buf, 'PNG')
        buf.seek(0)

        return send_file(buf, mimetype='image/png')
    except Exception as e:
        print(f"Error generating CAPTCHA: {e}")
        return "Error generating CAPTCHA", 500

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    try:
        if request.method == 'POST':
            # Retrieve form data
            first_name = request.form['first_name']
            last_name = request.form['last_name']
            company_name = request.form['company_name']
            street_address = request.form['street_address']
            city = request.form['city']
            state = request.form['state']
            country = request.form['country']
            zip_code = request.form['zip']
            phone = request.form['phone']
            email = request.form['email']
            confirm_email = request.form['confirm_email']
            password = request.form['password']
            confirm_password = request.form['confirm_password']
            security_code = request.form['security_code']
            
            # Validate form inputs
            if password != confirm_password:
                return "Passwords do not match", 400
            if email != confirm_email:
                return "Emails do not match", 400
            if security_code != session.get('captcha_text'):
                return "Invalid security code", 400
            if len(password) < 8:
                return "Password must be at least 8 characters long", 400
            if not any(char.isupper() for char in password):
                return "Password must contain at least one upper case character", 400
            if not any(char.islower() for char in password):
                return "Password must contain at least one lower case character", 400
            
            # Check if email already exists
            existing_user = User.query.filter_by(email=email).first()
            print(f"Checking if user with email {email} exists: {existing_user}")
            if existing_user:
                print(f"User with email {email} already exists.")
                return "Email already exists", 400
            
            # Create new user
            new_user = User(
                first_name=first_name,
                last_name=last_name,
                company_name=company_name,
                street_address=street_address,
                city=city,
                state=state,
                country=country,
                zip_code=zip_code,
                phone=phone,
                email=email
            )
            new_user.set_password(password)
            
            # Add user to the database
            db.session.add(new_user)
            db.session.commit()
            print(f"User {email} added to the database successfully.")
            
            # Generate a valid username
            username = f"{first_name.lower()}{last_name.lower()}{random.randint(1000, 9999)}"
            
            # Create client account on VoIP.ms
            voipms_params_client = {
                'api_username': VOIP_MS_API_USERNAME,
                'api_password': VOIP_MS_API_PASSWORD,
                'method': 'signupClient',
                'firstname': first_name,
                'lastname': last_name,
                'company': company_name,
                'address': street_address,
                'city': city,
                'state': state,
                'country': country,  # Make sure this matches a valid country code from VoIP.ms API
                'zip': zip_code,
                'phone_number': phone,
                'email': email,
                'confirm_email': confirm_email,
                'password': password,
                'confirm_password': confirm_password,
                'activate': 1,  # Optional: activate client
                'balance_management': 'all'  # Optional: balance management
            }
            voipms_response_client = requests.get(VOIP_MS_API_URL, params=voipms_params_client)
            voipms_result_client = voipms_response_client.json()
            
            if voipms_result_client['status'] == 'success':
                # Fetch valid protocols
                get_protocols_params = {
                    'api_username': VOIP_MS_API_USERNAME,
                    'api_password': VOIP_MS_API_PASSWORD,
                    'method': 'getProtocols'
                }
                protocols_response = requests.get(VOIP_MS_API_URL, params=get_protocols_params)
                protocols_result = protocols_response.json()
                
                if protocols_result['status'] == 'success':
                    # Find the SIP protocol value
                    sip_protocol = next((protocol['value'] for protocol in protocols_result['protocols'] if protocol['description'].upper() == 'SIP'), None)
                    
                    if not sip_protocol:
                        return "SIP protocol not found", 400

                    # Fetch valid routes
                    get_routes_params = {
                        'api_username': VOIP_MS_API_USERNAME,
                        'api_password': VOIP_MS_API_PASSWORD,
                        'method': 'getRoutes'
                    }
                    routes_response = requests.get(VOIP_MS_API_URL, params=get_routes_params)
                    routes_result = routes_response.json()

                    if routes_result['status'] == 'success':
                        # Find the premium route value
                        premium_route = next((route['value'] for route in routes_result['routes'] if route['description'].lower() == 'premium'), None)

                        if not premium_route:
                            return "Premium route not found", 400

                        # Fetch valid music on hold options
                        get_music_on_hold_params = {
                            'api_username': VOIP_MS_API_USERNAME,
                            'api_password': VOIP_MS_API_PASSWORD,
                            'method': 'getMusicOnHold'
                        }
                        music_on_hold_response = requests.get(VOIP_MS_API_URL, params=get_music_on_hold_params)
                        music_on_hold_result = music_on_hold_response.json()

                        if music_on_hold_result['status'] == 'success':
                            print(f"Music on hold options: {music_on_hold_result}")

                            # Find the default music on hold value
                            default_music_on_hold = next((music['value'] for music in music_on_hold_result.get('music_on_hold', []) if music['description'].lower() == 'no music'), None)

                            if not default_music_on_hold:
                                return "Default music on hold not found", 400

                            # Fetch valid device types
                            get_device_types_params = {
                                'api_username': VOIP_MS_API_USERNAME,
                                'api_password': VOIP_MS_API_PASSWORD,
                                'method': 'getDeviceTypes'
                            }
                            device_types_response = requests.get(VOIP_MS_API_URL, params=get_device_types_params)
                            device_types_result = device_types_response.json()

                            if device_types_result['status'] == 'success':
                                # Find the first device type value
                                default_device_type = next((device['value'] for device in device_types_result['device_types']), None)

                                if not default_device_type:
                                    return "Default device type not found", 400

                                # Fetch valid codecs
                                get_allowed_codecs_params = {
                                    'api_username': VOIP_MS_API_USERNAME,
                                    'api_password': VOIP_MS_API_PASSWORD,
                                    'method': 'getAllowedCodecs'
                                }
                                allowed_codecs_response = requests.get(VOIP_MS_API_URL, params=get_allowed_codecs_params)
                                allowed_codecs_result = allowed_codecs_response.json()

                                print(f"Allowed codecs options: {allowed_codecs_result}")

                                if allowed_codecs_result['status'] == 'success':
                                    # Find the valid allowed codecs values
                                    allowed_codecs = ';'.join([codec['value'] for codec in allowed_codecs_result['allowed_codecs']])

                                    # Ensure caller ID is a valid 10-digit number
                                    if len(phone) != 10 or not phone.isdigit():
                                        return "Invalid caller ID number", 400

                                    # If client creation is successful, proceed to create sub-account
                                    voipms_params_subaccount = {
                                        'api_username': VOIP_MS_API_USERNAME,
                                        'api_password': VOIP_MS_API_PASSWORD,
                                        'method': 'createSubAccount',
                                        'username': username,
                                        'protocol': sip_protocol,  # Use the correct protocol value
                                        'description': 'Sub Account',
                                        'auth_type': 'user',  # Assuming 'user' as a default authorization type
                                        'password': password,
                                        'device_type': default_device_type,  # Use the correct device type
                                        'callerid_number': phone,
                                        'lock_international': 'no',  # Assuming 'no' as a default lock international
                                        'international_route': premium_route,  # Use the correct route value
                                        'music_on_hold': default_music_on_hold,  # Use the correct music on hold
                                        'allowed_codecs': allowed_codecs,  # Use the correct allowed codecs
                                        'dtmf_mode': 'rfc2833',  # Assuming 'rfc2833' as a default DTMF mode
                                        'nat': 'yes',  # Assuming 'yes' as a default NAT mode
                                    }

                                    # Debugging: Print all parameters
                                    print("Creating sub-account with parameters:")
                                    for key, value in voipms_params_subaccount.items():
                                        print(f"{key}: {value}")

                                    voipms_response_subaccount = requests.get(VOIP_MS_API_URL, params=voipms_params_subaccount)
                                    voipms_result_subaccount = voipms_response_subaccount.json()

                                    if voipms_result_subaccount['status'] == 'success':
                                        return "Account created successfully on VOIP COMPANY and VoIP.ms!"
                                    else:
                                        print(f"Error creating sub-account on VoIP.ms: {voipms_result_subaccount}")
                                        return f"Error creating sub-account on VoIP.ms: {voipms_result_subaccount['status']}", 400
                                else:
                                    return f"Error fetching allowed codecs: {allowed_codecs_result['status']}", 400
                            else:
                                return f"Error fetching device types: {device_types_result['status']}", 400
                        else:
                            return f"Error fetching music on hold: {music_on_hold_result['status']}", 400
                    else:
                        return f"Error fetching routes: {routes_result['status']}", 400
                else:
                    return f"Error fetching protocols: {protocols_result['status']}", 400
            else:
                print(f"Error creating client account on VoIP.ms: {voipms_result_client}")
                return f"Error creating client account on VoIP.ms: {voipms_result_client['status']}", 400

        return render_template('signup.html')  # Render the HTML form
    except Exception as e:
        print(f"Error in signup: {e}")
        return "Error processing signup", 500

@app.route('/delete_user', methods=['POST'])
def delete_user():
    try:
        email = request.form['email']

        # Find the user by email
        user = User.query.filter_by(email=email).first()

        if user:
            # Delete the user from the database
            db.session.delete(user)
            db.session.commit()
            return jsonify({"status": "success", "message": "User deleted successfully"}), 200
        else:
            return jsonify({"status": "error", "message": "User not found"}), 404
    except Exception as e:
        print(f"Error deleting user: {e}")
        return jsonify({"status": "error", "message": "Error deleting user"}), 500

if __name__:
    print("Starting Flask app")
    try:
        app.run(host='0.0.0.0', port=8000, debug=True)
    except Exception as e:
        print(f"Error starting Flask app: {e}")
