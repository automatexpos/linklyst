import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, abort, jsonify, Response
)
from dotenv import load_dotenv
from requests_oauthlib import OAuth2Session
import bcrypt
from supabase import create_client, Client
import cloudinary
import cloudinary.uploader
import cloudinary.api

load_dotenv()

# Allow insecure transport for local development (HTTP instead of HTTPS)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

APP_SECRET = os.getenv("FLASK_SECRET_KEY", "dev_secret")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SITE_BASE = os.getenv("SITE_BASE", "http://localhost:5000")

# Google OAuth configuration  
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "99509622971-ojflcvsc9667aveghpt3qk8qmna6jlks.apps.googleusercontent.com")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "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")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:5000/auth/google/callback")

GOOGLE_AUTHORIZATION_BASE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# Cloudinary configuration
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Set SUPABASE_URL and SUPABASE_KEY in .env")

if CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET
    )

app = Flask(__name__, static_folder="static", template_folder="templates")
app.secret_key = APP_SECRET

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Domain redirection for production - DISABLED TO FIX REDIRECT LOOP
# @app.before_request
# def enforce_domain():
#     """Redirect www to non-www domain for SEO consistency"""
#     # Only apply redirects if we're on the production domain
#     if request.host and 'linklyst.space' in request.host:
#         if request.host == 'www.linklyst.space':
#             return redirect(request.url.replace('www.linklyst.space', 'linklyst.space'), code=301)
#     
#     # No HTTPS redirect needed - Vercel handles this automatically

@app.before_request
def check_trial_expiration():
    """Check if user's trial has expired and disable account if necessary"""
    # Skip check for public routes
    public_routes = ['index', 'login', 'register', 'public_profile', 'public_category_direct', 
                    'public_subcategory_direct', 'robots_txt', 'sitemap_xml', 'username_redirect',
                    'privacy_policy', 'terms_of_service', 'api_stats']
    
    if request.endpoint in public_routes or request.endpoint is None:
        return
        
    # Skip check for static files and auth routes
    if request.path.startswith('/static/') or request.path.startswith('/auth/'):
        return
    
    user_id = session.get("user_id")
    if not user_id:
        return  # Not logged in
    
    try:
        # Get current user
        user_res = supabase.table("users").select("*").eq("id", user_id).execute()
        if not user_res.data:
            return
            
        user = user_res.data[0]
        
        # Check if user is on trial and if trial has expired
        if user.get("is_trial") and user.get("trial_end"):
            from datetime import datetime
            trial_end = datetime.fromisoformat(user["trial_end"].replace('Z', '+00:00'))
            
            if datetime.utcnow().replace(tzinfo=trial_end.tzinfo) > trial_end:
                # Trial has expired, disable account
                supabase.table("users").update({
                    "is_active": False,
                    "is_trial": False,
                    "subscription_status": "expired"
                }).eq("id", user_id).execute()
                
                session.clear()
                flash("Your 7-day free trial has expired. Please upgrade to continue using Linklyst.", "warning")
                return redirect(url_for("index"))
                
    except Exception as e:
        print(f"Error checking trial expiration: {e}")
        # Don't block the user if there's an error, just log it
        pass

# --- helpers ---
def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    res = supabase.table("users").select("*").eq("id", uid).execute()
    if not res.data:
        return None
    user = res.data[0]
    # Check if user account is active
    if not user.get("is_active", True):
        # Clear session for inactive users
        session.pop("user_id", None)
        return None
    return user

@app.context_processor
def inject_user():
    return dict(user=current_user(), trial_info=get_trial_info())

def get_trial_info():
    """Get trial information for the current user"""
    user = current_user()
    if not user:
        return None
        
    if not user.get("is_trial"):
        return {"is_trial": False, "is_active": user.get("is_active", True)}
    
    try:
        from datetime import datetime
        trial_end = datetime.fromisoformat(user["trial_end"].replace('Z', '+00:00'))
        now = datetime.utcnow().replace(tzinfo=trial_end.tzinfo)
        days_left = (trial_end - now).days
        
        return {
            "is_trial": True,
            "trial_end": trial_end,
            "days_left": max(0, days_left),
            "hours_left": max(0, (trial_end - now).seconds // 3600) if days_left == 0 else 0,
            "is_expired": now > trial_end
        }
    except Exception as e:
        print(f"Error calculating trial info: {e}")
        return {"is_trial": False, "is_active": user.get("is_active", True)}

def normalize_url(url):
    """Ensure URL has proper protocol prefix"""
    if not url:
        return url
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        # Add https:// by default for security
        url = 'https://' + url
    return url

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user:
            # Check if there was a user_id in session but no active user returned
            # This means the account was deactivated
            if session.get("user_id"):
                flash("Your account is not active. Please contact support.", "danger")
                session.pop("user_id", None)
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return wrapper

def get_user_analytics(user_id):
    """Get comprehensive analytics for a user"""
    try:
        # Get total links count
        links_res = supabase.table("links").select("id", count="exact").eq("user_id", user_id).execute()
        total_links = links_res.count or 0
        
        # Get total clicks count from clicks table
        if total_links > 0:
            # Get all link IDs for this user
            user_links = supabase.table("links").select("id").eq("user_id", user_id).execute()
            user_link_ids = [link["id"] for link in user_links.data] if user_links.data else []
            
            # Count clicks for user's links
            if user_link_ids:
                clicks_res = supabase.table("clicks").select("id", count="exact").in_("link_id", user_link_ids).execute()
                total_clicks = clicks_res.count or 0
            else:
                total_clicks = 0
        else:
            total_clicks = 0
        
        # Get categories count
        try:
            categories_res = supabase.table("categories").select("id", count="exact").eq("user_id", user_id).execute()
            categories_count = categories_res.count or 0
        except:
            categories_count = 0
        
        # Get subcategories count
        try:
            subcategories_res = supabase.table("subcategories").select("id", count="exact").eq("user_id", user_id).execute()
            subcategories_count = subcategories_res.count or 0
        except:
            subcategories_count = 0
        
        # Get trending links (top 2 links with highest click counts)
        trending_links = []
        if total_links > 0:
            try:
                # Get all links with their details
                all_links = supabase.table("links").select("*").eq("user_id", user_id).execute()
                link_stats = []
                
                for link in all_links.data:
                    clicks_res = supabase.table("clicks").select("id", count="exact").eq("link_id", link["id"]).execute()
                    click_count = clicks_res.count or 0
                    
                    link_stats.append({
                        "title": link["title"],
                        "url": link["url"],
                        "clicks": click_count,
                        "id": link["id"]
                    })
                
                # Sort by clicks and get top 2
                link_stats.sort(key=lambda x: x["clicks"], reverse=True)
                trending_links = link_stats[:2]
                
            except Exception as e:
                pass  # Skip trending links if error occurs
        
        return {
            "total_links": total_links,
            "total_clicks": total_clicks,
            "categories_count": categories_count,
            "subcategories_count": subcategories_count,
            "trending_links": trending_links
        }
        
    except Exception as e:
        # Return empty stats if there's an error
        return {
            "total_links": 0,
            "total_clicks": 0,
            "categories_count": 0,
            "subcategories_count": 0,
            "trending_links": []
        }

@app.template_filter("datetimefmt")
def datetimefmt(value, fmt="%Y-%m-%d %H:%M"):
    if not value:
        return ""
    # supabase returns iso string
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except:
            return value
    return value.strftime(fmt)

# --- Routes ---
@app.route("/")
def index():
    # Show public marketing homepage
    return render_template("index.html")

# --- Auth ---
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")
    email = request.form.get("email","").strip().lower()
    username = request.form.get("username","").strip().lower()
    password = request.form.get("password","")
    if not email or not username or not password:
        flash("Fill all fields","danger")
        return redirect(url_for("register"))
    pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Calculate trial end date (7 days from now)
    from datetime import datetime, timedelta
    trial_start = datetime.utcnow()
    trial_end = trial_start + timedelta(days=7)
    
    # insert user with trial information
    res = supabase.table("users").insert({
        "email": email,
        "username": username,
        "password_hash": pw_hash,
        "is_active": True,  # Active during trial
        "trial_start": trial_start.isoformat(),
        "trial_end": trial_end.isoformat(),
        "is_trial": True,
        "subscription_status": "trial"
    }).execute()
    if res.data == []:
        flash("Email or username already taken","danger")
        return redirect(url_for("register"))
    user_id = res.data[0]["id"]
    supabase.table("profiles").insert({
        "user_id": user_id,
        "display_name": username
    }).execute()
    flash(f"Account created successfully! Your 7-day free trial is now active until {trial_end.strftime('%B %d, %Y')}.","success")
    return redirect(url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")
    email = request.form.get("email","").strip().lower()
    password = request.form.get("password","")
    
    res = supabase.table("users").select("*").eq("email", email).execute()
    if not res.data:
        flash("Invalid credentials","danger")
        return redirect(url_for("login"))
    user = res.data[0]
    
    # Check if user signed up with Google (no password)
    if user["password_hash"] is None:
        flash("This account was created with Google. Please use 'Login with Google' button.", "info")
        return redirect(url_for("login"))
    
    if not bcrypt.checkpw(password.encode('utf-8'), user["password_hash"].encode('utf-8')):
        flash("Invalid credentials","danger")
        return redirect(url_for("login"))
    
    # Check if account is active
    if not user.get("is_active", True):
        flash("Your account is not active. Please contact support.", "danger")
        return redirect(url_for("login"))
    
    session["user_id"] = user["id"]
    flash("Logged in","success")
    next_url = request.args.get("next") or url_for("dashboard")
    return redirect(next_url)

@app.route("/logout", methods=["GET","POST"])
def logout():
    if request.method == "GET":
        return render_template("confirm_logout.html")
    session.pop("user_id", None)
    flash("Logged out","info")
    return redirect(url_for("index"))

# --- Google OAuth Routes ---
@app.route("/auth/google")
def google_login():
    """Initiate Google OAuth login"""
    if not CLIENT_ID or not CLIENT_SECRET:
        flash("Google OAuth not configured. Please contact administrator.", "danger")
        return redirect(url_for("login"))
    
    # Use dynamic redirect URI based on current request
    redirect_uri = url_for('google_callback', _external=True)
    
    google = OAuth2Session(
        CLIENT_ID, 
        redirect_uri=redirect_uri, 
        scope=["openid", "email", "profile"]
    )
    authorization_url, state = google.authorization_url(
        GOOGLE_AUTHORIZATION_BASE_URL, 
        access_type="offline", 
        prompt="select_account"
    )
    session["oauth_state"] = state
    return redirect(authorization_url)

@app.route("/auth/google/callback")
def google_callback():
    """Handle Google OAuth callback"""
    # Check if there's an error from Google
    if 'error' in request.args:
        error = request.args.get('error')
        error_description = request.args.get('error_description', 'Unknown error')
        flash(f"Google authentication failed: {error_description}", "danger")
        return redirect(url_for("login"))
    
    # Check if oauth_state exists in session
    if "oauth_state" not in session:
        flash("OAuth session expired. Please try again.", "danger")
        return redirect(url_for("login"))
    
    try:
        # Use dynamic redirect URI based on current request  
        redirect_uri = url_for('google_callback', _external=True)
        
        google = OAuth2Session(
            CLIENT_ID, 
            redirect_uri=redirect_uri, 
            state=session["oauth_state"]
        )
        
        token = google.fetch_token(
            GOOGLE_TOKEN_URL, 
            client_secret=CLIENT_SECRET, 
            authorization_response=request.url,
            include_client_id=True
        )
        
        # Get user info from Google
        user_info_response = google.get(GOOGLE_USER_INFO_URL)
        
        if user_info_response.status_code != 200:
            flash("Failed to get user information from Google.", "danger")
            return redirect(url_for("login"))
            
        user_info = user_info_response.json()
        
        google_id = user_info.get("id")
        email = user_info.get("email", "").lower().strip()
        name = user_info.get("name", "")
        
        if not email or not google_id:
            flash("Failed to get user information from Google.", "danger")
            return redirect(url_for("login"))
        
        # Check if user exists with this Google ID
        existing_user = supabase.table("users").select("*").eq("google_id", google_id).execute()
        
        if existing_user.data:
            # User exists with Google ID, check if account is active
            user = existing_user.data[0]
            if not user.get("is_active", True):
                flash("Your account is not active. Please contact support.", "danger")
                return redirect(url_for("login"))
            
            session["user_id"] = user["id"]
            session.pop("oauth_state", None)
            flash(f"Welcome back, {name}!", "success")
            return redirect(url_for("dashboard"))
        
        # Check if user exists with this email (traditional signup)
        email_user = supabase.table("users").select("*").eq("email", email).execute()
        
        if email_user.data:
            # User exists with email but no Google ID, check if account is active
            user = email_user.data[0]
            if not user.get("is_active", True):
                flash("Your account is not active. Please contact support.", "danger")
                return redirect(url_for("login"))
            
            # Link the Google account
            supabase.table("users").update({
                "google_id": google_id
            }).eq("id", user["id"]).execute()
            
            session["user_id"] = user["id"]
            session.pop("oauth_state", None)
            flash(f"Google account linked successfully! Welcome back, {name}!", "success")
            return redirect(url_for("dashboard"))
        
        # New user, create account
        # Generate username from email or name
        username = email.split('@')[0].lower()
        
        # Check if username exists and make it unique
        username_check = supabase.table("users").select("username").eq("username", username).execute()
        counter = 1
        original_username = username
        while username_check.data:
            username = f"{original_username}{counter}"
            username_check = supabase.table("users").select("username").eq("username", username).execute()
            counter += 1
        
        # Calculate trial end date (7 days from now)
        from datetime import datetime, timedelta
        trial_start = datetime.utcnow()
        trial_end = trial_start + timedelta(days=7)
        
        # Create new user with Google authentication and trial
        new_user = supabase.table("users").insert({
            "email": email,
            "username": username,
            "google_id": google_id,
            "password_hash": None,  # No password for OAuth users
            "is_active": True,  # Active during trial
            "trial_start": trial_start.isoformat(),
            "trial_end": trial_end.isoformat(),
            "is_trial": True,
            "subscription_status": "trial"
        }).execute()
        
        if not new_user.data:
            flash("Failed to create account. Please try again.", "danger")
            return redirect(url_for("register"))
        
        user_id = new_user.data[0]["id"]
        
        # Create profile
        supabase.table("profiles").insert({
            "user_id": user_id,
            "display_name": name or username
        }).execute()
        
        session.pop("oauth_state", None)
        flash(f"Account created successfully! Please wait for the confirmation to use your account.", "info")
        return redirect(url_for("login"))
        
    except Exception as e:
        import traceback
        print(f"OAuth error: {str(e)}")
        print(f"Full traceback: {traceback.format_exc()}")
        flash(f"Authentication failed: {str(e)}", "danger")
        return redirect(url_for("login"))

# --- Dashboard ---
@app.route("/dashboard")
@login_required
def dashboard():
    u = current_user()
    profile = supabase.table("profiles").select("*").eq("user_id", u["id"]).execute().data[0]
    
    # Check for pending upgrade request
    try:
        pending_request = supabase.table("upgrade_requests").select("*").eq("user_id", u["id"]).eq("status", "pending").execute()
        u["pending_upgrade_request"] = len(pending_request.data) > 0
    except Exception as e:
        # If upgrade_requests table doesn't exist, assume no pending request
        u["pending_upgrade_request"] = False
    
    # Get categories for this user
    try:
        categories = supabase.table("categories").select("*").eq("user_id", u["id"]).eq("is_active", True).order("sort_order").execute().data
        
        # Get subcategory count and direct links count for each category
        for category in categories:
            subcategory_count = supabase.table("subcategories").select("id", count="exact").eq("category_id", category["id"]).eq("is_active", True).execute().count
            category["subcategory_count"] = subcategory_count or 0
            
            # Get direct links count (links directly attached to category)
            direct_links_count = supabase.table("links").select("id", count="exact").eq("category_id", category["id"]).eq("is_active", True).execute().count
            category["direct_links_count"] = direct_links_count or 0
            
    except Exception as e:
        # If categories table doesn't exist yet, fall back to empty list
        categories = []
        flash("Please apply the database schema to use the category system.", "info")
    
    # Get analytics data
    analytics = get_user_analytics(u["id"])
    return render_template("dashboard.html", user=u, profile=profile, categories=categories, analytics=analytics, site_base=SITE_BASE)

# --- Categories ---
@app.route("/categories")
@login_required
def categories():
    u = current_user()
    categories = supabase.table("categories").select("*").eq("user_id", u["id"]).eq("is_active", True).order("sort_order").execute().data
    
    # Add subcategory count to each category
    for category in categories:
        subcategory_count = supabase.table("subcategories").select("id", count="exact").eq("category_id", category["id"]).eq("user_id", u["id"]).execute().count
        category["subcategory_count"] = subcategory_count or 0
    
    return render_template("categories.html", categories=categories, user=u)

@app.route("/category/add", methods=["POST"])
@login_required
def add_category():
    u = current_user()
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    color = request.form.get("color", "#6366f1").strip()
    icon_url = None
    
    if not name:
        flash("Category name is required", "danger")
        return redirect(url_for("dashboard"))
    
    # Handle icon file upload
    if 'icon_file' in request.files:
        icon_file = request.files['icon_file']
        if icon_file and icon_file.filename != '':
            try:
                # Upload to Cloudinary
                upload_result = cloudinary.uploader.upload(
                    icon_file,
                    folder="linktree_icons/categories",
                    transformation=[
                        {"width": 64, "height": 64, "crop": "fill"},
                        {"quality": "auto", "fetch_format": "auto"}
                    ]
                )
                icon_url = upload_result['secure_url']
            except Exception as e:
                flash(f"Failed to upload icon: {str(e)}", "danger")
                return redirect(url_for("dashboard"))
    
    try:
        # Get max sort_order
        max_res = supabase.table("categories").select("sort_order").eq("user_id", u["id"]).order("sort_order", desc=True).limit(1).execute()
        max_order = max_res.data[0]["sort_order"] if max_res.data else 0
        
        supabase.table("categories").insert({
            "user_id": u["id"],
            "name": name,
            "description": description,
            "color": color,
            "icon_url": icon_url,
            "sort_order": max_order + 1
        }).execute()
        flash("Category added successfully", "success")
    except Exception as e:
        flash("Error adding category. Name might already exist.", "danger")
    
    return redirect(url_for("dashboard"))

@app.route("/category/<int:category_id>")
@login_required
def category_subcategories(category_id):
    u = current_user()
    
    # Get category
    category_res = supabase.table("categories").select("*").eq("id", category_id).eq("user_id", u["id"]).execute()
    if not category_res.data:
        abort(404)
    category = category_res.data[0]
    
    # Get subcategories
    subcategories = supabase.table("subcategories").select("*").eq("category_id", category_id).eq("is_active", True).order("sort_order").execute().data
    
    # Add link count for each subcategory
    for subcategory in subcategories:
        link_count = supabase.table("links").select("id", count="exact").eq("subcategory_id", subcategory["id"]).execute().count
        subcategory["link_count"] = link_count or 0
    
    # Get direct links for this category (links not in subcategories)
    direct_links = supabase.table("links").select("*").eq("category_id", category_id).eq("is_active", True).order("sort_order").execute().data
    
    return render_template("subcategories.html", category=category, subcategories=subcategories, direct_links=direct_links, user=u)

# --- Subcategories ---
@app.route("/category/<int:category_id>/subcategory/add", methods=["POST"])
@login_required
def add_subcategory(category_id):
    u = current_user()
    
    # Verify category ownership
    category_res = supabase.table("categories").select("*").eq("id", category_id).eq("user_id", u["id"]).execute()
    if not category_res.data:
        abort(404)
    
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    color = request.form.get("color", "#6366f1").strip()
    icon_url = None
    
    if not name:
        flash("Subcategory name is required", "danger")
        return redirect(url_for("category_subcategories", category_id=category_id))
    
    # Handle icon file upload
    if 'icon_file' in request.files:
        icon_file = request.files['icon_file']
        if icon_file and icon_file.filename != '':
            try:
                # Upload to Cloudinary
                upload_result = cloudinary.uploader.upload(
                    icon_file,
                    folder="linktree_icons/subcategories",
                    transformation=[
                        {"width": 64, "height": 64, "crop": "fill"},
                        {"quality": "auto", "fetch_format": "auto"}
                    ]
                )
                icon_url = upload_result['secure_url']
            except Exception as e:
                flash(f"Failed to upload icon: {str(e)}", "danger")
                return redirect(url_for("category_subcategories", category_id=category_id))
    
    try:
        # Get max sort_order
        max_res = supabase.table("subcategories").select("sort_order").eq("category_id", category_id).order("sort_order", desc=True).limit(1).execute()
        max_order = max_res.data[0]["sort_order"] if max_res.data else 0
        
        supabase.table("subcategories").insert({
            "category_id": category_id,
            "user_id": u["id"],
            "name": name,
            "description": description,
            "color": color,
            "icon_url": icon_url,
            "sort_order": max_order + 1
        }).execute()
        flash("Subcategory added successfully", "success")
    except Exception as e:
        flash("Error adding subcategory. Name might already exist in this category.", "danger")
    
    return redirect(url_for("category_subcategories", category_id=category_id))

@app.route("/subcategory/<int:subcategory_id>")
@login_required
def subcategory_links(subcategory_id):
    u = current_user()
    
    # Get subcategory and verify access
    subcategory_res = supabase.table("subcategories").select("*, categories!inner(*)").eq("id", subcategory_id).eq("categories.user_id", u["id"]).execute()
    if not subcategory_res.data:
        abort(404)
    subcategory = subcategory_res.data[0]
    
    # Get links for this subcategory
    links = supabase.table("links").select("*").eq("subcategory_id", subcategory_id).order("sort_order").execute().data
    
    return render_template("subcategory_links.html", subcategory=subcategory, links=links, user=u)

# Add link to subcategory
@app.route("/subcategory/<int:subcategory_id>/link/add", methods=["POST"])
@login_required
def add_link_to_subcategory(subcategory_id):
    u = current_user()
    
    # Verify subcategory access
    subcategory_res = supabase.table("subcategories").select("*, categories!inner(*)").eq("id", subcategory_id).eq("categories.user_id", u["id"]).execute()
    if not subcategory_res.data:
        abort(404)
    
    title = request.form.get("title","").strip()
    url = request.form.get("url","").strip()
    description = request.form.get("description","").strip()
    image_url = request.form.get("image_url","").strip()
    
    if not title or not url:
        flash("Title and URL required","danger")
        return redirect(url_for("subcategory_links", subcategory_id=subcategory_id))
    
    # Normalize URL to include protocol
    url = normalize_url(url)
    
    # get max sort_order for this subcategory
    links_res = supabase.table("links").select("sort_order").eq("subcategory_id", subcategory_id).order("sort_order",desc=True).limit(1).execute()
    max_pos = links_res.data[0]["sort_order"] if links_res.data else 0
    pos = max_pos + 1
    
    link_data = {
        "user_id": u["id"],
        "subcategory_id": subcategory_id,
        "title": title,
        "url": url,
        "description": description,
        "sort_order": pos,
        "is_public": True
    }
    
    # Add image_url if provided
    if image_url:
        link_data["image_url"] = image_url
    
    try:
        print(f"DEBUG: Inserting link with data: {link_data}")  # Debug log
        result = supabase.table("links").insert(link_data).execute()
        print(f"DEBUG: Insert result: {result.data}")  # Debug log
        flash("Link added successfully","success")
    except Exception as e:
        print(f"DEBUG: Error inserting link: {str(e)}")  # Debug log
        flash("Error adding link. Please check the URL format.","danger")
        
    return redirect(url_for("subcategory_links", subcategory_id=subcategory_id))

# Add link directly to category
@app.route("/category/<int:category_id>/link/add", methods=["POST"])
@login_required
def add_link_to_category(category_id):
    u = current_user()
    
    # Verify category access
    category_res = supabase.table("categories").select("*").eq("id", category_id).eq("user_id", u["id"]).execute()
    if not category_res.data:
        abort(404)
    
    title = request.form.get("title","").strip()
    url = request.form.get("url","").strip()
    description = request.form.get("description","").strip()
    image_url = request.form.get("image_url","").strip()
    
    if not title or not url:
        flash("Title and URL required","danger")
        return redirect(url_for("category_subcategories", category_id=category_id))
    
    # Normalize URL to include protocol
    url = normalize_url(url)
    
    # get max sort_order for this category's direct links
    links_res = supabase.table("links").select("sort_order").eq("category_id", category_id).order("sort_order",desc=True).limit(1).execute()
    max_pos = links_res.data[0]["sort_order"] if links_res.data else 0
    pos = max_pos + 1
    
    link_data = {
        "user_id": u["id"],
        "category_id": category_id,
        "title": title,
        "url": url,
        "description": description,
        "sort_order": pos,
        "is_public": True
    }
    
    # Add image_url if provided
    if image_url:
        link_data["image_url"] = image_url
    
    try:
        print(f"DEBUG: Inserting category link with data: {link_data}")  # Debug log
        result = supabase.table("links").insert(link_data).execute()
        print(f"DEBUG: Insert result: {result.data}")  # Debug log
        flash("Link added successfully","success")
    except Exception as e:
        print(f"DEBUG: Error inserting category link: {str(e)}")  # Debug log
        flash("Error adding link. Please check the URL format.","danger")
        
    return redirect(url_for("category_subcategories", category_id=category_id))

# Edit and delete subcategories
@app.route("/subcategory/<int:subcategory_id>/edit", methods=["GET", "POST"])
@login_required
def edit_subcategory(subcategory_id):
    u = current_user()
    
    # Get subcategory and verify access
    subcategory_res = supabase.table("subcategories").select("*, categories!inner(*)").eq("id", subcategory_id).eq("categories.user_id", u["id"]).execute()
    if not subcategory_res.data:
        abort(404)
    subcategory = subcategory_res.data[0]
    
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        color = request.form.get("color", "#6366f1").strip()
        icon_url = subcategory.get("icon_url")
        
        if not name:
            flash("Subcategory name is required", "danger")
            return render_template("edit_subcategory.html", subcategory=subcategory, user=u)
        
        # Handle icon file upload
        if 'icon_file' in request.files:
            icon_file = request.files['icon_file']
            if icon_file and icon_file.filename != '':
                try:
                    upload_result = cloudinary.uploader.upload(
                        icon_file,
                        folder="linktree_icons/subcategories",
                        transformation=[
                            {"width": 64, "height": 64, "crop": "fill"},
                            {"quality": "auto", "fetch_format": "auto"}
                        ]
                    )
                    icon_url = upload_result['secure_url']
                except Exception as e:
                    flash(f"Failed to upload icon: {str(e)}", "danger")
                    return render_template("edit_subcategory.html", subcategory=subcategory, user=u)
        
        try:
            supabase.table("subcategories").update({
                "name": name,
                "description": description,
                "color": color,
                "icon_url": icon_url
            }).eq("id", subcategory_id).execute()
            flash("Subcategory updated successfully", "success")
            return redirect(url_for("category_subcategories", category_id=subcategory["categories"]["id"]))
        except Exception as e:
            flash("Error updating subcategory. Name might already exist.", "danger")
    
    return render_template("edit_subcategory.html", subcategory=subcategory, user=u)

@app.route("/subcategory/<int:subcategory_id>/delete", methods=["POST"])
@login_required
def delete_subcategory(subcategory_id):
    u = current_user()
    
    # Get subcategory and verify access
    subcategory_res = supabase.table("subcategories").select("*, categories!inner(*)").eq("id", subcategory_id).eq("categories.user_id", u["id"]).execute()
    if not subcategory_res.data:
        abort(404)
    subcategory = subcategory_res.data[0]
    category_id = subcategory["categories"]["id"]
    
    try:
        # Delete all links in this subcategory first
        supabase.table("links").delete().eq("subcategory_id", subcategory_id).eq("user_id", u["id"]).execute()
        # Delete the subcategory
        supabase.table("subcategories").delete().eq("id", subcategory_id).execute()
        flash(f"Subcategory '{subcategory['name']}' deleted successfully", "success")
    except Exception as e:
        flash("Error deleting subcategory", "danger")
    
    return redirect(url_for("category_subcategories", category_id=category_id))

@app.route("/link/<link_id>/edit", methods=["GET","POST"])
@login_required
def edit_link(link_id):
    u = current_user()
    link_res = supabase.table("links").select("*").eq("id", link_id).eq("user_id", u["id"]).execute()
    if not link_res.data:
        abort(404)
    link = link_res.data[0]
    if request.method == "GET":
        return render_template("edit_link.html", link=link)
    title = request.form.get("title","").strip()
    url = request.form.get("url","").strip()
    is_public = bool(request.form.get("is_public"))
    
    # Normalize URL to include protocol
    url = normalize_url(url)
    
    try:
        supabase.table("links").update({
            "title":title, "url":url, "is_public":is_public
        }).eq("id", link_id).execute()
        flash("Saved","success")
    except Exception as e:
        flash("Error saving link. Please check the URL format.","danger")
        
    return redirect(url_for("dashboard"))

@app.route("/category/<int:category_id>/edit", methods=["GET", "POST"])
@login_required
def edit_category(category_id):
    u = current_user()
    category_res = supabase.table("categories").select("*").eq("id", category_id).eq("user_id", u["id"]).execute()
    if not category_res.data:
        abort(404)
    category = category_res.data[0]
    
    if request.method == "GET":
        return render_template("edit_category.html", category=category)
    
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    color = request.form.get("color", "#2563eb").strip()
    icon_url = category.get("icon_url")  # Keep existing icon by default
    
    if not name:
        flash("Category name is required", "danger")
        return render_template("edit_category.html", category=category)
    
    # Handle icon file upload
    if 'icon_file' in request.files:
        icon_file = request.files['icon_file']
        if icon_file and icon_file.filename != '':
            try:
                # Upload to Cloudinary
                upload_result = cloudinary.uploader.upload(
                    icon_file,
                    folder="linktree_icons/categories",
                    transformation=[
                        {"width": 64, "height": 64, "crop": "fill"},
                        {"quality": "auto", "fetch_format": "auto"}
                    ]
                )
                icon_url = upload_result['secure_url']
            except Exception as e:
                flash(f"Failed to upload icon: {str(e)}", "danger")
                return render_template("edit_category.html", category=category)
    
    try:
        supabase.table("categories").update({
            "name": name,
            "description": description,
            "color": color,
            "icon_url": icon_url
        }).eq("id", category_id).execute()
        flash("Category updated successfully", "success")
    except Exception as e:
        flash("Error updating category", "danger")
        
    return redirect(url_for("dashboard"))

@app.route("/category/<int:category_id>/delete", methods=["POST"])
@login_required
def delete_category(category_id):
    u = current_user()
    
    # First, get all subcategories in this category
    subcategories = supabase.table("subcategories").select("id").eq("category_id", category_id).eq("user_id", u["id"]).execute().data
    
    # Delete all links associated with subcategories in this category
    for subcategory in subcategories:
        supabase.table("links").delete().eq("subcategory_id", subcategory["id"]).eq("user_id", u["id"]).execute()
    
    # Delete all direct links in this category (links without subcategory)
    supabase.table("links").delete().eq("category_id", category_id).eq("user_id", u["id"]).execute()
    
    # Delete all subcategories in this category
    supabase.table("subcategories").delete().eq("category_id", category_id).eq("user_id", u["id"]).execute()
    
    # Finally, delete the category
    supabase.table("categories").delete().eq("id", category_id).eq("user_id", u["id"]).execute()
    
    flash("Category and all associated subcategories and links deleted", "info")
    return redirect(url_for("dashboard"))

# --- OLD BRAND ROUTES (DEPRECATED - USING SUBCATEGORIES NOW) ---
# These routes are commented out since we migrated from brands to subcategories

# @app.route("/brand/<int:brand_id>/edit", methods=["GET", "POST"])
# @login_required
# def edit_brand(brand_id):
#     # This route has been replaced by edit_subcategory
#     return redirect(url_for("dashboard"))

# @app.route("/brand/<int:brand_id>/delete", methods=["POST"])
# @login_required
# def delete_brand(brand_id):
#     # This route has been replaced by delete_subcategory
#     return redirect(url_for("dashboard"))
    
    # Redirect back to the category page if we have a category_id
    if category_id:
        return redirect(url_for("category_brands", category_id=category_id))
    else:
        return redirect(url_for("dashboard"))

@app.route("/link/<link_id>/delete", methods=["POST"])
@login_required
def delete_link(link_id):
    u = current_user()
    
    # Get the subcategory_id and category_id for redirect
    link_res = supabase.table("links").select("subcategory_id, category_id").eq("id", link_id).eq("user_id", u["id"]).execute()
    
    if not link_res.data:
        flash("Link not found", "danger")
        return redirect(url_for("dashboard"))
    
    link_data = link_res.data[0]
    subcategory_id = link_data.get("subcategory_id")
    category_id = link_data.get("category_id")
    
    supabase.table("links").delete().eq("id", link_id).eq("user_id", u["id"]).execute()
    flash("Link deleted", "info")
    
    # Redirect based on where the link was located
    if subcategory_id:
        return redirect(url_for("subcategory_links", subcategory_id=subcategory_id))
    elif category_id:
        return redirect(url_for("category_subcategories", category_id=category_id))
    else:
        return redirect(url_for("dashboard"))

@app.route("/link/reorder", methods=["POST"])
@login_required
def reorder_links():
    u = current_user()
    order = request.get_json()
    if not isinstance(order,list):
        return jsonify({"error":"invalid"}),400
    for pos, lid in enumerate(order):
        supabase.table("links").update({"sort_order":pos}).eq("id",lid).eq("user_id",u["id"]).execute()
    return jsonify({"ok":True})

@app.route("/profile/edit", methods=["POST"])
@login_required
def edit_profile():
    u = current_user()
    display_name = request.form.get("display_name","").strip()
    bio = request.form.get("bio","").strip()
    avatar_url = request.form.get("avatar_url","").strip()
    theme = request.form.get("theme","default").strip()
    
    # Handle avatar file upload
    if 'avatar_file' in request.files:
        avatar_file = request.files['avatar_file']
        if avatar_file and avatar_file.filename != '':
            try:
                # Upload to Cloudinary
                upload_result = cloudinary.uploader.upload(
                    avatar_file,
                    folder="linktree_avatars",
                    transformation=[
                        {"width": 300, "height": 300, "crop": "fill", "gravity": "face"},
                        {"quality": "auto", "fetch_format": "auto"}
                    ]
                )
                avatar_url = upload_result['secure_url']
                flash("Avatar uploaded successfully!", "success")
            except Exception as e:
                flash(f"Failed to upload avatar: {str(e)}", "danger")
                return redirect(url_for("dashboard"))
    
    supabase.table("profiles").update({
        "display_name": display_name, 
        "bio": bio, 
        "avatar_url": avatar_url, 
        "theme": theme
    }).eq("user_id", u["id"]).execute()
    
    flash("Profile updated", "success")
    return redirect(url_for("dashboard"))

# --- Public page ---
@app.route("/u/<username>/category/<int:category_id>")
def public_category_direct(username, category_id):
    """Direct link to a specific category"""
    return redirect(url_for('public_profile', username=username, category=category_id))

@app.route("/u/<username>/subcategory/<int:subcategory_id>")
def public_subcategory_direct(username, subcategory_id):
    """Direct link to a specific subcategory"""
    return redirect(url_for('public_profile', username=username, subcategory=subcategory_id))

@app.route("/u/<username>")
def public_profile(username):
    user_res = supabase.table("users").select("*").eq("username",username).execute()
    if not user_res.data:
        abort(404)
    user_row = user_res.data[0]
    profile = supabase.table("profiles").select("*").eq("user_id",user_row["id"]).execute().data[0]
    
    # Check for direct category or subcategory linking via URL parameters
    category_id = request.args.get('category')
    subcategory_id = request.args.get('subcategory')
    
    # Get categories for public display
    try:
        categories = supabase.table("categories").select("*").eq("user_id", user_row["id"]).eq("is_active", True).order("sort_order").execute().data
    except Exception as e:
        # Fallback to old system if categories don't exist
        links = supabase.table("links").select("*").eq("user_id",user_row["id"]).eq("is_public",True).order("sort_order").execute().data
        return render_template("profile.html", profile=profile, user=user_row, links=links)
    
    return render_template("user_profile_seo.html", profile=profile, user=user_row, categories=categories, 
                         direct_category_id=category_id, direct_subcategory_id=subcategory_id)

# --- Redirect + record click ---
@app.route("/r/<link_id>")
def redirect_link(link_id):
    link_res = supabase.table("links").select("*").eq("id",link_id).execute()
    if not link_res.data:
        abort(404)
    link = link_res.data[0]
    ref = request.referrer or None
    supabase.table("clicks").insert({"link_id":link_id,"referrer":ref}).execute()
    return redirect(link["url"])

# --- Simple stats json ---
@app.route("/api/stats/<username>")
def api_stats(username):
    user_res = supabase.table("users").select("*").eq("username",username).execute()
    if not user_res.data:
        return jsonify({"error":"not found"}),404
    user_id = user_res.data[0]["id"]
    # get clicks aggregated manually
    links_res = supabase.table("links").select("*").eq("user_id",user_id).execute()
    out=[]
    for link in links_res.data:
        clicks_res = supabase.table("clicks").select("id").eq("link_id",link["id"]).execute()
        out.append({"id":link["id"],"title":link["title"],"clicks":len(clicks_res.data)})
    return jsonify({"username":username,"links":out})

# --- API endpoints for public profile ---
@app.route("/api/category/<int:category_id>/content")
def api_category_content(category_id):
    """Get subcategories and direct links for a category (public API)"""
    # Verify category exists and is active
    category_res = supabase.table("categories").select("user_id, name").eq("id", category_id).eq("is_active", True).execute()
    if not category_res.data:
        return jsonify({"error": "Category not found"}), 404
    
    category = category_res.data[0]
    
    # Get subcategories for this category
    subcategories = supabase.table("subcategories").select("*").eq("category_id", category_id).eq("is_active", True).order("sort_order").execute().data
    
    # Add link count for each subcategory
    for subcategory in subcategories:
        link_count = supabase.table("links").select("id", count="exact").eq("subcategory_id", subcategory["id"]).eq("is_active", True).eq("is_public", True).execute().count
        subcategory["link_count"] = link_count or 0
    
    # Get direct links for this category
    direct_links = supabase.table("links").select("*").eq("category_id", category_id).eq("is_active", True).eq("is_public", True).order("sort_order").execute().data
    
    return jsonify({
        "category": category,
        "subcategories": subcategories, 
        "direct_links": direct_links
    })

@app.route("/api/subcategory/<int:subcategory_id>/links")
def api_subcategory_links(subcategory_id):
    """Get links for a subcategory (public API)"""
    # Verify subcategory exists and is active
    subcategory_res = supabase.table("subcategories").select("user_id, name").eq("id", subcategory_id).eq("is_active", True).execute()
    if not subcategory_res.data:
        return jsonify({"error": "Subcategory not found"}), 404
    
    subcategory = subcategory_res.data[0]
    
    # Get links for this subcategory
    links = supabase.table("links").select("*").eq("subcategory_id", subcategory_id).eq("is_active", True).eq("is_public", True).order("sort_order").execute().data
    
    return jsonify({"subcategory": subcategory, "links": links})

# --- Health Check & Debugging APIs ---
@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint with debugging info"""
    try:
        import os
        return jsonify({
            "status": "healthy",
            "timestamp": str(datetime.now()),
            "flask_secret_set": bool(os.getenv("FLASK_SECRET_KEY")),
            "supabase_url_set": bool(os.getenv("SUPABASE_URL")),
            "supabase_key_set": bool(os.getenv("SUPABASE_KEY")),
            "site_base": os.getenv("SITE_BASE", "not_set"),
            "environment": "production" if os.getenv("VERCEL") else "development"
        })
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500

@app.route("/api/test-dependencies", methods=["GET"])
def test_dependencies():
    """Test if all required dependencies are available"""
    try:
        import requests
        import bs4
        import cloudinary
        import cloudinary.uploader
        
        return jsonify({
            "status": "success",
            "requests": requests.__version__,
            "beautifulsoup4": bs4.__version__,
            "cloudinary": cloudinary.__version__
        })
    except ImportError as e:
        return jsonify({
            "status": "error",
            "error": f"Missing dependency: {str(e)}"
        }), 500

@app.route("/api/detect-link-info", methods=["POST"])
@login_required
def detect_link_info():
    """Auto-detect product name and image from a URL"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        if not url:
            return jsonify({"error": "URL is required"}), 400
        
        # Add protocol if missing
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Import the scraping functions
        try:
            import requests
            from bs4 import BeautifulSoup
        except ImportError as e:
            return jsonify({"error": f"Missing required packages: {str(e)}"}), 500
        
        # Scrape the URL
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
        except requests.RequestException as e:
            return jsonify({"error": f"Could not access the URL: {str(e)}"}), 400
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract product/page title
        title = None
        
        # Try Open Graph title first
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()
        
        # Fallback to regular title tag
        if not title:
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.text.strip()
        
        # Fallback to h1
        if not title:
            h1_tag = soup.find("h1")
            if h1_tag:
                title = h1_tag.text.strip()
        
        # Extract product image
        image_url = None
        uploaded_image_url = None
        
        # Try Open Graph image first
        og_image = soup.find("meta", property="og:image")
        if og_image and og_image.get("content"):
            image_url = og_image["content"]
        
        # Try other common meta tags
        if not image_url:
            twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
            if twitter_image and twitter_image.get("content"):
                image_url = twitter_image["content"]
        
        # Try to find main product image
        if not image_url:
            # Look for images with common product image attributes
            product_img = soup.find("img", {"class": ["product-image", "main-image", "hero-image"]})
            if product_img and product_img.get("src"):
                image_url = product_img["src"]
        
        # Upload image to Cloudinary if found
        if image_url:
            try:
                # Make image URL absolute if it's relative
                if image_url.startswith('/'):
                    from urllib.parse import urljoin
                    image_url = urljoin(url, image_url)
                elif not image_url.startswith(('http://', 'https://')):
                    from urllib.parse import urljoin
                    image_url = urljoin(url, '/' + image_url)
                
                # Upload to Cloudinary
                try:
                    upload_result = cloudinary.uploader.upload(
                        image_url,
                        folder="linktree_links",
                        transformation=[
                            {"width": 200, "height": 200, "crop": "fill"},
                            {"quality": "auto", "fetch_format": "auto"}
                        ]
                    )
                    uploaded_image_url = upload_result['secure_url']
                except Exception as cloudinary_error:
                    print(f"Cloudinary upload failed: {str(cloudinary_error)}")
                    # Continue without image if Cloudinary upload fails
                
            except Exception as e:
                print(f"Failed to process image: {str(e)}")
                # Continue without image if image processing fails
        
        return jsonify({
            "title": title or "Untitled",
            "image_url": uploaded_image_url or image_url,  # Fallback to original image if Cloudinary fails
            "original_image_url": image_url,
            "cloudinary_success": uploaded_image_url is not None
        })
        
    except Exception as e:
        print(f"Error in detect_link_info: {str(e)}")
        import traceback
        traceback.print_exc()  # Print full stack trace for debugging
        return jsonify({"error": f"Failed to detect link information: {str(e)}"}), 500

# Debug OAuth configuration
@app.route("/oauth-debug")
def oauth_debug():
    # Generate the dynamic redirect URI
    dynamic_redirect_uri = url_for('google_callback', _external=True)
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>OAuth Configuration Debug</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .config-box {{ background: #f5f5f5; padding: 20px; border-radius: 5px; margin: 10px 0; }}
            .url {{ background: #e7f3ff; padding: 10px; border-left: 4px solid #2196F3; margin: 10px 0; font-family: monospace; }}
            .success {{ color: #4CAF50; }}
            .error {{ color: #f44336; }}
        </style>
    </head>
    <body>
        <h2>🔧 OAuth Configuration Debug</h2>
        
        <div class="config-box">
            <h3>Current Configuration:</h3>
            <p><strong>CLIENT_ID:</strong> {CLIENT_ID[:20]}...</p>
            <p><strong>Current Domain:</strong> {request.url_root}</p>
            <p><strong>Dynamic Redirect URI:</strong></p>
            <div class="url">{dynamic_redirect_uri}</div>
        </div>
        
        <div class="config-box">
            <h3>📋 Step-by-Step Fix:</h3>
            <ol>
                <li>Go to <a href="https://console.cloud.google.com/" target="_blank">Google Cloud Console</a></li>
                <li>Navigate to <strong>APIs & Services > Credentials</strong></li>
                <li>Find your OAuth 2.0 Client ID and click <strong>Edit</strong></li>
                <li>In <strong>"Authorized redirect URIs"</strong>, add these URLs:</li>
                <div class="url">
                    {dynamic_redirect_uri}<br>
                    http://localhost:5000/auth/google/callback<br>
                    http://127.0.0.1:5000/auth/google/callback
                </div>
                <li>Click <strong>Save</strong></li>
                <li>Wait 5-10 minutes for changes to propagate</li>
            </ol>
        </div>
        
        <div class="config-box">
            <h3>🧪 Test Gmail Signup/Login Flow:</h3>
            <p>After fixing Google Console:</p>
            <ol>
                <li><strong>New Gmail User:</strong> Click "Sign up with Google" → Account created with Gmail email/username</li>
                <li><strong>Existing Gmail User:</strong> Click "Continue with Google" → Logged in automatically</li>
                <li><strong>Link Accounts:</strong> Traditional user uses Gmail with same email → Accounts linked</li>
            </ol>
        </div>
        
        <p>
            <a href="/login" style="background: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">🔙 Back to Login</a>
            <a href="/auth/google" style="background: #2196F3; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-left: 10px;">🧪 Test Google OAuth</a>
        </p>
    </body>
    </html>
    """

# Debug route to test database
@app.route("/debug")
@login_required  
def debug():
    u = current_user()
    try:
        # Test analytics data
        analytics = get_user_analytics(u["id"])
        
        # Get raw data for debugging
        links = supabase.table("links").select("*").eq("user_id", u["id"]).execute()
        all_links = supabase.table("links").select("*").execute()  # All links in database
        
        # Check for orphaned links (links without user_id or with null user_id)
        orphaned_links = supabase.table("links").select("*").is_("user_id", "null").execute()
        
        clicks = supabase.table("clicks").select("*").execute()
        categories = supabase.table("categories").select("*").eq("user_id", u["id"]).execute()
        subcategories = supabase.table("subcategories").select("*").eq("user_id", u["id"]).execute()
        
        # Test the count queries specifically
        try:
            links_count_test = supabase.table("links").select("id", count="exact").eq("user_id", u["id"]).execute()
        except Exception as e:
            links_count_test = f"Error: {str(e)}"
        
        try:
            categories_count_test = supabase.table("categories").select("id", count="exact").eq("user_id", u["id"]).execute()
        except Exception as e:
            categories_count_test = f"Error: {str(e)}"
            
        try:
            subcategories_count_test = supabase.table("subcategories").select("id", count="exact").eq("user_id", u["id"]).execute()
        except Exception as e:
            subcategories_count_test = f"Error: {str(e)}"
        
        return f"""
        <h1>Debug Analytics</h1>
        <p><strong>User ID:</strong> {u['id']}</p>
        <p><strong>Username:</strong> {u['username']}</p>
        
        <h3>🔍 Raw Data Queries:</h3>
        <p><strong>Your Links in DB:</strong> {len(links.data) if links.data else 0}</p>
        <p><strong>All Links in DB:</strong> {len(all_links.data) if all_links.data else 0}</p>
        <p><strong>Total Clicks in DB:</strong> {len(clicks.data) if clicks.data else 0}</p>
        <p><strong>Your Categories:</strong> {len(categories.data) if categories.data else 0}</p>
        <p><strong>Your Subcategories:</strong> {len(subcategories.data) if subcategories.data else 0}</p>
        
        <h3>🧮 Count Query Tests:</h3>
        <p><strong>Links Count Query:</strong> {links_count_test.count if hasattr(links_count_test, 'count') else str(links_count_test)}</p>
        <p><strong>Categories Count Query:</strong> {categories_count_test.count if hasattr(categories_count_test, 'count') else str(categories_count_test)}</p>
        <p><strong>Subcategories Count Query:</strong> {subcategories_count_test.count if hasattr(subcategories_count_test, 'count') else str(subcategories_count_test)}</p>
        
        <h3>📊 Analytics Function Result:</h3>
        <p><strong>Total Links:</strong> {analytics['total_links']}</p>
        <p><strong>Total Clicks:</strong> {analytics['total_clicks']}</p>
        <p><strong>Categories Count:</strong> {analytics['categories_count']}</p>
        <p><strong>Subcategories Count:</strong> {analytics['subcategories_count']}</p>
        <p><strong>Trending Links:</strong> {len(analytics['trending_links'])}</p>
        
        <h3>📋 Your Link Details:</h3>
        {'<br>'.join([f"• <strong>{link['title']}</strong> (ID: {link['id']}, User ID: {link.get('user_id', 'MISSING!')}, Subcategory: {link.get('subcategory_id', 'Direct')}, Category: {link.get('category_id', 'N/A')})" for link in links.data]) if links.data else '❌ <strong>No links found for your user ID!</strong>'}
        
        <h3>🔍 Orphaned Links (No User ID):</h3>
        {'<br>'.join([f"• <strong>{link['title']}</strong> (ID: {link['id']}, User ID: {link.get('user_id', 'NULL')}, Category: {link.get('category_id', 'N/A')}, Subcategory: {link.get('subcategory_id', 'N/A')})" for link in orphaned_links.data]) if orphaned_links.data else '✅ <strong>No orphaned links found!</strong>'}
        
        <h3>🖱️ Click Details (First 10):</h3>
        {'<br>'.join([f"• Click on Link ID: {click['link_id']} at {click.get('clicked_at', 'Unknown time')}" for click in clicks.data[:10]]) if clicks.data else '❌ <strong>No clicks found in database!</strong>'}
        
        <h3>🎯 Troubleshooting:</h3>
        <p><strong>Step 1:</strong> Do you have any links? {'✅ Yes' if links.data else '❌ No - Create some links first!'}</p>
        <p><strong>Step 2:</strong> Does clicks table exist? {'✅ Yes' if clicks.data is not None else '❌ No - Run the clicks table SQL!'}</p>
        <p><strong>Step 3:</strong> Have you clicked any links? {'✅ Yes' if clicks.data else '❌ No - Visit your public profile and click some links!'}</p>
        
        <h3>🔗 Quick Actions:</h3>
        <p><a href="/u/{u['username']}" target="_blank">🔗 Visit Your Public Profile</a> (Click some links to generate clicks)</p>
        <p><a href="/dashboard">🏠 Back to Dashboard</a></p>
        
        <hr>
        <small><strong>Note:</strong> If you see 0 links, you need to create categories, then subcategories (optional), then add links to categories or subcategories.</small>
        """
    except Exception as e:
        return f"""
        <h1>Debug Info</h1>
        <p>User ID: {u['id']}</p>
        <p>Error: {str(e)}</p>
        <p>❌ Error occurred during debugging</p>
        <p><a href="/fix-orphaned-links">🔧 Fix Orphaned Links</a></p>
        <a href="/dashboard">Back to Dashboard</a>
        """

@app.route("/fix-orphaned-links")
@login_required  
def fix_orphaned_links():
    u = current_user()
    try:
        # Get orphaned links that belong to user's categories or subcategories
        orphaned_links = supabase.table("links").select("*").is_("user_id", "null").execute()
        
        fixed_count = 0
        
        if orphaned_links.data:
            for link in orphaned_links.data:
                # Try to determine ownership through category or subcategory
                if link.get("category_id"):
                    # Check if category belongs to current user
                    category = supabase.table("categories").select("user_id").eq("id", link["category_id"]).eq("user_id", u["id"]).execute()
                    if category.data:
                        # This link belongs to user's category
                        supabase.table("links").update({"user_id": u["id"]}).eq("id", link["id"]).execute()
                        fixed_count += 1
                        
                elif link.get("subcategory_id"):
                    # Check if subcategory belongs to current user through category
                    subcategory = supabase.table("subcategories").select("*, categories!inner(user_id)").eq("id", link["subcategory_id"]).eq("categories.user_id", u["id"]).execute()
                    if subcategory.data:
                        # This link belongs to user's subcategory
                        supabase.table("links").update({"user_id": u["id"]}).eq("id", link["id"]).execute()
                        fixed_count += 1
        
        return f"""
        <h1>Fix Orphaned Links</h1>
        <p><strong>Fixed {fixed_count} orphaned links for your account.</strong></p>
        <p>These links now have proper user ownership and can be deleted normally.</p>
        <p><a href="/debug">🔍 View Debug Info</a></p>
        <p><a href="/dashboard">🏠 Back to Dashboard</a></p>
        """
        
    except Exception as e:
        return f"""
        <h1>Fix Orphaned Links</h1>
        <p>Error: {str(e)}</p>
        <p><a href="/dashboard">Back to Dashboard</a></p>
        """

# --- Support Request System ---
@app.route("/api/submit-support-request", methods=["POST"])
def submit_support_request():
    """Handle support request form submissions"""
    try:
        data = request.get_json()
        
        # Validate required fields
        name = data.get('name', '').strip()
        email = data.get('email', '').strip().lower()
        request_text = data.get('request', '').strip()
        
        if not name or not email or not request_text:
            return jsonify({"success": False, "error": "All fields are required"}), 400
        
        # Basic email validation
        import re
        if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            return jsonify({"success": False, "error": "Please enter a valid email address"}), 400
        
        # Get current user if logged in
        current_user_obj = current_user()
        user_id = current_user_obj["id"] if current_user_obj else None
        
        # If user is logged in but form has different email, show warning but allow submission
        logged_in_email = current_user_obj["email"] if current_user_obj else None
        
        # Insert support request into database
        request_data = {
            "user_id": user_id,
            "name": name,
            "email": email,
            "request": request_text,
            "status": "open",
            "priority": "normal"
        }
        
        result = supabase.table("linklyst_requests").insert(request_data).execute()
        
        if result.data:
            # Log successful submission
            print(f"Support request submitted - ID: {result.data[0]['id']}, Email: {email}, User ID: {user_id}")
            
            return jsonify({
                "success": True, 
                "message": "Your request has been submitted successfully. You will be contacted by our support team soon.",
                "request_id": result.data[0]['id']
            })
        else:
            return jsonify({"success": False, "error": "Failed to submit request. Please try again."}), 500
            
    except Exception as e:
        print(f"Error submitting support request: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": "An unexpected error occurred. Please try again."}), 500

# --- Static File Debug Route ---
@app.route("/static/<path:filename>")
def static_files(filename):
    """Explicitly handle static files for Vercel deployment"""
    from flask import send_from_directory
    import os
    
    # Debug: Check if file exists
    file_path = os.path.join(app.static_folder, filename)
    print(f"DEBUG: Requesting static file: {filename}")
    print(f"DEBUG: Full path: {file_path}")
    print(f"DEBUG: File exists: {os.path.exists(file_path)}")
    print(f"DEBUG: Static folder: {app.static_folder}")
    
    if os.path.exists(file_path):
        return send_from_directory(app.static_folder, filename)
    else:
        from flask import abort
        print(f"DEBUG: Static file not found: {filename}")
        abort(404)

@app.route("/static/blog.css")
def serve_blog_css():
    """Serve blog.css with anti-cache headers for custom domain"""
    from flask import send_from_directory, make_response
    import os
    
    # Check if the CSS file exists
    css_path = os.path.join(app.static_folder, 'blog.css')
    if not os.path.exists(css_path):
        abort(404)
    
    # Create response with anti-cache headers
    response = make_response(send_from_directory(app.static_folder, 'blog.css'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['Content-Type'] = 'text/css'
    
    print(f"Serving blog.css for domain: {request.host}")
    return response

@app.route("/debug/static")
def debug_static():
    """Debug route to check static files"""
    import os
    static_files = []
    
    for root, dirs, files in os.walk(app.static_folder):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), app.static_folder)
            static_files.append(rel_path)
    
    return f"""
    <h1>Static Files Debug</h1>
    <p><strong>Static folder:</strong> {app.static_folder}</p>
    <p><strong>Files found:</strong></p>
    <ul>
    {''.join([f'<li><a href="/static/{f}" target="_blank">{f}</a></li>' for f in static_files])}
    </ul>
    <p><a href="/blog">Test Blog</a></p>
    """

@app.route("/debug/domain")
def debug_domain():
    """Debug route to check domain-specific issues"""
    return f"""
    <h1>Domain Debug Information</h1>
    <p><strong>Request URL:</strong> {request.url}</p>
    <p><strong>Host:</strong> {request.host}</p>
    <p><strong>Base URL:</strong> {request.base_url}</p>
    <p><strong>URL Root:</strong> {request.url_root}</p>
    <p><strong>Environment:</strong> {"Vercel" if os.getenv("VERCEL") else "Local"}</p>
    <p><strong>Headers:</strong></p>
    <ul>
    {''.join([f'<li><strong>{k}:</strong> {v}</li>' for k, v in request.headers])}
    </ul>
    
    <h3>Static File Tests:</h3>
    <p><a href="/static/blog.css" target="_blank">Test blog.css direct link</a></p>
    <p><a href="/static/styles.css" target="_blank">Test styles.css direct link</a></p>
    
    <h3>Blog Tests:</h3>
    <p><a href="/blog" target="_blank">Test Blog Page</a></p>
    
    <script>
    // Test CSS loading via JavaScript
    function testCSSLoading() {{
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = '/static/blog.css?t=' + Date.now();
        link.onload = function() {{
            document.getElementById('css-test').innerHTML = '✅ CSS loads successfully';
            document.getElementById('css-test').style.color = 'green';
        }};
        link.onerror = function() {{
            document.getElementById('css-test').innerHTML = '❌ CSS failed to load';
            document.getElementById('css-test').style.color = 'red';
        }};
        document.head.appendChild(link);
    }}
    
    window.onload = testCSSLoading;
    </script>
    
    <p id="css-test">🔄 Testing CSS loading...</p>
    """

# --- SEO Routes ---
@app.route("/robots.txt")
def robots_txt():
    """Generate robots.txt dynamically"""
    return """User-agent: *
Allow: /
Allow: /u/
Disallow: /dashboard
Disallow: /api/
Disallow: /auth/
Disallow: /profile/
Disallow: /category/
Disallow: /subcategory/
Disallow: /link/

Sitemap: https://linklyst.space/sitemap.xml""", 200, {'Content-Type': 'text/plain'}

@app.route("/sitemap.xml")
def sitemap_xml():
    """Generate sitemap.xml dynamically"""
    from flask import Response
    from datetime import datetime
    
    pages = []
    today = datetime.now().date().isoformat()
    
    # Static pages
    pages.append(['/', today])
    pages.append(['/register', today])
    pages.append(['/login', today])
    
    # Dynamic user pages - get all users with active profiles
    try:
        users = supabase.table("users").select("username").execute()
        for user in users.data:
            if user.get('username'):
                pages.append([f'/u/{user["username"]}', today])
    except Exception as e:
        print(f"Error fetching users for sitemap: {e}")
    
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    
    for page, date in pages:
        xml.append(f'<url><loc>https://linklyst.space{page}</loc><lastmod>{date}</lastmod><changefreq>weekly</changefreq><priority>0.8</priority></url>')
    
    xml.append("</urlset>")
    
    return Response("\n".join(xml), mimetype='application/xml')

# Add a simple username route that redirects to /u/<username>
@app.route("/<username>")
def username_redirect(username):
    """Redirect /<username> to /u/<username> for better SEO"""
    # First check if it's a known route to avoid conflicts
    known_routes = ['register', 'login', 'dashboard', 'categories', 'profile', 'robots.txt', 'sitemap.xml', 'api', 'auth', 'u', 'r']
    if username in known_routes:
        abort(404)
    
    # Check if user exists
    user_res = supabase.table("users").select("username").eq("username", username).execute()
    if not user_res.data:
        abort(404)
    
    return redirect(url_for('public_profile', username=username), code=301)

# --- Legal Pages ---
@app.route("/privacy")
def privacy_policy():
    """Privacy Policy page"""
    return render_template("privacy.html")

@app.route("/terms")
def terms_of_service():
    """Terms of Service page"""
    return render_template("terms.html")

# --- Upgrade System Routes ---
@app.route("/upgrade")
@login_required
def upgrade():
    """Show upgrade page"""
    return render_template("upgrade.html")

@app.route("/upgrade/request", methods=["POST"])
@login_required
def submit_upgrade_request():
    """Submit upgrade request for admin approval"""
    try:
        user = current_user()
        if not user:
            flash("Please log in to submit an upgrade request.", "error")
            return redirect(url_for("login"))
        
        business_name = request.form.get("business_name", "").strip()
        use_case = request.form.get("use_case", "").strip()
        additional_info = request.form.get("additional_info", "").strip()
        
        if not business_name or not use_case:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("upgrade"))
        
        # Check if upgrade_requests table exists and if user already has a pending request
        try:
            existing_request = supabase.table("upgrade_requests").select("*").eq("user_id", user["id"]).eq("status", "pending").execute()
            
            if existing_request.data:
                flash("You already have a pending upgrade request. Please wait for admin approval.", "info")
                return redirect(url_for("upgrade"))
        except Exception as table_error:
            # If table doesn't exist, show helpful error message
            if "does not exist" in str(table_error).lower():
                flash("Upgrade system is not yet configured. Please contact support at support@automatexpo.com", "error")
                print(f"upgrade_requests table not found. Please create it using Supabase Dashboard.")
                return redirect(url_for("upgrade"))
            raise table_error
        
        # Insert upgrade request
        request_data = {
            "user_id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "business_name": business_name,
            "use_case": use_case,
            "additional_info": additional_info,
            "status": "pending",
            "requested_at": datetime.utcnow().isoformat(),
            "trial_end": user.get("trial_end")
        }
        
        result = supabase.table("upgrade_requests").insert(request_data).execute()
        
        if result.data:
            flash("Upgrade request submitted successfully! An admin will review your request within 24 hours.", "success")
            print(f"Upgrade request submitted - User: {user['username']}, Email: {user['email']}")
        else:
            flash("Failed to submit upgrade request. Please try again.", "error")
            
    except Exception as e:
        print(f"Error submitting upgrade request: {str(e)}")
        error_msg = str(e).lower()
        if "does not exist" in error_msg:
            flash("Upgrade system is being configured. Please try again later or contact support.", "info")
        else:
            flash("An error occurred while submitting your request. Please try again.", "error")
    
    return redirect(url_for("upgrade"))

@app.route("/admin/upgrade-requests")
@login_required
def admin_upgrade_requests():
    """Admin page to view and manage upgrade requests"""
    user = current_user()
    
    # Simple admin check - in production, you'd want proper role-based access
    admin_emails = ["admin@linklyst.space", "support@automatexpo.com"]  # Add your admin emails
    
    if not user or user.get("email") not in admin_emails:
        abort(403)  # Forbidden
    
    try:
        # Get all upgrade requests
        requests = supabase.table("upgrade_requests").select("*").order("requested_at", desc=True).execute()
        return render_template("admin_upgrade_requests.html", requests=requests.data)
    except Exception as e:
        error_msg = str(e).lower()
        if "does not exist" in error_msg:
            flash("Upgrade system database not configured. Please set up the upgrade_requests table first.", "error")
            print("upgrade_requests table missing. Please create it in Supabase Dashboard.")
        else:
            print(f"Error fetching upgrade requests: {e}")
            flash("Error loading upgrade requests.", "error")
        return redirect(url_for("dashboard"))

@app.route("/admin/upgrade-requests/<request_id>/approve", methods=["POST"])
@login_required
def approve_upgrade_request(request_id):
    """Approve an upgrade request"""
    user = current_user()
    admin_emails = ["admin@linklyst.space", "support@automatexpo.com"]
    
    if not user or user.get("email") not in admin_emails:
        abort(403)
    
    try:
        # Get the upgrade request
        upgrade_request = supabase.table("upgrade_requests").select("*").eq("id", request_id).execute()
        
        if not upgrade_request.data:
            flash("Upgrade request not found.", "error")
            return redirect(url_for("admin_upgrade_requests"))
        
        request_data = upgrade_request.data[0]
        user_id = request_data["user_id"]
        
        # Update user to Pro status
        supabase.table("users").update({
            "is_trial": False,
            "subscription_status": "active",
            "is_active": True,
            "subscription_start": datetime.utcnow().isoformat(),
            "subscription_end": None  # No end date for active subscriptions
        }).eq("id", user_id).execute()
        
        # Mark request as approved
        supabase.table("upgrade_requests").update({
            "status": "approved",
            "approved_at": datetime.utcnow().isoformat(),
            "approved_by": user["email"]
        }).eq("id", request_id).execute()
        
        flash(f"Upgrade request approved for {request_data['username']}!", "success")
        print(f"Upgrade approved - User: {request_data['username']} by Admin: {user['email']}")
        
    except Exception as e:
        print(f"Error approving upgrade request: {e}")
        flash("Error approving upgrade request.", "error")
    
    return redirect(url_for("admin_upgrade_requests"))

@app.route("/admin/upgrade-requests/<request_id>/reject", methods=["POST"])
@login_required
def reject_upgrade_request(request_id):
    """Reject an upgrade request"""
    user = current_user()
    admin_emails = ["admin@linklyst.space", "support@automatexpo.com"]
    
    if not user or user.get("email") not in admin_emails:
        abort(403)
    
    try:
        rejection_reason = request.form.get("reason", "").strip()
        
        # Mark request as rejected
        supabase.table("upgrade_requests").update({
            "status": "rejected",
            "rejected_at": datetime.utcnow().isoformat(),
            "rejected_by": user["email"],
            "rejection_reason": rejection_reason
        }).eq("id", request_id).execute()
        
        flash("Upgrade request rejected.", "success")
        
    except Exception as e:
        print(f"Error rejecting upgrade request: {e}")
        flash("Error rejecting upgrade request.", "error")
    
    return redirect(url_for("admin_upgrade_requests"))

# --- Admin Blog Routes ---
@app.route("/admin/blog/posts")
@login_required
def admin_blog_posts():
    """Admin page to manage blog posts"""
    user = current_user()
    admin_emails = ["admin@linklyst.space", "support@automatexpo.com"]
    
    print(f"DEBUG Admin Check - User: {user}")
    print(f"DEBUG Admin Check - User email: {user.get('email') if user else 'None'}")
    print(f"DEBUG Admin Check - Admin emails: {admin_emails}")
    print(f"DEBUG Admin Check - Email in admin list: {user.get('email') in admin_emails if user else False}")
    
    if not user or user.get("email") not in admin_emails:
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("dashboard"))
    
    try:
        status_filter = request.args.get('status', 'all')
        page = request.args.get('page', 1, type=int)
        per_page = 20
        offset = (page - 1) * per_page
        
        # Build query based on status filter
        query = supabase.table("blog_posts").select("*")
        if status_filter != 'all':
            query = query.eq("status", status_filter)
        
        # Get posts with pagination
        posts_result = query.order("created_at", desc=True).range(offset, offset + per_page - 1).execute()
        
        # Get total count
        count_query = supabase.table("blog_posts").select("id", count="exact")
        if status_filter != 'all':
            count_query = count_query.eq("status", status_filter)
        count_result = count_query.execute()
        
        posts = posts_result.data if posts_result.data else []
        total_posts = count_result.count if hasattr(count_result, 'count') else 0
        
        # Calculate pagination
        has_prev = page > 1
        has_next = (page * per_page) < total_posts
        prev_num = page - 1 if has_prev else None
        next_num = page + 1 if has_next else None
        
        return render_template("admin/blog_posts.html",
                             posts=posts,
                             total_posts=total_posts,
                             status_filter=status_filter,
                             page=page,
                             has_prev=has_prev,
                             has_next=has_next,
                             prev_num=prev_num,
                             next_num=next_num)
    
    except Exception as e:
        print(f"Error in admin_blog_posts: {e}")
        flash("Error loading blog posts.", "error")
        return render_template("admin/blog_posts.html", posts=[], total_posts=0, status_filter='all')

@app.route("/admin/blog/post/new")
@login_required 
def admin_new_blog_post():
    """Admin page to create new blog post"""
    user = current_user()
    admin_emails = ["admin@linklyst.space", "support@automatexpo.com"]
    
    if not user or user.get("email") not in admin_emails:
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("dashboard"))
    
    try:
        # Get categories for dropdown (handle if table doesn't exist)
        categories = []
        try:
            categories_result = supabase.table("blog_categories").select("*").order("name").execute()
            categories = categories_result.data if categories_result.data else []
        except Exception as cat_error:
            print(f"Blog categories table not found: {cat_error}")
            categories = []
        
        return render_template("admin/blog_post_form.html", 
                             post=None, 
                             categories=categories,
                             current_tags=[], 
                             mode='new',
                             is_edit=False)
    except Exception as e:
        print(f"Error loading new post form: {e}")
        flash("Error loading form.", "error")
        return redirect(url_for("admin_blog_posts"))

@app.route("/admin/blog/post/<int:post_id>/edit")
@login_required
def admin_edit_blog_post(post_id):
    """Admin page to edit existing blog post"""
    user = current_user()
    admin_emails = ["admin@linklyst.space", "support@automatexpo.com"]
    
    if not user or user.get("email") not in admin_emails:
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("dashboard"))
    
    try:
        # Get post
        post_result = supabase.table("blog_posts").select("*").eq("id", post_id).execute()
        if not post_result.data:
            flash("Blog post not found.", "error")
            return redirect(url_for("admin_blog_posts"))
        
        post = post_result.data[0]
        
        # Process tags for display
        current_tags = []
        if post.get('tags'):
            current_tags = [tag.strip() for tag in post['tags'].split(',') if tag.strip()]
        
        # Get categories for dropdown (handle if table doesn't exist)
        categories = []
        try:
            categories_result = supabase.table("blog_categories").select("*").order("name").execute()
            categories = categories_result.data if categories_result.data else []
        except Exception as cat_error:
            print(f"Blog categories table not found: {cat_error}")
            categories = []
        
        return render_template("admin/blog_post_form.html", 
                             post=post, 
                             categories=categories,
                             current_tags=current_tags,
                             mode='edit', 
                             is_edit=True)
    except Exception as e:
        print(f"Error loading edit post form: {e}")
        flash("Error loading form.", "error")
        return redirect(url_for("admin_blog_posts"))

@app.route("/admin/blog/post", methods=["POST"])
@app.route("/admin/blog/post/<int:post_id>", methods=["POST"])
@login_required
def admin_save_blog_post(post_id=None):
    """Save blog post (create or update)"""
    user = current_user()
    admin_emails = ["admin@linklyst.space", "support@automatexpo.com"]
    
    print(f"DEBUG: admin_save_blog_post called with post_id={post_id}, method={request.method}")
    print(f"DEBUG: Request URL: {request.url}")
    
    if not user or user.get("email") not in admin_emails:
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("dashboard"))
    
    try:
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()
        excerpt = request.form.get("excerpt", "").strip()
        status = request.form.get("status", "draft")
        category_id = request.form.get("category_id")
        featured_image = request.form.get("featured_image", "").strip()
        meta_title = request.form.get("meta_title", "").strip()
        meta_description = request.form.get("meta_description", "").strip()
        tags = request.form.get("tags", "").strip()
        
        if not title or not content:
            flash("Title and content are required.", "error")
            return redirect(request.url)
        
        # Generate slug from title
        import re
        slug = re.sub(r'[^a-zA-Z0-9\s-]', '', title.lower())
        slug = re.sub(r'\s+', '-', slug).strip('-')
        
        # Check if slug exists (exclude current post if editing)
        slug_check = supabase.table("blog_posts").select("id").eq("slug", slug)
        if post_id:
            slug_check = slug_check.neq("id", post_id)
        existing_slug = slug_check.execute()
        
        if existing_slug.data:
            slug = f"{slug}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Build post data with only the fields that exist in the table
        post_data = {
            "title": title,
            "slug": slug,
            "content": content,
            "excerpt": excerpt or content[:200] + "..." if len(content) > 200 else content,
            "status": status,
            "author_id": user["id"],
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Add optional fields if they have values
        if category_id:
            post_data["category_id"] = int(category_id)
        if featured_image:
            post_data["featured_image"] = featured_image
        if tags:
            post_data["tags"] = tags
        
        # Try to add meta fields, but don't fail if they don't exist
        try:
            if meta_title or title:
                post_data["meta_description"] = meta_description or excerpt or (content[:200] + "..." if len(content) > 200 else content)
        except:
            pass
        
        if post_id:
            # Update existing post
            try:
                existing_post = supabase.table("blog_posts").select("published_at").eq("id", post_id).execute().data[0]
                if status == "published" and not existing_post.get("published_at"):
                    post_data["published_at"] = datetime.utcnow().isoformat()
            except:
                pass  # If we can't check published_at, continue anyway
            
            supabase.table("blog_posts").update(post_data).eq("id", post_id).execute()
            flash("Blog post updated successfully!", "success")
        else:
            # Create new post
            post_data["created_at"] = datetime.utcnow().isoformat()
            if status == "published":
                post_data["published_at"] = datetime.utcnow().isoformat()
            
            supabase.table("blog_posts").insert(post_data).execute()
            flash("Blog post created successfully!", "success")
        
        return redirect(url_for("admin_blog_posts"))
        
    except Exception as e:
        print(f"Error saving blog post: {e}")
        flash("Error saving blog post.", "error")
        return redirect(request.url)

@app.route("/admin/blog/post/<int:post_id>/delete", methods=["POST"])
@login_required
def admin_delete_blog_post(post_id):
    """Delete blog post"""
    user = current_user()
    admin_emails = ["admin@linklyst.space", "support@automatexpo.com"]
    
    if not user or user.get("email") not in admin_emails:
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("dashboard"))
    
    try:
        supabase.table("blog_posts").delete().eq("id", post_id).execute()
        flash("Blog post deleted successfully!", "success")
    except Exception as e:
        print(f"Error deleting blog post: {e}")
        flash("Error deleting blog post.", "error")
    
    return redirect(url_for("admin_blog_posts"))

@app.route("/admin/blog")
@login_required
def admin_blog_dashboard():
    """Admin blog dashboard with overview stats"""
    user = current_user()
    admin_emails = ["admin@linklyst.space", "support@automatexpo.com"]
    
    if not user or user.get("email") not in admin_emails:
        flash("Access denied. Admin privileges required.", "error")
        return redirect(url_for("dashboard"))
    
    try:
        # Get blog stats
        total_posts = supabase.table("blog_posts").select("id", count="exact").execute().count or 0
        published_posts = supabase.table("blog_posts").select("id", count="exact").eq("status", "published").execute().count or 0
        draft_posts = supabase.table("blog_posts").select("id", count="exact").eq("status", "draft").execute().count or 0
        
        # Get recent posts
        recent_posts_result = supabase.table("blog_posts").select("*").order("created_at", desc=True).limit(5).execute()
        recent_posts = recent_posts_result.data if recent_posts_result.data else []
        
        stats = {
            'total_posts': total_posts,
            'published_posts': published_posts,
            'draft_posts': draft_posts,
        }
        
        return render_template("admin/blog_dashboard.html", stats=stats, recent_posts=recent_posts)
    except Exception as e:
        print(f"Error in admin_blog_dashboard: {e}")
        flash("Error loading dashboard.", "error")
        return redirect(url_for("dashboard"))

# --- Blog System Routes ---
def convert_blog_post_dates(posts):
    """Convert string dates to datetime objects for template compatibility"""
    from datetime import datetime
    
    if not posts:
        return posts
        
    for post in posts:
        # Convert string dates to datetime objects for template strftime compatibility
        for date_field in ['published_at', 'created_at', 'updated_at']:
            if post.get(date_field) and isinstance(post[date_field], str):
                try:
                    # Parse ISO format date string
                    post[date_field] = datetime.fromisoformat(post[date_field].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    # If parsing fails, set to None
                    post[date_field] = None
    return posts

@app.route("/blog")
def blog_index():
    """Blog homepage with SEO optimization"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 12
        offset = (page - 1) * per_page
        
        # Get published posts with pagination
        posts_query = supabase.table("blog_posts").select("*").eq("status", "published").order("published_at", desc=True).range(offset, offset + per_page - 1)
        posts_result = posts_query.execute()
        
        # Get total count for pagination
        count_result = supabase.table("blog_posts").select("id", count="exact").eq("status", "published").execute()
        total_posts = count_result.count if hasattr(count_result, 'count') else 0
        
        # Get featured posts (latest 3)
        featured_result = supabase.table("blog_posts").select("*").eq("status", "published").order("published_at", desc=True).limit(3).execute()
        
        # Get categories with post counts
        categories_result = supabase.table("blog_categories").select("*").execute()
        
        posts = posts_result.data if posts_result.data else []
        featured_posts = featured_result.data if featured_result.data else []
        categories = categories_result.data if categories_result.data else []
        
        # Convert string dates to datetime objects for template compatibility
        posts = convert_blog_post_dates(posts)
        featured_posts = convert_blog_post_dates(featured_posts)
        

        # Calculate pagination info
        has_prev = page > 1
        has_next = (page * per_page) < total_posts
        prev_num = page - 1 if has_prev else None
        next_num = page + 1 if has_next else None
        
        return render_template("blog/index.html", 
                             posts=posts, 
                             featured_posts=featured_posts,
                             categories=categories,
                             page=page,
                             has_prev=has_prev,
                             has_next=has_next,
                             prev_num=prev_num,
                             next_num=next_num,
                             total_posts=total_posts)
    except Exception as e:
        print(f"Error in blog_index: {e}")
        return render_template("blog/index.html", posts=[], featured_posts=[], categories=[], page=1, has_prev=False, has_next=False, prev_num=None, next_num=None, total_posts=0)

@app.route("/blog/<slug>")
def blog_post(slug):
    """Individual blog post with full SEO optimization"""
    try:
        # Get blog post
        post_result = supabase.table("blog_posts").select("*").eq("slug", slug).eq("status", "published").execute()
        
        if not post_result.data:
            abort(404)
        
        post = post_result.data[0]
        
        # Convert string dates to datetime objects for template compatibility
        post = convert_blog_post_dates([post])[0]
        
        # Increment view count
        try:
            supabase.table("blog_posts").update({"views": post.get("views", 0) + 1}).eq("id", post["id"]).execute()
            post["views"] = post.get("views", 0) + 1
        except:
            pass  # Don't fail if view count update fails
        
        # Get related posts (same category, exclude current)
        related_posts = []
        if post.get("category_id"):
            related_result = supabase.table("blog_posts").select("*").eq("category_id", post["category_id"]).neq("id", post["id"]).eq("status", "published").order("published_at", desc=True).limit(3).execute()
            related_posts = related_result.data if related_result.data else []
            related_posts = convert_blog_post_dates(related_posts)
        
        return render_template("blog/post.html", 
                             post=post, 
                             related_posts=related_posts)
    except Exception as e:
        print(f"Error in blog_post: {e}")
        abort(404)

if __name__ == "__main__":
    # For local development only
    app.run(debug=False, host="127.0.0.1", port=5000)