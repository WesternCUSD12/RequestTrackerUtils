-- Asset Tags Table
DROP TABLE IF EXISTS asset_tags;

CREATE TABLE asset_tags (
  tag_number INTEGER PRIMARY KEY,          -- The numeric part of the tag (e.g., 1025)
  full_tag TEXT UNIQUE NOT NULL,           -- The complete tag (e.g., W12-1025)
  rt_asset_id INTEGER NULL,                -- The corresponding RT Asset ID (filled on confirmation)
  generated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  confirmed_at TIMESTAMP NULL              -- Timestamp when confirmed by RT
);

-- Optional: Index for faster lookup if needed later, e.g., by rt_asset_id
-- CREATE INDEX IF NOT EXISTS idx_asset_tags_rt_id ON asset_tags (rt_asset_id);
