CREATE TABLE IF NOT EXISTS agent_events (
    event_id INT NOT NULL AUTO_INCREMENT,
    emergency_id INT NULL,
    request_id INT NULL,
    actor_user_id INT NULL,
    provider_id INT NULL,
    event_type VARCHAR(80) NOT NULL,
    event_status VARCHAR(30) NOT NULL DEFAULT 'recorded',
    details JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (event_id),
    KEY ix_agent_events_emergency_created (emergency_id, created_at),
    KEY ix_agent_events_request_created (request_id, created_at),
    CONSTRAINT fk_agent_events_emergency
        FOREIGN KEY (emergency_id)
        REFERENCES emergencies (emergency_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_agent_events_request
        FOREIGN KEY (request_id)
        REFERENCES service_requests (request_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_agent_events_actor_user
        FOREIGN KEY (actor_user_id)
        REFERENCES users (user_id)
        ON DELETE SET NULL,
    CONSTRAINT fk_agent_events_provider
        FOREIGN KEY (provider_id)
        REFERENCES service_providers (provider_id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
