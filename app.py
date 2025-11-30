from flask import Flask, render_template, render_template_string, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json
import math

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blood_supply.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Database Models
class BloodInventory(db.Model):
    blood_id = db.Column(db.String(20), primary_key=True)
    blood_type = db.Column(db.String(5), nullable=False)
    product_type = db.Column(db.String(20), nullable=False)
    donation_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    current_location = db.Column(db.String(10), nullable=False)
    temperature_zone = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='Available')
    
    def to_dict(self):
        return {
            'blood_id': self.blood_id,
            'blood_type': self.blood_type,
            'product_type': self.product_type,
            'donation_date': self.donation_date.strftime('%Y-%m-%d'),
            'expiry_date': self.expiry_date.strftime('%Y-%m-%d'),
            'current_location': self.current_location,
            'temperature_zone': self.temperature_zone,
            'status': self.status,
            'days_remaining': (self.expiry_date - datetime.now().date()).days
        }

class Location(db.Model):
    location_code = db.Column(db.String(10), primary_key=True)
    location_name = db.Column(db.String(100), nullable=False)
    location_type = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    current_stock = db.Column(db.Integer, default=0)
    temperature_capability = db.Column(db.String(50), nullable=False)
    contact_person = db.Column(db.String(100))
    phone_number = db.Column(db.String(20))
    
    def to_dict(self):
        return {
            'location_code': self.location_code,
            'location_name': self.location_name,
            'location_type': self.location_type,
            'capacity': self.capacity,
            'current_stock': self.current_stock,
            'temperature_capability': self.temperature_capability,
            'contact_person': self.contact_person,
            'phone_number': self.phone_number,
            'usage_percentage': math.ceil((self.current_stock / self.capacity) * 100) if self.capacity > 0 else 0
        }

class Transportation(db.Model):
    shipment_id = db.Column(db.String(20), primary_key=True)
    from_location = db.Column(db.String(10), nullable=False)
    to_location = db.Column(db.String(10), nullable=False)
    scheduled_departure = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='Scheduled')
    driver_name = db.Column(db.String(100))
    driver_contact = db.Column(db.String(20))
    security_status = db.Column(db.String(20), default='Secure')

class ExpiryAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blood_id = db.Column(db.String(20), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)
    alert_date = db.Column(db.DateTime, default=datetime.now)
    days_remaining = db.Column(db.Integer)
    action_taken = db.Column(db.String(50), default='Pending')

# Utility Functions
def calculate_expiry_date(donation_date, product_type):
    """Calculate expiry date based on product type"""
    expiry_days = {
        'Whole Blood': 35,
        'RBC': 42,
        'Platelets': 5,
        'Plasma': 365
    }
    return donation_date + timedelta(days=expiry_days.get(product_type, 35))

def get_temperature_zone(product_type):
    """Determine storage temperature requirements"""
    temp_zones = {
        'Whole Blood': 'Refrigerated (1-6°C)',
        'RBC': 'Refrigerated (1-6°C)',
        'Platelets': 'Room Temp (20-24°C)',
        'Plasma': 'Frozen (-18°C or below)'
    }
    return temp_zones.get(product_type, 'Refrigerated (1-6°C)')

def translate_text(text, target_lang):
    """Handle language translation"""
    translations = {
        'en': {
            'Blood Supply Chain Management': 'Blood Supply Chain Management',
            'Dashboard': 'Dashboard',
            'Inventory': 'Inventory',
            'Expired Blood': 'Expired Blood',
            'Reports': 'Reports',
            'Mobile Entry': 'Mobile Entry',
            'Total Blood Units': 'Total Blood Units',
            'Expiring Soon': 'Expiring Soon',
            'Active Shipments': 'Active Shipments',
            'Storage Locations': 'Storage Locations',
            'Add New Blood Unit': 'Add New Blood Unit',
            'Blood Type': 'Blood Type',
            'Product Type': 'Product Type',
            'Donation Date': 'Donation Date',
            'Current Location': 'Current Location',
            'Status': 'Status',
            'Actions': 'Actions',
            'Dispose': 'Dispose',
            'Close': 'Close',
            'Save': 'Save',
            'Submit': 'Submit',
            'Cancel': 'Cancel',
            'Yes': 'Yes',
            'No': 'No',
            'Expired': 'Expired',
            'Expiring Soon': 'Expiring Soon',
            'Good': 'Good',
            'Available': 'Available',
            'Used': 'Used',
            'Disposed': 'Disposed'
        },
        'my': {
            'Blood Supply Chain Management': 'သွေးထောက်ပံ့ရေးကွင်းဆက်စီမံခန့်ခွဲမှုစနစ်',
            'Dashboard': 'ပင်မစာမျက်နှာ',
            'Inventory': 'စာရင်း',
            'Expired Blood': 'သက်တမ်းကုန်သွေး',
            'Reports': 'အစီရင်ခံစာများ',
            'Mobile Entry': 'မိုဘိုင်းထည့်သွင်းမှု',
            'Total Blood Units': 'စုစုပေါင်းသွေးယူနစ်',
            'Expiring Soon': 'သက်တမ်းကုန်ရန်နီးပါး',
            'Active Shipments': 'တက်ကြွသွေးပို့ဆောင်မှုများ',
            'Storage Locations': 'သိုလှောင်ရာနေရာများ',
            'Add New Blood Unit': 'သွေးယူနစ်အသစ်ထည့်ရန်',
            'Blood Type': 'သွေးအမျိုးအစား',
            'Product Type': 'ထုတ်ကုန်အမျိုးအစား',
            'Donation Date': 'လှူဒါန်းသည့်ရက်စွဲ',
            'Current Location': 'လက်ရှိတည်နေရာ',
            'Status': 'အခြေအနေ',
            'Actions': 'လုပ်ဆောင်ချက်များ',
            'Dispose': 'စွန့်ပစ်ရန်',
            'Close': 'ပိတ်ရန်',
            'Save': 'သိမ်းရန်',
            'Submit': 'တင်သွင်းရန်',
            'Cancel': 'မလုပ်တော့',
            'Yes': 'ဟုတ်ကဲ့',
            'No': 'မဟုတ်ပါ',
            'Expired': 'သက်တမ်းကုန်',
            'Expiring Soon': 'သက်တမ်းကုန်ရန်နီးပါး',
            'Good': 'ကောင်းမွန်',
            'Available': 'ရရှိနိုင်',
            'Used': 'အသုံးပြုပြီး',
            'Disposed': 'စွန့်ပစ်ပြီး'
        }
    }
    return translations.get(target_lang, {}).get(text, text)

def get_current_language():
    """Get current language from session"""
    return session.get('language', 'en')

def get_expired_blood_count():
    """Get count of expired blood units"""
    today = datetime.now().date()
    return BloodInventory.query.filter(BloodInventory.expiry_date < today).count()

def get_expiring_soon_count(days=7):
    """Get count of blood units expiring soon"""
    today = datetime.now().date()
    future_date = today + timedelta(days=days)
    return BloodInventory.query.filter(
        BloodInventory.expiry_date >= today,
        BloodInventory.expiry_date <= future_date
    ).count()

# Routes
@app.route('/')
def dashboard():
    language = get_current_language()
    
    # Statistics
    total_units = BloodInventory.query.count()
    expiring_soon = get_expiring_soon_count()
    active_shipments = Transportation.query.filter_by(status='In Transit').count()
    storage_locations = Location.query.count()
    
    # Recent alerts
    recent_alerts = ExpiryAlert.query.order_by(ExpiryAlert.alert_date.desc()).limit(5).all()
    
    # Location capacity
    locations = Location.query.all()
    
    return render_template('dashboard.html',
                         language=language,
                         total_units=total_units,
                         expiring_soon=expiring_soon,
                         active_shipments=active_shipments,
                         storage_locations=storage_locations,
                         recent_alerts=recent_alerts,
                         locations=locations,
                         translate_text=translate_text)

@app.route('/inventory')
def inventory():
    language = get_current_language()
    
    # Filter parameters
    blood_type_filter = request.args.get('blood_type', '')
    location_filter = request.args.get('location', '')
    
    # Query with filters
    query = BloodInventory.query
    
    if blood_type_filter:
        query = query.filter(BloodInventory.blood_type == blood_type_filter)
    if location_filter:
        query = query.filter(BloodInventory.current_location == location_filter)
    
    inventory_items = query.all()
    locations = Location.query.all()
    
    return render_template('inventory.html',
                         language=language,
                         inventory_items=inventory_items,
                         locations=locations,
                         blood_type_filter=blood_type_filter,
                         location_filter=location_filter,
                         translate_text=translate_text)

@app.route('/expired-blood')
def expired_blood():
    language = get_current_language()
    
    today = datetime.now().date()
    expired_items = BloodInventory.query.filter(BloodInventory.expiry_date < today).all()
    
    return render_template('expired_blood.html',
                         language=language,
                         expired_items=expired_items,
                         translate_text=translate_text)

@app.route('/reports')
def reports():
    language = get_current_language()
    
    # Comprehensive statistics
    total_units = BloodInventory.query.count()
    expiring_3_days = get_expiring_soon_count(3)
    expired_units = get_expired_blood_count()
    
    # Calculate wastage rate
    wastage_rate = (expired_units / total_units * 100) if total_units > 0 else 0
    
    # Blood type distribution
    blood_types = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    blood_type_distribution = {}
    for bt in blood_types:
        count = BloodInventory.query.filter_by(blood_type=bt).count()
        blood_type_distribution[bt] = count
    
    # Location capacity summaries
    locations = Location.query.all()
    
    return render_template('reports.html',
                         language=language,
                         total_units=total_units,
                         expiring_3_days=expiring_3_days,
                         expired_units=expired_units,
                         wastage_rate=round(wastage_rate, 2),
                         blood_type_distribution=blood_type_distribution,
                         locations=locations,
                         translate_text=translate_text)

@app.route('/mobile')
def mobile_quick_entry():
    language = get_current_language()
    from flask import Flask, render_template_string, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'myanmar-blood-supply-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blood_supply.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Translation dictionaries - FIXED: Added missing translations and fixed syntax
BURMESE_TO_ENGLISH = {
    # Navigation
    'မြန်မာသွေးရည်ကြည်ထောက်ပံ့ရေးစနစ်': 'Myanmar Blood Supply Chain System',
    'ပင်မစာမျက်နှာ': 'Dashboard',
    'သွေးစာရင်း': 'Inventory',
    'သိုလှောင်ရန်နေရာများ': 'Locations',
    'ပို့ဆောင်ရေး': 'Transportation',
    'အစီရင်ခံစာများ': 'Reports',
    'မိုဘိုင်း': 'Mobile',
    
    # Common terms
    'သွေးအမျိုးအစား': 'Blood Type',
    'သွေးလှူရန်နေ့စွဲ': 'Donation Date',
    'သက်တမ်းကုန်ဆုံးရက်': 'Expiry Date',
    'လက်ရှိတည်နေရာ': 'Current Location',
    'အပူချိန်ဇုန်': 'Temperature Zone',
    'အခြေအနေ': 'Status',
    'သိမ်းဆည်းမည်': 'Save',
    'မှတ်တမ်းထည့်မည်': 'Add Record',
    'ရှာဖွေမည်': 'Search',
    'စာရင်းသွင်းမည်': 'Register',
    'ပယ်ဖျက်မည်': 'Cancel',
    'စိစစ်ချက်များ': 'Filters',
    'နေရာအားလုံး': 'All Locations',
    'အမျိုးအစားအားလုံး': 'All Types',
    'ရှင်းလင်းမည်': 'Clear',
    'ပြည့်သော': 'full',
    
    # Blood types
    'အေပေါင်း': 'A+',
    'ဘီပေါင်း': 'B+',
    'အိုပေါင်း': 'O+',
    'အေဘီပေါင်း': 'AB+',
    
    # Product types
    'သွေးပြည့်ဝ': 'Whole Blood',
    'သွေးနီဥ': 'RBC',
    'သွေးဥဆဲလ်များ': 'Platelets',
    'သွေးရည်ကြည်': 'Plasma',
    
    # Status
    'ရရှိနိုင်': 'Available',
    'သုံးပြီး': 'Used',
    'သက်တမ်းကုန်': 'Expired',
    'စီစဉ်ထား': 'Scheduled',
    'ပို့ဆောင်နေ': 'In Transit',
    
    # Alerts and messages
    'အောင်မြင်စွာသိမ်းဆည်းပြီး': 'Successfully saved',
    'မှားယွင်းမှုရှိသည်': 'Error occurred',
    'သတိပေးချက်': 'Warning',
    'အန္တရာယ်ရှိ': 'Danger',
    'သွေးယူနစ်ထည့်သွင်းပြီး': 'Blood unit added',
    'သွေးယူနစ်': 'Blood unit',
    'ရက်သတ္တပတ်': 'days',
    'သတိပေးချက်မရှိပါ': 'No recent alerts',
    'လျင်မြန်သောလုပ်ဆောင်ချက်များ': 'Quick Actions',
    'မိုဘိုင်းဖြင့်ထည့်သွင်းမည်': 'Mobile Entry',
    'သွေးယူနစ်ထည့်သွင်းမည်': 'Add Blood Unit',
    'အစီရင်ခံစာကြည့်ရှုမည်': 'View Reports',
    'စာရင်းအင်းများ': 'Reports & Analytics',
    'သွေးဆုံးရှုံးနိုင်ခြေ': 'Wastage Risk',
    
    # Dashboard
    'ပင်မစာမျက်နှာအခြေအနေ': 'Dashboard Overview',
    'စုစုပေါင်းသွေးယူနစ်များ': 'Total Blood Units',
    'သက်တမ်းတိုတောင်းမည့်အရာ (ရက် ၇)': 'Expiring Soon (7 days)',
    'တက်ကြွသောပို့ဆောင်မှုများ': 'Active Shipments',
    'သိုလှောင်�ရာနေရာများ': 'Storage Locations',
    'နေရာလုံလောက်မှုအခြေအနေ': 'Location Capacity',
    'မကြာသေးမီသတိပေးချက်များ': 'Recent Alerts',
    'သွေးယူနစ် သက်တမ်းကုန်ဆုံးရန်': 'expiring in',
    
    # Inventory
    'သွေးစာရင်း': 'Blood Inventory',
    'သွေးယူနစ်ထည့်သွင်းမည်': 'Add Blood Unit',
    'သွေးအမျိုးအစားရွေးချယ်ပါ': 'Select Blood Type',
    'ထုတ်ကုန်အမျိုးအစားရွေးချယ်ပါ': 'Select Product Type',
    'လက်ရှိတည်နေရာရွေးချယ်ပါ': 'Select Location',
    'သွေးယူနစ်များမတွေ့ရှိပါ': 'No blood units found',
    'ရက်ကျန်ရှိ': 'Days Left',
    
    # Transportation
    'ပို့ဆောင်ရေးအခြေအနေ': 'Transportation',
    'ပို့ဆောင်မှုအိုင်ဒီ': 'Shipment ID',
    'မှ': 'From',
    'သို့': 'To',
    
    # Locations
    'ကုဒ်': 'Code',
    'စတော့': 'Stock',
    'ယူနစ်': 'units',
    'ဆက်သွယ်ရန်': 'Contact',

    # Expired Blood Management
    'သက်တမ်းကုန်သွေးယူနစ်များ': 'Expired Blood Units',
    'သက်တမ်းကုန်ယူနစ်': 'expired units',
    'ရက်ပေါင်း': 'Days Expired',
    'လုပ်ဆောင်ချက်များ': 'Actions',
    'စွန့်ပစ်ပြီးဟုမှတ်သားမည်': 'Mark as Disposed',
    'သွေးယူနစ်ကိုစွန့်ပစ်ပြီးဟုမှတ်သားမလားသေချာပါသလား': 'Are you sure you want to mark this blood unit as disposed?',
    'သွေးယူနစ်ကိုစွန့်ပစ်ပြီးဟုမှတ်သားပြီး': 'Blood unit marked as disposed',
    'သတိပေးချက် - သက်တမ်းကုန်သွေးရှိပါသည်': 'Alert: Expired Blood Detected',
    'သွေးယူနစ်သက်တမ်းကုန်သွားပြီးဂရုစိုက်ရန်လိုအပ်သည်': 'blood units have expired and require attention.',
    'သက်တမ်းကုန်သွေးစီမံခန့်ခွဲမည်': 'Manage Expired Blood',
    'သက်တမ်းကုန်နှုန်း': 'Wastage Rate',
    'စီမံခန့်ခွဲရန်': 'Manage',
    'သက်တမ်းကုန်သွေးများ': 'Expired Units',
    'သက်တမ်းကုန်': 'Expired',
    'စွန့်ပစ်ပြီးပြီ': 'Disposed',
    'သက်တမ်းကုန်သွေး�ယူနစ်များမတွေ့ရှိပါ': 'No expired blood units found',
    'သွေးယူနစ်အားလုံးသက်တမ်းမကုန်သေးပါ': 'All blood units are within their validity period.',
    'သွေးစာရင်းသို့ပြန်သွားမည်': 'Back to Inventory',
    
    # New translations for Reports and Mobile
    'သွေးအမျိုးအစားခွဲခြားမှု': 'Blood Type Distribution',
    'အရေအတွက်': 'Count',
    'ရာခိုင်နှုန်း': 'Percentage',
    'မှတ်တမ်းထည့်နေသည်': 'Adding...',
    'ခဏအကြာတွင်': 'Just now',
    'မကြာသေးမီမှတ်တမ်းများ': 'Recent Entries',
    'မကြာသေးမီမှတ်တမ်းမရှိပါ': 'No recent entries',
    'အမြန်သွေးယူနစ်ထည့်သွင်းမည်': 'Quick Blood Unit Entry',
    'နေရာအကျဉ်းချုပ်': 'Location Summary',
    'အချက်အလက်များ': 'Analytics',
    'စာရင်းဇယား': 'Statistics',
    # Add to BURMESE_TO_ENGLISH dictionary:
    'ဖုန်းနံပါတ်': 'Phone',
    'အပူချိန်စွမ်းရည်': 'Temperature Capability',
}

ENGLISH_TO_BURMESE = {v: k for k, v in BURMESE_TO_ENGLISH.items()}

def get_current_language():
    """Get current language from session or default to English"""
    return session.get('language', 'en')

def translate_text(text, lang=None):
    """Translate text between Burmese and English"""
    if lang is None:
        lang = get_current_language()
    
    if lang == 'en':
        return BURMESE_TO_ENGLISH.get(text, text)
    else:
        return ENGLISH_TO_BURMESE.get(text, text)

# Database Models
class BloodInventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blood_id = db.Column(db.String(50), unique=True, nullable=False)
    blood_type = db.Column(db.String(10), nullable=False)
    product_type = db.Column(db.String(20), nullable=False)
    donation_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    current_location = db.Column(db.String(50), nullable=False)
    temperature_zone = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='Available')

class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location_code = db.Column(db.String(20), unique=True, nullable=False)
    location_name = db.Column(db.String(100), nullable=False)
    location_type = db.Column(db.String(20), nullable=False)
    capacity = db.Column(db.Integer)
    current_stock = db.Column(db.Integer, default=0)
    temperature_capability = db.Column(db.String(100))
    contact_person = db.Column(db.String(100))
    phone_number = db.Column(db.String(20))

class Transportation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    shipment_id = db.Column(db.String(50), unique=True, nullable=False)
    from_location = db.Column(db.String(50), nullable=False)
    to_location = db.Column(db.String(50), nullable=False)
    scheduled_departure = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='Scheduled')
    driver_name = db.Column(db.String(100))
    driver_contact = db.Column(db.String(20))
    security_status = db.Column(db.String(20), default='Safe')

class ExpiryAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blood_id = db.Column(db.String(50), nullable=False)
    alert_type = db.Column(db.String(20), nullable=False)
    alert_date = db.Column(db.DateTime, nullable=False)
    days_remaining = db.Column(db.Integer)
    action_taken = db.Column(db.Boolean, default=False)

# Utility Functions
def calculate_expiry_date(product_type, donation_date):
    if isinstance(donation_date, str):
        donation_dt = datetime.strptime(donation_date, '%Y-%m-%d').date()
    else:
        donation_dt = donation_date
    
    if product_type == "Whole Blood":
        expiry_dt = donation_dt + timedelta(days=35)
    elif product_type == "RBC":
        expiry_dt = donation_dt + timedelta(days=42)
    elif product_type == "Platelets":
        expiry_dt = donation_dt + timedelta(days=5)
    elif product_type == "Plasma":
        expiry_dt = donation_dt + timedelta(days=365)
    else:
        expiry_dt = donation_dt + timedelta(days=30)
    
    return expiry_dt

def get_temperature_zone(product_type):
    zones = {
        "Whole Blood": "2-6C",
        "RBC": "2-6C", 
        "Platelets": "20-24C",
        "Plasma": "-18C"
    }
    return zones.get(product_type, "2-6C")

# HTML Templates as strings - FIXED: Proper template syntax and structure
BASE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Myanmar Blood Supply Chain WMS</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body { background-color: #f8f9fa; }
        .card { box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075); border: 1px solid rgba(0, 0, 0, 0.125); }
        .navbar-brand { font-weight: bold; }
        .progress { height: 8px; }
        .table th { border-top: none; font-weight: 600; }
        .badge { font-size: 0.75em; }
        .alert { border: none; border-radius: 0.5rem; }
        .btn { border-radius: 0.5rem; }
        .language-switcher { margin-right: 15px; }
        .stat-card { min-height: 120px; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-danger">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-tint"></i> {{ translate("Myanmar Blood WMS") }}
            </a>
            <div class="navbar-nav">
                <a class="nav-link" href="/">{{ translate("Dashboard") }}</a>
                <a class="nav-link" href="/inventory">{{ translate("Inventory") }}</a>
                <a class="nav-link" href="/locations">{{ translate("Locations") }}</a>
                <a class="nav-link" href="/transportation">{{ translate("Transport") }}</a>
                <a class="nav-link" href="/reports">{{ translate("Reports") }}</a>
                <a class="nav-link" href="/mobile">{{ translate("Mobile") }}</a>
            </div>
            <div class="language-switcher">
                <select id="languageSelect" class="form-select form-select-sm">
                    <option value="en" {% if lang == "en" %}selected{% endif %}>English</option>
                    <option value="my" {% if lang == "my" %}selected{% endif %}>မြန်မာ</option>
                </select>
            </div>
        </div>
    </nav>

    <div class="container mt-4">
        <div id="alert-container"></div>
        {{ content | safe }}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function showAlert(message, type = 'success') {
            const alertDiv = document.createElement('div');
            alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
            alertDiv.innerHTML = `
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.getElementById('alert-container').appendChild(alertDiv);
            
            setTimeout(() => {
                alertDiv.remove();
            }, 5000);
        }
        
        // Check for expired blood on page load
        document.addEventListener('DOMContentLoaded', function() {
            checkExpiredBlood();
        });
        
        function checkExpiredBlood() {
            fetch('/api/expired_blood_count')
                .then(response => response.json())
                .then(data => {
                    if (data.expired_count > 0) {
                        showExpiredBloodAlert(data.expired_count);
                    }
                });
        }
        
        function showExpiredBloodAlert(count) {
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-danger alert-dismissible fade show';
            alertDiv.innerHTML = `
                <div class="d-flex align-items-center">
                    <i class="fas fa-exclamation-triangle fa-2x me-3"></i>
                    <div>
                        <h5 class="mb-1">{{ translate("Alert: Expired Blood Detected") }}</h5>
                        <p class="mb-2">${count} {{ translate("blood units have expired and require attention.") }}</p>
                        <div>
                            <a href="/expired-blood" class="btn btn-sm btn-danger me-2">
                                <i class="fas fa-cog me-1"></i>{{ translate("Manage Expired Blood") }}
                            </a>
                            <a href="/reports" class="btn btn-sm btn-outline-danger">
                                <i class="fas fa-chart-bar me-1"></i>{{ translate("View Reports") }}
                            </a>
                        </div>
                    </div>
                </div>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            document.getElementById('alert-container').prepend(alertDiv);
        }
        
        // Language switcher
        document.getElementById('languageSelect').addEventListener('change', function() {
            const lang = this.value;
            
            fetch('/api/set_language', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({language: lang})
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    window.location.reload();
                }
            })
            .catch(error => {
                console.error('Error setting language:', error);
            });
        });
    </script>
    {{ scripts | safe }}
</body>
</html>
'''

# Routes
@app.route('/')
def dashboard():
    lang = get_current_language()
    
    total_units = BloodInventory.query.filter_by(status='Available').count()
    
    expiring_soon = BloodInventory.query.filter(
        BloodInventory.status == 'Available',
        BloodInventory.expiry_date <= datetime.now().date() + timedelta(days=7)
    ).count()
    
    locations = Location.query.all()
    location_data = []
    for loc in locations:
        usage_percent = round((loc.current_stock / loc.capacity * 100), 1) if loc.capacity and loc.capacity > 0 else 0
        location_data.append({
            'location_name': loc.location_name,
            'current_stock': loc.current_stock,
            'capacity': loc.capacity,
            'usage_percent': usage_percent
        })
    
    recent_alerts = ExpiryAlert.query.filter_by(action_taken=False).order_by(ExpiryAlert.alert_date.desc()).limit(5).all()
    active_transport = Transportation.query.filter(Transportation.status.in_(['Scheduled', 'In Transit'])).count()
    
    content = render_template_string('''
    <div class="row">
        <div class="col-12">
            <h1 class="mb-4">{{ translate("Dashboard Overview") }}</h1>
        </div>
    </div>

    <div class="row mb-4">
        <div class="col-md-3 mb-3">
            <div class="card text-white bg-primary stat-card">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h2 class="mb-0">''' + str(total_units) + '''</h2>
                            <p class="mb-0">{{ translate("Total Blood Units") }}</p>
                        </div>
                        <div class="display-6">
                            <i class="fas fa-tint"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-md-3 mb-3">
            <div class="card text-white bg-warning stat-card">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h2 class="mb-0">''' + str(expiring_soon) + '''</h2>
                            <p class="mb-0">{{ translate("Expiring Soon (7 days)") }}</p>
                        </div>
                        <div class="display-6">
                            <i class="fas fa-exclamation-triangle"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-md-3 mb-3">
            <div class="card text-white bg-info stat-card">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h2 class="mb-0">''' + str(active_transport) + '''</h2>
                            <p class="mb-0">{{ translate("Active Shipments") }}</p>
                        </div>
                        <div class="display-6">
                            <i class="fas fa-truck"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-md-3 mb-3">
            <div class="card text-white bg-success stat-card">
                <div class="card-body">
                    <div class="d-flex justify-content-between align-items-center">
                        <div>
                            <h2 class="mb-0">''' + str(len(locations)) + '''</h2>
                            <p class="mb-0">{{ translate("Storage Locations") }}</p>
                        </div>
                        <div class="display-6">
                            <i class="fas fa-hospital"></i>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div class="row">
        <div class="col-md-6 mb-4">
            <div class="card h-100">
                <div class="card-header bg-white">
                    <h5 class="card-title mb-0">{{ translate("Location Capacity") }}</h5>
                </div>
                <div class="card-body">
    ''' + ''.join([f'''
                    <div class="mb-3">
                        <div class="d-flex justify-content-between mb-1">
                            <span class="small">{loc['location_name']}</span>
                            <span class="small text-muted">{loc['current_stock']}/{loc['capacity']}</span>
                        </div>
                        <div class="progress" style="height: 8px;">
                            <div class="progress-bar {'bg-warning' if loc['usage_percent'] > 80 else 'bg-success'}" 
                                 role="progressbar" style="width: {loc['usage_percent']}%"
                                 aria-valuenow="{loc['usage_percent']}" aria-valuemin="0" aria-valuemax="100">
                            </div>
                        </div>
                        <small class="text-muted">{loc['usage_percent']}% {{ translate("full") }}</small>
                    </div>''' for loc in location_data]) + '''
                </div>
            </div>
        </div>

        <div class="col-md-6 mb-4">
            <div class="card h-100">
                <div class="card-header bg-white">
                    <h5 class="card-title mb-0">{{ translate("Recent Alerts") }}</h5>
                </div>
                <div class="card-body">
    ''' + (''.join([f'''
                    <div class="alert alert-warning alert-dismissible fade show py-2 mb-2">
                        <div class="d-flex align-items-center">
                            <i class="fas fa-exclamation-circle me-2"></i>
                            <small class="flex-grow-1">
                                {{ translate("Blood unit") }} <strong>{alert.blood_id}</strong> 
                                {{ translate("expiring in") }} {alert.days_remaining} {{ translate("days") }}
                            </small>
                        </div>
                        <button type="button" class="btn-close btn-close-sm" data-bs-dismiss="alert"></button>
                    </div>''' for alert in recent_alerts]) if recent_alerts else '''
                    <div class="text-center text-muted py-4">
                        <i class="fas fa-check-circle fa-2x mb-2"></i>
                        <p class="mb-0">{{ translate("No recent alerts") }}</p>
                    </div>''') + '''
                </div>
            </div>

            <div class="card mt-4">
                <div class="card-header bg-white">
                    <h5 class="card-title mb-0">{{ translate("Quick Actions") }}</h5>
                </div>
                <div class="card-body">
                    <div class="d-grid gap-2">
                        <a href="/mobile" class="btn btn-primary">
                            <i class="fas fa-mobile-alt me-2"></i>{{ translate("Mobile Entry") }}
                        </a>
                        <a href="/inventory" class="btn btn-outline-primary">
                            <i class="fas fa-plus me-2"></i>{{ translate("Add Blood Unit") }}
                        </a>
                        <a href="/reports" class="btn btn-outline-info">
                            <i class="fas fa-chart-bar me-2"></i>{{ translate("View Reports") }}
                        </a>
                    </div>
                </div>
            </div>
        </div>
    </div>
    ''', lang=lang, translate=translate_text)
    
    return render_template_string(BASE_TEMPLATE, content=content, scripts='', lang=lang, translate=translate_text)

@app.route('/inventory')
def inventory():
    lang = get_current_language()
    
    blood_type = request.args.get('blood_type', '')
    location = request.args.get('location', '')
    
    query = BloodInventory.query
    
    if blood_type:
        query = query.filter_by(blood_type=blood_type)
    if location:
        query = query.filter_by(current_location=location)
    
    inventory_items = query.order_by(BloodInventory.expiry_date).all()
    locations = Location.query.all()
    
    # Prepare inventory data for template
    inventory_data = []
    for item in inventory_items:
        days_left = (item.expiry_date - datetime.now().date()).days
        
        if days_left <= 0:
            status_text = translate_text("Expired", lang)
            status_class = "bg-dark"
        elif days_left <= 3:
            status_text = f"{days_left} {translate_text('days', lang)}"
            status_class = "bg-danger"
        elif days_left <= 7:
            status_text = f"{days_left} {translate_text('days', lang)}"
            status_class = "bg-warning"
        else:
            status_text = f"{days_left} {translate_text('days', lang)}"
            status_class = "bg-success"
            
        inventory_data.append({
            'blood_id': item.blood_id,
            'blood_type': item.blood_type,
            'product_type': item.product_type,
            'location': item.current_location,
            'expiry_date': item.expiry_date.strftime('%Y-%m-%d'),
            'status_text': status_text,
            'status_class': status_class
        })
    
    inventory_template = '''
    <div class="row">
        <div class="col-12">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h1>{{ translate("Blood Inventory") }}</h1>
                <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addInventoryModal">
                    <i class="fas fa-plus me-2"></i>{{ translate("Add Blood Unit") }}
                </button>
            </div>
        </div>
    </div>

    <div class="card mb-4">
        <div class="card-header">
            <h5 class="card-title mb-0">{{ translate("Filters") }}</h5>
        </div>
        <div class="card-body">
            <form method="GET" class="row g-3">
                <div class="col-md-4">
                    <label class="form-label">{{ translate("Blood Type") }}</label>
                    <select name="blood_type" class="form-select">
                        <option value="">{{ translate("All Types") }}</option>
                        <option value="A+" {% if request.args.get("blood_type") == "A+" %}selected{% endif %}>A+</option>
                        <option value="B+" {% if request.args.get("blood_type") == "B+" %}selected{% endif %}>B+</option>
                        <option value="O+" {% if request.args.get("blood_type") == "O+" %}selected{% endif %}>O+</option>
                        <option value="AB+" {% if request.args.get("blood_type") == "AB+" %}selected{% endif %}>AB+</option>
                    </select>
                </div>
                <div class="col-md-4">
                    <label class="form-label">{{ translate("Location") }}</label>
                    <select name="location" class="form-select">
                        <option value="">{{ translate("All Locations") }}</option>
                        {% for loc in all_locations %}
                        <option value="{{ loc.location_code }}" {% if request.args.get("location") == loc.location_code %}selected{% endif %}>
                            {{ loc.location_name }}
                        </option>
                        {% endfor %}
                    </select>
                </div>
                <div class="col-md-4">
                    <label class="form-label">&nbsp;</label>
                    <div>
                        <button type="submit" class="btn btn-outline-primary">{{ translate("Filter") }}</button>
                        <a href="/inventory" class="btn btn-outline-secondary">{{ translate("Clear") }}</a>
                    </div>
                </div>
            </form>
        </div>
    </div>

    <div class="card">
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>{{ translate("Blood ID") }}</th>
                            <th>{{ translate("Blood Type") }}</th>
                            <th>{{ translate("Product Type") }}</th>
                            <th>{{ translate("Location") }}</th>
                            <th>{{ translate("Expiry Date") }}</th>
                            <th>{{ translate("Status") }}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for item in inventory_data %}
                        <tr>
                            <td>{{ item.blood_id }}</td>
                            <td><span class="badge bg-danger">{{ item.blood_type }}</span></td>
                            <td>{{ item.product_type }}</td>
                            <td>{{ item.location }}</td>
                            <td>{{ item.expiry_date }}</td>
                            <td><span class="badge {{ item.status_class }}">{{ item.status_text }}</span></td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="6" class="text-center text-muted">{{ translate("No blood units found") }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    '''
    
    content = render_template_string(inventory_template, 
                                   inventory_data=inventory_data, 
                                   all_locations=locations,
                                   request=request,
                                   lang=lang, 
                                   translate=translate_text)
    
    return render_template_string(BASE_TEMPLATE, content=content, scripts='', lang=lang, translate=translate_text)

@app.route('/expired-blood')
def expired_blood():
    lang = get_current_language()
    
    expired_blood = BloodInventory.query.filter(
        BloodInventory.expiry_date < datetime.now().date()
    ).all()
    
    # Prepare expired blood data for template
    expired_data = []
    for item in expired_blood:
        days_expired = (datetime.now().date() - item.expiry_date).days
        expired_data.append({
            'blood_id': item.blood_id,
            'blood_type': item.blood_type,
            'product_type': item.product_type,
            'location': item.current_location,
            'donation_date': item.donation_date.strftime('%Y-%m-%d'),
            'expiry_date': item.expiry_date.strftime('%Y-%m-%d'),
            'days_expired': days_expired
        })
    
    expired_template = '''
    <div class="row">
        <div class="col-12">
            <div class="d-flex justify-content-between align-items-center mb-4">
                <h1>{{ translate("Expired Blood Units") }}</h1>
                <span class="badge bg-danger fs-6">{{ expired_count }} {{ translate("expired units") }}</span>
            </div>
        </div>
    </div>

    <div class="card">
        <div class="card-body">
            {% if expired_data %}
            <div class="table-responsive">
                <table class="table table-striped table-hover">
                    <thead class="table-light">
                        <tr>
                            <th>{{ translate("Blood ID") }}</th>
                            <th>{{ translate("Blood Type") }}</th>
                            <th>{{ translate("Product Type") }}</th>
                            <th>{{ translate("Location") }}</th>
                            <th>{{ translate("Donation Date") }}</th>
                            <th>{{ translate("Expiry Date") }}</th>
                            <th>{{ translate("Days Expired") }}</th>
                            <th>{{ translate("Actions") }}</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for item in expired_data %}
                        <tr>
                            <td><strong>{{ item.blood_id }}</strong></td>
                            <td><span class="badge bg-danger">{{ item.blood_type }}</span></td>
                            <td>{{ translate(item.product_type) }}</td>
                            <td>{{ item.location }}</td>
                            <td>{{ item.donation_date }}</td>
                            <td>{{ item.expiry_date }}</td>
                            <td><span class="badge bg-dark">{{ item.days_expired }} {{ translate("days") }}</span></td>
                            <td>
                                <button class="btn btn-sm btn-outline-danger" onclick="markAsDisposed('{{ item.blood_id }}')">
                                    <i class="fas fa-trash me-1"></i>{{ translate("Mark as Disposed") }}
                                </button>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
            {% else %}
            <div class="text-center py-5">
                <i class="fas fa-check-circle fa-3x text-success mb-3"></i>
                <h4 class="text-muted">{{ translate("No expired blood units found") }}</h4>
                <p class="text-muted">{{ translate("All blood units are within their validity period.") }}</p>
                <a href="/inventory" class="btn btn-primary mt-3">
                    <i class="fas fa-arrow-left me-2"></i>{{ translate("Back to Inventory") }}
                </a>
            </div>
            {% endif %}
        </div>
    </div>

    <script>
    function markAsDisposed(bloodId) {
        if (confirm('{{ translate("Are you sure you want to mark this blood unit as disposed?") }}')) {
            fetch('/api/dispose_blood/' + bloodId, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(result => {
                if (result.success) {
                    showAlert('{{ translate("Blood unit marked as disposed") }}', 'success');
                    setTimeout(() => {
                        location.reload();
                    }, 1500);
                } else {
                    showAlert('{{ translate("Error") }}: ' + result.error, 'danger');
                }
            });
        }
    }
    </script>
    '''
    
    content = render_template_string(expired_template, 
                                   expired_data=expired_data,
                                   expired_count=len(expired_data),
                                   lang=lang, 
                                   translate=translate_text)
    
    return render_template_string(BASE_TEMPLATE, content=content, scripts='', lang=lang, translate=translate_text)

@app.route('/reports')
def reports():
    lang = get_current_language()
    total_units = BloodInventory.query.count()
    
    # Fix: Expiring soon should be units expiring in 3 days but not expired
    expiring_soon = BloodInventory.query.filter(
        BloodInventory.expiry_date <= datetime.now().date() + timedelta(days=3),
        BloodInventory.expiry_date >= datetime.now().date()
    ).count()
    
    expired_count = BloodInventory.query.filter(
        BloodInventory.expiry_date < datetime.now().date()
    ).count()
    
    # Get blood type distribution
    blood_types = ['A+', 'B+', 'O+', 'AB+']
    blood_type_data = []
    for blood_type in blood_types:
        count = BloodInventory.query.filter_by(blood_type=blood_type).count()
        percentage = (count / total_units * 100) if total_units > 0 else 0
        blood_type_data.append({
            'type': blood_type,
            'count': count,
            'percentage': percentage
        })
    
    locations = Location.query.all()
    
    content = render_template_string('''
    <div class="row">
        <div class="col-12">
            <h1 class="mb-4">{{ translate("Reports & Analytics") }}</h1>
        </div>
    </div>
    
    <div class="row mb-4">
        <div class="col-md-3 mb-3">
            <div class="card text-white bg-primary stat-card">
                <div class="card-body text-center">
                    <h2 class="display-4 mb-2">''' + str(total_units) + '''</h2>
                    <p class="mb-0">{{ translate("Total Blood Units") }}</p>
                </div>
            </div>
        </div>
        <div class="col-md-3 mb-3">
            <div class="card text-white bg-warning stat-card">
                <div class="card-body text-center">
                    <h2 class="display-4 mb-2">''' + str(expiring_soon) + '''</h2>
                    <p class="mb-0">{{ translate("Expiring in 3 Days") }}</p>
                </div>
            </div>
        </div>
        <div class="col-md-3 mb-3">
            <div class="card text-white bg-danger stat-card">
                <div class="card-body text-center">
                    <h2 class="display-4 mb-2">''' + str(expired_count) + '''</h2>
                    <p class="mb-0">{{ translate("Expired Units") }}</p>
                </div>
            </div>
        </div>
        <div class="col-md-3 mb-3">
            <div class="card text-white bg-info stat-card">
                <div class="card-body text-center">
                    <h2 class="display-4 mb-2">''' + f'{(expired_count/total_units*100) if total_units > 0 else 0:.1f}%' + '''</h2>
                    <p class="mb-0">{{ translate("Wastage Rate") }}</p>
                </div>
            </div>
        </div>
    </div>
    
    <div class="row">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header bg-white">
                    <h5 class="card-title mb-0">{{ translate("Blood Type Distribution") }}</h5>
                </div>
                <div class="card-body">
                    <div class="table-responsive">
                        <table class="table table-striped">
                            <thead>
                                <tr>
                                    <th>{{ translate("Blood Type") }}</th>
                                    <th>{{ translate("Count") }}</th>
                                    <th>{{ translate("Percentage") }}</th>
                                </tr>
                            </thead>
                            <tbody>
    ''' + ''.join([f'''
                                <tr>
                                    <td><span class="badge bg-danger">{data['type']}</span></td>
                                    <td>{data['count']}</td>
                                    <td>{data['percentage']:.1f}%</td>
                                </tr>''' for data in blood_type_data]) + '''
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="col-md-4">
            <div class="card">
                <div class="card-header bg-white">
                    <h5 class="card-title mb-0">{{ translate("Quick Actions") }}</h5>
                </div>
                <div class="card-body">
                    <div class="d-grid gap-2">
    ''' + (f'''
                        <a href="/expired-blood" class="btn btn-danger">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            {{ translate("Manage Expired Blood") }} ({expired_count})
                        </a>
    ''' if expired_count > 0 else '') + '''
                        <a href="/inventory" class="btn btn-outline-primary">
                            <i class="fas fa-list me-2"></i>
                            {{ translate("View All Inventory") }}
                        </a>
                        <a href="/mobile" class="btn btn-outline-success">
                            <i class="fas fa-mobile-alt me-2"></i>
                            {{ translate("Mobile Entry") }}
                        </a>
                    </div>
                </div>
            </div>
            
            <div class="card mt-4">
                <div class="card-header bg-white">
                    <h5 class="card-title mb-0">{{ translate("Location Summary") }}</h5>
                </div>
                <div class="card-body">
    ''' + ''.join([f'''
                    <div class="mb-3">
                        <div class="d-flex justify-content-between">
                            <small><strong>{loc.location_name}</strong></small>
                            <small>{loc.current_stock}/{loc.capacity}</small>
                        </div>
                        <div class="progress" style="height: 6px;">
                            <div class="progress-bar {'bg-warning' if (loc.current_stock/loc.capacity*100) > 80 else 'bg-success'}" 
                                 style="width: {(loc.current_stock/loc.capacity*100) if loc.capacity else 0:.1f}%"></div>
                        </div>
                    </div>''' for loc in locations]) + '''
                </div>
            </div>
        </div>
    </div>
    ''', lang=lang, translate=translate_text)
    
    return render_template_string(BASE_TEMPLATE, content=content, scripts='', lang=lang, translate=translate_text)

# FIXED: Mobile Entry route with complete functionality
@app.route('/mobile')
def mobile_interface():
    lang = get_current_language()
    locations = Location.query.all()
    
    content = render_template_string('''
    <div class="row">
        <div class="col-12">
            <h1 class="mb-4">{{ translate("Mobile Quick Entry") }}</h1>
        </div>
    </div>
    
    <div class="row justify-content-center">
        <div class="col-md-8">
            <div class="card">
                <div class="card-header bg-white">
                    <h5 class="card-title mb-0">
                        <i class="fas fa-mobile-alt me-2"></i>{{ translate("Quick Blood Unit Entry") }}
                    </h5>
                </div>
                <div class="card-body">
                    <form id="mobileEntryForm">
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">{{ translate("Blood Type") }} *</label>
                                <select name="blood_type" class="form-select" required>
                                    <option value="">{{ translate("Select Blood Type") }}</option>
                                    <option value="A+">A+</option>
                                    <option value="B+">B+</option>
                                    <option value="O+">O+</option>
                                    <option value="AB+">AB+</option>
                                </select>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">{{ translate("Product Type") }} *</label>
                                <select name="product_type" class="form-select" required>
                                    <option value="">{{ translate("Select Product Type") }}</option>
                                    <option value="Whole Blood">{{ translate("Whole Blood") }}</option>
                                    <option value="RBC">{{ translate("RBC") }}</option>
                                    <option value="Platelets">{{ translate("Platelets") }}</option>
                                    <option value="Plasma">{{ translate("Plasma") }}</option>
                                </select>
                            </div>
                        </div>
                        
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">{{ translate("Donation Date") }} *</label>
                                <input type="date" name="donation_date" class="form-control" required 
                                       value="''' + datetime.now().date().strftime('%Y-%m-%d') + '''">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">{{ translate("Current Location") }} *</label>
                                <select name="current_location" class="form-select" required>
                                    <option value="">{{ translate("Select Location") }}</option>
    ''' + ''.join([f'''
                                    <option value="{loc.location_code}">{loc.location_name}</option>''' for loc in locations]) + '''
                                </select>
                            </div>
                        </div>
                        
                        <div class="row">
                            <div class="col-12">
                                <div class="d-grid">
                                    <button type="submit" class="btn btn-primary btn-lg">
                                        <i class="fas fa-plus-circle me-2"></i>{{ translate("Add Blood Unit") }}
                                    </button>
                                </div>
                            </div>
                        </div>
                    </form>
                </div>
            </div>
            
            <div class="card mt-4">
                <div class="card-header bg-white">
                    <h5 class="card-title mb-0">
                        <i class="fas fa-history me-2"></i>{{ translate("Recent Entries") }}
                    </h5>
                </div>
                <div class="card-body">
                    <div id="recentEntries">
                        <div class="text-center text-muted py-4">
                            <i class="fas fa-inbox fa-2x mb-2"></i>
                            <p>{{ translate("No recent entries") }}</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
    document.getElementById('mobileEntryForm').addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(this);
        const data = Object.fromEntries(formData);
        
        // Show loading state
        const submitBtn = this.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>{{ translate("Adding...") }}';
        submitBtn.disabled = true;
        
        fetch('/api/quick_entry', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                showAlert('{{ translate("Blood unit added successfully") }}: ' + result.blood_id, 'success');
                this.reset();
                // Reset donation date to today
                this.querySelector('input[name="donation_date"]').value = new Date().toISOString().split('T')[0];
                addRecentEntry(result.blood_id, data.blood_type, data.product_type);
            } else {
                showAlert('{{ translate("Error") }}: ' + result.error, 'danger');
            }
        })
        .catch(error => {
            showAlert('{{ translate("Error") }}: ' + error, 'danger');
        })
        .finally(() => {
            submitBtn.innerHTML = originalText;
            submitBtn.disabled = false;
        });
    });
    
    function addRecentEntry(bloodId, bloodType, productType) {
        const recentEntries = document.getElementById('recentEntries');
        const noEntries = recentEntries.querySelector('.text-muted');
        
        if (noEntries) {
            recentEntries.innerHTML = '';
        }
        
        const entryDiv = document.createElement('div');
        entryDiv.className = 'alert alert-success alert-dismissible fade show';
        entryDiv.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <strong>${bloodId}</strong><br>
                    <small class="text-muted">${bloodType} • ${productType}</small>
                </div>
                <small class="text-muted">{{ translate("Just now") }}</small>
            </div>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        recentEntries.prepend(entryDiv);
        
        // Limit to 5 recent entries
        const alerts = recentEntries.querySelectorAll('.alert');
        if (alerts.length > 5) {
            alerts[alerts.length - 1].remove();
        }
    }
    </script>
    ''', lang=lang, translate=translate_text)
    
    return render_template_string(BASE_TEMPLATE, content=content, scripts='', lang=lang, translate=translate_text)

# Other routes
@app.route('/locations')
def locations():
    lang = get_current_language()
    locations = Location.query.all()
    
    # Pre-translate common terms
    code_text = translate_text("Code", lang)
    stock_text = translate_text("Stock", lang)
    units_text = translate_text("units", lang)
    contact_text = translate_text("Contact", lang)
    phone_text = translate_text("Phone", lang)
    temp_text = translate_text("Temperature Capability", lang)
    storage_text = translate_text("Storage Locations", lang)
    
    locations_content = f'''
    <div class="row">
        <div class="col-12">
            <h1 class="mb-4">{storage_text}</h1>
        </div>
    </div>
    
    <div class="row">
    '''
    
    for loc in locations:
        usage_percent = (loc.current_stock / loc.capacity * 100) if loc.capacity and loc.capacity > 0 else 0
        progress_bar_class = 'bg-warning' if usage_percent > 80 else 'bg-success'
        
        locations_content += f'''
        <div class="col-md-4 mb-4">
            <div class="card">
                <div class="card-body">
                    <h5 class="card-title">{loc.location_name}</h5>
                    <p>
                        <strong>{code_text}:</strong> {loc.location_code}<br>
                        <strong>{stock_text}:</strong> {loc.current_stock}/{loc.capacity} {units_text}<br>
                        <strong>{contact_text}:</strong> {loc.contact_person}<br>
                        <strong>{phone_text}:</strong> {loc.phone_number}
                    </p>
                    <div class="progress">
                        <div class="progress-bar {progress_bar_class}" 
                             style="width: {usage_percent:.1f}%">
                            {usage_percent:.1f}%
                        </div>
                    </div>
                    <small class="text-muted mt-2 d-block">
                        <strong>{temp_text}:</strong> {loc.temperature_capability}
                    </small>
                </div>
            </div>
        </div>
        '''
    
    locations_content += '''
    </div>
    '''
    
    return render_template_string(BASE_TEMPLATE, content=locations_content, scripts='', lang=lang, translate=translate_text)
@app.route('/transportation')
def transportation():
    lang = get_current_language()
    shipments = Transportation.query.all()
    transport_html = '<h1>{{ translate("Transportation") }}</h1><div class="card"><div class="card-body"><table class="table"><thead><tr><th>{{ translate("Shipment ID") }}</th><th>{{ translate("From") }}</th><th>{{ translate("To") }}</th><th>{{ translate("Status") }}</th></tr></thead><tbody>' + ''.join([f'<tr><td>{ship.shipment_id}</td><td>{ship.from_location}</td><td>{ship.to_location}</td><td><span class="badge bg-primary">{ship.status}</span></td></tr>' for ship in shipments]) + '</tbody></table></div></div>'
    content = render_template_string(transport_html, lang=lang, translate=translate_text)
    return render_template_string(BASE_TEMPLATE, content=content, scripts='', lang=lang, translate=translate_text)

# API Routes
@app.route('/api/set_language', methods=['POST'])
def set_language():
    """API endpoint to set language preference"""
    data = request.get_json()
    language = data.get('language', 'en')
    
    if language in ['en', 'my']:
        session['language'] = language
        session.permanent = True
        return jsonify({'success': True, 'language': language})
    
    return jsonify({'success': False, 'error': 'Invalid language'})

@app.route('/api/expired_blood_count')
def expired_blood_count():
    expired_count = BloodInventory.query.filter(
        BloodInventory.expiry_date < datetime.now().date()
    ).count()
    return jsonify({'expired_count': expired_count})

@app.route('/api/dispose_blood/<blood_id>', methods=['POST'])
def dispose_blood(blood_id):
    try:
        blood_unit = BloodInventory.query.filter_by(blood_id=blood_id).first()
        if blood_unit:
            # Update location stock
            location = Location.query.filter_by(location_code=blood_unit.current_location).first()
            if location and location.current_stock > 0:
                location.current_stock -= 1
            
            # Remove the blood unit from inventory
            db.session.delete(blood_unit)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Blood unit disposed successfully'})
        else:
            return jsonify({'success': False, 'error': 'Blood unit not found'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# FIXED: Add missing API endpoint for mobile entry
@app.route('/api/quick_entry', methods=['POST'])
def quick_entry():
    data = request.get_json()
    
    try:
        blood_id = f"{data['blood_type']}_{data['product_type']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        expiry_date = calculate_expiry_date(data['product_type'], data['donation_date'])
        
        new_item = BloodInventory(
            blood_id=blood_id,
            blood_type=data['blood_type'],
            product_type=data['product_type'],
            donation_date=datetime.strptime(data['donation_date'], '%Y-%m-%d').date(),
            expiry_date=expiry_date,
            current_location=data['current_location'],
            temperature_zone=get_temperature_zone(data['product_type'])
        )
        
        db.session.add(new_item)
        
        # Update location stock
        location = Location.query.filter_by(location_code=data['current_location']).first()
        if location:
            location.current_stock += 1
        
        db.session.commit()
        
        # Check if expiring soon and create alert
        days_remaining = (expiry_date - datetime.now().date()).days
        if days_remaining <= 7:
            alert = ExpiryAlert(
                blood_id=blood_id,
                alert_type='Expiring',
                alert_date=datetime.now(),
                days_remaining=days_remaining
            )
            db.session.add(alert)
            db.session.commit()
        
        return jsonify({'success': True, 'blood_id': blood_id})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

# FIXED: Add missing API endpoint for inventory
@app.route('/api/inventory', methods=['POST'])
def add_inventory():
    data = request.get_json()
    
    try:
        blood_id = f"{data['blood_type']}_{data['product_type']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        expiry_date = calculate_expiry_date(data['product_type'], data['donation_date'])
        
        new_item = BloodInventory(
            blood_id=blood_id,
            blood_type=data['blood_type'],
            product_type=data['product_type'],
            donation_date=datetime.strptime(data['donation_date'], '%Y-%m-%d').date(),
            expiry_date=expiry_date,
            current_location=data['current_location'],
            temperature_zone=get_temperature_zone(data['product_type'])
        )
        
        db.session.add(new_item)
        
        # Update location stock
        location = Location.query.filter_by(location_code=data['current_location']).first()
        if location:
            location.current_stock += 1
        
        db.session.commit()
        
        # Check if expiring soon and create alert
        days_remaining = (expiry_date - datetime.now().date()).days
        if days_remaining <= 7:
            alert = ExpiryAlert(
                blood_id=blood_id,
                alert_type='Expiring',
                alert_date=datetime.now(),
                days_remaining=days_remaining
            )
            db.session.add(alert)
            db.session.commit()
        
        return jsonify({'success': True, 'blood_id': blood_id})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

def init_db():
    with app.app_context():
        db.create_all()
        
        if Location.query.count() == 0:
            print("Creating sample data...")
            
            locations = [
                Location(
                    location_code='YGN_MAIN',
                    location_name='Yangon Main Blood Bank',
                    location_type='Storage',
                    capacity=1000,
                    current_stock=0,
                    temperature_capability='2-6C, 20-24C, -18C',
                    contact_person='Dr. Aung Kyaw',
                    phone_number='+95-1-123456'
                ),
                Location(
                    location_code='MDY_REGIONAL',
                    location_name='Mandalay Regional Center',
                    location_type='Storage',
                    capacity=500,
                    current_stock=0,
                    temperature_capability='2-6C',
                    contact_person='Dr. Mya Mya',
                    phone_number='+95-2-234567'
                )
            ]
            
            for location in locations:
                db.session.add(location)
            
            db.session.commit()
            
            # Add sample blood units including some expired ones
            for i in range(15):
                blood_type = ['A+', 'B+', 'O+', 'AB+'][i % 4]
                product = ['Whole Blood', 'RBC', 'Platelets'][i % 3]
                location_code = ['YGN_MAIN', 'MDY_REGIONAL'][i % 2]
                
                # Create some expired samples
                if i < 3:  # First 3 units are expired
                    donation_date = datetime.now().date() - timedelta(days=40)
                else:
                    donation_date = datetime.now().date() - timedelta(days=i % 20)
                
                expiry_date = calculate_expiry_date(product, donation_date)
                
                blood_unit = BloodInventory(
                    blood_id=f"{blood_type}_{product}_{i:03d}",
                    blood_type=blood_type,
                    product_type=product,
                    donation_date=donation_date,
                    expiry_date=expiry_date,
                    current_location=location_code,
                    temperature_zone=get_temperature_zone(product)
                )
                db.session.add(blood_unit)
                
                location = Location.query.filter_by(location_code=location_code).first()
                if location:
                    location.current_stock += 1
            
            db.session.commit()
            print("Sample data added successfully!")
        else:
            print("Database already contains data.")

if __name__ == '__main__':
    print("Starting Myanmar Blood Supply Chain Management System...")
    init_db()
    print("System ready! Access at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)