from flask import Flask, redirect, url_for, session, request
from requests_oauthlib import OAuth2Session
import os

# Allow insecure transport for local development (HTTP instead of HTTPS)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
# Use a fixed secret key for development to maintain sessions across restarts
app.secret_key = "your-secret-key-for-development"

# Replace with your credentials - you can also use environment variables
CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "99509622971-ojflcvsc9667aveghpt3qk8qmna6jlks.apps.googleusercontent.com")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "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")
REDIRECT_URI = "http://127.0.0.1:5000/callback"

AUTHORIZATION_BASE_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://accounts.google.com/o/oauth2/token"
USER_INFO_URL = "https://www.googleapis.com/oauth2/v1/userinfo"

@app.route("/")
def index():
    return '<a href="/login">Login with Google</a>'

@app.route("/login")
def login():
    google = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=["openid", "email", "profile"])
    authorization_url, state = google.authorization_url(AUTHORIZATION_BASE_URL, access_type="offline", prompt="select_account")
    session["oauth_state"] = state
    return redirect(authorization_url)

@app.route("/callback")
def callback():
    # Debug: Print session contents
    print(f"Session contents: {dict(session)}")
    
    # Check if oauth_state exists in session
    if "oauth_state" not in session:
        return "Error: OAuth state not found in session. Please try logging in again.", 400
    
    try:
        google = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, state=session["oauth_state"])
        
        # Debug information
        print(f"CLIENT_ID: {CLIENT_ID}")
        print(f"REDIRECT_URI: {REDIRECT_URI}")
        print(f"Authorization response URL: {request.url}")
        
        token = google.fetch_token(
            TOKEN_URL, 
            client_secret=CLIENT_SECRET, 
            authorization_response=request.url,
            include_client_id=True
        )
        
        session["oauth_token"] = token
        user_info = google.get(USER_INFO_URL).json()
        
        # Example: Store in DB here
        email = user_info["email"]
        name = user_info["name"]
        
        # Clear the oauth_state from session after successful authentication
        session.pop("oauth_state", None)
        
        return f"Hello {name}, your email is {email}"
    except Exception as e:
        print(f"Full error details: {e}")
        return f"Error during OAuth callback: {str(e)}<br><br>Check the console for more details.", 500

if __name__ == "__main__":
    app.run(debug=True)
