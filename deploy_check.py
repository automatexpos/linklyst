#!/usr/bin/env python3
"""
Deployment checklist script for LinkLyst
Run this script before deploying to verify your setup
"""

import os
from pathlib import Path

def check_file_exists(filepath, required=True):
    """Check if a file exists and return status"""
    exists = Path(filepath).exists()
    status = "✅" if exists else ("❌" if required else "⚠️")
    req_text = " (required)" if required else " (optional)"
    print(f"{status} {filepath}{req_text if not exists and not required else ''}")
    return exists

def check_env_example():
    """Check if .env.example has required variables"""
    required_vars = [
        'FLASK_SECRET_KEY',
        'SUPABASE_URL', 
        'SUPABASE_KEY',
        'SITE_BASE',
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET',
        'GOOGLE_REDIRECT_URI'
    ]
    
    if not Path('.env.example').exists():
        print("❌ .env.example file not found")
        return False
        
    with open('.env.example', 'r') as f:
        content = f.read()
        
    missing = []
    for var in required_vars:
        if var not in content:
            missing.append(var)
            
    if missing:
        print(f"❌ Missing variables in .env.example: {', '.join(missing)}")
        return False
    else:
        print("✅ .env.example contains all required variables")
        return True

def main():
    print("🚀 LinkLyst Vercel Deployment Checklist")
    print("=" * 50)
    
    print("\n📁 Required Files:")
    all_good = True
    
    # Required files
    required_files = [
        'app.py',
        'requirements.txt', 
        'vercel.json',
        'runtime.txt',
        '.env.example',
        '.gitignore',
        '.vercelignore',
        'README.md'
    ]
    
    for file in required_files:
        if not check_file_exists(file, required=True):
            all_good = False
    
    print("\n📂 Required Directories:")
    required_dirs = ['static', 'templates', 'migrations']
    for dir in required_dirs:
        if not check_file_exists(dir, required=True):
            all_good = False
    
    print("\n🔧 Configuration Check:")
    if not check_env_example():
        all_good = False
    
    print("\n📋 Next Steps:")
    if all_good:
        print("✅ All files are ready for deployment!")
        print("\n🚀 To deploy:")
        print("1. Push this code to GitHub")
        print("2. Connect your GitHub repo to Vercel")  
        print("3. Add environment variables in Vercel dashboard")
        print("4. Update Google OAuth redirect URI")
        print("5. Deploy!")
    else:
        print("❌ Please fix the issues above before deploying")
    
    print(f"\n📝 Don't forget to:")
    print("- Set up your Supabase database with migrations")
    print("- Configure Google OAuth in Google Cloud Console") 
    print("- Add all environment variables in Vercel dashboard")
    print("- Update SITE_BASE and GOOGLE_REDIRECT_URI for production")

if __name__ == "__main__":
    main()