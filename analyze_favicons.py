#!/usr/bin/env python3
"""
Check favicon file signatures and optimize them for web use
"""
import os
from pathlib import Path

def check_file_signature(filepath):
    """Check the file signature to determine actual file type"""
    with open(filepath, 'rb') as f:
        signature = f.read(16)
    
    # Common file signatures
    if signature.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'PNG'
    elif signature.startswith(b'\xff\xd8\xff'):
        return 'JPEG'
    elif signature.startswith(b'GIF'):
        return 'GIF'
    elif signature.startswith(b'\x00\x00\x01\x00') or signature.startswith(b'\x00\x00\x02\x00'):
        return 'ICO'
    elif signature.startswith(b'<svg') or signature.startswith(b'<?xml'):
        return 'SVG'
    else:
        return f'Unknown (starts with: {signature[:8].hex()})'

def analyze_favicon_files():
    """Analyze all favicon files in the static directory"""
    static_dir = Path("static")
    
    favicon_files = [
        "favicon.ico",
        "favicon.png", 
        "favicon-16x16.png",
        "favicon-32x32.png",
        "apple-touch-icon.png"
    ]
    
    print("📁 Analyzing favicon files...")
    print("=" * 50)
    
    for filename in favicon_files:
        filepath = static_dir / filename
        if filepath.exists():
            file_size = filepath.stat().st_size
            file_type = check_file_signature(filepath)
            
            print(f"📄 {filename}")
            print(f"   Size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
            print(f"   Type: {file_type}")
            
            # Check if file is oversized
            if filename.endswith('.ico') and file_size > 50000:  # 50KB
                print("   ⚠️  ICO file is quite large for a favicon")
            elif filename.endswith('.png') and file_size > 20000:  # 20KB
                print("   ⚠️  PNG file is quite large for a favicon")
            
            print()
        else:
            print(f"❌ {filename} - File not found")
    
    # Check if all files are identical
    file_sizes = []
    for filename in favicon_files:
        filepath = static_dir / filename
        if filepath.exists():
            file_sizes.append(filepath.stat().st_size)
    
    if len(set(file_sizes)) == 1 and len(file_sizes) > 1:
        print("⚠️  WARNING: All favicon files have the same size - they might be identical!")
        print("   Consider creating properly sized versions for each file.")

if __name__ == "__main__":
    analyze_favicon_files()