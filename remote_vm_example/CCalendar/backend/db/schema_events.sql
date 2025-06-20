CREATE TABLE IF NOT EXISTS events (
	id          CHAR(36) PRIMARY KEY,
	owner       VARCHAR(32) NOT NULL,
	title       VARCHAR(256) NOT NULL,
	description VARCHAR(256) NOT NULL,
	date        CHAR(10) NOT NULL
);

CREATE INDEX IF NOT EXISTS events_idx_owner ON events (owner);
CREATE INDEX IF NOT EXISTS events_idx_date ON events (date);
