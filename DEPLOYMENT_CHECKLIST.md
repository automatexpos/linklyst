# 🚀 Vercel Deployment Checklist

## Pre-Deployment Setup

### 1. Supabase Database
- [ ] Supabase project created
- [ ] All SQL migrations from `migrations/` folder applied
- [ ] Database tables confirmed working
- [ ] RLS policies configured (if needed)
- [ ] API keys copied (URL + anon key)

### 2. Google OAuth Configuration
- [ ] Google Cloud Project created
- [ ] OAuth 2.0 credentials generated
- [ ] Authorized redirect URIs configured:
  - [ ] `http://localhost:5000/auth/google/callback` (development)
  - [ ] `https://your-domain.vercel.app/auth/google/callback` (production)
- [ ] Client ID and Secret saved

### 3. Cloudinary (Optional)
- [ ] Cloudinary account created
- [ ] Cloud name, API key, and secret copied

## Vercel Deployment

### 4. Repository Setup
- [ ] Code pushed to GitHub
- [ ] All development files removed
- [ ] `.env` not committed (should be in `.gitignore`)

### 5. Vercel Configuration
- [ ] Repository imported to Vercel
- [ ] Environment variables configured in Vercel dashboard:

```bash
# Required
FLASK_SECRET_KEY=your-secret-key-here
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your-anon-key
SITE_BASE=https://your-app.vercel.app
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret  
GOOGLE_REDIRECT_URI=https://your-app.vercel.app/auth/google/callback

# Optional (for file uploads)
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
```

### 6. First Deployment
- [ ] Deploy button clicked in Vercel
- [ ] Build completed successfully
- [ ] Domain assigned by Vercel

## Post-Deployment Testing

### 7. Basic Functionality
- [ ] Homepage loads correctly
- [ ] Registration works
- [ ] Login works (email/password)
- [ ] Google OAuth works
- [ ] Dashboard loads for logged-in users
- [ ] Categories and links can be created
- [ ] Public profiles work (`/u/username`)
- [ ] Click tracking works (`/r/link_id`)

### 8. Database Operations
- [ ] User registration creates database records
- [ ] Link creation stores in database
- [ ] Click tracking records clicks
- [ ] Categories and subcategories work

### 9. OAuth Flow
- [ ] "Login with Google" redirects correctly
- [ ] Google authorization completes
- [ ] User account created/linked properly
- [ ] Redirect back to application works

### 10. Admin Features (if applicable)
- [ ] Admin login works (`support@automatexpo.com`)
- [ ] Blog admin panel accessible
- [ ] Blog posts can be created/edited
- [ ] Blog routes work (`/blog`, `/blog/post-slug`)

## Final Steps

### 11. Production Cleanup
- [ ] Remove debug logging from production
- [ ] Confirm all hardcoded localhost URLs updated
- [ ] Test on different devices/browsers
- [ ] Monitor Vercel function usage
- [ ] Set up custom domain (optional)

### 12. Monitoring
- [ ] Vercel analytics enabled
- [ ] Supabase usage monitored
- [ ] Error tracking configured
- [ ] Backup strategy in place

## Rollback Plan

If deployment fails:
1. Check Vercel function logs
2. Verify environment variables
3. Test database connectivity
4. Check Google OAuth configuration
5. Rollback to previous deployment if needed

## Common Issues

- **OAuth redirect_uri_mismatch**: Update Google Console with correct Vercel domain
- **Database connection failed**: Check Supabase URL and key in Vercel env vars
- **Static files not loading**: Ensure `/static` folder is properly deployed
- **Import errors**: Check all dependencies in `requirements.txt`