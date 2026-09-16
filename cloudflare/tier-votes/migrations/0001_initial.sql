PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ballots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tier TEXT NOT NULL CHECK (tier IN ('T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7')),
  voter_hash TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (tier, voter_hash)
);

CREATE TABLE IF NOT EXISTS votes (
  ballot_id INTEGER NOT NULL,
  class_name TEXT NOT NULL,
  grade TEXT NOT NULL CHECK (grade IN ('S', 'A', 'B', 'C')),
  score INTEGER NOT NULL CHECK (score BETWEEN 1 AND 4),
  PRIMARY KEY (ballot_id, class_name),
  FOREIGN KEY (ballot_id) REFERENCES ballots(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_ballots_tier ON ballots(tier);
CREATE INDEX IF NOT EXISTS idx_votes_class_name ON votes(class_name);
