-- Quick migration to rename position column to sort_order
-- Use this if you have existing data you want to preserve

-- Rename the column in the links table
ALTER TABLE links RENAME COLUMN position TO sort_order;

-- Update the index name
DROP INDEX IF EXISTS ix_links_user_pos;
CREATE INDEX ix_links_user_sort ON links(user_id, sort_order);

-- Update the sample data function if it exists
DROP FUNCTION IF EXISTS get_public_links(bigint);

-- Recreate the function with correct column name
CREATE OR REPLACE FUNCTION get_public_links(profile_user_id bigint)
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
  JOIN users u ON l.user_id = u.id
  WHERE l.user_id = profile_user_id 
    AND l.is_active = true 
    AND l.is_public = true 
    AND u.is_active = true
  ORDER BY l.sort_order ASC, l.created_at ASC;
END;
$$ LANGUAGE plpgsql;