-- Blog System Migration for LinkLyst
-- Adds comprehensive blog functionality with SEO optimization

-- Blog Categories Table
CREATE TABLE blog_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    meta_description VARCHAR(160),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Blog Tags Table
CREATE TABLE blog_tags (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL UNIQUE,
    slug VARCHAR(50) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Blog Posts Table
CREATE TABLE blog_posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    slug VARCHAR(200) NOT NULL UNIQUE,
    content TEXT NOT NULL,
    excerpt VARCHAR(300),
    meta_description VARCHAR(160),
    meta_keywords VARCHAR(255),
    author_id INTEGER REFERENCES users(id),
    category_id INTEGER REFERENCES blog_categories(id),
    featured_image VARCHAR(500),
    featured_image_alt VARCHAR(200),
    status VARCHAR(20) DEFAULT 'draft' CHECK (status IN ('draft', 'published', 'archived')),
    published_at TIMESTAMP,
    views INTEGER DEFAULT 0,
    reading_time INTEGER, -- estimated reading time in minutes
    canonical_url VARCHAR(500),
    robots_meta VARCHAR(100) DEFAULT 'index,follow',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Blog Post Tags Junction Table (Many-to-Many)
CREATE TABLE blog_post_tags (
    id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES blog_posts(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES blog_tags(id) ON DELETE CASCADE,
    UNIQUE(post_id, tag_id)
);

-- Blog Comments Table (for engagement and SEO)
CREATE TABLE blog_comments (
    id SERIAL PRIMARY KEY,
    post_id INTEGER REFERENCES blog_posts(id) ON DELETE CASCADE,
    author_name VARCHAR(100) NOT NULL,
    author_email VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'spam', 'deleted')),
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- SEO-optimized indexes
CREATE INDEX idx_blog_posts_slug ON blog_posts(slug);
CREATE INDEX idx_blog_posts_status ON blog_posts(status);
CREATE INDEX idx_blog_posts_published_at ON blog_posts(published_at);
CREATE INDEX idx_blog_posts_category ON blog_posts(category_id);
CREATE INDEX idx_blog_posts_author ON blog_posts(author_id);
CREATE INDEX idx_blog_categories_slug ON blog_categories(slug);
CREATE INDEX idx_blog_tags_slug ON blog_tags(slug);
CREATE INDEX idx_blog_comments_post ON blog_comments(post_id);
CREATE INDEX idx_blog_comments_status ON blog_comments(status);

-- Insert default blog categories for SEO content strategy
INSERT INTO blog_categories (name, slug, description, meta_description) VALUES
('Link-in-Bio Tips', 'link-in-bio-tips', 'Expert tips and strategies for optimizing your bio links', 'Discover proven strategies to maximize your link-in-bio effectiveness and drive more traffic from social media profiles.'),
('Social Media Marketing', 'social-media-marketing', 'Social media marketing strategies for creators and businesses', 'Learn social media marketing tactics to grow your audience and convert followers into customers using bio links.'),
('Creator Economy', 'creator-economy', 'Insights and trends in the creator economy', 'Stay updated on creator economy trends, monetization strategies, and tools that help influencers build successful businesses.'),
('Platform Comparisons', 'platform-comparisons', 'Comparing link-in-bio tools and platforms', 'Detailed comparisons of Linktree alternatives and bio link platforms to help you choose the best tool for your needs.'),
('Analytics & Growth', 'analytics-growth', 'Using analytics to grow your online presence', 'Learn how to track, measure, and optimize your bio link performance with analytics and growth hacking strategies.');

-- Insert popular SEO-focused tags
INSERT INTO blog_tags (name, slug) VALUES
('Linktree Alternative', 'linktree-alternative'),
('Bio Link Optimization', 'bio-link-optimization'),
('Instagram Marketing', 'instagram-marketing'),
('TikTok Marketing', 'tiktok-marketing'),
('Creator Tools', 'creator-tools'),
('Social Media Strategy', 'social-media-strategy'),
('Link Analytics', 'link-analytics'),
('Conversion Optimization', 'conversion-optimization'),
('Personal Branding', 'personal-branding'),
('Influencer Marketing', 'influencer-marketing'),
('Content Marketing', 'content-marketing'),
('SEO Tips', 'seo-tips'),
('Free Tools', 'free-tools'),
('Business Growth', 'business-growth'),
('Digital Marketing', 'digital-marketing');

-- Create function to automatically update reading time
CREATE OR REPLACE FUNCTION calculate_reading_time(content_text TEXT)
RETURNS INTEGER AS $$
DECLARE
    word_count INTEGER;
    reading_time INTEGER;
BEGIN
    -- Count words (approximately)
    word_count := array_length(string_to_array(regexp_replace(content_text, '<[^>]*>', '', 'g'), ' '), 1);
    -- Assume 200 words per minute reading speed
    reading_time := GREATEST(1, ROUND(word_count::NUMERIC / 200));
    RETURN reading_time;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically calculate reading time on insert/update
CREATE OR REPLACE FUNCTION update_blog_post_reading_time()
RETURNS TRIGGER AS $$
BEGIN
    NEW.reading_time := calculate_reading_time(NEW.content);
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER blog_posts_reading_time_trigger
    BEFORE INSERT OR UPDATE ON blog_posts
    FOR EACH ROW
    EXECUTE FUNCTION update_blog_post_reading_time();

-- Create view for published posts with category and tag information (for performance)
CREATE VIEW published_blog_posts AS
SELECT 
    bp.*,
    bc.name as category_name,
    bc.slug as category_slug,
    bc.description as category_description,
    u.username as author_username,
    ARRAY_AGG(bt.name) as tag_names,
    ARRAY_AGG(bt.slug) as tag_slugs
FROM blog_posts bp
LEFT JOIN blog_categories bc ON bp.category_id = bc.id
LEFT JOIN users u ON bp.author_id = u.id
LEFT JOIN blog_post_tags bpt ON bp.id = bpt.post_id
LEFT JOIN blog_tags bt ON bpt.tag_id = bt.id
WHERE bp.status = 'published'
GROUP BY bp.id, bc.id, u.id;

-- Create additional indexes for the view
CREATE INDEX idx_published_blog_posts ON blog_posts(status, published_at DESC) WHERE status = 'published';