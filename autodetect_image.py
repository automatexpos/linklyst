import os
import requests
from bs4 import BeautifulSoup
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

# Load environment variables (Cloudinary credentials)
load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

def scrape_product(link):
    """
    Detects product name and main product image URL from a link.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(link, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')

    # Extract product name (typical for many sites)
    title = (
        soup.find("meta", property="og:title")
        or soup.find("h1")
        or soup.find("title")
    )
    product_name = title["content"] if title and title.has_attr("content") else title.text.strip()

    # Extract main product image
    image = soup.find("meta", property="og:image")
    product_image_url = image["content"] if image and image.has_attr("content") else None

    return product_name, product_image_url


def upload_to_cloudinary(image_url):
    """
    Uploads an image URL to Cloudinary and returns the uploaded URL.
    """
    upload_result = cloudinary.uploader.upload(image_url)
    return upload_result["secure_url"]


if __name__ == "__main__":
    link = input("Enter product link: ")

    product_name, product_image_url = scrape_product(link)

    if not product_image_url:
        print("Could not find product image automatically.")
    else:
        print(f"Product Name: {product_name}")
        print(f"Product Image URL: {product_image_url}")

        uploaded_url = upload_to_cloudinary(product_image_url)
        print("Uploaded to Cloudinary:", uploaded_url)
