# LinkLyst - Personal Link Management Platform

LinkLyst is a Flask-based web application that allows users to organize and manage their personal links in categories and brands, with click tracking and public profile sharing capabilities.

## Features

- **User Authentication**: Traditional email/password and Google OAuth login
- **Link Organization**: Organize links by categories and brands
- **Click Tracking**: Track clicks on shared links with analytics
- **Public Profiles**: Share your curated links publicly with a custom username
- **Responsive Design**: Works on desktop and mobile devices
- **Cloud Storage**: Profile pictures via Cloudinary integration

## Tech Stack

- **Backend**: Flask (Python)
- **Database**: Supabase (PostgreSQL)
- **Authentication**: Flask sessions + Google OAuth
- **File Storage**: Cloudinary
- **Deployment**: Vercel (Serverless)

## Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd LinkLyst
   ```

2. **Set up Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Environment Configuration**
   - Copy `.env.example` to `.env`
   - Fill in your configuration values:
     - Supabase URL and API key
     - Google OAuth credentials
     - Cloudinary credentials (optional)
     - Flask secret key

4. **Database Setup**
   - Create a Supabase project
   - Run the SQL migrations from the `migrations/` folder
   - Update your `.env` with Supabase credentials

5. **Run the application**
   ```bash
   python app.py
   ```

## Vercel Deployment

### Prerequisites

1. **Supabase Database**: Set up and configure your Supabase project
2. **Google OAuth**: Configure OAuth credentials in Google Cloud Console
3. **Cloudinary Account** (optional): For profile picture uploads

### Deployment Steps

1. **Fork/Clone this repository** to your GitHub account

2. **Connect to Vercel**:
   - Go to [vercel.com](https://vercel.com)
   - Import your GitHub repository
   - Vercel will automatically detect it as a Python project

3. **Configure Environment Variables** in Vercel Dashboard:
   ```
   FLASK_SECRET_KEY=your-secret-key-here
   SUPABASE_URL=your-supabase-url
   SUPABASE_KEY=your-supabase-anon-key
   SITE_BASE=https://your-app.vercel.app
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   GOOGLE_REDIRECT_URI=https://your-app.vercel.app/auth/google/callback
   CLOUDINARY_CLOUD_NAME=your-cloudinary-name (optional)
   CLOUDINARY_API_KEY=your-cloudinary-key (optional)
   CLOUDINARY_API_SECRET=your-cloudinary-secret (optional)
   ```

4. **Update Google OAuth Settings**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Update your OAuth redirect URI to match your Vercel domain
   - Add `https://your-app.vercel.app/auth/google/callback`

5. **Deploy**: Vercel will automatically deploy when you push to your main branch

### Important Notes for Production

- **Domain Configuration**: Update `SITE_BASE` and `GOOGLE_REDIRECT_URI` to match your production domain
- **Database Migrations**: Ensure all SQL migrations are applied to your Supabase database
- **Environment Variables**: Never commit `.env` files - use Vercel's environment variable settings
- **HTTPS**: Vercel automatically provides HTTPS, which is required for Google OAuth

## File Structure

```
LinkLyst/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── runtime.txt           # Python version for Vercel
├── vercel.json           # Vercel deployment configuration
├── .vercelignore         # Files to exclude from deployment
├── .env.example          # Environment variables template
├── static/               # CSS, JS, and static assets
├── templates/            # HTML templates
├── migrations/           # Database migration files
└── README.md            # This file
```

## API Endpoints

- `/` - Homepage
- `/register` - User registration
- `/login` - User login
- `/auth/google` - Google OAuth login
- `/dashboard` - User dashboard
- `/categories` - Manage categories
- `/u/<username>` - Public profile
- `/r/<link_id>` - Link redirect (click tracking)
- `/api/stats/<username>` - Public stats API

## Database Schema

The application uses the following main tables:
- `users` - User accounts and profiles
- `categories` - Link categories
- `brands` - Brands within categories
- `links` - Individual links
- `clicks` - Click tracking data

See `migrations/` folder for complete schema.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test locally
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
1. Check the existing GitHub issues
2. Create a new issue with detailed description
3. Include error logs and configuration details (without sensitive data)

## Security

- Never commit `.env` files or API keys
- Use strong secret keys in production
- Regularly update dependencies
- Monitor Supabase and Cloudinary usage