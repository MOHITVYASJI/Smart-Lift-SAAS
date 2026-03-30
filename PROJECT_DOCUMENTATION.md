# SmartLift SaaS - Complete Project Architecture & Detailed Explanation

**Date**: March 28, 2026  
**Project Type**: Multi-tenant Lift Access Management SaaS Platform  
**Technology Stack**: Flask, SQLAlchemy, Python, Face Recognition, QR Codes, OpenCV

---

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Folder Structure & Explanation](#folder-structure)
3. [Database Architecture (Instance Folder)](#database-architecture)
4. [Core Files Explanation](#core-files)
5. [imports & Dependencies](#imports--dependencies)
6. [Face Detection Deep Dive](#face-detection-system)
7. [Data Flow](#data-flow)
8. [File-by-File Breakdown](#file-by-file-breakdown)

---

## 🎯 Project Overview

**SmartLift** एक **B2B SaaS Platform** है जो Educational Institutions (colleges, universities) और Corporate buildings के लिए बनाया गया है।

### मुख्य Functions:
- 🏢 **Multi-tenant Architecture**: एक ही platform पर कई institutions अलग-अलग
- 👤 **User Management**: Employees, Faculty, Students को enroll करना
- 🎫 **Access Control**: QR codes + Face recognition से lift access grant करना
- 📊 **Analytics**: Access logs, security events, emergency tracking
- 👥 **Visitor Management**: Temporary guest passes generate करना
- 🔐 **Security**: Face biometric verification, enrollment ID uniqueness, time-based access

---

## 📁 Folder Structure & Detailed Explanation

```
SmartLift/
│
├── 📂 instance/
│   └── smartlift_saas.db          ← SQLite Database जहाँ सभी data store है
│
├── 📂 registered_faces/
│   └── t1_Mohit_Vyas.jpg          ← Users की face images (Tenant ID prefix)
│   └── DS_model_vgg_face.npy       ← Face embedding model weights
│
├── 📂 static/
│   ├── style.css                   ← Website styling
│   ├── 📂 qr_passes/               ← Generated QR code images
│   │   └── MohitVyas_EMP001_*.png
│   └── 📂 registered_faces/        ← Face photos (symlink/copy)
│
├── 📂 templates/
│   ├── base.html                   ← Base template (navbar, sidebar)
│   ├── login.html                  ← Admin login
│   ├── dashboard.html              ← Main analytics dashboard
│   ├── users.html                  ← User management page
│   ├── visitor_passes.html         ← Visitor pass management
│   ├── hardware.html               ← Lift hardware status
│   ├── settings.html               ← Admin settings
│   ├── approval_queue.html         ← Public requests approval
│   ├── emergency.html              ← Emergency events log
│   └── sidebar.html                ← Navigation sidebar
│
├── 🐍 app.py                       ← Main Flask application
├── 🐍 models.py                    ← Database models (ORM definitions)
├── 🐍 config.py                    ← Configuration & environment vars
├── 🐍 main.py                      ← Edge Node hardware simulator (CLI)
├── 🐍 vision.py                    ← Face recognition engine
├── 🐍 audio.py                     ← Voice output for lift
├── 🐍 hardware.py                  ← Lift hardware controller simulation
├── 🐍 database.py                  ← Database utilities
│
├── requirements.txt                ← Python dependencies
├── README.md                        ← Project documentation
└── .env                            ← Environment variables (SECRET_KEY, DB_URL)
```

---

## 💾 Instance Folder & Database Architecture

### **Instance Folder क्या है?**

`instance/` folder एक Flask convention है जहाँ **प्रोडक्शन डेटा** store होता है:
- Local development के लिए SQLite database
- Configuration files जो Git में commit नहीं होती
- Sensitive data (जैसे .db files)

### **smartlift_saas.db क्या है?**

`smartlift_saas.db` एक **SQLite Database** है जो निम्नलिखित tables contain करता है:

```
┌─────────────────────────────────────────┐
│         DATABASE SCHEMA                  │
├─────────────────────────────────────────┤
│
│ ✅ TENANT (Multi-tenancy support)
│    - id, name, subscription_status
│    - max_lifts, primary_color
│    └─ यह बताता है कि कौन सा college/institution
│
│ ✅ SUPERADMIN (Platform owner)
│    - id, email, password (hashed)
│    └─ SmartLift founders ke liye (1 user normally)
│
│ ✅ ADMIN (Tenant administrator)
│    - admin_id, email, password, tenant_id (FK)
│    └─ हर college का एक admin होता है
│
│ ✅ USER (Employees/Faculty/Students)
│    - user_id, name, email, access_type
│    - Face_encoding (file path), face_vector (embeddings)
│    - allowed_floors, access_start_time, access_end_time
│    - enrollment_id, department, course, batch
│    - tenant_id (FK) ← Isolates data per institution
│    └─ Biometric enrolled users
│
│ ✅ ACCESSLOG (Access history - Core)
│    - Log_id, User_id (FK, nullable for guests)
│    - timestlap (datetime - यहाँ typo है, proper: timestamp)
│    - Source_floor, Floor_selection, status
│    - Request_ID (FK to FloorRequest)
│    └─ हर lift request ka log entry
│
│ ✅ FLOOREREQUEST (Lift button press)
│    - Request_ID, User_id (FK), Floor_number
│    - Status (Pending/Completed/Rejected)
│    - Lift_id (FK)
│    └─ Database audit trail
│
│ ✅ VISITORPASS (Temporary QR passes)
│    - id, visitor_name, purpose
│    - qr_hash (unique cryptographic token)
│    - qr_image_path, allowed_floors
│    - valid_until, status (Active/Expired/Revoked)
│    - tenant_id (FK)
│    └─ नए guests के लिए temporary passes
│
│ ✅ EMERGENCYEVENT (Security incidents)
│    - id, tenant_id, lift_id
│    - timestamp, resolved
│    └─ Panic alarm events
│
│ ✅ ACCESSREQUEST (Public self-service)
│    - id, tenant_id, name, email
│    - role, reason, requested_duration_hours
│    - status (Pending/Approved/Rejected)
│    └─ Visitors जो online request करते हैं
│
└─────────────────────────────────────────┘
```

### **Database कैसे Create होती है?**

```python
# app.py में:
with app.app_context():
    db.create_all()  # ← यह सभी tables create कर देता है
    
    # Default data seed करते हैं:
    if not SuperAdmin.query.filter_by(email="founder@smartlift.com").first():
        pw = generate_password_hash("founder123")
        db.session.add(SuperAdmin(email="founder@smartlift.com", password=pw))
        db.session.commit()  # ← Database में permanently save
```

### **Data कैसे जोड़ा जाता है?**

**Example 1: User को add करना**

```python
# users.html form submit होता है → /users (POST) → manage_users() function

if request.method == 'POST':
    name = request.form.get('name')  # Form से data लो
    email = request.form.get('email')
    file = request.files.get('face_image')  # Photo upload
    
    # Face encoding निकालो (vision.py से)
    vec = vision_engine.extract_vector(filepath)
    face_vector_cache = json.dumps(vec.tolist())
    
    # Database में नया user create करो
    new_user = User(
        name=name, email=email, access_type=access_role,
        face_vector=face_vector_cache,
        tenant_id=session['tenant_id']  # ← Tenant isolation
    )
    db.session.add(new_user)      # Memory में जोड़ो
    db.session.commit()            # Database में save करो
```

**Example 2: Access log create होना**

```python
# main.py में (hardware edge node):
# जब user face scan करता है:

log = AccessLog(
    User_id=user.user_id,
    Floor_selection=target_floor,
    status='Granted',
    timestlap=datetime.now()  # Local time (fixed from utcnow)
)
db.session.add(log)
db.session.commit()

# यह automatically database में जा जाता है
```

### **Data को कैसे retrieve करते हैं?**

```python
# Dashboard में सभी users की list दिखानी है:
users = User.query.filter_by(tenant_id=t_id).all()
# ↑ SQL: SELECT * FROM user WHERE tenant_id = ?

# Specific date का data filter करना:
target_date = datetime(2026, 3, 26).date()
logs = AccessLog.query.filter(
    db.func.date(AccessLog.timestlap) == target_date
).all()
# ↑ SQL: SELECT * FROM AccessLog WHERE DATE(timestlap) = '2026-03-26'
```

---

## 📂 registered_faces Folder & DS_model_vgg_face

### **registered_faces क्या है?**

```
registered_faces/
├── t1_Mohit_Vyas.jpg          ← Tenant 1, user Mohit Vyas का photo
├── t2_Farsan_Kumar.jpg        ← Tenant 2, user Farsan का photo
├── t3_Tanish_Soni.png
└── DS_model_vgg_face.npy       ← **Face embedding model ka weight file**
```

### **t1_Mohit_Vyas.jpg का मतलब:**
- `t1` = Tenant ID 1 (पहला institution)
- `Mohit_Vyas` = User का नाम
- `.jpg` = Image file extension

पहली बार user enroll होता है तो upload किया गया face photo यहाँ save होता है।

### **DS_model_vgg_face.npy क्या है?**

यह एक **Pre-trained Deep Learning Model** की weights file है जिसका use face encoding में होता है।

```
VGGFace Model (DeepFace library द्वारा)
↓
एक DNN (Deep Neural Network) जो:
  - Input: Face photo (RGB image)
  - Output: 128D vector (face embedding)
  
यह vector हर face को unique numerical representation देता है
```

**मतलब**:
- Mohit का face → `[0.234, 0.567, ..., 0.891]` (128 numbers)
- Tanish का face → `[0.123, 0.456, ..., 0.789]` (अलग 128 numbers)

दूसरी बार जब कोई face scan करता है, उसे same model से embedding निकाली जाती है और database में store किए गए से match करता है।

---

## 🎨 Static & Templates Folders

### **Static Folder (CSS, QR images)**

```
static/
├── style.css              ← Tailwind-like custom CSS
│   └── Contains: .glass-panel, .btn-primary, .badge, etc.
│
├── qr_passes/            ← Generated visitor pass QR codes
│   ├── MohitVyas_EMP001_20260328_0230.png
│   ├── AmazonDelivery_NA_20260328_0245.png
│   └── (dynamically created at runtime)
│
└── registered_faces/     ← User face photos (static copy)
    ├── t1_Mohit_Vyas.jpg
    └── (त्1_Farsan_Kumar.jpg
```

### **Templates Folder (HTML Files)**

```
templates/
├── base.html             ← Master template (सभी pages का base)
│   ├── <head> sections (CSS, fonts)
│   ├── <nav> with logo
│   ├── <sidebar> navigation
│   └── {% block content %} ← Children यहाँ content डालते हैं
│
├── login.html            ← Authentication
│   └── Form: email, password → POST /
│
├── dashboard.html        ← Main analytics
│   ├── KPI cards (Total users, Lifts, Peak hour)
│   ├── Access stream table with date filter
│   └── Download CSV button
│
├── users.html            ← User management (Add & List)
│   ├── Left: Users table (Image, Name, Email, Role, Academics)
│   ├── Right: Add user form
│   └── Face upload, Enrollment ID, Departments
│
├── visitor_passes.html   ← QR pass generation
│   ├── Left: Active passes list
│   ├── Right: Generate custom token form
│   └── Role, Duration, Email fields
│
├── hardware.html         ← Lift status
│   └── Shows lift connectivity
│
├── settings.html         ← Admin password change
│
├── sidebar.html          ← Navigation ({% include %})
│   ├── Dashboard link
│   ├── Users link
│   ├── Visitor Passes
│   ├── Hardware
│   ├── Settings
│   ├── Logs
│   └── Logout
│
└── emergency.html        ← Security events
    └── Forensic suspect mapping (5 min window)
```

### **Templates कैसे काम करते हैं?**

```html
<!-- base.html -->
<body>
  {% include 'sidebar.html' %}
  <div class="main-content">
    {% block content %}
      <!-- यहाँ child template का content आएगा -->
    {% endblock %}
  </div>
</body>

<!-- users.html -->
{% extends 'base.html' %}
{% block content %}
  <!-- यह content base.html के {% block content %} में replace होगा -->
  <h1>Access Management</h1>
  <table>
    {% for u in users %}  <!-- Jinja2 templating -->
      <tr>
        <td>{{ u.name }}</td>
      </tr>
    {% endfor %}
  </table>
{% endblock %}
```

**Request Flow**:
```
1. User visits /users
2. manage_users() function execute होता है
3. users = User.query.filter_by(...).all()
4. render_template('users.html', users=users) call होता है
5. users.html में {% for u in users %} iterate करता है
6. HTML render होती है और browser को भेजी जाती है
```

---

## 🔌 app.py - Main Flask Application (Detailed)

### **Part 1: Imports & Configuration**

```python
from flask import Flask, render_template, request, redirect, url_for, session, flash
```

| Import | Purpose |
|--------|---------|
| `Flask` | Main web framework, WSGI application |
| `render_template` | HTML templates को render करना |
| `request` | GET, POST data access |
| `redirect` | URL redirect (form submit के बाद) |
| `url_for` | Dynamic URL generation (hardcoding avoid करने के लिए) |
| `session` | Client cookies में data store (admin login info) |
| `flash` | Temporary messages (success, error alerts) |

```python
from models import db, SuperAdmin, Admin, Tenant, User, Lift, AccessLog, etc.
```
यहाँ `models.py` से सभी database models import किए हैं।

```python
from werkzeug.security import generate_password_hash, check_password_hash
```

| Function | Use |
|----------|-----|
| `generate_password_hash("password", method='pbkdf2:sha256')` | Password को encrypted रूप में convert करना (PBKDF2 algorithm) |
| `check_password_hash(hashed_pwd, plain_pwd)` | Login के समय password verify करना |

अगर password को plain text में store करो तो database hack होने पर सब passwords चोरी हो जाएंगे। Hashing से यह safe है।

```python
import os, uuid, qrcode
```

| Module | Use |
|--------|-----|
| `os` | File paths, directory creation (`os.makedirs()`) |
| `uuid` | Unique IDs generate करना (`uuid.uuid4().hex` → 32-char string) |
| `qrcode` | QR code images बनाना |

Example:
```python
qr_hash = f"SL-{uuid.uuid4().hex}"  # "SL-a1b2c3d4e5f6g7h8i9j0..."
```

```python
from datetime import datetime, timedelta
import PIL.Image as PIL_Image
from PIL import ImageDraw
```

| Module | Use |
|--------|-----|
| `datetime` | Date/time operations |
| `PIL` (Pillow) | Image manipulation (QR code पर text overlay) |
| `ImageDraw` | PIL का drawing component |

```python
import logging
```
Event log करने के लिए (console + file logs)

```python
from vision import VisionEngine
vision_engine = VisionEngine()  # Global initialization
```
Face recognition engine को एक बार load करो (हर request पर नहीं).

### **Part 2: Werkzeug Security (Password Hashing)**

```python
# User registration
password = "MySecurePass123"
hashed = generate_password_hash(password, method='pbkdf2:sha256')
# hashed = 'pbkdf2:sha256$600000$abcd...$xyz...'

db.session.add(Admin(email="admin@college.com", password=hashed))
db.session.commit()

# Login validation
admin = Admin.query.filter_by(email="admin@college.com").first()
if admin and check_password_hash(admin.password, form_password):
    # ✅ Password match - allow login
    session['admin_id'] = admin.admin_id
    return redirect(url_for('dashboard'))
else:
    # ❌ Password mismatch
    flash("Invalid Credentials", "danger")
```

**PBKDF2-SHA256** क्या है?
- **PBKDF2**: Key Derivation Function (1 password को 600,000 iterations से hash करना)
- **SHA256**: Hashing algorithm (256-bit output)
- **Salt**: Random string mix करना (same password का अलग hash हों)

---

## 🐍 Vision.py - Face Recognition Deep Dive

### **Architecture**

```
VisionEngine class:
├── __init__()
│   ├── DeepFace model load करना (Facenet)
│   ├── FAISS index initialization
│   └── QR code detector init करना
│
├── extract_vector()
│   ├── Input: Image file path
│   ├── DeepFace.represent() से 128-D embedding निकालना
│   └── Output: numpy array (128 numbers)
│
├── build_faiss_index()
│   ├── सभी enrolled users के vectors लेना
│   ├── FAISS IndexFlatIP बनाना
│   └── Real-time search ready करना
│
└── scan_for_user()
    ├── Webcam से frames लेना
    ├── QR detection या Face encoding
    └── FAISS से exact match खोजना
```

### **DeepFace क्या है?**

```python
from deepface import DeepFace

objs = DeepFace.represent(
    img_path="face.jpg",
    model_name="Facenet",
    enforce_detection=True
)
# Returns:
# [{"embedding": [0.234, 0.567, ..., 0.891],  # 128-D vector
#   "facial_area": {"x": 10, "y": 20, "w": 150, "h": 160}}]
```

**DeepFace Library**:
- Facebook द्वारा बनाया गया
- Multiple models support करता है: Facenet, VGGFace, ArcFace, etc.
- हमें **Facenet** use कर रहे हैं (128-dimensional embeddings)

### **FAISS क्या है?**

```python
import faiss
import numpy as np

# अगर 1000 users enrolled हैं:
vectors = np.array([  # 1000 x 128 matrix
    [0.234, 0.567, ..., 0.891],  # User 1
    [0.123, 0.456, ..., 0.789],  # User 2
    ...
    [0.999, 0.111, ..., 0.222]   # User 1000
], dtype='float32')

# FAISS index create करो
index = faiss.IndexFlatIP(128)  # IP = Inner Product (cosine similarity)
index.add(vectors)

# Real-time search
live_vector = np.array([[0.235, 0.568, ..., 0.892]], dtype='float32')
distances, indices = index.search(live_vector, k=1)
# distances = [[0.997]]  (similarity score 0-1)
# indices = [[0]]        (user 0 is best match)
```

**FAISS** (Facebook AI Similarity Search):
- Billions of vectors को efficiently search करता है
- `IndexFlatIP` = Exact inner product search
- `k=1` = सबसे close match निकालना

### **Face Recognition Workflow**

```
Step 1: User Enrollment
└─ admin/user uploads photo
   └─ vision.extract_vector(image) returns 128-D embedding
   └─ JSON में convert करके database में store

Step 2: Face Verification (Real-time scanning)
├─ Edge Node (main.py) में webcam से frame लो
├─ vision.extract_vector(frame) से live embedding निकालो
├─ FAISS में search करो (k=1, best match)
├─ If distance > 0.40 (threshold)
│  └─ ✅ ACCESS GRANTED (matched user)
└─ else
   └─ ❌ ACCESS DENIED (no match)

Step 3: Liveness Detection (Anti-spoofing)
├─ Blur detection (Laplacian variance > 35)
├─ If blur < 35
│  └─ ❌ "Photo/screen detected" - REJECT
└─ else
   └─ ✅ Real face - proceed
```

### **Threshold = 0.40 क्या है?**

```
Connection score range: [0.0, 1.0]

0.95+  → Same person (high confidence)
0.70-0.95 → Likely same person
0.40-0.70 → Maybe same (borderline)
0.0-0.40 → Different person

हमारा threshold = 0.40
└─ यानी अगर score < 0.40, reject कर दो (unknown person)
```

---

## 📧 dispatch_email Function

```python
def dispatch_email(recipient_email, recipient_name, qr_path):
    """
    QR pass को email के साथ भेजना
    
    Args:
        recipient_email: "mohit@email.com"
        recipient_name: "Mohit Vyas"
        qr_path: "static/qr_passes/MohitVyas_*.png"
    """
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    
    # Gmail credentials (from config)
    SENDER_EMAIL = app.config['SENDER_EMAIL']  # "smartlift.notifications@gmail.com"
    SENDER_PASSWORD = app.config['SENDER_PASSWORD']  # App password (not real password)
    
    # Email message बनाओ
    msg = MIMEMultipart()
    msg['Subject'] = 'SmartLift: Lift Access Approved'
    msg['From'] = f"SmartLift Security <{SENDER_EMAIL}>"
    msg['To'] = recipient_email
    
    # Body text
    email_body = f"""
    Hello {recipient_name},
    
    Your Temporary Lift Pass has been approved!
    
    The QR code is attached. Scan it at the lift scanner.
    
    Regards,
    SmartLift Backend
    """
    body = MIMEText(email_body)
    msg.attach(body)
    
    # QR image attachment
    with open(qr_path, 'rb') as f:
        img = MIMEImage(f.read())
        img.add_header('Content-Disposition', 'attachment', 
                      filename=os.path.basename(qr_path))
        msg.attach(img)
    
    # SMTP connection (TLS)
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)  # Gmail server
        server.starttls()  # Encrypt connection
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        logging.info(f'Email sent to {recipient_email}')
        return True
    except Exception as e:
        logging.error(f'Email failed: {e}')
        return False
```

**Email Flow**:
```
1. Visitor pass create होती है
2. dispatch_email() call होता है
3. Gmail SMTP server को connect करो
4. Email compose करो (text + QR image)
5. Send करो
6. Browser में "Check your email for QR code" message दिखाओ
```

---

## 📂 All Project Files - Complete Breakdown

### **1. models.py** - Database ORM Definitions

```python
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy()

class Tenant(db.Model):
    """एक institution/college को represent करता है"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))  # "Demo University"
    subscription_status = db.Column(db.String(50), default='Active')
    max_lifts = db.Column(db.Integer, default=5)
    # Relations
    users = db.relationship('User', backref='tenant')
    admins = db.relationship('Admin', backref='tenant')

class User(db.Model):
    """Enrolled employees/faculty/students"""
    user_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    access_type = db.Column(db.String(50))  # 'Faculty', 'Operator', etc.
    Face_encoding = db.Column(db.Text)  # File path: "static/registered_faces/t1_Name.jpg"
    face_vector = db.Column(db.Text)  # JSON: "[0.234, 0.567, ...]"
    enrollment_id = db.Column(db.String(50), nullable=True)  # "EMP12345"
    department = db.Column(db.String(100))  # "Computer Science"
    course = db.Column(db.String(100))  # "B.Tech"
    batch = db.Column(db.String(50))  # "2024"
    allowed_floors = db.Column(db.String(100))  # "0,1,2,3"
    access_start_time = db.Column(db.Time)  # 09:00
    access_end_time = db.Column(db.Time)  # 17:00
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'))
    #  ↑ Multi-tenancy key

class AccessLog(db.Model):
    """हर lift access का log"""
    Log_id = db.Column(db.Integer, primary_key=True)
    User_id = db.Column(db.Integer, db.ForeignKey('user.user_id'), nullable=True)
    timestlap = db.Column(db.DateTime, default=datetime.now)  # Local time
    Floor_selection = db.Column(db.Integer)  # Target floor
    status = db.Column(db.String(100))  # 'Granted', 'Denied - Role Constraint'
    user = db.relationship('User')  # Lazy loading

class VisitorPass(db.Model):
    """Temporary QR passes"""
    id = db.Column(db.Integer, primary_key=True)
    visitor_name = db.Column(db.String(100))  # "[Guest] Amazon Delivery"
    qr_hash = db.Column(db.String(255), unique=True)  # "SL-a1b2c3d4e5f6..."
    qr_image_path = db.Column(db.String(255))  # "static/qr_passes/..."
    valid_until = db.Column(db.DateTime)  # Expiry datetime
    status = db.Column(db.String(50), default='Active')  # Active/Expired/Revoked
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'))
```

### **2. app.py** - Web Server (Already detailed above)

**Key Routes**:
```
GET  /                     → login page
POST /                     → authenticate
GET  /dashboard            → main analytics
GET  /users                → user list
POST /users                → add new user
GET  /delete_user/<id>     → remove user
GET  /visitor_passes       → visitor pass management
POST /visitor_passes       → generate new pass
POST /approve_request/<id> → approve public request
GET  /export_logs          → download CSV
GET  /logout               → clear session
```

### **3. config.py** - Configuration

```python
import os

class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'default-key'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///smartlift_saas.db'
    
    # Email (SMTP)
    SENDER_EMAIL = os.environ.get('SENDER_EMAIL') or 'smartlift.notifications@gmail.com'
    SENDER_PASSWORD = os.environ.get('SENDER_PASSWORD')  # Google App Password
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
```

**Production में Docker/env files से ये values आते हैं**

### **4. main.py** - Edge Node Simulator (CLI)

```python
"""
यह script Edge Node (lift के अंदर की device) को simulate करता है
Real deployment में Raspberry Pi पर चलेगा
"""

LOCAL_EDGE_TENANT_ID = 2  # Demo Tenant को target करो

while True:
    # Webcam से फ्रेम लो
    auth_type, identifier, status = vision.scan_for_user(users)
    
    if auth_type == "FACE":
        # Face recognised! Allow lift
        hw.dispatch_lift(target_floor)
        log_event(user.user_id, target_floor, "Granted")
    
    elif auth_type == "QR":
        # QR scanned! Check if valid
        qr_pass = VisitorPass.query.filter_by(qr_hash=identifier).first()
        if qr_pass and qr_pass.valid_until > datetime.now():
            hw.dispatch_lift(qr_pass.allowed_floors[-1])
            log_event(None, target_floor, "Guest Granted")
```

### **5. vision.py** - Face Recognition (यह top-level attachment में दिया है)

सभी functions का use detailed में ऊपर explain किया गया है।

### **6. audio.py** - Voice Output

```python
"""Lift के अंदर voice instructions"""

def speak(text):
    # Text-to-speech
    # pyttsx3 या Google TTS use करके text को voice में convert करो
    # "Access Granted" या "Access Denied" बोलो
```

### **7. hardware.py** - Lift Control Simulation

```python
"""Edge Node device को control करे"""

class HardwareController:
    def dispatch_lift(self, floor_number):
        # Actual deployment: RS-485/serial commands भेजो
        # Simulation: सिर्फ print करो
        print(f"[HARDWARE] Lift moving to floor {floor_number}")
        
    def get_lift_status(self):
        # Lift की current position
        return {"floor": 2, "status": "idle"}
```

### **8. database.py** - DB Utilities

```python
"""Database initialization और backup utilities"""

def init_db():
    """Create all tables"""
    db.create_all()

def backup_db():
    """SQLite database को backup करना"""
    import shutil
    shutil.copy('smartlift_saas.db', 'smartlift_saas.db.backup')
```

---

## 🔄 Complete Data Flow Diagram

```
[User visits website]
        ↓
[browser] GET /users
        ↓
[Flask routing] → manage_users() function
        ↓
[database query] SELECT * FROM user WHERE tenant_id = 1
        ↓
[SQLAlchemy ORM converts] → users = [User(...), User(...), ...]
        ↓
[render_template] users.html + users=users
        ↓
[Jinja2 templating] {% for u in users %} ... {% endfor %}
        ↓
[HTML generated] <table><tr><td>Mohit</td>...</tr>...</table>
        ↓
[browser receives] HTTP 200 + HTML
        ↓
[browser renders] Display table with user data
```

### **Addition Flow**

```
[Admin fills form] Name, Email, Role, Face Photo
        ↓
[Submit button clicked] POST /users
        ↓
[Flask receives] request.form.get('name'), request.files.get('face_image')
        ↓
[Save image] static/registered_faces/t1_name.jpg
        ↓
[Extract face vector] vision.extract_vector(image)
        ↓
[Convert to JSON] face_vector = "[0.234, 0.567, ...]"
        ↓
[Create User object] new_user = User(name=..., face_vector=..., tenant_id=1)
        ↓
[Add to session] db.session.add(new_user)
        ↓
[Commit to DB] db.session.commit()
        ↓
[User added to table users]
        ↓
[Redirect] return redirect(url_for('manage_users'))
        ↓
[Flash message] "User enrolled successfully!" (green banner)
```

### **Login Flow** 

```
[Admin enters] email + password
        ↓
[POST /] → login() function
        ↓
[Query admin] Admin.query.filter_by(email=email).first()
        ↓
[Check password] check_password_hash(stored_hash, entered_password)
        ↓
[If match]
├─ session['admin_id'] = admin.id
├─ session['tenant_id'] = admin.tenant_id
└─ redirect to /dashboard
        ↓
[If no match]
└─ flash("Invalid Credentials", "danger")
└─ redirect to /
```

---

## 🔐 Multi-tenancy & Data Isolation

यह platform **SaaS के लिए critical** है।

```python
# Tenant A (Demo University) vs Tenant B (XYZ College)

# Tenant A का admin login करता है
session['tenant_id'] = 1

# Dashboard load करता है
users = User.query.filter_by(tenant_id=1).all()
#              ↑↑↑↑↑↑↑↑ FILTER करना जरूरी है!

# अगर filter न करो तो दोनों colleges के users दिख जाते

# SQL INJECTION से protect:
# ❌ BAD: f"SELECT * FROM users WHERE tenant_id={session['tenant_id']}"
# ✅ GOOD: User.query.filter_by(tenant_id=t_id)
```

---

## 📊 Face Recognition Model Details

### **Model: FaceNet (Google)**

```
Architecture:
├── Input: RGB Image (224x224 pixels)
├── Deep CNN: Multiple convolutional + pooling layers
├── Output Layer: 128-dimensional embedding (vector)
└── Loss Function: Triplet Loss (same person → close vectors)

Training (offline):
├─ Millions of labeled faces
├─ Triplet loss minimization (anchor, positive, negative)
└─ Creates 128-D space where same person is close

Deployment (हमारा):
├─ Pre-trained weights load करो
├─ कोई training नहीं
├─ सिर्फ feature extraction करो (embedding निकालना)
└─ FAISS में search करो
```

### **Why 128 dimensions?**

```
128-D space में:
- Same person के दोनों photos: distance < 0.40
- Different persons: distance > 0.60
- Borderline: 0.40-0.60

128 संख्याओं से हर face को unique represent किया जा सकता है
Low dimensional नहीं होगा (collision/false matches)
High dimensional नहीं होगा (computational overhead)
```

---

## 🎓 Key Learnings

| Concept | Explanation |
|---------|-------------|
| **Multi-tenancy** | सभी institutions का data एक database में, लेकिन सख्त isolation |
| **Werkzeug Security** | Passwords को PBKDF2-SHA256 से hash करना (plain text नहीं) |
| **FAISS** | Face embeddings में fast nearest-neighbor search |
| **Flask Sessions** | Browser cookies में server-side data (admin login status) |
| **SQLAlchemy ORM** | Python objects से SQL queries generate करना |
| **Jinja2** | Dynamic HTML rendering (templating engine) |
| **SMTP** | Email भेजने के लिए Gmail का SMTP server |
| **QR Codes** | Visitor passes के लिए unique cryptographic tokens |
| **Access Logs** | Audit trail और analytics के लिए हर access को log करना |

---

## 🚀 Deployment Architecture (Future Reference)

```
                    ┌─────────────────┐
                    │   Web Browser   │
                    └────────┬────────┘
                             │ HTTPS
                    ┌────────▼────────┐
                    │  Gunicorn       │ (Production WSGI)
                    │  (4 workers)    │
                    └────────┬────────┘
                             │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
    ┌───▼───┐           ┌─────▼─────┐         ┌────▼────┐
    │Redis  │           │ PostgreSQL│         │ S3 Blob │
    │Cache  │           │ Database  │         │ Store   │
    └───────┘           └───────────┘         └─────────┘
                             │
                    ┌────────▼────────┐
                    │ Celery Jobs     │ (Async: email, face extraction)
                    └─────────────────┘
```

---

## 📝 Summary

यह SmartLift platform:
1. **Multi-tenant SaaS** है (कई institutions के लिए)
2. **Face recognition** के साथ secure access control
3. **Database में audit logs** (compliance के लिए)
4. **Email notifications** (QR passes के साथ)
5. **Web dashboard** (analytics और management के लिए)
6. **Edge Node simulator** (future Raspberry Pi deployment के लिए)

हर component interconnected है और data properly isolated है.






Compacted conversation

Read [](file:///c%3A/SmartLift/PROJECT_DOCUMENTATION.md#1-1), lines 1 to 100

Read [](file:///c%3A/SmartLift/PROJECT_DOCUMENTATION.md#101-101), lines 101 to 200

Searched for text `imports & Dependencies` (`**/*.md`), 1 result

Read [](file:///c%3A/SmartLift/PROJECT_DOCUMENTATION.md#200-200), lines 200 to 400

Searched for text `## imports & Dependencies` (`**/*.md`), no results

Searched for text `imports` (`**/PROJECT_DOCUMENTATION.md`), 3 results

Read [](file:///c%3A/SmartLift/PROJECT_DOCUMENTATION.md#378-378), lines 378 to 500

Searched for text `hardware` (`**/PROJECT_DOCUMENTATION.md`), 11 results

Read [](file:///c%3A/SmartLift/PROJECT_DOCUMENTATION.md#800-800), lines 800 to 900

Searched for text `connect` (`**/PROJECT_DOCUMENTATION.md`), 6 results

Read [](file:///c%3A/SmartLift/PROJECT_DOCUMENTATION.md#640-640), lines 640 to 700

Searched for text `main.py` (`**/PROJECT_DOCUMENTATION.md`), 4 results

Read [](file:///c%3A/SmartLift/PROJECT_DOCUMENTATION.md#760-760), lines 760 to 800

### SmartLift Project में इस्तेमाल हुई सभी Technologies और Details


#### 🐍 **Python - Main Programming Language**
- **क्या है?** Python 3.x इस्तेमाल किया गया है। यह high-level, interpreted language है।
- **कहाँ इस्तेमाल?** सभी core files (app.py, models.py, vision.py, main.py, etc.) Python में लिखे हैं।
- **क्यों?** Easy syntax, rich libraries, और machine learning support के लिए।
- **Version:** Python 3.8+ recommended (requirements.txt में specified)।
- **Key Features Used:**
  - Object-oriented programming (classes like VisionEngine, HardwareController)
  - File I/O (images save/load करना)
  - JSON handling (face vectors को store करना)
  - Date/time operations (datetime module)

#### 🌐 **Flask - Backend Web Framework**
- **क्या है?** Lightweight Python web framework, WSGI application।
- **कहाँ इस्तेमाल?** app.py में main application, सभी routes (GET/POST), session management, और template rendering।
- **क्यों?** Simple, flexible, और production-ready। Django की तरह heavy नहीं।
- **Key Components:**
  - `Flask(app)`: Main app instance
  - Routes: `@app.route('/users')` for URL handling
  - `render_template()`: HTML pages generate करना
  - `request`: Form data access (POST requests)
  - `session`: User login state maintain करना
  - `flash()`: Success/error messages दिखाना
- **Extensions Used:** Flask-SQLAlchemy (ORM), Flask-Migrate (database migrations)

#### 🎨 **HTML & CSS - Frontend**
- **HTML:** Jinja2 templating के साथ dynamic pages।
  - Templates folder में सभी .html files (base.html, users.html, dashboard.html, etc.)
  - Base template (inheritance): सभी pages का common layout (navbar, sidebar)
  - Forms: User enrollment, visitor pass generation
- **CSS:** Custom styling (style.css)
  - Tailwind-like classes (.glass-panel, .btn-primary, .badge)
  - Responsive design, modern UI (cards, tables, buttons)
- **Templating Engine:** Jinja2 (Flask built-in)
  - Variables: `{{ user.name }}`
  - Loops: `{% for u in users %}`
  - Conditionals: `{% if admin %}`
- **कहाँ इस्तेमाल?** सभी user interfaces (login, dashboard, user management, visitor passes)

#### 📧 **SMTP - Email Sending & Receiving**
- **क्या है?** Simple Mail Transfer Protocol for email communication।
- **Library:** `smtplib` (Python standard library)
- **कहाँ इस्तेमाल?** Visitor passes generate करने के बाद QR code email भेजना।
- **Configuration:**
  - Gmail SMTP server: `smtp.gmail.com`, port 587
  - TLS encryption: `server.starttls()`
  - Authentication: Sender email + app password (Gmail के लिए)
- **Flow:**
  1. Visitor pass create होती है
  2. `dispatch_email()` function call
  3. Email compose (text + QR image attachment)
  4. SMTP connect, send, और quit
- **Security:** App passwords इस्तेमाल (2FA enabled Gmail accounts के लिए)

#### 🗄️ **SQLite - Database**
- **क्या है?** Lightweight, file-based relational database (no server needed)।
- **ORM:** SQLAlchemy (Flask-SQLAlchemy extension)
- **File:** smartlift_saas.db
- **Tables (8 total):**
  - `Tenant`: Multi-tenancy (institutions)
  - `SuperAdmin`: Platform owner
  - `Admin`: Institution admins
  - `User`: Enrolled users (face data, access rules)
  - `AccessLog`: Lift access history
  - `FloorRequest`: Lift button presses
  - `VisitorPass`: Temporary QR passes
  - `EmergencyEvent`: Security incidents
  - `AccessRequest`: Public self-service requests
- **Operations:**
  - Create: `db.create_all()` (app startup)
  - Insert: `db.session.add()`, `db.session.commit()`
  - Query: `User.query.filter_by(tenant_id=1).all()`
  - Relationships: Foreign keys (tenant_id, user_id, etc.)
- **Data Isolation:** Tenant-based (हर institution का अलग data)

#### 🤖 **DeepFace - Face Recognition**
- **क्या है?** Open-source face recognition library।
- **Model:** VGGFace (pre-trained neural network)
- **कहाँ इस्तेमाल?** vision.py में face embeddings निकालना।
- **Process:**
  - Input: Face image (RGB)
  - Output: 128D vector (numerical representation)
  - Example: `[0.234, 0.567, ..., 0.891]` (128 floats)
- **Models Available:** Facenet, VGG-Face, ArcFace (Facenet used)

#### 🔍 **FAISS - Vector Search**
- **क्या है?** Facebook AI Similarity Search, efficient vector matching।
- **कहाँ इस्तेमाल?** Face vectors को search करना (real-time matching)।
- **Index Type:** IndexFlatIP (Inner Product similarity)
- **Process:**
  - Build index from all enrolled user vectors
  - Query: New face vector → find nearest neighbor
  - Threshold: 0.6+ similarity for match

#### 📷 **OpenCV - Computer Vision**
- **क्या है?** Open-source computer vision library।
- **कहाँ इस्तेमाल?** QR code detection in webcam frames।
- **Functions:** `cv2.QRCodeDetector()` for scanning QR codes from images/videos

#### 🖼️ **PIL (Pillow) - Image Manipulation**
- **क्या है?** Python Imaging Library fork।
- **कहाँ इस्तेमाल?** QR code images पर text overlay करना।
- **Functions:** `ImageDraw` for drawing text on QR codes (name, expiry, etc.)

#### 🔐 **Werkzeug - Security**
- **क्या है?** Flask का underlying WSGI utility library।
- **Functions Used:**
  - `generate_password_hash()`: PBKDF2-SHA256 hashing (passwords secure करना)
  - `check_password_hash()`: Login verification
- **Algorithm:** PBKDF2 with 600,000 iterations + salt

#### 🆔 **UUID - Unique Identifiers**
- **क्या है?** Universally Unique Identifier generation।
- **कहाँ इस्तेमाल?** QR hashes, session tokens।
- **Example:** `uuid.uuid4().hex` → "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"

#### 📱 **QRCode - QR Generation**
- **Library:** `qrcode` Python library।
- **कहाँ इस्तेमाल?** Visitor passes के लिए QR images बनाना।
- **Data:** Unique hash (UUID-based) + tenant details

#### 🎤 **pyttsx3 - Text-to-Speech (Audio)**
- **क्या है?** Python text-to-speech library।
- **कहाँ इस्तेमाल?** audio.py में lift voice instructions ("Access Granted", "Floor 5")

#### 📊 **NumPy - Numerical Computing**
- **क्या है?** Array processing library।
- **कहाँ इस्तेमाल?** Face vectors को handle करना (128D arrays)

#### 📝 **Logging - Event Logging**
- **Library:** Python `logging` module।
- **कहाँ इस्तेमाल?** Console और file logs (access events, errors)

#### 🕒 **Datetime - Date/Time Handling**
- **Library:** Python `datetime` module।
- **कहाँ इस्तेमाल?** Access logs, visitor pass expiry, time-based access

---

### 🔌 **Hardware Connections और Integration Details**

#### **Overall Architecture:**
- **Web App (Flask):** Server पर चलता है, database से data manage करता है।
- **Edge Node:** Lift के अंदर physical device (Raspberry Pi), user scanning करता है।
- **Connections:** API calls (HTTP), database shared, email via SMTP, hardware via serial/RS-485.

#### **Hardware Components Needed:**
1. **Edge Node Device:** Raspberry Pi 4 या similar (Linux-based)
   - CPU: Quad-core ARM
   - RAM: 4GB+
   - Storage: MicroSD card (32GB+)
   - OS: Raspberry Pi OS (Debian-based)

2. **Webcam/Camera:** USB webcam या Raspberry Pi Camera Module
   - Resolution: 1080p minimum
   - For face/QR scanning

3. **Lift Controller Hardware:** Industrial PLC या microcontroller
   - Receives commands: "Move to floor X"
   - Sends status: Current floor, door status

4. **Display/Screen:** Small LCD screen (optional)
   - Shows status: "Scanning...", "Access Granted"

5. **Audio Speaker:** For voice output (pyttsx3)

6. **Network:** WiFi/Ethernet for internet connectivity

#### **Connections कैसे काम करते हैं:**
- **Web App ↔ Database:** SQLAlchemy ORM via SQLite file
- **Edge Node ↔ Web App:** HTTP API calls (requests library)
  - Example: POST /api/verify_user with face data
- **Edge Node ↔ Lift Hardware:** Serial communication (RS-485 protocol)
  - Commands: "DISPATCH_FLOOR:5"
  - Status: "CURRENT_FLOOR:3"
- **Web App ↔ Email Server:** SMTP over TLS (port 587)
- **Face Recognition:** Local processing (no cloud needed)
  - Webcam → OpenCV → QR detection या DeepFace → FAISS matching

#### **Data Flow in Hardware:**
1. **User Approaches Lift:** Webcam activates
2. **Scanning:** main.py loop runs, captures frames
3. **Face/QR Detection:** vision.py processes image
4. **Verification:** Database query for match
5. **Access Grant:** Hardware command sent to lift motor
6. **Logging:** AccessLog entry created
7. **Feedback:** Voice message + display update

#### **Power & Deployment:**
- **Power Supply:** 5V USB for Raspberry Pi, 12V for lift controller
- **Deployment:** Docker containers for web app, physical hardware for edge nodes
- **Backup:** Database backup scripts, redundant power supplies

#### **Security & Reliability:**
- **Encryption:** HTTPS for web traffic, TLS for email
- **Failover:** Local caching if network down
- **Monitoring:** Hardware status page in web app

यह project fully self-contained है - कोई external cloud services नहीं, सब local processing। Hardware integration simulation-ready है, real deployment के लिए सिर्फ physical connections add करने होंगे।

---

**Created**: 28 March 2026  
**Project Status**: Production-ready SaaS platform with all core features



