-- Add testimonials table
CREATE TABLE IF NOT EXISTS testimonials (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    avatar_url TEXT,
    position VARCHAR(255),
    company VARCHAR(255),
    rating INTEGER DEFAULT 5,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    display_order INTEGER DEFAULT 0
);

-- Insert sample testimonials
INSERT INTO testimonials (name, content, avatar_url, position, company, rating, is_active, display_order) VALUES
('Emily Carter', 'LinkLyst transformed how I share my digital presence. The interface is clean, fast, and my audience loves the organized layout!', 'https://images.unsplash.com/photo-1494790108755-2616b612b786?w=150&h=150&fit=crop&crop=face', 'Digital Marketing Manager', 'Creative Studios', 5, true, 1),
('James Liu', 'As a content creator with multiple platforms, LinkLyst made it seamless to showcase all my work in one beautiful page.', 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&h=150&fit=crop&crop=face', 'Content Creator', 'YouTube', 5, true, 2),
('Sophia Martinez', 'The customization options are fantastic! I can match my brand perfectly and my click-through rates have increased by 40%.', 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=150&h=150&fit=crop&crop=face', 'Brand Manager', 'Fashion Forward', 5, true, 3),
('David Kim', 'LinkLyst''s analytics help me understand which content resonates most with my audience. It''s a game-changer for my business.', 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=150&h=150&fit=crop&crop=face', 'Business Owner', 'Tech Innovations', 5, true, 4),
('Laura Nguyen', 'I''ve tried other link-in-bio tools, but LinkLyst''s simplicity and powerful features make it the clear winner.', 'https://images.unsplash.com/photo-1489424731084-a5d8b219a5bb?w=150&h=150&fit=crop&crop=face', 'Influencer', 'Lifestyle Blog', 5, true, 5),
('Michael Rodriguez', 'The mobile optimization is perfect. My followers can easily access all my links whether they''re on phone or desktop.', 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&h=150&fit=crop&crop=face', 'Social Media Manager', 'Fitness Pro', 5, true, 6);

-- Create index for better performance
CREATE INDEX IF NOT EXISTS idx_testimonials_active_order ON testimonials (is_active, display_order);