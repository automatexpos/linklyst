-- ========================================
-- LINKTREE CLONE DATABASE SCHEMA
-- ========================================

-- Drop existing tables if they exist to avoid conflicts
drop table if exists clicks cascade;
drop table if exists links cascade;
drop table if exists profiles cascade;
drop table if exists users cascade;

-- ========================================
-- TABLE DEFINITIONS
-- ========================================

-- users table
create table users (
  id bigserial primary key,
  email text unique not null check (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
  username text unique not null check (length(username) >= 3 and length(username) <= 30),
  password_hash text not null,
  is_active boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- profiles table (one-to-one with users)
create table profiles (
  id bigserial primary key,
  user_id bigint unique references users(id) on delete cascade,
  display_name text check (length(display_name) <= 100),
  bio text check (length(bio) <= 500),
  avatar_url text,
  theme text default 'default' check (theme in ('default', 'dark', 'light', 'colorful')),
  is_public boolean default true,
  custom_url text unique check (custom_url ~* '^[a-zA-Z0-9_-]+$' and length(custom_url) >= 3),
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- links table
create table links (
  id bigserial primary key,
  user_id bigint references users(id) on delete cascade,
  title text not null check (length(title) <= 200),
  url text not null check (url ~* '^https?://'),
  description text check (length(description) <= 500),
  sort_order integer default 0,
  is_active boolean default true,
  is_public boolean default true,
  click_count integer default 0,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- clicks table for analytics
create table clicks (
  id bigserial primary key,
  link_id bigint references links(id) on delete cascade,
  clicked_at timestamptz default now(),
  ip_address inet,
  user_agent text,
  referrer text,
  country text,
  city text
);

-- ========================================
-- INDEXES FOR PERFORMANCE
-- ========================================

create index ix_users_email on users(email);
create index ix_users_username on users(username);
create index ix_users_active on users(is_active);

create index ix_profiles_user_id on profiles(user_id);
create index ix_profiles_custom_url on profiles(custom_url);
create index ix_profiles_public on profiles(is_public);

create index ix_links_user_id on links(user_id);
create index ix_links_user_sort on links(user_id, sort_order);
create index ix_links_active on links(is_active);
create index ix_links_public on links(is_public);

create index ix_clicks_link_id on clicks(link_id);
create index ix_clicks_date on clicks(clicked_at);
create index ix_clicks_link_date on clicks(link_id, clicked_at);

-- ========================================
-- FUNCTIONS AND TRIGGERS
-- ========================================

-- Function to update updated_at timestamp
create or replace function update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

-- Triggers for updated_at
create trigger update_users_updated_at 
  before update on users 
  for each row execute procedure update_updated_at_column();

create trigger update_profiles_updated_at 
  before update on profiles 
  for each row execute procedure update_updated_at_column();

create trigger update_links_updated_at 
  before update on links 
  for each row execute procedure update_updated_at_column();

-- Function to increment click count
create or replace function increment_click_count()
returns trigger as $$
begin
  update links set click_count = click_count + 1 where id = new.link_id;
  return new;
end;
$$ language plpgsql;

-- Trigger to increment click count when click is recorded
create trigger increment_link_clicks 
  after insert on clicks 
  for each row execute procedure increment_click_count();

-- ========================================
-- ROW LEVEL SECURITY (RLS)
-- ========================================

-- Note: Since we're using Flask with custom authentication (not Supabase Auth),
-- we'll disable RLS and handle security in our application layer.
-- This is appropriate for server-side applications using service keys.

-- Disable RLS on all tables for service key access
alter table users disable row level security;
alter table profiles disable row level security;  
alter table links disable row level security;
alter table clicks disable row level security;

-- Alternative: If you want to enable RLS later with proper Supabase Auth integration,
-- you would need to modify your Flask app to use Supabase Auth instead of custom auth.
-- For now, security is handled at the application level in Flask routes.

-- ========================================
-- PUBLIC ACCESS FUNCTIONS
-- ========================================

-- Function to get public profile by custom URL
create or replace function get_public_profile(custom_url_param text)
returns table (
  user_id bigint,
  display_name text,
  bio text,
  avatar_url text,
  theme text,
  custom_url text
) 
security definer
as $$
begin
  return query
  select 
    p.user_id,
    p.display_name,
    p.bio,
    p.avatar_url,
    p.theme,
    p.custom_url
  from profiles p
  join users u on p.user_id = u.id
  where p.custom_url = custom_url_param 
    and p.is_public = true 
    and u.is_active = true;
end;
$$ language plpgsql;

-- Function to get public links for a user
create or replace function get_public_links(profile_user_id bigint)
returns table (
  id bigint,
  title text,
  url text,
  description text,
  sort_order integer,
  click_count integer
)
security definer
as $$
begin
  return query
  select 
    l.id,
    l.title,
    l.url,
    l.description,
    l.sort_order,
    l.click_count
  from links l
  join users u on l.user_id = u.id
  where l.user_id = profile_user_id 
    and l.is_active = true 
    and l.is_public = true 
    and u.is_active = true
  order by l.sort_order asc, l.created_at asc;
end;
$$ language plpgsql;

-- ========================================
-- GRANTS AND PERMISSIONS
-- ========================================

-- Grant usage on sequences
grant usage on sequence users_id_seq to anon, authenticated;
grant usage on sequence profiles_id_seq to anon, authenticated;
grant usage on sequence links_id_seq to anon, authenticated;
grant usage on sequence clicks_id_seq to anon, authenticated;

-- Grant permissions for authenticated users
grant select, insert, update, delete on users to authenticated;
grant select, insert, update, delete on profiles to authenticated;
grant select, insert, update, delete on links to authenticated;
grant select, insert on clicks to authenticated, anon;

-- Grant select access to public functions
grant execute on function get_public_profile(text) to anon, authenticated;
grant execute on function get_public_links(bigint) to anon, authenticated;

-- ========================================
-- SAMPLE DATA (OPTIONAL - REMOVE IN PRODUCTION)
-- ========================================

-- Uncomment below to insert sample data for testing
/*
insert into users (email, username, password_hash) values 
('demo@example.com', 'demo', '$2b$12$dummy.hash.for.testing.purposes');

insert into profiles (user_id, display_name, bio, custom_url, theme) values 
(1, 'Demo User', 'This is a demo profile for testing purposes.', 'demo', 'default');

insert into links (user_id, title, url, description, sort_order) values 
(1, 'My Website', 'https://example.com', 'Check out my personal website', 1),
(1, 'GitHub', 'https://github.com/demo', 'My coding projects', 2),
(1, 'Twitter', 'https://twitter.com/demo', 'Follow me on Twitter', 3);
*/
