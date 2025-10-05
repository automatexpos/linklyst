import os
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, abort, jsonify
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
    return dict(user=current_user())

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
                flash("Your account has been deactivated. Please contact support.", "danger")
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
        
        print(f"Debug: Found {total_links} links for user {user_id}")
        
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
        
        print(f"Debug: Found {total_clicks} total clicks")
        
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
                print(f"Debug: Error getting trending links: {str(e)}")
        
        print(f"Debug: Analytics - Links: {total_links}, Clicks: {total_clicks}, Categories: {categories_count}, Subcategories: {subcategories_count}")
        
        return {
            "total_links": total_links,
            "total_clicks": total_clicks,
            "categories_count": categories_count,
            "subcategories_count": subcategories_count,
            "trending_links": trending_links
        }
        
    except Exception as e:
        print(f"Debug: Error in get_user_analytics: {str(e)}")
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
    u = current_user()
    if u:
        # If user is logged in, redirect to dashboard
        return redirect(url_for("dashboard"))
    else:
        # If not logged in, redirect to login
        return redirect(url_for("login"))

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
    # insert user
    res = supabase.table("users").insert({
        "email": email,
        "username": username,
        "password_hash": pw_hash
    }).execute()
    if res.data == []:
        flash("Email or username already taken","danger")
        return redirect(url_for("register"))
    user_id = res.data[0]["id"]
    supabase.table("profiles").insert({
        "user_id": user_id,
        "display_name": username
    }).execute()
    flash("Account created. Please log in.","success")
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
        flash("Your account has been deactivated. Please contact support.", "danger")
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
    print(f"Debug: OAuth callback called with URL: {request.url}")
    print(f"Debug: Session oauth_state: {session.get('oauth_state', 'NOT FOUND')}")
    print(f"Debug: Request args: {dict(request.args)}")
    
    # Check if there's an error from Google
    if 'error' in request.args:
        error = request.args.get('error')
        error_description = request.args.get('error_description', 'Unknown error')
        print(f"Debug: Google OAuth error: {error} - {error_description}")
        flash(f"Google authentication failed: {error_description}", "danger")
        return redirect(url_for("login"))
    
    # Check if oauth_state exists in session
    if "oauth_state" not in session:
        print("Debug: OAuth state not found in session")
        flash("OAuth session expired. Please try again.", "danger")
        return redirect(url_for("login"))
    
    try:
        # Use dynamic redirect URI based on current request  
        redirect_uri = url_for('google_callback', _external=True)
        print(f"Debug: Using redirect_uri: {redirect_uri}")
        
        google = OAuth2Session(
            CLIENT_ID, 
            redirect_uri=redirect_uri, 
            state=session["oauth_state"]
        )
        
        print(f"Debug: Fetching token from Google...")
        token = google.fetch_token(
            GOOGLE_TOKEN_URL, 
            client_secret=CLIENT_SECRET, 
            authorization_response=request.url,
            include_client_id=True
        )
        print(f"Debug: Token received successfully")
        
        # Get user info from Google
        print(f"Debug: Getting user info from Google...")
        user_info_response = google.get(GOOGLE_USER_INFO_URL)
        print(f"Debug: User info response status: {user_info_response.status_code}")
        
        if user_info_response.status_code != 200:
            print(f"Debug: Failed to get user info. Response: {user_info_response.text}")
            flash("Failed to get user information from Google.", "danger")
            return redirect(url_for("login"))
            
        user_info = user_info_response.json()
        print(f"Debug: User info received: {user_info}")
        
        google_id = user_info.get("id")
        email = user_info.get("email", "").lower().strip()
        name = user_info.get("name", "")
        
        print(f"Debug: Extracted - ID: {google_id}, Email: {email}, Name: {name}")
        
        if not email or not google_id:
            print("Debug: Missing email or google_id")
            flash("Failed to get user information from Google.", "danger")
            return redirect(url_for("login"))
        
        # Check if user exists with this Google ID
        existing_user = supabase.table("users").select("*").eq("google_id", google_id).execute()
        
        if existing_user.data:
            # User exists with Google ID, check if account is active
            user = existing_user.data[0]
            if not user.get("is_active", True):
                flash("Your account has been deactivated. Please contact support.", "danger")
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
                flash("Your account has been deactivated. Please contact support.", "danger")
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
        
        # Create new user with Google authentication
        new_user = supabase.table("users").insert({
            "email": email,
            "username": username,
            "google_id": google_id,
            "password_hash": None  # No password for OAuth users
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
        
        session["user_id"] = user_id
        session.pop("oauth_state", None)
        flash(f"Account created successfully! Welcome, {name}!", "success")
        return redirect(url_for("dashboard"))
        
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
        supabase.table("links").insert(link_data).execute()
        flash("Link added successfully","success")
    except Exception as e:
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
        supabase.table("links").insert(link_data).execute()
        flash("Link added successfully","success")
    except Exception as e:
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
        supabase.table("links").delete().eq("subcategory_id", subcategory_id).execute()
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
    
    return render_template("public_profile.html", profile=profile, user=user_row, categories=categories, 
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
    """Simple health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": str(datetime.now())})

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
        {'<br>'.join([f"• <strong>{link['title']}</strong> (ID: {link['id']}, Subcategory: {link.get('subcategory_id', 'Direct')}, Category: {link.get('category_id', 'N/A')})" for link in links.data]) if links.data else '❌ <strong>No links found for your user ID!</strong>'}
        
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
        <a href="/dashboard">Back to Dashboard</a>
        """