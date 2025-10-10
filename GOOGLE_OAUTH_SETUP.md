# Google OAuth Setup Instructions

## 1. Google Cloud Console Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google+ API" and enable it
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Choose "Web application"
   - Add authorized redirect URIs:
     - For local development: `http://localhost:5000/auth/google/callback`
     - For production: `https://yourdomain.com/auth/google/callback`
   - Save the Client ID and Client Secret

## 2. Environment Variables Setup

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Update the following variables in `.env`:
- `GOOGLE_CLIENT_ID`: Your Google OAuth Client ID
- `GOOGLE_CLIENT_SECRET`: Your Google OAuth Client Secret
- `GOOGLE_REDIRECT_URI`: Your callback URL (should match what you set in Google Console)

## 3. Database Migration

Run the SQL migration to add Google OAuth support:

1. Go to your Supabase dashboard
2. Open the SQL editor
3. Copy and paste the contents of `migrations/add_google_oauth.sql`
4. Run the migration

## 4. Install Dependencies

Install the new OAuth dependency:

```bash
pip install -r requirements.txt
```

## 5. Test the Integration

1. Start your Flask app: `python app.py`
2. Go to the login page
3. Click "Continue with Google"
4. Complete the OAuth flow
5. You should be logged in and redirected to the dashboard

## Features

### For Users:
- **Sign up with Google**: New users can create accounts using their Google account
- **Login with Google**: Existing Google users can log in with one click
- **Account Linking**: Users who created traditional accounts can link their Google account
- **Hybrid Authentication**: Users can choose between traditional email/password or Google OAuth

### For Developers:
- **Secure OAuth Flow**: Proper state management and error handling
- **Database Integration**: Google user data is stored in your existing user structure
- **Fallback Support**: Traditional authentication still works alongside OAuth
- **User Experience**: Clear messaging for different authentication scenarios

## Security Notes

- OAuth state is properly managed to prevent CSRF attacks
- Google user information is validated before account creation
- Existing accounts are safely linked when using the same email
- Passwords are not required for OAuth-only users