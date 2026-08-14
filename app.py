from flask import Flask, render_template, request, jsonify
import joblib, pandas as pd, re, string
from phone_lookup import lookup_number
from police_locator import find_police_stations
import os
import PyPDF2
import google.generativeai as genai



app = Flask(__name__)


model = joblib.load("Random Forest_best_model.pkl")
encoder = joblib.load("label_encoder.pkl")


recent_checks = []


suspicious_keywords = [
    'login', 'signin', 'verify', 'update',
    'banking', 'account', 'secure', 'ebay', 'paypal'
]

def extract_features(url: str) -> pd.DataFrame:
    """Extract features from a URL for ML model."""
    features = {
        'url_length': len(url),
        'num_digits': sum(c.isdigit() for c in url),
        'num_special_chars': sum(c in string.punctuation for c in url),
        'num_subdomains': url.count('.') - 1,
        'has_ip': 1 if re.search(r'\d+\.\d+\.\d+\.\d+', url) else 0,
        'has_https': int(url.lower().startswith("https")),
        'num_params': url.count('?'),
        'num_fragments': url.count('#'),
        'num_slashes': url.count('/'),
        'has_suspicious_words': int(any(word in url.lower() for word in suspicious_keywords)),
    }
    tld = url.split('.')[-1]
    features['tld_length'] = len(tld)
    features['is_common_tld'] = int(tld in ['com', 'org', 'net', 'edu', 'gov'])
    features['has_hex'] = int(bool(re.search(r'%[0-9a-fA-F]{2}', url)))
    features['repeated_chars'] = int(bool(re.search(r'(.)\1{3,}', url)))
    return pd.DataFrame([features])

# Set up the Google API Key
os.environ["GOOGLE_API_KEY"] = "AIzaSyAW_VHHUYs4XGedMBbFs6ryejREhriKQW0"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# Initialize the Gemini model
model_2 = genai.GenerativeModel("gemini-2.5-flash")

# functions
def predict_fake_or_real_email_content(text):
    prompt = f"""
    You are an expert in identifying scam messages in text, email etc. Analyze the given text and classify it as:

    - **Real/Legitimate** (Authentic, safe message)
    - **Scam/Fake** (Phishing, fraud, or suspicious message)

    **for the following Text:**
    {text}

    **Return a clear message indicating whether this content is real or a scam. 
    If it is a scam, mention why it seems fraudulent. If it is real, state that it is legitimate.**

    **Only return the classification message and nothing else.**
    Note: Don't return empty or null, you only need to return message for the input text
    """

    response = model_2.generate_content(prompt)
    return response.text.strip() if response else "Classification failed."


@app.route('/')
def home():
    return render_template('home.html')

@app.route('/index', methods=['GET', 'POST'])
def index():
    """Phishing URL detection"""
    result, url = None, ""
    if request.method == 'POST':
        url = request.form['url'].strip()
        if url:
            features = extract_features(url)
            pred = model.predict(features)
            pred_class = encoder.inverse_transform(pred)[0]
            if pred_class == 'benign':
                result = "URL is: Safe"
            else:
                result = f"URL is: Unsafe ({pred_class})"

            
            if len(recent_checks) >= 5:
                recent_checks.pop(0)
            recent_checks.append({'url': url, 'result': result})

    return render_template('index.html', result=result, url=url, recent_checks=recent_checks[::-1])

@app.route('/phone', methods=['GET', 'POST'])
def phone_lookup():
    """Phone number lookup"""
    result, phone = None, ""
    if request.method == 'POST':
        phone = request.form['phone'].strip()
        if phone:
            result = lookup_number(phone)
    return render_template('phone.html', result=result, phone=phone)

@app.route('/map')
def map_view():
    """Render generated map page"""
    return render_template('mylocation.html')


@app.route("/police", methods=["GET", "POST"])
def police_locator():
    stations, query, error_message = [], "", None
    if request.method == "POST":
        query = request.form["location"].strip()
        if query:
            stations, map_file, error_message = find_police_stations(query)
    return render_template("police.html", stations=stations, query=query, error_message=error_message)

@app.route("/police/map")
def police_map():
    return render_template("police_map.html")


@app.route("/Awareness")
def awareness():
    return render_template("Awarenness.html")

@app.route('/scan', methods=["GET", "POST"])
def detect_scam():
    if 'file' not in request.files:
        return render_template("scan_file.html", message="No file uploaded.")

    file = request.files['file']
    extracted_text = ""

    if file.filename.endswith('.pdf'):
        pdf_reader = PyPDF2.PdfReader(file)
        extracted_text = " ".join([page.extract_text() for page in pdf_reader.pages if page.extract_text()])
    elif file.filename.endswith('.txt'):
        extracted_text = file.read().decode("utf-8")
    else:
        return render_template("scan_file.html", message="Invalid file type. Please upload a PDF or TXT file.")

    if not extracted_text.strip():
        return render_template("scan_file.html", message="File is empty or text could not be extracted.")

    message = predict_fake_or_real_email_content(extracted_text)
    return render_template("scan_file.html", message=message)


if __name__ == '__main__':
    app.run(debug=True)
