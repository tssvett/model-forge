--liquibase formatted sql

--changeset modelforge:004-create-app-settings-table
CREATE TABLE IF NOT EXISTS app_settings (
    setting_key   VARCHAR(100) PRIMARY KEY,
    setting_value VARCHAR(500) NOT NULL
);

--changeset modelforge:004-seed-default-settings
INSERT INTO app_settings (setting_key, setting_value) SELECT 'ml_mock_mode', 'true' WHERE NOT EXISTS (SELECT 1 FROM app_settings WHERE setting_key = 'ml_mock_mode');
INSERT INTO app_settings (setting_key, setting_value) SELECT 'ml_device', 'cpu' WHERE NOT EXISTS (SELECT 1 FROM app_settings WHERE setting_key = 'ml_device');
