from flask import Flask, render_template, request, jsonify
import json
import os
from datetime import datetime, timedelta
import numpy as np

app = Flask(__name__)

# Simpan data di file JSON (sederhana)
DATA_FILE = 'metabolism_data.json'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {
        'users': {},
        'activities': []
    }

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def calculate_derivative(calories_data, time_data):
    """Hitung turunan dE/dt (perubahan kalori terhadap waktu)"""
    if len(calories_data) < 2:
        return [0]
    
    derivatives = []
    for i in range(1, len(calories_data)):
        dt = time_data[i] - time_data[i-1]
        if dt > 0:
            dE = calories_data[i] - calories_data[i-1]
            derivatives.append(dE/dt)
        else:
            derivatives.append(0)
    
    # Tambahkan 0 untuk titik pertama
    return [0] + derivatives

def analyze_slope(derivatives):
    """Analisis slope untuk deteksi penurunan metabolisme"""
    if len(derivatives) < 3:
        return "Data belum cukup untuk analisis"
    
    # Hitung rata-rata slope 3 titik terakhir
    recent_slope = np.mean(derivatives[-3:])
    previous_slope = np.mean(derivatives[-6:-3]) if len(derivatives) >= 6 else recent_slope
    
    if recent_slope < previous_slope * 0.7:  # Penurunan >30%
        return "⚠️ WARNING: Penurunan signifikan dalam laju pembakaran kalori!"
    elif recent_slope < previous_slope:
        return "ℹ️ PERHATIAN: Tren penurunan laju metabolisme terdeteksi"
    else:
        return "✅ Laju metabolisme stabil/naik"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    
    # Ambil data dari form
    berat_badan = float(data['weight'])
    tinggi = float(data['height'])
    usia = int(data['age'])
    aktivitas = data['activities']
    
    # Hitung BMR (Basal Metabolic Rate)
    # Rumus Mifflin-St Jeor
    bmr = 10 * berat_badan + 6.25 * tinggi - 5 * usia + 5
    
    # Faktor aktivitas
    faktor_aktivitas = {
        'sedentary': 1.2,
        'ringan': 1.375,
        'sedang': 1.55,
        'berat': 1.725,
        'sangat_berat': 1.9
    }
    
    tdee = bmr * faktor_aktivitas.get(aktivitas, 1.2)
    
    # Generate data simulasi untuk kurva
    days = list(range(1, 31))
    
    # Simulasi data kalori harian dengan variasi
    np.random.seed(42)
    base_calories = [tdee + np.random.normal(0, 100) for _ in days]
    
    # Hitung turunan (dE/dt)
    # Asumsikan dt = 1 hari
    derivatives = calculate_derivative(base_calories, days)
    
    # Analisis slope
    analysis_result = analyze_slope(derivatives)
    
    # Simpan data
    data_store = load_data()
    user_id = f"user_{len(data_store['users']) + 1}"
    
    data_store['users'][user_id] = {
        'profile': {
            'weight': berat_badan,
            'height': tinggi,
            'age': usia,
            'activity': aktivitas,
            'bmr': bmr,
            'tdee': tdee
        },
        'calories_data': base_calories,
        'derivatives': derivatives,
        'analysis': analysis_result,
        'timestamp': datetime.now().isoformat()
    }
    
    save_data(data_store)
    
    return jsonify({
        'bmr': round(bmr, 2),
        'tdee': round(tdee, 2),
        'days': days,
        'calories': [round(c, 2) for c in base_calories],
        'derivatives': [round(d, 2) for d in derivatives],
        'analysis': analysis_result
    })

@app.route('/dashboard')
def dashboard():
    data_store = load_data()
    
    if not data_store['users']:
        return render_template('dashboard.html', 
                             has_data=False,
                             message="Belum ada data yang dianalisis")
    
    # Ambil data terakhir
    latest_user = list(data_store['users'].values())[-1]
    
    return render_template('dashboard.html',
                         has_data=True,
                         profile=latest_user['profile'],
                         days=list(range(1, 31)),
                         calories=latest_user['calories_data'],
                         derivatives=latest_user['derivatives'],
                         analysis=latest_user['analysis'])

@app.route('/api/trend', methods=['GET'])
def get_trend():
    """API untuk mendapatkan data trend metabolisme"""
    data_store = load_data()
    
    if not data_store['users']:
        return jsonify({'error': 'No data available'})
    
    trends = []
    for user_id, user_data in data_store['users'].items():
        trends.append({
            'id': user_id,
            'tdee': user_data['profile']['tdee'],
            'avg_calories': np.mean(user_data['calories_data']),
            'avg_derivative': np.mean(user_data['derivatives']),
            'analysis': user_data['analysis'],
            'timestamp': user_data['timestamp']
        })
    
    return jsonify(trends)

if __name__ == '__main__':
    app.run(debug=True, port=5000)