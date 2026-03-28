--liquibase formatted sql

--changeset modelforge:004-create-app-settings-table
--preconditions onFail:MARK_RAN
--precondition-sql-check expectedResult:0 SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'app_settings'
CREATE TABLE app_settings (
    "key"   VARCHAR(100) PRIMARY KEY,
    "value" VARCHAR(500) NOT NULL
);

--changeset modelforge:004-seed-default-settings
--preconditions onFail:MARK_RAN
--precondition-sql-check expectedResult:0 SELECT COUNT(*) FROM app_settings WHERE "key" = 'ml_mock_mode'
INSERT INTO app_settings ("key", "value") VALUES ('ml_mock_mode', 'true');
INSERT INTO app_settings ("key", "value") VALUES ('ml_device', 'cpu');
