CREATE TABLE IF NOT EXISTS invites (
	id          CHAR(36) PRIMARY KEY,
	user_from   VARCHAR(32) NOT NULL,
	user_to     VARCHAR(32) NOT NULL,
	title       VARCHAR(256) NOT NULL,
	description VARCHAR(256) NOT NULL,
	date        CHAR(10) NOT NULL
);

CREATE INDEX IF NOT EXISTS invites_idx_from ON invites (user_from);
CREATE INDEX IF NOT EXISTS invites_idx_to ON invites (user_to);
CREATE INDEX IF NOT EXISTS invites_idx_date ON invites (date);
