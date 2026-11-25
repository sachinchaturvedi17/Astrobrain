-- AstroNaradMuni v1.4.0 — Hostinger hPanel MySQL / MariaDB Schema
-- Import this file in Hostinger hPanel -> Websites -> Databases -> phpMyAdmin
-- (Note: src/aipandit/db.py also runs CREATE TABLE IF NOT EXISTS automatically on startup)

CREATE TABLE IF NOT EXISTS users_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_key VARCHAR(64) NOT NULL UNIQUE,
    full_name VARCHAR(120),
    gender VARCHAR(32),
    dob VARCHAR(16) NOT NULL,
    tob VARCHAR(16),
    time_certainty VARCHAR(32),
    place VARCHAR(160),
    latitude DOUBLE,
    longitude DOUBLE,
    timezone VARCHAR(64),
    is_minor INT DEFAULT 0,
    lagna_sign VARCHAR(32),
    moon_sign VARCHAR(32),
    moon_nakshatra VARCHAR(64),
    moon_pada INT,
    sun_sign VARCHAR(32),
    dasha_maha VARCHAR(32),
    dasha_antar VARCHAR(32),
    dasha_antar_end VARCHAR(16),
    lang VARCHAR(8) DEFAULT 'en',
    visit_count INT DEFAULT 1,
    created_at VARCHAR(32) NOT NULL,
    last_seen_at VARCHAR(32) NOT NULL,
    INDEX idx_users_created (created_at),
    INDEX idx_users_place (place)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS chat_interactions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_key VARCHAR(64),
    user_name VARCHAR(120),
    question TEXT NOT NULL,
    topic VARCHAR(64),
    intent VARCHAR(64),
    lang VARCHAR(8),
    answer TEXT,
    confidence VARCHAR(32),
    created_at VARCHAR(32) NOT NULL,
    INDEX idx_chat_user (user_key),
    INDEX idx_chat_topic (topic),
    INDEX idx_chat_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS kundli_downloads (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_key VARCHAR(64),
    full_name VARCHAR(120),
    dob VARCHAR(16),
    tob VARCHAR(16),
    place VARCHAR(160),
    lagna_sign VARCHAR(32),
    moon_sign VARCHAR(32),
    created_at VARCHAR(32) NOT NULL,
    INDEX idx_dl_user (user_key),
    INDEX idx_dl_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pandit_bookings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ref_code VARCHAR(32) NOT NULL UNIQUE,
    full_name VARCHAR(120),
    phone VARCHAR(32) NOT NULL,
    slot VARCHAR(32),
    topic VARCHAR(64),
    note TEXT,
    dob VARCHAR(16),
    tob VARCHAR(16),
    place VARCHAR(160),
    latitude DOUBLE,
    longitude DOUBLE,
    timezone VARCHAR(64),
    created_at VARCHAR(32) NOT NULL,
    INDEX idx_booking_phone (phone),
    INDEX idx_booking_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
