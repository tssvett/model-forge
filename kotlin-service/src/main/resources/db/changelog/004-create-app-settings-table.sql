--liquibase formatted sql

--changeset modelforge:004-create-app-settings-table
CREATE TABLE app_settings (
    setting_key   VARCHAR(100) PRIMARY KEY,
    setting_value VARCHAR(500) NOT NULL
);

--changeset modelforge:004-seed-default-settings
INSERT INTO app_settings (setting_key, setting_value) VALUES ('ml_mock_mode', 'true');
INSERT INTO app_settings (setting_key, setting_value) VALUES ('ml_device', 'cpu');
