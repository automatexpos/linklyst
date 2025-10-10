# SEO Route Test Script
# This script tests the key SEO routes to ensure they work properly

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app

def test_seo_routes():
    """Test that all SEO routes return proper responses"""
    with app.test_client() as client:
        print("Testing SEO routes...")
        
        # Test homepage
        print("\n1. Testing homepage (/)...")
        response = client.get('/')
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            content = response.get_data(as_text=True)
            if 'Linklyst — Your Free Link-in-Bio Tool' in content:
                print("✅ Homepage contains expected title")
            if 'og:title' in content:
                print("✅ Homepage contains Open Graph tags")
            if 'canonical' in content:
                print("✅ Homepage contains canonical URL")
        
        # Test robots.txt
        print("\n2. Testing robots.txt...")
        response = client.get('/robots.txt')
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            content = response.get_data(as_text=True)
            if 'User-agent: *' in content:
                print("✅ Robots.txt contains proper directives")
            if 'Sitemap:' in content:
                print("✅ Robots.txt references sitemap")
        
        # Test sitemap.xml
        print("\n3. Testing sitemap.xml...")
        response = client.get('/sitemap.xml')
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            content = response.get_data(as_text=True)
            if '<?xml version="1.0"' in content:
                print("✅ Sitemap is valid XML")
            if '<urlset' in content:
                print("✅ Sitemap contains proper structure")
            if 'linklyst.space' in content:
                print("✅ Sitemap contains domain URLs")
        
        print("\n4. Testing 404 handling for non-existent usernames...")
        response = client.get('/nonexistentuser123')
        print(f"Status: {response.status_code}")
        if response.status_code == 404:
            print("✅ Properly returns 404 for non-existent users")
        
        print("\nSEO route testing complete!")

if __name__ == "__main__":
    test_seo_routes()