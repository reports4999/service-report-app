# ================================================================
#  ServiceReport Pro — app.py  (RENDER DEPLOYMENT - FIXED)
#  Complete Auth: Register + Login (2-step OTP) + Forgot Password
#  Live email OTP via Gmail SMTP
# ================================================================

# ✅ FIX 1: All imports at the TOP
import os
from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import mysql.connector
from datetime import datetime, timedelta
import random, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "servicereport_ultra_secret_2026")

# ✅ FIX 2: CORS now allows ALL origins (works on Render + localhost)
CORS(app, supports_credentials=True, origins="*")

# ================================================================
# ⚙️  GMAIL CONFIGURATION
#     On Render → set these as Environment Variables (not hardcoded)
#     Render Dashboard → your service → Environment → Add Variable
#     GMAIL_SENDER   = adityaphadnis11@gmail.com
#     GMAIL_PASSWORD = ihov mzhn cylj njho
# ================================================================
GMAIL_SENDER   = os.environ.get("GMAIL_SENDER",   "adityaphadnis11@gmail.com")
GMAIL_PASSWORD = os.environ.get("GMAIL_PASSWORD", "ihov mzhn cylj njho")

APP_NAME       = "ServiceReport Pro"
OTP_EXPIRY_MIN = 10
MAX_ATTEMPTS   = 5

# ================================================================
# ✅ FIX 3: DATABASE — Use environment variable for Render
#    Option A (Free): Use PlanetScale / Clever Cloud / Railway MySQL
#    Option B: Use SQLite for testing (no setup needed)
#
#    On Render, set these Environment Variables:
#    DB_HOST     = your-cloud-mysql-host
#    DB_USER     = your-db-username
#    DB_PASSWORD = your-db-password
#    DB_NAME     = your-db-name
#    DB_PORT     = 3306
# ================================================================
def db():
    return mysql.connector.connect(
        host     = os.environ.get("DB_HOST",     "localhost"),
        user     = os.environ.get("DB_USER",     "root"),
        password = os.environ.get("DB_PASSWORD", ""),
        database = os.environ.get("DB_NAME",     "test"),
        port     = int(os.environ.get("DB_PORT", 3306)),
        autocommit = True
    )

def init_db():
    c = db()
    cur = c.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
        id         INT AUTO_INCREMENT PRIMARY KEY,
        username   VARCHAR(100) NOT NULL,
        email      VARCHAR(200) NOT NULL UNIQUE,
        password   VARCHAR(255) NOT NULL,
        created_at DATETIME DEFAULT NOW()
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS reports (
        id         INT AUTO_INCREMENT PRIMARY KEY,
        title      VARCHAR(300),
        content    TEXT,
        created_at DATETIME DEFAULT NOW()
    )""")
    cur.close(); c.close()


# ================================================================
# OTP STORE  { "purpose:email": {otp, expires, attempts} }
# ================================================================
OTP_STORE = {}

def otp_create(purpose: str, email: str) -> str:
    otp = str(random.randint(100000, 999999))
    OTP_STORE[f"{purpose}:{email}"] = {
        "otp":      otp,
        "expires":  datetime.now() + timedelta(minutes=OTP_EXPIRY_MIN),
        "attempts": 0
    }
    return otp

def otp_verify(purpose: str, email: str, user_input: str) -> str:
    """Returns: 'ok' | 'wrong' | 'expired' | 'missing' | 'locked'"""
    key = f"{purpose}:{email}"
    rec = OTP_STORE.get(key)
    if not rec:                          return "missing"
    if datetime.now() > rec["expires"]:  del OTP_STORE[key]; return "expired"
    if rec["attempts"] >= MAX_ATTEMPTS:  return "locked"
    if rec["otp"] != user_input.strip():
        OTP_STORE[key]["attempts"] += 1; return "wrong"
    del OTP_STORE[key]   # one-time use
    return "ok"

OTP_MSG = {
    "wrong":   "Incorrect OTP. Please try again.",
    "expired": "OTP has expired. Please request a new one.",
    "missing": "OTP not found. Please request a new one.",
    "locked":  "Too many attempts. Please request a new OTP.",
}


# ================================================================
# EMAIL SENDER
# ================================================================
def send_otp_email(to_email: str, otp: str, purpose: str, name: str = "User") -> bool:

    titles   = {"register": "Confirm your email", "login": "Your login code", "reset": "Reset your password"}
    contexts = {
        "register": "You're signing up for <strong>ServiceReport Pro</strong>. Use the code below to verify your email address.",
        "login":    "A login attempt was made to your account. Use the code below to complete sign-in.",
        "reset":    "A password reset was requested for your account. Use the code below to proceed.",
    }
    icons    = {"register": "✉️", "login": "🔐", "reset": "🔒"}

    title   = titles.get(purpose, "Verification Code")
    context = contexts.get(purpose, "Use the code below.")
    icon    = icons.get(purpose, "🔑")

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#09131f;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#09131f;padding:48px 0;">
  <tr><td align="center">
  <table width="560" cellpadding="0" cellspacing="0" border="0" style="max-width:560px;width:100%;">
    <tr><td style="padding-bottom:28px;text-align:center;">
      <table cellpadding="0" cellspacing="0" border="0" align="center">
        <tr>
          <td style="background:#e8a04a;width:9px;height:9px;border-radius:50%;"></td>
          <td style="width:10px;"></td>
          <td style="font-size:20px;font-weight:700;color:#ffffff;letter-spacing:-0.3px;">
            ServiceReport <span style="color:#e8a04a;">Pro</span>
          </td>
        </tr>
      </table>
    </td></tr>
    <tr><td style="background:#0f1c2e;border-radius:20px;overflow:hidden;border:1px solid rgba(255,255,255,0.07);">
      <tr><td style="background:linear-gradient(90deg,#1e3352,#162236);padding:32px 40px;border-bottom:1px solid rgba(255,255,255,0.06);">
        <table width="100%"><tr>
          <td>
            <div style="font-size:32px;margin-bottom:10px;">{icon}</div>
            <div style="font-size:22px;font-weight:700;color:#ffffff;margin-bottom:6px;">{title}</div>
            <div style="font-size:14px;color:#8aa0b8;line-height:1.6;">{context}</div>
          </td>
          <td width="80" valign="top" align="right">
            <div style="font-size:11px;color:rgba(255,255,255,0.25);text-transform:uppercase;letter-spacing:1px;">Secured by<br><span style="color:#e8a04a;">{APP_NAME}</span></div>
          </td>
        </tr></table>
      </td></tr>
      <tr><td style="padding:40px;text-align:center;">
        <div style="font-size:12px;color:#8aa0b8;letter-spacing:2px;text-transform:uppercase;margin-bottom:18px;">One-Time Password</div>
        <div style="background:#09131f;border:2px solid rgba(232,160,74,0.4);border-radius:16px;padding:28px 20px;display:inline-block;min-width:280px;">
          <div style="font-size:48px;font-weight:800;letter-spacing:18px;color:#e8a04a;font-family:Georgia,serif;padding-left:18px;">{otp}</div>
        </div>
        <div style="margin-top:18px;font-size:13px;color:#8aa0b8;">
          Valid for <strong style="color:#ffffff;">{OTP_EXPIRY_MIN} minutes</strong> &nbsp;·&nbsp; One-time use only
        </div>
      </td></tr>
      <tr><td style="padding:0 40px 36px;">
        <div style="background:#0a1929;border-radius:12px;padding:18px 20px;border-left:3px solid #e8a04a;">
          <div style="font-size:13px;color:#cbd5e1;line-height:1.7;">
            Hi <strong style="color:#ffffff;">{name}</strong>, this code was requested from <strong style="color:#e8a04a;">{APP_NAME}</strong>.<br>
            <span style="color:#8aa0b8;">If you didn't request this, you can safely ignore this email. Do <strong style="color:#ff9a96;">not share</strong> this code with anyone.</span>
          </div>
        </div>
      </td></tr>
      <tr><td style="background:#09131f;padding:18px 40px;border-top:1px solid rgba(255,255,255,0.05);text-align:center;">
        <div style="font-size:12px;color:rgba(255,255,255,0.2);">© 2026 {APP_NAME} &nbsp;·&nbsp; Pune, India &nbsp;·&nbsp; This is an automated email, please do not reply</div>
      </td></tr>
    </td></tr>
  </table>
  </td></tr>
</table>
</body>
</html>
"""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"{icon} {title} — {APP_NAME}"
        msg["From"]    = f"{APP_NAME} <{GMAIL_SENDER}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as s:
            s.login(GMAIL_SENDER, GMAIL_PASSWORD)
            s.sendmail(GMAIL_SENDER, to_email, msg.as_string())
        print(f"[EMAIL ✓] OTP sent to {to_email} ({purpose})")
        return True
    except smtplib.SMTPAuthenticationError:
        print("[EMAIL ✗] Gmail authentication failed.")
        return False
    except smtplib.SMTPException as e:
        print(f"[EMAIL ✗] SMTP error: {e}")
        return False
    except Exception as e:
        print(f"[EMAIL ✗] Unexpected error: {e}")
        return False


def mask_email(email):
    local, domain = email.split("@")
    return local[:2] + "****@" + domain


def user_by_email(email):
    c = db(); cur = c.cursor()
    cur.execute("SELECT id,username,email,password FROM users WHERE email=%s", (email,))
    row = cur.fetchone(); cur.close(); c.close()
    return row


# ================================================================
# ─── REGISTER ─────────────────────────────────────────────────
# ================================================================

@app.route("/register/send-otp", methods=["POST"])
def register_send_otp():
    d        = request.json or {}
    username = d.get("username","").strip()
    email    = d.get("email","").strip().lower()
    password = d.get("password","")

    if len(username) < 2:
        return jsonify(error="Username must be at least 2 characters."), 400
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        return jsonify(error="Enter a valid email address."), 400
    if len(password) < 6:
        return jsonify(error="Password must be at least 6 characters."), 400

    if user_by_email(email):
        return jsonify(error="This email is already registered. Please log in."), 409

    otp  = otp_create("register", email)
    sent = send_otp_email(email, otp, "register", username)
    if not sent:
        return jsonify(error="Could not send OTP email. Check GMAIL_SENDER and GMAIL_PASSWORD."), 500

    session["reg"] = {"username": username, "email": email, "password": password}
    return jsonify(ok=True, masked=mask_email(email))


@app.route("/register/verify-otp", methods=["POST"])
def register_verify_otp():
    d     = request.json or {}
    inp   = d.get("otp","").strip()
    reg   = session.get("reg")
    if not reg:
        return jsonify(error="Session expired. Please start again."), 400

    status = otp_verify("register", reg["email"], inp)
    if status != "ok":
        return jsonify(error=OTP_MSG[status]), 400

    try:
        c = db(); cur = c.cursor()
        cur.execute("INSERT INTO users (username,email,password) VALUES (%s,%s,%s)",
                    (reg["username"], reg["email"], reg["password"]))
        uid = cur.lastrowid; cur.close(); c.close()
    except mysql.connector.IntegrityError:
        return jsonify(error="Email already registered."), 409

    session.pop("reg", None)
    session["uid"]      = uid
    session["username"] = reg["username"]
    return jsonify(ok=True, message="Account created! Logging you in...")


@app.route("/register/resend-otp", methods=["POST"])
def register_resend():
    reg = session.get("reg")
    if not reg: return jsonify(error="Session expired."), 400
    otp  = otp_create("register", reg["email"])
    sent = send_otp_email(reg["email"], otp, "register", reg["username"])
    return jsonify(ok=sent, message="New OTP sent." if sent else "Failed to send.")


# ================================================================
# ─── LOGIN ────────────────────────────────────────────────────
# ================================================================

@app.route("/login/send-otp", methods=["POST"])
def login_send_otp():
    d        = request.json or {}
    email    = d.get("email","").strip().lower()
    password = d.get("password","")

    if not email or not password:
        return jsonify(error="Email and password are required."), 400

    u = user_by_email(email)
    if not u or u[3] != password:
        return jsonify(error="Incorrect email or password."), 401

    uid, username, _, _ = u
    otp  = otp_create("login", email)
    sent = send_otp_email(email, otp, "login", username)
    if not sent:
        return jsonify(error="Could not send OTP email. Check GMAIL_SENDER and GMAIL_PASSWORD."), 500

    session["pre"] = {"uid": uid, "username": username, "email": email}
    return jsonify(ok=True, masked=mask_email(email), username=username)


@app.route("/login/verify-otp", methods=["POST"])
def login_verify_otp():
    d    = request.json or {}
    inp  = d.get("otp","").strip()
    pre  = session.get("pre")
    if not pre: return jsonify(error="Session expired. Please log in again."), 400

    status = otp_verify("login", pre["email"], inp)
    if status != "ok":
        return jsonify(error=OTP_MSG[status]), 400

    session.pop("pre", None)
    session["uid"]      = pre["uid"]
    session["username"] = pre["username"]
    return jsonify(ok=True, message="Login successful.")


@app.route("/login/resend-otp", methods=["POST"])
def login_resend():
    pre = session.get("pre")
    if not pre: return jsonify(error="Session expired."), 400
    otp  = otp_create("login", pre["email"])
    sent = send_otp_email(pre["email"], otp, "login", pre["username"])
    return jsonify(ok=sent, message="New OTP sent." if sent else "Failed to send.")


# ================================================================
# ─── FORGOT PASSWORD ──────────────────────────────────────────
# ================================================================

@app.route("/forgot/send-otp", methods=["POST"])
def forgot_send_otp():
    d     = request.json or {}
    email = d.get("email","").strip().lower()
    if not email or "@" not in email:
        return jsonify(error="Enter a valid email address."), 400

    u = user_by_email(email)
    if u:
        otp = otp_create("reset", email)
        send_otp_email(email, otp, "reset", u[1])
        session["reset_email"] = email

    return jsonify(ok=True, masked=mask_email(email))


@app.route("/forgot/verify-otp", methods=["POST"])
def forgot_verify_otp():
    d     = request.json or {}
    inp   = d.get("otp","").strip()
    email = session.get("reset_email")
    if not email: return jsonify(error="Session expired."), 400

    status = otp_verify("reset", email, inp)
    if status != "ok":
        return jsonify(error=OTP_MSG[status]), 400

    session["reset_ok"] = email
    return jsonify(ok=True)


@app.route("/forgot/reset-password", methods=["POST"])
def forgot_reset():
    d        = request.json or {}
    password = d.get("password","")
    email    = session.get("reset_ok")
    if not email: return jsonify(error="Unauthorized. Complete OTP verification first."), 403
    if len(password) < 6: return jsonify(error="Password must be at least 6 characters."), 400

    c = db(); cur = c.cursor()
    cur.execute("UPDATE users SET password=%s WHERE email=%s", (password, email))
    cur.close(); c.close()
    session.pop("reset_ok", None); session.pop("reset_email", None)
    return jsonify(ok=True, message="Password updated. You can now log in.")


@app.route("/forgot/resend-otp", methods=["POST"])
def forgot_resend():
    email = session.get("reset_email")
    if not email: return jsonify(error="Session expired."), 400
    u = user_by_email(email)
    if u:
        otp = otp_create("reset", email)
        send_otp_email(email, otp, "reset", u[1])
    return jsonify(ok=True, message="New OTP sent.")


# ================================================================
# ─── SESSION UTILS ────────────────────────────────────────────
# ================================================================

@app.route("/auth/me")
def auth_me():
    if "uid" not in session:
        return jsonify(logged_in=False, username=None)
    return jsonify(logged_in=True, username=session.get("username"))


@app.route("/auth/logout")
def auth_logout():
    session.clear()
    return jsonify(ok=True)


# ================================================================
# ─── TEST EMAIL ───────────────────────────────────────────────
# ================================================================
@app.route("/test-email")
def test_email():
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=8) as s:
            s.login(GMAIL_SENDER, GMAIL_PASSWORD)
        test_otp = str(random.randint(100000, 999999))
        sent = send_otp_email(GMAIL_SENDER, test_otp, "register", "Test User")
        if sent:
            return jsonify(ok=True, message=f"✅ Email sent to {GMAIL_SENDER}. Check your inbox!", sender=GMAIL_SENDER)
        else:
            return jsonify(ok=False, error="Login OK but send failed. Check terminal logs."), 500
    except smtplib.SMTPAuthenticationError:
        return jsonify(ok=False, step="authentication", error="Gmail App Password is wrong."), 401
    except Exception as e:
        return jsonify(ok=False, step="unknown", error=str(e)), 500


# ================================================================
# ─── FRONTEND ROUTES ─────────────────────────────────────────
# ================================================================

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/index.html")
def index_alias():
    return render_template("index.html")

@app.route("/login.html")
def login_page():
    return render_template("login.html")

@app.route("/register.html")
def register_page():
    return render_template("register.html")

@app.route("/forgot_password.html")
def forgot_page():
    return render_template("forgot_password.html")

@app.route("/portfolio.html")
def portfolio():
    return render_template("portfolio.html")

@app.route("/manage.html")
def manage():
    return render_template("manage.html")


# ================================================================
# ─── CONTACT FORM EMAIL ──────────────────────────────────────
# ================================================================

CONTACT_RECEIVER = os.environ.get("CONTACT_RECEIVER", "reportsservice4999@gmail.com")

@app.route("/send-contact", methods=["POST"])
def send_contact():
    try:
        d       = request.json or {}
        fname   = d.get("fname","").strip()
        lname   = d.get("lname","").strip()
        email   = d.get("email","").strip()
        subject = d.get("subject","").strip() or "New Contact Message — ServiceReport Pro"
        message = d.get("message","").strip()

        if not fname or not email or not message:
            return jsonify(error="Missing required fields."), 400

        full_name = f"{fname} {lname}".strip()

        html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#09131f;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#09131f;padding:40px 0;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#0f1c2e;
  border-radius:16px;overflow:hidden;border:1px solid rgba(255,255,255,0.07);">
  <tr><td style="background:#162236;padding:24px 36px;border-bottom:1px solid rgba(255,255,255,0.07);">
    <span style="font-size:20px;font-weight:800;color:#fff;">ServiceReport <span style="color:#e8a04a;">Pro</span></span>
    <span style="font-size:12px;color:#8aa0b8;margin-left:12px;">New Contact Message</span>
  </td></tr>
  <tr><td style="padding:32px 36px;">
    <div style="background:#1e3352;border-radius:10px;padding:20px 24px;margin-bottom:24px;">
      <table width="100%" cellpadding="4" cellspacing="0">
        <tr><td style="font-size:11px;color:#8aa0b8;">From</td><td style="font-size:14px;font-weight:700;color:#fff;text-align:right;">{full_name}</td></tr>
        <tr><td style="font-size:11px;color:#8aa0b8;">Email</td><td style="font-size:14px;color:#e8a04a;text-align:right;">{email}</td></tr>
        <tr><td style="font-size:11px;color:#8aa0b8;">Subject</td><td style="font-size:14px;color:#fff;text-align:right;">{subject}</td></tr>
      </table>
    </div>
    <div style="font-size:11px;color:#8aa0b8;margin-bottom:10px;">MESSAGE</div>
    <div style="background:#1e3352;border-left:3px solid #e8a04a;border-radius:0 8px 8px 0;
      padding:18px 20px;font-size:14px;color:#e2e8f0;line-height:1.8;white-space:pre-wrap;">{message}</div>
  </td></tr>
  <tr><td style="background:#09131f;padding:16px 36px;font-size:11px;color:rgba(255,255,255,0.2);text-align:center;">
    © 2026 ServiceReport Pro · Pune, India
  </td></tr>
</table>
</td></tr>
</table>
</body></html>"""

        msg = MIMEMultipart("alternative")
        msg["Subject"]  = f"📩 Contact: {subject} — {full_name}"
        msg["From"]     = f"ServiceReport Pro <{GMAIL_SENDER}>"
        msg["To"]       = CONTACT_RECEIVER
        msg["Reply-To"] = email
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=12) as s:
            s.login(GMAIL_SENDER, GMAIL_PASSWORD)
            s.sendmail(GMAIL_SENDER, CONTACT_RECEIVER, msg.as_string())

        return jsonify(ok=True, message="Message sent successfully.")
    except smtplib.SMTPAuthenticationError:
        return jsonify(error="Gmail authentication failed."), 500
    except Exception as e:
        return jsonify(error=str(e)), 500


# ================================================================
# ─── SEND REPORT EMAIL ───────────────────────────────────────
# ================================================================

@app.route("/send-report-email", methods=["POST"])
def send_report_email():
    try:
        data       = request.json or {}
        from_name  = data.get("from_name", "").strip()
        to_email   = data.get("to_email", "").strip().lower()
        cc_email   = data.get("cc_email", "").strip().lower()
        subject    = data.get("subject", "Service Report").strip()
        report_id  = data.get("report_id")
        message    = data.get("message", "").strip()

        if not to_email or not report_id:
            return jsonify(error="Recipient email and report ID are required."), 400

        c = db(); cur = c.cursor()
        cur.execute("SELECT id, title, content, created_at FROM reports WHERE id=%s", (report_id,))
        row = cur.fetchone(); cur.close(); c.close()

        if not row:
            return jsonify(error="Report not found."), 404

        rid, title, content, created_at = row
        date_str = created_at.strftime("%d %B %Y") if created_at else ""

        html = build_report_email_html(title, content, date_str, from_name, message)
        text = build_report_email_text(title, content, date_str, from_name, message)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject or f"Service Report — {title}"
        msg["From"]    = f"{from_name or APP_NAME} <{GMAIL_SENDER}>"
        msg["To"]      = to_email
        if cc_email:
            msg["Cc"]  = cc_email

        msg.attach(MIMEText(text, "plain"))
        msg.attach(MIMEText(html, "html"))

        recipients = [to_email] + ([cc_email] if cc_email else [])

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=12) as s:
            s.login(GMAIL_SENDER, GMAIL_PASSWORD)
            s.sendmail(GMAIL_SENDER, recipients, msg.as_string())

        return jsonify(ok=True, message=f"Report sent to {to_email} successfully.")
    except smtplib.SMTPAuthenticationError:
        return jsonify(error="Gmail authentication failed."), 500
    except Exception as e:
        return jsonify(error=f"Failed to send email: {str(e)}"), 500


def parse_report_content(content):
    lines = (content or "").split("\n")
    fields = {}
    faults = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("─") or line.startswith("Report "):
            continue
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip().lower().replace(" ", "_")
            val = val.strip()
            if key == "faults":
                faults = [f.strip() for f in val.split(",") if f.strip()]
            else:
                fields[key] = val
    fields["faults"] = faults
    return fields


def build_report_email_html(title, content, date_str, sender_name, message):
    f = parse_report_content(content)
    faults_html = "".join(
        f'<span style="display:inline-block;background:#fff3cd;border:1px solid #f59e0b;color:#92400e;'
        f'border-radius:20px;font-size:11px;font-weight:700;padding:3px 12px;margin:2px 4px 2px 0">{fault}</span>'
        for fault in f.get("faults", [])
    ) or '<span style="color:#94a3b8;font-style:italic;">None recorded</span>'

    def row(label, value):
        val = value or "—"
        return (
            f'<tr>'
            f'<td style="padding:8px 12px;font-size:11px;font-weight:700;color:#64748b;'
            f'text-transform:uppercase;letter-spacing:1px;width:38%;border-bottom:1px solid #f1f5f9;">{label}</td>'
            f'<td style="padding:8px 12px;font-size:13px;color:#0f172a;border-bottom:1px solid #f1f5f9;">{val}</td>'
            f'</tr>'
        )

    def section(label, body_html):
        return (
            f'<div style="margin-bottom:22px;">'
            f'<div style="background:#fff8ee;border-left:4px solid #e8a04a;padding:7px 14px;'
            f'font-size:10px;font-weight:800;color:#92400e;letter-spacing:2px;'
            f'text-transform:uppercase;margin-bottom:10px;">{label}</div>'
            f'{body_html}'
            f'</div>'
        )

    msg_block = (
        f'<div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;'
        f'padding:14px 18px;margin-bottom:24px;font-size:13px;color:#0c4a6e;line-height:1.7;">'
        f'<strong style="color:#0369a1;">{sender_name or "The sender"} writes:</strong><br>{message}</div>'
        if message else ""
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#09131f;font-family:Arial,Helvetica,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#09131f;padding:40px 0;">
<tr><td align="center">
<table width="620" cellpadding="0" cellspacing="0" style="max-width:620px;width:100%;">
  <tr><td style="background:#0f1c2e;border-radius:16px 16px 0 0;padding:28px 36px;border-bottom:1px solid rgba(255,255,255,0.08);">
    <table width="100%"><tr>
      <td><div style="font-size:20px;font-weight:800;color:#fff;">ServiceReport <span style="color:#e8a04a;">Pro</span></div></td>
      <td align="right"><div style="background:#e8a04a;color:#0f1c2e;font-size:10px;font-weight:800;padding:6px 14px;border-radius:6px;">SERVICE REPORT</div></td>
    </tr></table>
  </td></tr>
  <tr><td style="background:#ffffff;padding:36px;">
    {msg_block}
    <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:16px 20px;margin-bottom:24px;">
      <div style="font-size:17px;font-weight:800;color:#0f172a;">{title or "Service Report"}</div>
      <div style="font-size:12px;color:#64748b;margin-top:4px;">📅 {date_str}</div>
    </div>
    {section("Customer Details",
        f'<table width="100%" style="border-collapse:collapse;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">'
        + row("Customer Name", f.get("customer",""))
        + row("Address", f.get("address",""))
        + row("City", f.get("city",""))
        + row("UPS Model", f.get("model") or f.get("ups_model",""))
        + row("KVA Rating", f.get("kva",""))
        + "</table>"
    )}
    {section("Type of Fault", f'<div style="padding:8px 0;">{faults_html}</div>')}
    {section("Observation",
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px 16px;font-size:13px;color:#0f172a;line-height:1.8;">{f.get("observation","") or "—"}</div>'
    )}
    {section("Action Taken",
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px 16px;font-size:13px;color:#0f172a;line-height:1.8;">{f.get("action_taken","") or "—"}</div>'
    )}
    {section("Maintenance Readings",
        f'<table width="100%" style="border-collapse:collapse;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">'
        + row("Input Voltage", f.get("input_voltage",""))
        + row("Output Voltage", f.get("output_voltage",""))
        + row("Fan Status", f.get("fan_status",""))
        + "</table>"
    )}
    {section("Signatures",
        f'<table width="100%" style="border-collapse:collapse;border:1px solid #e2e8f0;border-radius:8px;overflow:hidden;">'
        + row("Engineer", f.get("engineer",""))
        + row("Customer", f.get("customer",""))
        + row("Date", f.get("date", date_str))
        + "</table>"
    )}
  </td></tr>
  <tr><td style="background:#0f1c2e;padding:20px 36px;border-radius:0 0 16px 16px;">
    <table width="100%"><tr>
      <td style="font-size:12px;color:#8aa0b8;">Sent via <strong style="color:#e8a04a;">{APP_NAME}</strong> · Pune, India</td>
      <td align="right" style="font-size:11px;color:rgba(255,255,255,0.25);">Generated: {datetime.now().strftime("%d %b %Y, %I:%M %p")}</td>
    </tr></table>
  </td></tr>
</table>
</td></tr></table>
</body></html>"""


def build_report_email_text(title, content, date_str, sender_name, message):
    f = parse_report_content(content)
    lines = [
        f"SERVICE REPORT — {APP_NAME}", "=" * 50,
        f"Title  : {title}", f"Date   : {date_str}", "",
    ]
    if message:
        lines += [f"Message from {sender_name or 'sender'}:", message, ""]
    lines += [
        "CUSTOMER DETAILS", "-" * 30,
        f"Customer : {f.get('customer','—')}", f"Address  : {f.get('address','—')}",
        f"City     : {f.get('city','—')}", f"Model    : {f.get('model') or f.get('ups_model','—')}",
        f"KVA      : {f.get('kva','—')}", "",
        "FAULT TYPE", "-" * 30, ", ".join(f.get("faults", [])) or "None", "",
        "OBSERVATION", "-" * 30, f.get("observation","—"), "",
        "ACTION TAKEN", "-" * 30, f.get("action_taken","—"), "",
        "MAINTENANCE", "-" * 30,
        f"Input Voltage  : {f.get('input_voltage','—')}",
        f"Output Voltage : {f.get('output_voltage','—')}",
        f"Fan Status     : {f.get('fan_status','—')}", "",
        "SIGNATURES", "-" * 30,
        f"Engineer : {f.get('engineer','—')}", f"Customer : {f.get('customer','—')}",
        f"Date     : {f.get('date', date_str)}", "",
        "=" * 50, f"Sent via {APP_NAME} · Pune, India",
    ]
    return "\n".join(lines)


# ================================================================
# ─── REPORTS ─────────────────────────────────────────────────
# ================================================================

@app.route("/save-report", methods=["POST"])
def save_report():
    d = request.json or {}
    c = db(); cur = c.cursor()
    cur.execute("INSERT INTO reports(title,content,created_at) VALUES(%s,%s,%s)",
                (d.get("title"), d.get("reportData"), datetime.now()))
    cur.close(); c.close()
    return "Saved ✅"

@app.route("/get-reports")
def get_reports():
    c = db(); cur = c.cursor()
    cur.execute("SELECT * FROM reports ORDER BY id DESC")
    rows = cur.fetchall(); cur.close(); c.close()
    return jsonify([{"id":r[0],"title":r[1],"content":r[2],"date":str(r[3])} for r in rows])

@app.route("/delete-report/<int:rid>", methods=["DELETE"])
def delete_report(rid):
    c = db(); cur = c.cursor()
    cur.execute("DELETE FROM reports WHERE id=%s",(rid,))
    cur.close(); c.close(); return "Deleted"

@app.route("/update-report/<int:rid>", methods=["PUT"])
def update_report(rid):
    d = request.json or {}
    c = db(); cur = c.cursor()
    cur.execute("UPDATE reports SET title=%s,content=%s WHERE id=%s",
                (d.get("title"),d.get("reportData"),rid))
    cur.close(); c.close(); return "Updated"

@app.route("/duplicate-report/<int:rid>", methods=["POST"])
def duplicate_report(rid):
    c = db(); cur = c.cursor()
    cur.execute("SELECT title,content FROM reports WHERE id=%s",(rid,))
    row = cur.fetchone()
    if not row: return "Not found", 404
    cur.execute("INSERT INTO reports(title,content,created_at) VALUES(%s,%s,NOW())",
                (row[0]+" (Copy)", row[1]))
    cur.close(); c.close(); return "Copied"


# ================================================================
# ✅ FIX 4: Only ONE startup block — removed the duplicate
# ================================================================
if __name__ == "__main__":
    init_db()
    port = int(os.environ.get("PORT", 5000))   # Render gives its own PORT
    print(f"\n  {APP_NAME} running on port {port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
