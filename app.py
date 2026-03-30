from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, SuperAdmin, Admin, Tenant, User, Lift, AccessLog, VisitorPass, EmergencyEvent, AccessRequest
from werkzeug.security import generate_password_hash, check_password_hash
import os
import uuid
import qrcode
from datetime import datetime, timedelta
import PIL.Image as PIL_Image
from PIL import ImageDraw
import logging

# Vision engine loaded once to avoid repeated imports at each form submit (avoids Flask reloader/reset loops)
try:
    from vision import VisionEngine
    vision_engine = VisionEngine()
except Exception as e:
    vision_engine = None
    logging.warning(f"VisionEngine init failed: {e}")

def synthesize_custom_qr(qr_hash, name, role, valid_until, ID="", tenant_name="", email=""):
    import qrcode
    from PIL import Image, ImageDraw
    import os
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_hash)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    
    canvas_w = qr_img.width + 40
    canvas_h = qr_img.height + 170  # Increased for more details
    canvas = Image.new('RGB', (canvas_w, canvas_h), 'white')
    canvas.paste(qr_img, (20, 20))
    
    draw = ImageDraw.Draw(canvas)
    y = qr_img.height + 25
    id_str = f" | ID: {ID}" if ID else ""
    
    # Enhanced details with tenant and email
    if tenant_name:
        draw.text((25, y), f"INSTITUTION: {tenant_name}", fill="black")
        y += 18
    draw.text((25, y), f"IDENTITY: {name}", fill="black")
    draw.text((25, y+18), f"ROLE: {role}{id_str}", fill="black")
    if email:
        draw.text((25, y+36), f"EMAIL: {email}", fill="black")
        draw.text((25, y+54), f"EXPIRES: {valid_until.strftime('%Y-%m-%d %H:%M')}", fill="red")
    else:
        draw.text((25, y+36), f"EXPIRES: {valid_until.strftime('%Y-%m-%d %H:%M')}", fill="red")
    
    safe_name = name.replace(" ", "_")
    timestamp = valid_until.strftime('%Y%m%d_%H%M')
    filename = f"{safe_name}_{ID or 'NA'}_{timestamp}.png"
    filepath = os.path.join('static', 'qr_passes', filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    canvas.save(filepath)
    return filepath

def dispatch_email(recipient_email, recipient_name, qr_path):
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    import os
    
    # =========================================================
    # PHASE 11 SMTP: YOU MUST FILL THESE OUT FOR LIVE EMAILS!
    # Generate an "App Password" from your Google Account settings 
    # Do NOT put your normal Google password here.
    # =========================================================
    SENDER_EMAIL = app.config['SENDER_EMAIL'] 
    SENDER_PASSWORD = app.config['SENDER_PASSWORD']
    
    try:
        msg = MIMEMultipart()
        msg['Subject'] = 'SmartLift: Institutional Lift Access Approved'
        msg['From'] = f"SmartLift Security <{SENDER_EMAIL}>"
        msg['To'] = recipient_email
        
        email_body = f"Hello {recipient_name},\n\nYour Temporary Lift Pass request has been manually Approved by your local Administration.\n\nThe customized QR Cryptographic Identity Token is attached to this email. You may scan this barcode directly at any Edge Node scanner on-site.\n\nRegards,\nSmartLift Backend Service Engine"
        body = MIMEText(email_body)
        msg.attach(body)
        
        with open(qr_path, 'rb') as f:
            img = MIMEImage(f.read())
            img.add_header('Content-Disposition', 'attachment', filename=os.path.basename(qr_path))
            msg.attach(img)
            
        print(f"--> [SMTP ENGINE] Connecting to TLS Gateway smtp.gmail.com:587...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"--> [SMTP 250 OK] Successfully relayed payload to {recipient_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("\n[SMTP AUTH ERROR] Authentication failed! Did you remember to use a 16-digit Google App Password?")
        return False
    except Exception as e:
        print(f"\n[SMTP FATAL ERROR]: {e}")
        return False


import logging

app = Flask(__name__)
app.config.from_object('config.Config')
logging.basicConfig(level=getattr(logging, app.config['LOG_LEVEL']))

os.makedirs('static/registered_faces', exist_ok=True)

db.init_app(app)

with app.app_context():
    db.create_all()
    # 1. Create Root SuperAdmin (Mohit & Team)
    if not SuperAdmin.query.filter_by(email="founder@smartlift.com").first():
        pw = generate_password_hash("founder123", method='pbkdf2:sha256')
        db.session.add(SuperAdmin(email="founder@smartlift.com", password=pw))
        db.session.commit()
    
    # 2. Create Demo Tenant if none
    if not Tenant.query.first():
        demo_tenant = Tenant(name="Demo University", subscription_type="Enterprise", max_lifts=10)
        db.session.add(demo_tenant)
        db.session.commit()
        # Create Demo Admin associated with this tenant
        admin_pw = generate_password_hash("admin123", method='pbkdf2:sha256')
        db.session.add(Admin(email="admin@demo.com", password=admin_pw, tenant_id=demo_tenant.id))
        # Create Demo Lift associated with this tenant
        db.session.add(Lift(name="Main Building Lift", status="Online", tenant_id=demo_tenant.id))
        db.session.commit()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        # 1. Check SuperAdmin First
        super_admin = SuperAdmin.query.filter_by(email=email).first()
        if super_admin and check_password_hash(super_admin.password, password):
            session['superadmin_id'] = super_admin.id
            return redirect(url_for('superadmin_dashboard'))
            
        # 2. Check Local Tenant Admin Second
        tenant_admin = Admin.query.filter_by(email=email).first()
        if tenant_admin and check_password_hash(tenant_admin.password, password):
            # Check Subscription Rules
            if tenant_admin.tenant.subscription_status != 'Active':
                flash("Your institution's subscription is suspended. Please contact SmartLift Founders.", "danger")
                return redirect(url_for('login'))
                
            session['admin_id'] = tenant_admin.admin_id
            session['tenant_id'] = tenant_admin.tenant_id
            return redirect(url_for('dashboard'))
            
        flash("Invalid Credentials. Access Denied.", "danger")
    return render_template('login.html')

# --------------------------
# SUPERADMIN ROUTES
# --------------------------
@app.route('/superadmin')
def superadmin_dashboard():
    if 'superadmin_id' not in session: return redirect(url_for('login'))
    tenants = Tenant.query.order_by(Tenant.created_at.desc()).all()
    return render_template('superadmin_dashboard.html', tenants=tenants, total_tenants=len(tenants))

@app.route('/superadmin/add_tenant', methods=['POST'])
def add_tenant():
    if 'superadmin_id' not in session: return redirect(url_for('login'))
    name = request.form.get('name')
    sub_type = request.form.get('subscription_type')
    max_lifts = request.form.get('max_lifts')
    admin_email = request.form.get('admin_email')
    admin_pass = request.form.get('admin_pass')
    
    new_tenant = Tenant(name=name, subscription_type=sub_type, max_lifts=int(max_lifts))
    db.session.add(new_tenant)
    db.session.commit()
    
    hashed_pw = generate_password_hash(admin_pass, method='pbkdf2:sha256')
    db.session.add(Admin(email=admin_email, password=hashed_pw, tenant_id=new_tenant.id))
    db.session.commit()
    
    flash(f"Tenant '{name}' onboarded successfully!", "success")
    return redirect(url_for('superadmin_dashboard'))

@app.route('/superadmin/toggle_tenant/<int:id>')
def toggle_tenant(id):
    if 'superadmin_id' not in session: return redirect(url_for('login'))
    tenant = Tenant.query.get(id)
    if tenant:
        tenant.subscription_status = 'Suspended' if tenant.subscription_status == 'Active' else 'Active'
        db.session.commit()
        flash(f"Tenant '{tenant.name}' status changed to {tenant.subscription_status}", "success")
    return redirect(url_for('superadmin_dashboard'))

# --------------------------
# TENANT ROUTES (Strict Isolation)
# --------------------------
@app.route('/dashboard')
def dashboard():
    if 'admin_id' not in session: return redirect(url_for('login'))
    t_id = session['tenant_id']
    tenant = Tenant.query.get(t_id)
    
    # Only fetch users and lifts for this specific tenant
    users = User.query.filter_by(tenant_id=t_id).all()
    active_lifts = Lift.query.filter_by(tenant_id=t_id, status="Online").count()
    
    # Phase 7: Functional SQLite Date Filtering
    filter_date = request.args.get('date')
    query = AccessLog.query.join(User, AccessLog.User_id == User.user_id, isouter=True).filter(
        db.or_(User.tenant_id == t_id, AccessLog.status.like('%Guest%'))
    )
    if filter_date:
        try:
            target_date = datetime.strptime(filter_date, '%Y-%m-%d').date()
            query = query.filter(db.func.date(AccessLog.timestlap) == target_date)
        except: pass
        
    logs = query.order_by(AccessLog.timestlap.desc()).limit(150).all()
    
    # Phase 7: Real Data Mapping for Identity Distributions
    dist = {'Operator': 0, 'Faculty': 0, 'Disability': 0, 'Temporary': 0, 'Guests': 0, 'Alerts': 0}
    for log in logs:
        if 'Alert' in log.status or 'Denied' in log.status or 'Rejected' in log.status:
            dist['Alerts'] += 1
        elif log.user:
            role = log.user.access_type
            if role in dist: dist[role] += 1
            else: dist['Temporary'] += 1
        elif 'Guest' in log.status:
            dist['Guests'] += 1
    chart_data = [dist['Operator'], dist['Faculty'], dist['Disability'], dist['Temporary'], dist['Guests'], dist['Alerts']]
    
    peak_hour = "N/A"
    try:
        from collections import Counter
        hours = [log.timestlap.hour for log in logs]
        if hours: peak_hour = f"{Counter(hours).most_common(1)[0][0]}:00"
    except: pass
    
    return render_template('dashboard.html', tenant=tenant, total_users=len(users), logs=logs, active_lifts=active_lifts, peak_hour=peak_hour, chart_data=chart_data)

@app.route('/export_logs')
def export_logs():
    if 'admin_id' not in session: 
        logging.warning('Unauthorized export attempt')
        return redirect(url_for('login'))
    t_id = session['tenant_id']
    from flask import Response
    from sqlalchemy.orm import joinedload
    
    filter_date = request.args.get('date')
    query = AccessLog.query.options(joinedload(AccessLog.user)).join(User, AccessLog.User_id == User.user_id, isouter=True).filter(
        db.or_(User.tenant_id == t_id, AccessLog.status.like('%Guest%'))
    )
    if filter_date:
        try:
            target_date = datetime.strptime(filter_date, '%Y-%m-%d').date()
            query = query.filter(db.func.date(AccessLog.timestlap) == target_date)
        except ValueError:
            logging.warning('Invalid date format in export: %s', filter_date)
    
    logs = query.order_by(AccessLog.timestlap.desc()).all()
    logging.info('Exporting %d logs for tenant %s, date %s by admin %s', len(logs), t_id, filter_date, session['admin_id'])
    
    # Eagerly load all data before streaming
    csv_data = []
    csv_data.append("Timestamp,Identity,Target_Floor,Status\n")
    
    for log in logs:
        name = log.user.name if log.user else "Unregistered/Guest"
        status = log.status.replace(',', '')
        csv_data.append(f"{log.timestlap.strftime('%Y-%m-%d %H:%M:%S')},{name},{log.Floor_selection},{status}\n")
            
    filename = f"Tenant_{t_id}_logs{'_' + filter_date.replace('-', '') if filter_date else ''}.csv"
    return Response(''.join(csv_data), mimetype='text/csv', headers={"Content-Disposition": f"attachment;filename={filename}"})

@app.route('/users', methods=['GET', 'POST'])
def manage_users():
    if 'admin_id' not in session: return redirect(url_for('login'))
    t_id = session['tenant_id']
    
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            access_role = request.form.get('access_role')
            floors = request.form.get('allowed_floors')
            start_time_str = request.form.get('start_time')
            end_time_str = request.form.get('end_time')
            email = request.form.get('email')
            enrollment_id = request.form.get('enrollment_id')
            department = request.form.get('department')
            course = request.form.get('course')
            batch = request.form.get('batch')
            file = request.files.get('face_image')
            
            # Validate required fields
            if not name or not email or not access_role or not floors:
                flash("Error: Name, Email, Role, and Floors are required.", "danger")
                return redirect(url_for('manage_users'))
            
            # Parse time fields safely
            start_time = None
            end_time = None
            try:
                if start_time_str:
                    start_time = datetime.strptime(start_time_str, '%H:%M').time()
                if end_time_str:
                    end_time = datetime.strptime(end_time_str, '%H:%M').time()
            except ValueError as te:
                logging.warning(f'Invalid time format: {te}')
            
            # Handle face image
            filepath = ""
            face_vector_cache = ""
            if file and file.filename != '':
                if not name:
                    flash("Error: Name is required to upload face.", "danger")
                    return redirect(url_for('manage_users'))
                
                # Prefix with tenant ID to prevent overwrites across tenants
                filename = f"t{t_id}_{name.replace(' ', '_')}.jpg"
                filepath = os.path.join('static', 'registered_faces', filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                file.save(filepath)
                
                try:
                    import json
                    if vision_engine:
                        vec = vision_engine.extract_vector(filepath)
                    else:
                        vec = None
                        logging.warning("VisionEngine unavailable at request time")
                    # Must normalize the vector inside extraction to sync with FAISS inner-product
                    if vec is not None:
                        face_vector_cache = json.dumps(vec.tolist())
                        logging.info(f'Face vector extracted for user {name}')
                    else:
                        flash("AI warning: No clear face detected in the photo or VisionEngine unavailable. Please re-upload.", "warning")
                except Exception as e:
                    logging.error(f"Face extraction error for {name}: {str(e)}")
                    flash(f"Warning: Face recognition failed but user enrolled. Error: {str(e)}", "warning")
            else:
                flash("Error: Face photo is required.", "danger")
                return redirect(url_for('manage_users'))
                
            # Check enrollment ID uniqueness
            if enrollment_id:
                existing = User.query.filter_by(tenant_id=t_id, enrollment_id=enrollment_id).first()
                if existing:
                    flash(f"Transaction Blocked: Enrollment ID '{enrollment_id}' officially belongs to {existing.name}.", "danger")
                    return redirect(url_for('manage_users'))
            
            # Create and save new user
            new_user = User(
                name=name, email=email, access_type=access_role, allowed_floors=floors, 
                Face_encoding=filepath, face_vector=face_vector_cache, 
                access_start_time=start_time, access_end_time=end_time, tenant_id=t_id,
                enrollment_id=enrollment_id, department=department, course=course, batch=batch
            )
            db.session.add(new_user)
            db.session.commit()
            logging.info(f'New user {name} enrolled for tenant {t_id} by admin {session.get("admin_id")}')
            flash(f"User {name} enrolled locally for your institution!", "success")
            return redirect(url_for('manage_users'))
            
        except Exception as e:
            db.session.rollback()
            logging.error(f'User enrollment error: {str(e)}')
            flash(f"Error enrolling user: {str(e)}", "danger")
            return redirect(url_for('manage_users'))
        
    users = User.query.filter_by(tenant_id=t_id).all()
    return render_template('users.html', users=users)

@app.route('/visitor_passes', methods=['GET', 'POST'])
def manage_visitor_passes():
    if 'admin_id' not in session: return redirect(url_for('login'))
    t_id = session['tenant_id']
    admin_id = session['admin_id']
    
    if request.method == 'POST':
        role = request.form.get('role', 'Guest')
        name = request.form.get('visitor_name')
        purpose = request.form.get('purpose')
        floors = request.form.get('allowed_floors')
        email = request.form.get('email')
        valid_until_str = request.form.get('valid_until') # Expected format YYYY-MM-DDTHH:MM
        
        qr_hash = f"SL-{uuid.uuid4().hex}"
        try:
            valid_until = datetime.strptime(valid_until_str, '%Y-%m-%dT%H:%M')
        except:
            valid_until = datetime.now() + timedelta(hours=2) # safety fallback
        
        # Get tenant name for QR
        tenant = Tenant.query.get(t_id)
        tenant_name = tenant.name if tenant else "SmartLift"
        
        # Phase 10 PIL Canvas Instantiation with enhanced details
        filepath = synthesize_custom_qr(qr_hash, name, role, valid_until, "", tenant_name, email)
        
        if email:
            dispatch_email(email, name, filepath)
        
        new_pass = VisitorPass(
            visitor_name=f"[{role}] {name}", purpose=purpose, qr_hash=qr_hash,
            qr_image_path=filepath, allowed_floors=floors,
            valid_until=valid_until, tenant_id=t_id,
            created_by_admin_id=admin_id
        )
        db.session.add(new_pass)
        db.session.commit()
        flash(f"Temporary {role} Pass deployed manually for {name}.", "success")
        return redirect(url_for('manage_visitor_passes'))
        
    # Phase 4 Auto-expire logic (basic sweep of DB)
    now = datetime.now()
    VisitorPass.query.filter(VisitorPass.valid_until < now, VisitorPass.status == 'Active').update({'status':'Expired'})
    db.session.commit()
    
    passes = VisitorPass.query.filter_by(tenant_id=t_id).order_by(VisitorPass.valid_until.desc()).all()
    return render_template('visitor_passes.html', passes=passes)

@app.route('/revoke_pass/<int:pass_id>')
def revoke_pass(pass_id):
    if 'admin_id' not in session: return redirect(url_for('login'))
    t_id = session['tenant_id']
    p = VisitorPass.query.get(pass_id)
    if p and p.tenant_id == t_id:
        p.status = 'Revoked'
        db.session.commit()
        flash(f"Access rights fundamentally severed for {p.visitor_name}.", "danger")
    return redirect(url_for('manage_visitor_passes'))

@app.route('/delete_pass/<int:pass_id>')
def delete_pass(pass_id):
    if 'admin_id' not in session: return redirect(url_for('login'))
    t_id = session['tenant_id']
    p = VisitorPass.query.get(pass_id)
    if p and p.tenant_id == t_id:
        db.session.delete(p)
        db.session.commit()
        flash(f"SQL Identity Record critically erased from existence.", "danger")
    return redirect(url_for('manage_visitor_passes'))

@app.route('/hardware')
def hardware():
    if 'admin_id' not in session: return redirect(url_for('login'))
    lifts = Lift.query.filter_by(tenant_id=session['tenant_id']).all()
    return render_template('hardware.html', lifts=lifts)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'admin_id' not in session: return redirect(url_for('login'))
    t_id = session['tenant_id']
    tenant = Tenant.query.get(t_id)
    admin = Admin.query.get(session['admin_id'])
    
    if request.method == 'POST':
        new_pass = request.form.get('new_password')
        if new_pass:
            admin.password = generate_password_hash(new_pass, method='pbkdf2:sha256')
            db.session.commit()
            flash("Administrator security token successfully rotated. Use this password upon next authorization.", "success")
            
    return render_template('settings.html', tenant=tenant, admin=admin)

@app.route('/api/panic/<int:lift_id>', methods=['POST'])
def api_panic(lift_id):
    # Simulated Edge Node hardware panic trigger
    lift = Lift.query.get(lift_id)
    if lift:
        ev = EmergencyEvent(tenant_id=lift.tenant_id, lift_id=lift_id)
        db.session.add(ev)
        db.session.commit()
        return {'status': 'alert_logged'}, 200
    return {'status': 'error'}, 404

@app.route('/emergency')
def emergency_dashboard():
    if 'admin_id' not in session: return redirect(url_for('login'))
    t_id = session['tenant_id']
    events = EmergencyEvent.query.filter_by(tenant_id=t_id).order_by(EmergencyEvent.timestamp.desc()).all()
    
    # Phase 8: Forensic Suspect Mapping
    forensics = []
    for e in events:
        # Find logs +/- 5 minutes
        start_bound = e.timestamp - timedelta(minutes=5)
        end_bound = e.timestamp + timedelta(minutes=5)
        suspects = AccessLog.query.join(User, AccessLog.User_id == User.user_id, isouter=True).filter(
            db.or_(User.tenant_id == t_id, AccessLog.status.like('%Guest%')),
            AccessLog.timestlap >= start_bound,
            AccessLog.timestlap <= end_bound
        ).all()
        forensics.append({'event': e, 'suspects': suspects})
        
    return render_template('emergency.html', forensics=forensics)

@app.route('/request_access', methods=['GET', 'POST'])
def public_request():
    if request.method == 'POST':
        tenant_id = request.form.get('tenant_id')
        name = request.form.get('name')
        email = request.form.get('email')
        role = request.form.get('role')
        enrollment_id = request.form.get('enrollment_id')
        department = request.form.get('department')
        reason = request.form.get('reason')
        hours = request.form.get('requested_duration_hours', 24)
        floors = request.form.get('floors', '0')
        
        # Verify enrollment_id duplicate externally if requested
        if enrollment_id:
            existing = User.query.filter_by(tenant_id=tenant_id, enrollment_id=enrollment_id).first()
            if existing and existing.name.lower() != name.lower():
                return f"Constraint Error: Enrollment ID officially registered to distinct identity ({existing.name}). Return and correct parameters.", 403
        
        req = AccessRequest(
            tenant_id=tenant_id, name=name, email=email, role=role, enrollment_id=enrollment_id,
            department=department, reason=reason, requested_duration_hours=int(hours), floors=floors
        )
        db.session.add(req)
        db.session.commit()
        return render_template('request_success.html')
        
    tenants = Tenant.query.filter_by(subscription_status='Active').all()
    return render_template('public_request.html', tenants=tenants)

@app.route('/approval_queue')
def approval_queue():
    if 'admin_id' not in session: return redirect(url_for('login'))
    t_id = session['tenant_id']
    reqs = AccessRequest.query.filter_by(tenant_id=t_id, status='Pending').all()
    return render_template('approval_queue.html', reqs=reqs)

@app.route('/approve_request/<int:req_id>')
def approve_request(req_id):
    if 'admin_id' not in session: return redirect(url_for('login'))
    t_id = session['tenant_id']
    r = AccessRequest.query.get(req_id)
    if r and r.tenant_id == t_id and r.status == 'Pending':
        r.status = 'Approved'
        # Generate physical QR via Phase 10 PIL Graphic Engine
        qr_hash = f"SL-{uuid.uuid4().hex}"
        valid_until = datetime.now() + timedelta(hours=r.requested_duration_hours)
        
        # Get tenant name for QR
        tenant = Tenant.query.get(t_id)
        tenant_name = tenant.name if tenant else "SmartLift"
        filepath = synthesize_custom_qr(qr_hash, r.name, r.role, valid_until, r.enrollment_id, tenant_name, r.email)
        
        # Phase 10: Launch SMTP Sequence
        dispatch_email(r.email, r.name, filepath)
        
        new_pass = VisitorPass(
            visitor_name=f"[{r.role} Approved] {r.name}", purpose=r.reason, qr_hash=qr_hash,
            qr_image_path=filepath, allowed_floors=r.floors, valid_until=valid_until,
            tenant_id=t_id, created_by_admin_id=session['admin_id']
        )
        db.session.add(new_pass)
        db.session.commit()
        flash(f"Public request approved for {r.name}. QR code automatically synthesized and routed to Visitor Passes.", "success")
    return redirect(url_for('approval_queue'))

@app.route('/delete_user/<int:user_id>')
def delete_user(user_id):
    if 'admin_id' not in session: return redirect(url_for('login'))
    t_id = session['tenant_id']
    user = User.query.get(user_id)
    if user and user.tenant_id == t_id:
        try:
            # Delete face image if exists
            if user.Face_encoding and os.path.exists(user.Face_encoding):
                os.remove(user.Face_encoding)
            db.session.delete(user)
            db.session.commit()
            logging.info(f'User {user.name} deleted by admin {session.get("admin_id")}')
            flash(f"User {user.name} removed from system.", "success")
        except Exception as e:
            db.session.rollback()
            logging.error(f'Error deleting user: {str(e)}')
            flash(f"Error deleting user: {str(e)}", "danger")
    return redirect(url_for('manage_users'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    # Avoid dev reloader crashes with heavy model package file changes (cv2/tensorflow)
    app.run(debug=False, use_reloader=False, port=8000, host='0.0.0.0')
