# This is the main server file for SwiftCart.
# It handles all the backend logic: user accounts, products, orders, and emails.
# We use Flask (a lightweight Python web framework) and SQLite (a simple file-based database).

from dotenv import load_dotenv
load_dotenv()
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3, hashlib, os, json, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import random
import socket
from datetime import datetime, timedelta

# Create the Flask app and tell it where to find HTML files and static assets
app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)  # Allow the frontend (running on the same machine) to talk to this server

# The database lives in the same folder as this file
DB_PATH = os.path.join(os.path.dirname(__file__), 'swiftcart.db')

otp_store = {}
# Format:
# {
#   "email@example.com": {
#       "otp": "123456",
#       "expires": datetime_object
#   }
# }

# DATABASE SETUP
def get_db():
    # Open a connection to the database and make rows behave like dictionaries
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    # This runs once when the server starts.
    # It creates the tables if they don't exist, then seeds demo products.

    conn = get_db()
    c = conn.cursor()

    # --- Users table: stores everyone who signs up ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            email         TEXT UNIQUE NOT NULL,
            phone         TEXT,
            address       TEXT,
            password_hash TEXT NOT NULL,
            created_at    TEXT DEFAULT (datetime('now'))
        )
    ''')

    # --- Products table: the store catalog ---
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT NOT NULL,
            description    TEXT,
            price          REAL NOT NULL,
            original_price REAL,
            category       TEXT,
            emoji          TEXT,
            rating         REAL DEFAULT 4.5,
            review_count   INTEGER DEFAULT 0,
            badge          TEXT,
            stock          INTEGER DEFAULT 100
        )
    ''')

    # --- Orders table: every purchase made on the site ---
    # Items are saved as JSON text because one order can have many products
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            items      TEXT NOT NULL,
            total      REAL NOT NULL,
            status     TEXT DEFAULT 'Placed',
            address    TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # Only add demo products if the table is empty (so we don't duplicate on restart)
    c.execute("SELECT COUNT(*) FROM products")
    if c.fetchone()[0] == 0:
        seed_products(c)

    conn.commit()
    conn.close()


def seed_products(c):
    # 30 realistic demo products across 8 categories.
    # Each row: (name, description, price, original_price, category, emoji, rating, reviews, badge, stock)

    products = [

        # ── ELECTRONICS ────────────────────────────────────────────────────────
        (
            "Sony WH-1000XM5 Headphones",
            "Industry-leading noise cancellation, 30-hour battery life, multipoint Bluetooth, connects to two devices at once.",
            24999, 32999, "Electronics", "🎧", 4.8, 18420, "Best Seller", 60
        ),
        (
            "Apple iPhone 15 Pro 256GB",
            "A17 Pro chip, titanium frame, 48MP triple camera system, USB-C fast charging, Action Button.",
            134900, 149900, "Electronics", "📱", 4.9, 42100, "Top Rated", 35
        ),
        (
            "Samsung 65\" 4K Neo QLED TV",
            "Quantum Matrix Technology, Dolby Atmos sound, 120Hz refresh, Gaming Hub built-in, slim bezel.",
            89999, 129999, "Electronics", "📺", 4.7, 6830, "Deal of the Day", 18
        ),
        (
            "Apple MacBook Air M3 13\"",
            "M3 chip with 18-hour battery, 8GB RAM, 256GB SSD, Liquid Retina display, fanless silent design.",
            114900, 124900, "Electronics", "💻", 4.9, 9210, "Top Rated", 25
        ),
        (
            "boAt Airdopes 141 TWS Earbuds",
            "42-hour total playtime, BEAST mode for low-latency gaming, ENx noise cancellation, IPX4 water resistant.",
            1299, 3490, "Electronics", "🎵", 4.3, 98450, "🔥 Hot Deal", 300
        ),
        (
            "Kindle Paperwhite 11th Gen",
            "300 ppi glare-free display, 10-week battery, waterproof (IPX8), 8GB storage, adjustable warm light.",
            13999, 16999, "Electronics", "📖", 4.8, 54200, "Amazon's Choice", 70
        ),
        (
            "GoPro HERO12 Black",
            "5.3K60 video, HyperSmooth 6.0 stabilization, 27MP photos, waterproof to 10m without a case.",
            34999, 45000, "Electronics", "📷", 4.7, 7640, "Trending", 40
        ),

        # ── FASHION ────────────────────────────────────────────────────────────
        (
            "Nike Air Max 270 Sneakers",
            "Max Air heel unit for all-day cushioning, breathable mesh upper, durable rubber outsole. Unisex sizing.",
            7995, 12995, "Fashion", "👟", 4.6, 23100, None, 90
        ),
        (
            "Levi's 511 Slim Fit Jeans",
            "Flex stretch denim, classic 5-pocket styling, slim through the thigh and leg opening. True to size.",
            3499, 5499, "Fashion", "👖", 4.4, 61800, None, 150
        ),
        (
            "Allen Solly Formal Shirt",
            "100% cotton, wrinkle-resistant finish, slim fit, machine washable. Available in 6 colours.",
            1299, 2499, "Fashion", "👔", 4.3, 14300, "Office Pick", 200
        ),
        (
            "Peter England Leather Watch",
            "Genuine leather strap, mineral glass, 30m water resistant, Japanese quartz movement.",
            2499, 4999, "Fashion", "⌚", 4.5, 8920, None, 80
        ),
        (
            "Ray-Ban Wayfarer Sunglasses",
            "Classic acetate frame, polarised G-15 lenses, 100% UV protection, unisex design.",
            8490, 11000, "Fashion", "🕶️", 4.7, 19200, "Iconic Pick", 55
        ),

        # ── HOME & KITCHEN ──────────────────────────────────────────────────────
        (
            "Prestige Iris 750W Mixer Grinder",
            "3 stainless steel jars (1.5L, 1L, 0.4L), 3-speed control with pulse, overload protection, 2-year warranty.",
            2299, 3999, "Home & Kitchen", "🍽️", 4.5, 32100, None, 85
        ),
        (
            "Instant Pot Duo 7-in-1 (6Qt)",
            "Pressure cooker, slow cooker, rice cooker, steamer, sauté pan, yoghurt maker, warmer, all in one pot.",
            7999, 12000, "Home & Kitchen", "🥘", 4.8, 28400, "Chef's Choice", 45
        ),
        (
            "Philips Air Fryer HD9200",
            "4.1L capacity, Rapid Air technology, up to 90% less fat, dishwasher-safe basket, 7 preset programmes.",
            6499, 9999, "Home & Kitchen", "🍟", 4.6, 41300, "Trending", 60
        ),
        (
            "Godrej 236L 3-Star Refrigerator",
            "Frost-free, inverter compressor saves energy, toughened glass shelves, vegetable crisper, 10-year warranty.",
            24999, 32000, "Home & Kitchen", "🧊", 4.5, 5640, None, 20
        ),

        # ── BEAUTY & HEALTH ─────────────────────────────────────────────────────
        (
            "Himalaya Moisturizing Cream 200ml",
            "Light daily moisturiser with aloe vera and winter cherry, non-greasy, suitable for all skin types.",
            199, 299, "Beauty & Health", "🧴", 4.3, 128000, None, 600
        ),
        (
            "Mamaearth Vitamin C Face Serum",
            "2% Vitamin C + 1% Niacinamide, fades dark spots in 4 weeks, dermatologically tested, 30ml.",
            599, 999, "Beauty & Health", "✨", 4.5, 67200, "Glow Up", 250
        ),
        (
            "Philips BT3231 Beard Trimmer",
            "Self-sharpening steel blades, 20 length settings (0.5–10mm), 60-min run time, fully washable.",
            1499, 2499, "Beauty & Health", "🪒", 4.6, 89400, "Men's Pick", 120
        ),
        (
            "Omron HEM-7120 Blood Pressure Monitor",
            "Clinically validated, upper arm cuff, stores 60 readings, Intellisense technology for accurate results.",
            1999, 2999, "Beauty & Health", "🩺", 4.7, 43800, None, 90
        ),

        # ── SPORTS & FITNESS ────────────────────────────────────────────────────
        (
            "Boldfit Yoga Mat 6mm Anti-Slip",
            "Eco-friendly TPE material, alignment guide lines, moisture-resistant, includes carry strap and bag.",
            899, 1999, "Sports", "🧘", 4.5, 56700, None, 180
        ),
        (
            "Decathlon 20kg Adjustable Dumbbell Set",
            "Cast iron plates with rubber coating, chrome handles, spin-lock collars, suitable for home gyms.",
            3499, 5000, "Sports", "🏋️", 4.7, 21300, "Home Gym Hero", 40
        ),
        (
            "Nivia Storm Football (Size 5)",
            "FIFA quality pro, 32-panel hand-stitched, butyl bladder for air retention, all-surface play.",
            799, 1299, "Sports", "⚽", 4.4, 34500, None, 200
        ),
        (
            "Cosco Jump Rope Speed Skipping",
            "Ball-bearing handles for smooth rotation, PVC rope, foam grip, adjustable length.",
            399, 699, "Sports", "🪢", 4.3, 28900, None, 350
        ),

        # ── BOOKS ───────────────────────────────────────────────────────────────
        (
            "Atomic Habits, James Clear",
            "The #1 bestselling guide on building good habits and breaking bad ones. Over 10 million copies sold.",
            399, 799, "Books", "📚", 4.9, 210000, "Must Read", 500
        ),
        (
            "Rich Dad Poor Dad, Robert Kiyosaki",
            "The classic personal finance book that changed how the world thinks about money. 30+ million copies.",
            299, 599, "Books", "💰", 4.7, 185000, "Bestseller", 500
        ),
        (
            "The Psychology of Money, Morgan Housel",
            "19 short stories on how people think about money, and how to think about it better.",
            349, 699, "Books", "🧠", 4.8, 94300, "Editor's Pick", 400
        ),

        # ── TOYS & KIDS ─────────────────────────────────────────────────────────
        (
            "LEGO Classic Creative Bricks (484 pcs)",
            "484 bricks in 33 colours, open-ended building for ages 4+, includes idea booklet.",
            2499, 3999, "Toys & Kids", "🧱", 4.8, 37200, "Kids' Favourite", 110
        ),
        (
            "Funskool Monopoly Classic Board Game",
            "The original property trading game, 2–8 players, ages 8+, includes all classic tokens.",
            699, 1299, "Toys & Kids", "🎲", 4.6, 62400, None, 150
        ),
        (
            "Hot Wheels 20-Car Gift Pack",
            "20 die-cast cars in 1:64 scale, random assortment of models, great for collectors and kids.",
            1299, 1999, "Toys & Kids", "🚗", 4.7, 48100, "Gift Ready", 200
        ),
    ]

    c.executemany('''
        INSERT INTO products
            (name, description, price, original_price, category, emoji, rating, review_count, badge, stock)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', products)

# PASSWORD HASHING
def hash_password(password):
    # We never store the actual password, only this scrambled version of it.
    # SHA-256 is a one-way function: you can't reverse it back to the original.
    return hashlib.sha256(password.encode()).hexdigest()

def send_otp_email(email, otp):
    SMTP_HOST  = "smtp.gmail.com"
    SMTP_PORT  = 587
    SMTP_USER  = os.getenv("EMAIL_USER")
    SMTP_PASS  = os.getenv("EMAIL_PASS")

    msg = MIMEMultipart()
    msg['Subject'] = "🔐 SwiftCart OTP Verification"
    msg['From'] = SMTP_USER
    msg['To'] = email

    html = f"""
    <h2>SwiftCart Email Verification</h2>
    <p>Your OTP is:</p>
    <h1>{otp}</h1>
    <p>This OTP will expire in 5 minutes.</p>
    """

    msg.attach(MIMEText(html, 'html'))

    try:
        # 🔥 ADD TIMEOUT HERE
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, email, msg.as_string())

    except (socket.timeout, Exception) as e:
        print("SMTP FAILED:", e)
        raise Exception("Email service not available")

# USER ACCOUNT ROUTES

@app.route('/api/send-otp', methods=['POST'])
def send_otp():
    data = request.json
    email = data.get('email')

    # Check that an email was actually provided before doing anything else
    if not email:
        return jsonify({'error': 'Email is required'}), 400

    # Check if this email is already registered — no point sending an OTP if it is
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE email=?', (email,)).fetchone()
    conn.close()

    if user:
        return jsonify({'error': 'This email is already registered. Please log in instead.'}), 400

    # Prevent spam (if OTP already active)
    existing = otp_store.get(email)

    if existing and datetime.now() < existing['expires']:
        return jsonify({'error': 'OTP already sent. Please wait'}), 429

    otp = str(random.randint(100000, 999999))

    otp_store[email] = {
        "otp": otp,
        "expires": datetime.now() + timedelta(minutes=5)
    }

    try:
        send_otp_email(email, otp)
        return jsonify({'success': True})
    except Exception as e:
        print("OTP error:", e)
        return jsonify({'error': 'Failed to send OTP'}), 500

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json

    # 1. Validate required fields FIRST
    for field in ['name', 'email', 'password']:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    # 2. Check OTP exists
    otp = data.get('otp')
    if not otp:
        return jsonify({'error': 'OTP is required'}), 400

    record = otp_store.get(data.get('email'))

    if not record:
        return jsonify({'error': 'Please request OTP first'}), 400

    if record['otp'] != otp:
        return jsonify({'error': 'Invalid OTP'}), 400

    if datetime.now() > record['expires']:
        return jsonify({'error': 'OTP expired'}), 400

    # 3. OTP verified → remove it
    otp_store.pop(data.get('email'))

    conn = get_db()
    try:
        conn.execute('''
            INSERT INTO users (name, email, phone, address, password_hash)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data['name'],
            data['email'],
            data.get('phone', ''),
            data.get('address', ''),
            hash_password(data['password'])
        ))
        conn.commit()

        # Fetch the newly created user to return their info to the frontend
        user = conn.execute('SELECT * FROM users WHERE email = ?', (data['email'],)).fetchone()
        return jsonify({'success': True, 'user': {
            'id': user['id'], 'name': user['name'],
            'email': user['email'], 'phone': user['phone'], 'address': user['address']
        }})

    except sqlite3.IntegrityError:
        # This happens if someone tries to register with an email already in the database
        return jsonify({'error': 'This email is already registered. Please log in.'}), 409
    finally:
        conn.close()


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json

    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password are required'}), 400

    conn = get_db()
    # Look for a user whose email AND hashed password both match
    user = conn.execute(
        'SELECT * FROM users WHERE email = ? AND password_hash = ?',
        (data['email'], hash_password(data['password']))
    ).fetchone()
    conn.close()

    if not user:
        return jsonify({'error': 'Incorrect email or password'}), 401

    return jsonify({'success': True, 'user': {
        'id': user['id'], 'name': user['name'],
        'email': user['email'], 'phone': user['phone'], 'address': user['address']
    }})


@app.route('/api/profile', methods=['PUT'])
def update_profile():
    data = request.json

    if not data.get('user_id'):
        return jsonify({'error': 'You must be logged in to update your profile'}), 401

    conn = get_db()
    conn.execute(
        'UPDATE users SET name=?, phone=?, address=? WHERE id=?',
        (data.get('name'), data.get('phone'), data.get('address'), data['user_id'])
    )
    conn.commit()

    user = conn.execute('SELECT * FROM users WHERE id=?', (data['user_id'],)).fetchone()
    conn.close()

    return jsonify({'success': True, 'user': {
        'id': user['id'], 'name': user['name'],
        'email': user['email'], 'phone': user['phone'], 'address': user['address']
    }})

# PRODUCT ROUTES
@app.route('/api/products', methods=['GET'])
def get_products():
    # The frontend can pass ?category=Electronics or ?search=phone to filter results
    category = request.args.get('category', '')
    search   = request.args.get('search', '')

    conn  = get_db()
    query = 'SELECT * FROM products WHERE 1=1'
    params = []

    if category:
        query += ' AND category = ?'
        params.append(category)

    if search:
        query += ' AND (name LIKE ? OR description LIKE ?)'
        params.extend([f'%{search}%', f'%{search}%'])

    products = conn.execute(query, params).fetchall()
    conn.close()

    return jsonify([dict(p) for p in products])


@app.route('/api/categories', methods=['GET'])
def get_categories():
    conn = get_db()
    rows = conn.execute('SELECT DISTINCT category FROM products ORDER BY category').fetchall()
    conn.close()
    return jsonify([r['category'] for r in rows])

# ORDER ROUTES
@app.route('/api/orders', methods=['POST'])
def place_order():
    data    = request.json
    user_id = data.get('user_id')
    items   = data.get('items', [])
    total   = data.get('total', 0)
    address = data.get('address', '')

    if not user_id or not items:
        return jsonify({'error': 'Order data is incomplete'}), 400

    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id=?', (user_id,)).fetchone()
    if not user:
        conn.close()
        return jsonify({'error': 'User account not found'}), 404

    # Save the order, items are stored as a JSON string
    cursor = conn.execute('''
        INSERT INTO orders (user_id, items, total, address)
        VALUES (?, ?, ?, ?)
    ''', (user_id, json.dumps(items), total, address))

    order_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Try to send a confirmation email, don't crash if email isn't configured
    try:
        send_order_email(dict(user), items, total, order_id, address)
        email_sent = True
    except Exception as e:
        print(f"Email not sent: {e}")
        email_sent = False

    return jsonify({'success': True, 'order_id': order_id, 'email_sent': email_sent})


@app.route('/api/orders/<int:user_id>', methods=['GET'])
def get_orders(user_id):
    conn   = get_db()
    orders = conn.execute(
        'SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC', (user_id,)
    ).fetchall()
    conn.close()

    result = []
    for o in orders:
        order = dict(o)
        order['items'] = json.loads(order['items'])  # Convert JSON string back to a list
        result.append(order)

    return jsonify(result)

# EMAIL, ORDER CONFIRMATION
def send_order_email(user, items, total, order_id, address):
    # ── SET THESE TO YOUR OWN GMAIL CREDENTIALS ──────────────────────────────
    SMTP_HOST  = "smtp.gmail.com"
    SMTP_PORT  = 587
    SMTP_USER  = os.getenv("EMAIL_USER")
    SMTP_PASS  = os.getenv("EMAIL_PASS")
    #   To get an App Password: Google Account → Security → 2-Step Verification → App passwords
    # ─────────────────────────────────────────────────────────────────────────

    # Build one table row per item in the order
    items_rows = "".join([
        f"""<tr>
              <td style='padding:10px 14px;border-bottom:1px solid #f0f0f0;font-size:14px'>{i['emoji']} {i['name']}</td>
              <td style='padding:10px 14px;border-bottom:1px solid #f0f0f0;text-align:center;font-size:14px'>×{i['quantity']}</td>
              <td style='padding:10px 14px;border-bottom:1px solid #f0f0f0;text-align:right;font-size:14px;font-weight:700'>₹{i['price'] * i['quantity']:,.0f}</td>
            </tr>"""
        for i in items
    ])

    html_body = f"""
    <div style="font-family:Arial,sans-serif;max-width:620px;margin:0 auto;background:#ffffff;border-radius:16px;overflow:hidden;border:1px solid #ebebeb">

      <!-- Header -->
      <div style="background:linear-gradient(135deg,#2563eb,#1d4ed8);padding:36px 28px;text-align:center">
        <h1 style="color:#fff;margin:0;font-size:28px;letter-spacing:-0.5px">⚡ SwiftCart</h1>
        <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:15px">Your order is confirmed!</p>
      </div>

      <!-- Body -->
      <div style="padding:32px 28px">
        <p style="font-size:16px;color:#111;margin-bottom:6px">Hi <strong>{user['name']}</strong>,</p>
        <p style="color:#555;font-size:14px;line-height:1.6">
          Great news, we've received your order and it's being processed.
          You'll get another update when it ships.
        </p>

        <!-- Order ID badge -->
        <div style="background:#eff6ff;border:1px solid #bfdbfe;border-radius:10px;padding:16px 20px;margin:24px 0;display:inline-block;width:100%">
          <p style="margin:0;font-size:12px;color:#93c5fd;text-transform:uppercase;letter-spacing:1px;font-weight:700">Order ID</p>
          <p style="margin:6px 0 0;font-size:22px;font-weight:800;color:#2563eb">#{order_id:06d}</p>
        </div>

        <!-- Items table -->
        <h3 style="font-size:15px;color:#111;margin-bottom:12px;border-bottom:2px solid #f0f0f0;padding-bottom:10px">Items Ordered</h3>
        <table style="width:100%;border-collapse:collapse">
          <thead>
            <tr style="background:#f8fafc">
              <th style="padding:10px 14px;text-align:left;font-size:12px;color:#888;font-weight:700;text-transform:uppercase">Product</th>
              <th style="padding:10px 14px;text-align:center;font-size:12px;color:#888;font-weight:700;text-transform:uppercase">Qty</th>
              <th style="padding:10px 14px;text-align:right;font-size:12px;color:#888;font-weight:700;text-transform:uppercase">Amount</th>
            </tr>
          </thead>
          <tbody>{items_rows}</tbody>
        </table>

        <!-- Total -->
        <div style="text-align:right;margin-top:4px;padding:14px 14px;background:#f8fafc;border-radius:8px">
          <span style="font-size:11px;color:#888;text-transform:uppercase;letter-spacing:1px">Order Total</span>
          <span style="font-size:22px;font-weight:800;color:#111;margin-left:12px">₹{total:,.0f}</span>
        </div>

        <!-- Delivery address -->
        <div style="margin-top:20px;padding:16px;background:#f0fdf4;border-radius:10px;border-left:4px solid #22c55e">
          <p style="margin:0;font-size:12px;color:#86efac;font-weight:700;text-transform:uppercase;letter-spacing:1px">Delivering to</p>
          <p style="margin:8px 0 0;color:#111;font-size:14px;line-height:1.5">{address or 'Address not provided'}</p>
        </div>

        <p style="color:#888;font-size:13px;margin-top:20px;text-align:center">
          Estimated delivery: <strong style="color:#111">3–5 business days</strong>
        </p>
      </div>

      <!-- Footer -->
      <div style="background:#f8fafc;padding:20px 28px;text-align:center;border-top:1px solid #ebebeb">
        <p style="color:#bbb;font-size:12px;margin:0">© 2025 SwiftCart · Fast. Reliable. Yours.</p>
      </div>
    </div>
    """

    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"✅ Order #{order_id:06d} Confirmed, SwiftCart"
    msg['From']    = f"SwiftCart <{SMTP_USER}>"
    msg['To']      = user['email']
    msg.attach(MIMEText(html_body, 'html'))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()           # Encrypt the connection before sending credentials
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, user['email'], msg.as_string())

# SERVE THE FRONTEND
@app.route('/')
def index():
    # Serve the main HTML page when someone visits the root URL
    return send_from_directory('templates', 'index.html')

init_db()

# START THE SERVER
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)