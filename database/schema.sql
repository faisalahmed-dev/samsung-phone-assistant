-- schema.sql
-- Creates the 3 tables: phones, specifications, prices
-- We delete old tables first, so every run starts fresh
-- (child tables first, because they point to phones)

DROP TABLE IF EXISTS prices;
DROP TABLE IF EXISTS specifications;
DROP TABLE IF EXISTS phones;

-- 1) One row per phone, with the important specs as clean numbers
CREATE TABLE phones (
    id                   INT AUTO_INCREMENT PRIMARY KEY,
    name                 VARCHAR(100) NOT NULL UNIQUE,
    brand                VARCHAR(50) DEFAULT 'Samsung',
    release_year         INT,
    announced            VARCHAR(100),
    status               VARCHAR(255),
    display_type         VARCHAR(255),
    display_size_inches  DECIMAL(4,2),
    display_resolution   VARCHAR(255),
    os                   VARCHAR(255),
    chipset              VARCHAR(255),
    ram_gb               INT,
    storage_options      VARCHAR(255),
    main_camera_mp       INT,
    main_camera          TEXT,
    selfie_camera        TEXT,
    battery_mah          INT,
    charging_watt        INT,
    battery_active_use   VARCHAR(100),
    battery_endurance    VARCHAR(100),
    weight_g             DECIMAL(6,1),
    dimensions           VARCHAR(255),
    gsmarena_url         VARCHAR(255),
    image_url            VARCHAR(255)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2) Every single spec from GSMArena, one row each
CREATE TABLE specifications (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    phone_id    INT NOT NULL,
    category    VARCHAR(50),
    spec_name   VARCHAR(100),
    spec_value  TEXT,
    FOREIGN KEY (phone_id) REFERENCES phones(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3) Prices, one row per currency
-- GSMArena shows the current market price, so we also save the date we collected it
CREATE TABLE prices (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    phone_id      INT NOT NULL,
    currency      VARCHAR(10),
    amount        DECIMAL(10,2),
    price_text    VARCHAR(255),
    collected_on  DATE,
    FOREIGN KEY (phone_id) REFERENCES phones(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;