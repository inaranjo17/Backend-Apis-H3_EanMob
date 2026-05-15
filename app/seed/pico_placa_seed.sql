CREATE TABLE IF NOT EXISTS pico_placa_sources (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(160) NOT NULL,
    source_type VARCHAR(40) NOT NULL DEFAULT 'web',
    url VARCHAR(500) NOT NULL,
    active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_pico_placa_sources_url (url)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pico_placa_sync_runs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_id INT NULL,
    status VARCHAR(40) NOT NULL,
    message TEXT NULL,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_pico_placa_sync_runs_source
        FOREIGN KEY (source_id) REFERENCES pico_placa_sources(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pico_placa_rules (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_id INT NULL,
    city VARCHAR(80) NOT NULL,
    weekday_start TINYINT NOT NULL DEFAULT 0,
    weekday_end TINYINT NOT NULL DEFAULT 4,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    odd_day_digits JSON NOT NULL,
    even_day_digits JSON NOT NULL,
    active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY ix_pico_placa_rules_city_active (city, active),
    CONSTRAINT fk_pico_placa_rules_source
        FOREIGN KEY (source_id) REFERENCES pico_placa_sources(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pico_placa_regional_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    source_id INT NULL,
    rule_id VARCHAR(120) NOT NULL,
    event_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    restricted_digits JSON NOT NULL,
    direction ENUM('inbound', 'outbound', 'both') NULL,
    active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_pico_placa_regional_events_rule_id (rule_id),
    KEY ix_pico_placa_regional_events_date_active (event_date, active),
    CONSTRAINT fk_pico_placa_regional_events_source
        FOREIGN KEY (source_id) REFERENCES pico_placa_sources(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pico_placa_regional_corridors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    event_rule_id VARCHAR(120) NOT NULL,
    corridor_id VARCHAR(120) NOT NULL,
    active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_pico_placa_regional_corridors_event_corridor (event_rule_id, corridor_id),
    KEY ix_pico_placa_regional_corridors_event_active (event_rule_id, active),
    CONSTRAINT fk_pico_placa_regional_corridors_event
        FOREIGN KEY (event_rule_id) REFERENCES pico_placa_regional_events(rule_id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO pico_placa_sources (name, source_type, url, active)
VALUES
    ('Secretaria Distrital de Movilidad Bogota', 'web', 'https://www.movilidadbogota.gov.co/web/pico_y_placa', 1),
    ('Gobernacion de Cundinamarca', 'web', 'https://www.cundinamarca.gov.co/', 1)
ON DUPLICATE KEY UPDATE
    name = VALUES(name),
    source_type = VALUES(source_type),
    active = VALUES(active);

INSERT INTO pico_placa_rules (
    source_id,
    city,
    weekday_start,
    weekday_end,
    start_time,
    end_time,
    odd_day_digits,
    even_day_digits,
    active
)
SELECT
    s.id,
    'BOGOTA',
    0,
    4,
    '06:00:00',
    '21:00:00',
    JSON_ARRAY('6', '7', '8', '9', '0'),
    JSON_ARRAY('1', '2', '3', '4', '5'),
    1
FROM pico_placa_sources s
WHERE s.url = 'https://www.movilidadbogota.gov.co/web/pico_y_placa'
  AND NOT EXISTS (
      SELECT 1
      FROM pico_placa_rules r
      WHERE UPPER(r.city) = 'BOGOTA'
        AND r.active = 1
  );
