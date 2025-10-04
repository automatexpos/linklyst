-- ========================================
-- CATEGORY SYSTEM EXTENSION
-- Add categories and brands to the existing schema
-- ========================================

-- Categories table
CREATE TABLE categories (
  id bigserial PRIMARY KEY,
  user_id bigint REFERENCES users(id) ON DELETE CASCADE,
  name text NOT NULL CHECK (length(name) >= 1 AND length(name) <= 100),
  description text CHECK (length(description) <= 500),
  icon_url text,
  color text DEFAULT '#6366f1' CHECK (color ~* '^#[0-9A-Fa-f]{6}$'),
  sort_order integer DEFAULT 0,
  is_active boolean DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(user_id, name)
);

-- Brands table (subcategories)
CREATE TABLE brands (
  id bigserial PRIMARY KEY,
  category_id bigint REFERENCES categories(id) ON DELETE CASCADE,
  user_id bigint REFERENCES users(id) ON DELETE CASCADE,
  name text NOT NULL CHECK (length(name) >= 1 AND length(name) <= 100),
  description text CHECK (length(description) <= 500),
  logo_url text,
  website_url text,
  sort_order integer DEFAULT 0,
  is_active boolean DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(category_id, name)
);

-- Update links table to reference brands instead of direct user links
ALTER TABLE links ADD COLUMN brand_id bigint REFERENCES brands(id) ON DELETE CASCADE;

-- Make user_id optional for links since they'll be linked through brands
ALTER TABLE links ALTER COLUMN user_id DROP NOT NULL;

-- Add indexes for performance
CREATE INDEX idx_categories_user_id ON categories(user_id);
CREATE INDEX idx_categories_user_sort ON categories(user_id, sort_order);
CREATE INDEX idx_categories_active ON categories(is_active);

CREATE INDEX idx_brands_category_id ON brands(category_id);
CREATE INDEX idx_brands_user_id ON brands(user_id);
CREATE INDEX idx_brands_category_sort ON brands(category_id, sort_order);
CREATE INDEX idx_brands_active ON brands(is_active);

CREATE INDEX idx_links_brand_id ON links(brand_id);

-- Update existing triggers for new tables
CREATE TRIGGER update_categories_updated_at 
  BEFORE UPDATE ON categories 
  FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_brands_updated_at 
  BEFORE UPDATE ON brands 
  FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

-- ========================================
-- HELPER FUNCTIONS FOR CATEGORY SYSTEM
-- ========================================

-- Function to get categories for a user
CREATE OR REPLACE FUNCTION get_user_categories(p_user_id bigint)
RETURNS TABLE (
  id bigint,
  name text,
  description text,
  icon_url text,
  color text,
  sort_order integer,
  brand_count bigint
)
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    c.id,
    c.name,
    c.description,
    c.icon_url,
    c.color,
    c.sort_order,
    COUNT(b.id) as brand_count
  FROM categories c
  LEFT JOIN brands b ON c.id = b.category_id AND b.is_active = true
  WHERE c.user_id = p_user_id 
    AND c.is_active = true
  GROUP BY c.id, c.name, c.description, c.icon_url, c.color, c.sort_order
  ORDER BY c.sort_order ASC, c.created_at ASC;
END;
$$ LANGUAGE plpgsql;

-- Function to get brands for a category
CREATE OR REPLACE FUNCTION get_category_brands(p_category_id bigint)
RETURNS TABLE (
  id bigint,
  name text,
  description text,
  logo_url text,
  website_url text,
  sort_order integer,
  link_count bigint
)
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    b.id,
    b.name,
    b.description,
    b.logo_url,
    b.website_url,
    b.sort_order,
    COUNT(l.id) as link_count
  FROM brands b
  LEFT JOIN links l ON b.id = l.brand_id AND l.is_active = true AND l.is_public = true
  WHERE b.category_id = p_category_id 
    AND b.is_active = true
  GROUP BY b.id, b.name, b.description, b.logo_url, b.website_url, b.sort_order
  ORDER BY b.sort_order ASC, b.created_at ASC;
END;
$$ LANGUAGE plpgsql;

-- Function to get links for a brand
CREATE OR REPLACE FUNCTION get_brand_links(p_brand_id bigint)
RETURNS TABLE (
  id bigint,
  title text,
  url text,
  description text,
  sort_order integer,
  click_count integer
)
SECURITY DEFINER
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    l.id,
    l.title,
    l.url,
    l.description,
    l.sort_order,
    l.click_count
  FROM links l
  WHERE l.brand_id = p_brand_id 
    AND l.is_active = true 
    AND l.is_public = true
  ORDER BY l.sort_order ASC, l.created_at ASC;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT EXECUTE ON FUNCTION get_user_categories(bigint) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_category_brands(bigint) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION get_brand_links(bigint) TO anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE ON categories TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON brands TO authenticated;
GRANT USAGE ON SEQUENCE categories_id_seq TO authenticated;
GRANT USAGE ON SEQUENCE brands_id_seq TO authenticated;

-- ========================================
-- SAMPLE DATA (Optional - for testing)
-- ========================================

-- Sample categories
/*
INSERT INTO categories (user_id, name, description, color, sort_order) VALUES 
(1, 'Bags', 'Luxury handbags and accessories', '#8b5cf6', 1),
(1, 'Shoes', 'Designer footwear collection', '#06b6d4', 2),
(1, 'Watches', 'Premium timepieces', '#f59e0b', 3);

-- Sample brands
INSERT INTO brands (category_id, user_id, name, description, sort_order) VALUES 
(1, 1, 'Gucci', 'Italian luxury fashion house', 1),
(1, 1, 'Prada', 'Milan-based luxury fashion house', 2),
(1, 1, 'Louis Vuitton', 'French fashion house', 3),
(2, 1, 'Nike', 'American athletic footwear', 1),
(2, 1, 'Adidas', 'German sportswear manufacturer', 2),
(3, 1, 'Rolex', 'Swiss luxury watch manufacturer', 1);
*/