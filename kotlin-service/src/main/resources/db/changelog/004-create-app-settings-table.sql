--liquibase formatted sql

--changeset modelforge:004-create-app-settings-table
--preconditions onFail:MARK_RAN onError:MARK_RAN
--precondition-sql-check expectedResult:0 SELECT COUNT(*) FROM information_schema.tables WHERE UPPER(table_name) = 'APP_SETTINGS'
CREATE TABLE app_settings (
    setting_key   VARCHAR(100) PRIMARY KEY,
    setting_value VARCHAR(500) NOT NULL
);

--changeset modelforge:004-seed-default-settings
--preconditions onFail:MARK_RAN onError:MARK_RAN
--precondition-sql-check expectedResult:0 SELECT COUNT(*) FROM app_settings WHERE setting_key = 'ml_mock_mode'
INSERT INTO app_settings (setting_key, setting_value) VALUES ('ml_mock_mode', 'true');
INSERT INTO app_settings (setting_key, setting_value) VALUES ('ml_device', 'cpu');
