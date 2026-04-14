-- Add image_url to markets
ALTER TABLE markets ADD COLUMN IF NOT EXISTS image_url TEXT;

-- Public storage bucket for creator-uploaded market images
INSERT INTO storage.buckets (id, name, public)
VALUES ('market-images', 'market-images', true)
ON CONFLICT (id) DO NOTHING;

-- Allow anyone to read market images
CREATE POLICY "Public read market images"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'market-images');

-- Allow authenticated users to upload market images
CREATE POLICY "Authenticated upload market images"
  ON storage.objects FOR INSERT
  TO authenticated
  WITH CHECK (bucket_id = 'market-images');
