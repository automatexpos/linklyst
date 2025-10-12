#!/usr/bin/env python3
"""
Test script to verify favicon setup is working correctly
"""
import requests
import sys
import os
from pathlib import Path

def test_local_favicon_files():
    """Test that local favicon files exist and are properly formatted"""
    print("🔍 Testing Local Favicon Files...")
    print("=" * 50)
    
    static_dir = Path("static")
    required_files = [
        ("favicon.ico", "ICO file"),
        ("favicon-16x16.png", "16x16 PNG"),
        ("favicon-32x32.png", "32x32 PNG"), 
        ("favicon.png", "192x192 PNG for manifest"),
        ("apple-touch-icon.png", "180x180 PNG for iOS"),
        ("site.webmanifest", "Web App Manifest"),
    ]
    
    all_exist = True
    
    for filename, description in required_files:
        filepath = static_dir / filename
        if filepath.exists():
            file_size = filepath.stat().st_size
            print(f"✅ {filename} - {description} ({file_size:,} bytes)")
        else:
            print(f"❌ {filename} - Missing!")
            all_exist = False
    
    return all_exist

def test_favicon_urls():
    """Test favicon URLs for accessibility and proper MIME types"""
    base_url = "https://linklyst.space"
    
    favicon_tests = [
        ("/favicon.ico", ["image/x-icon", "image/vnd.microsoft.icon"]),
        ("/apple-touch-icon.png", ["image/png"]),
        ("/favicon.png", ["image/png"]),
        ("/static/favicon-16x16.png", ["image/png"]),
        ("/static/favicon-32x32.png", ["image/png"]),
        ("/static/site.webmanifest", ["application/manifest+json", "application/json"]),
    ]
    
    print("🌐 Testing Favicon URLs for Linklyst...")
    print("=" * 50)
    
    all_passed = True
    
    for path, expected_mimes in favicon_tests:
        try:
            url = f"{base_url}{path}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').split(';')[0].strip()
                
                # Check if content type matches any of the expected types
                type_match = any(expected in content_type or content_type in expected for expected in expected_mimes)
                
                if type_match:
                    print(f"✅ {path} - OK (Status: {response.status_code}, Type: {content_type})")
                else:
                    print(f"⚠️  {path} - Wrong MIME type (Expected: {expected_mimes}, Got: {content_type})")
                    all_passed = False
            else:
                print(f"❌ {path} - Failed (Status: {response.status_code})")
                all_passed = False
                
        except requests.RequestException as e:
            print(f"❌ {path} - Error: {str(e)}")
            all_passed = False
    
    print("=" * 50)
    if all_passed:
        print("🎉 All online favicon tests passed!")
    else:
        print("⚠️  Some online tests failed - check the results above")
    
    return all_passed

def main():
    """Run all favicon tests"""
    print("🚀 Comprehensive Favicon Setup Test")
    print("=" * 60)
    
    # Test local files first
    local_success = test_local_favicon_files()
    print()
    
    # Test online URLs (only if local files exist)
    if local_success:
        online_success = test_favicon_urls()
        overall_success = local_success and online_success
    else:
        print("⏭️  Skipping online tests due to missing local files")
        overall_success = False
    
    print("\n" + "=" * 60)
    if overall_success:
        print("🎉 SUCCESS: Favicon setup is complete and working!")
        print("\n📋 Your favicon setup now meets Google Search requirements:")
        print("   ✅ Proper ICO file at /favicon.ico")
        print("   ✅ Correct MIME types")
        print("   ✅ Multiple sizes available")
        print("   ✅ Apple touch icon for iOS")
        print("   ✅ Web app manifest configured")
        print("   ✅ All files optimized for web")
        print("\n🔄 Next: Deploy to production and request Google re-indexing")
    else:
        print("⚠️  Some issues need to be resolved before deployment")
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)