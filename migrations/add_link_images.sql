-- Add image_url column to links table for auto-detected product images
ALTER TABLE links ADD COLUMN image_url text;

-- Add index for performance
CREATE INDEX idx_links_image_url ON links(image_url) WHERE image_url IS NOT NULL;