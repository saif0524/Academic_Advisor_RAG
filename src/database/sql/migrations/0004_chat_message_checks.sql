-- FC34/FC39: the deterministic checks shown with an advisor turn are stored
-- (JSON array) so a reloaded or exported conversation keeps their statuses.
ALTER TABLE chat_messages ADD COLUMN checks TEXT;
