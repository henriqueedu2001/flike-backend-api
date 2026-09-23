-- Apply once to a backed-up existing database, never to the shared/demo DB implicitly.
-- Historical keys intentionally keep request_id NULL: their origin cannot be inferred reliably.
-- Duplicate legacy e-mails must be resolved before this migration, not silently discarded.
SET time_zone = '+00:00';
ALTER TABLE user ADD UNIQUE KEY uq_user_email (email);
ALTER TABLE digital_key_request
    ADD COLUMN decided_at DATETIME NULL,
    MODIFY status ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'pending';
ALTER TABLE digital_key
    ADD COLUMN request_id INT NULL,
    ADD UNIQUE KEY uq_digital_key_request (request_id),
    ADD CONSTRAINT fk_digital_key_request FOREIGN KEY (request_id) REFERENCES digital_key_request(id),
    MODIFY expires_at DATETIME NULL,
    MODIFY created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP;
