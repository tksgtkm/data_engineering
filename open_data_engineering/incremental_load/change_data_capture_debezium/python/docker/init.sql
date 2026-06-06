CREATE SCHEMA dedp_schema;

CREATE EXTENSION postgis;

CREATE TABLE dedp_schema.visits (
    visit_id VARCHAR(40) NOT NULL,
    event_time TIMESTAMP NOT NULL,
    user_id TEXT NOT NULL,
    page VARCHAR(20) NOT NULL,
    PRIMARY KEY (visit_id, event_time)
);

ALTER TABLE dedp_schema.visits REPLICA IDENTITY FULL;