#!/usr/bin/env python3
"""
Generate optimized favicon files from the logo
"""
import os
import subprocess
import sys
from pathlib import Path

def create_favicons():
    """Create properly sized favicon files from logo.png"""
    
    try:
        from PIL import Image
    except ImportError:
        print("❌ PIL (Pillow) is not installed. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
        try:
            from PIL import Image
        except ImportError:
            print("❌ Failed to install Pillow. Please install manually: pip install Pillow")
            return False
    
    static_dir = Path("static")
    logo_path = static_dir / "logo.png"
    
    if not logo_path.exists():
        print(f"❌ Logo file not found: {logo_path}")
        return False
    
    print("🖼️  Generating optimized favicon files from logo...")
    print("=" * 50)
    
    try:
        # Open the original logo
        with Image.open(logo_path) as logo:
            # Convert to RGBA if not already
            if logo.mode != 'RGBA':
                logo = logo.convert('RGBA')
            
            # Define favicon sizes to generate
            favicon_configs = [
                ("favicon-16x16.png", 16, "PNG"),
                ("favicon-32x32.png", 32, "PNG"), 
                ("favicon.png", 192, "PNG"),  # For web manifest
                ("apple-touch-icon.png", 180, "PNG"),  # Apple devices
            ]
            
            for filename, size, format_type in favicon_configs:
                # Resize with high quality
                resized = logo.resize((size, size), Image.Resampling.LANCZOS)
                
                # Save the resized image
                output_path = static_dir / filename
                resized.save(output_path, format_type, optimize=True, quality=95)
                
                file_size = output_path.stat().st_size
                print(f"✅ {filename} - {size}x{size}px - {file_size:,} bytes ({file_size/1024:.1f} KB)")
            
            # Create ICO file with multiple sizes
            ico_sizes = [16, 32, 48]
            ico_images = []
            
            for size in ico_sizes:
                resized = logo.resize((size, size), Image.Resampling.LANCZOS)
                ico_images.append(resized)
            
            # Save as ICO
            ico_path = static_dir / "favicon.ico"
            ico_images[0].save(
                ico_path, 
                format='ICO', 
                sizes=[(img.width, img.height) for img in ico_images],
                append_images=ico_images[1:],
                optimize=True
            )
            
            ico_size = ico_path.stat().st_size
            print(f"✅ favicon.ico - Multi-size ICO - {ico_size:,} bytes ({ico_size/1024:.1f} KB)")
            
        print("\n🎉 All favicon files generated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error generating favicons: {str(e)}")
        return False

if __name__ == "__main__":
    success = create_favicons()
    if success:
        print("\n📋 Next steps:")
        print("1. The updated favicon files are ready")
        print("2. Deploy your changes to production")
        print("3. Test the favicon URLs")
        print("4. Submit to Google Search Console for re-indexing")
    exit(0 if success else 1)