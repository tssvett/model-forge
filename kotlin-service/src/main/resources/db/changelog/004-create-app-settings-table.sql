--liquibase formatted sql

--changeset modelforge:004-create-app-settings-table
CREATE TABLE IF NOT EXISTS app_settings (
    setting_key   VARCHAR(100) PRIMARY KEY,
    setting_value VARCHAR(500) NOT NULL
);

--changeset modelforge:004-seed-default-settings
INSERT INTO app_settings (setting_key, setting_value) VALUES ('ml_mock_mode', 'true') ON CONFLICT (setting_key) DO NOTHING;
INSERT INTO app_settings (setting_key, setting_value) VALUES ('ml_device', 'cpu') ON CONFLICT (setting_key) DO NOTHING;
