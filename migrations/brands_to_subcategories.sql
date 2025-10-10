-- ========================================
-- UPDATE BRANDS TO SUBCATEGORIES MIGRATION
-- Rename brands table to subcategories and add direct category links support
-- ========================================

-- Step 1: Create the new subcategories table (renamed from brands)
CREATE TABLE subcategories (
  id bigserial PRIMARY KEY,
  category_id bigint REFERENCES categories(id) ON DELETE CASCADE,
  user_id bigint REFERENCES users(id) ON DELETE CASCADE,
  name text NOT NULL CHECK (length(name) >= 1 AND length(name) <= 100),
  description text CHECK (length(description) <= 500),
  icon_url text,
  color text DEFAULT '#6366f1' CHECK (color ~* '^#[0-9A-Fa-f]{6}$'),
  sort_order integer DEFAULT 0,
  is_active boolean DEFAULT true,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now(),
  UNIQUE(category_id, name)
);

-- Step 2: Copy existing brands data to subcategories
INSERT INTO subcategories (
  id, category_id, user_id, name, description, 
  icon_url, sort_order, is_active, created_at, updated_at
)
SELECT 
  id, category_id, user_id, name, description,
  logo_url as icon_url, sort_order, is_active, created_at, updated_at
FROM brands;

-- Step 3: Update sequence for subcategories to continue from brands max id
SELECT setval('subcategories_id_seq', (SELECT COALESCE(MAX(id), 1) FROM subcategories));

-- Step 4: Add subcategory_id column to links table
ALTER TABLE links ADD COLUMN subcategory_id bigint REFERENCES subcategories(id) ON DELETE CASCADE;

-- Step 5: Update existing links to use subcategory_id instead of brand_id
UPDATE links SET subcategory_id = brand_id WHERE brand_id IS NOT NULL;

-- Step 6: Add category_id column to links for direct category links
ALTER TABLE links ADD COLUMN category_id bigint REFERENCES categories(id) ON DELETE CASCADE;

-- Step 7: Add constraint to ensure links belong to either subcategory OR category (but not both)
ALTER TABLE links ADD CONSTRAINT links_parent_check 
  CHECK (
    (subcategory_id IS NOT NULL AND category_id IS NULL) OR 
    (subcategory_id IS NULL AND category_id IS NOT NULL)
  );

-- Step 8: Create indexes for performance
CREATE INDEX idx_subcategories_category_id ON subcategories(category_id);
CREATE INDEX idx_subcategories_user_id ON subcategories(user_id);
CREATE INDEX idx_subcategories_category_sort ON subcategories(category_id, sort_order);
CREATE INDEX idx_subcategories_active ON subcategories(is_active);

CREATE INDEX idx_links_subcategory_id ON links(subcategory_id);
CREATE INDEX idx_links_category_id ON links(category_id);

-- Step 9: Update triggers for subcategories
CREATE TRIGGER update_subcategories_updated_at 
  BEFORE UPDATE ON subcategories 
  FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

-- Step 10: Remove old brand_id column from links (after data migration)
ALTER TABLE links DROP COLUMN brand_id;

-- Step 11: Drop the old brands table
DROP TABLE brands CASCADE;

-- ========================================
-- MIGRATION VERIFICATION QUERIES
-- ========================================

-- Verify the migration worked correctly
-- SELECT 'Subcategories created:', COUNT(*) FROM subcategories;
-- SELECT 'Links with subcategories:', COUNT(*) FROM links WHERE subcategory_id IS NOT NULL;
-- SELECT 'Links ready for direct category assignment:', COUNT(*) FROM links WHERE category_id IS NULL AND subcategory_id IS NULL;

-- ========================================
-- ROLLBACK INSTRUCTIONS (if needed)
-- ========================================

/*
-- To rollback this migration (create new migration file):

-- Recreate brands table
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

-- Copy data back
INSERT INTO brands SELECT * FROM subcategories;

-- Update links table
ALTER TABLE links ADD COLUMN brand_id bigint REFERENCES brands(id) ON DELETE CASCADE;
UPDATE links SET brand_id = subcategory_id WHERE subcategory_id IS NOT NULL;
ALTER TABLE links DROP COLUMN subcategory_id;
ALTER TABLE links DROP COLUMN category_id;
ALTER TABLE links DROP CONSTRAINT links_parent_check;

-- Drop subcategories table
DROP TABLE subcategories CASCADE;
*/