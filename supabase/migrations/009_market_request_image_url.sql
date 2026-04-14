-- Persist optional image URL on market requests
ALTER TABLE market_creation_requests
ADD COLUMN IF NOT EXISTS image_url TEXT;
