-- AI Accident Detection & Emergency Alert System
-- Run this file with MySQL before starting the Flask application.

CREATE DATABASE IF NOT EXISTS accident_detection
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE accident_detection;

CREATE TABLE IF NOT EXISTS users (
    user_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'operator') NOT NULL DEFAULT 'operator',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS severity_level (
    severity_level_id TINYINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    level_name VARCHAR(30) NOT NULL UNIQUE,
    priority_order TINYINT UNSIGNED NOT NULL UNIQUE,
    description VARCHAR(255) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS cameras (
    camera_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    camera_name VARCHAR(120) NOT NULL,
    location_description VARCHAR(255) NOT NULL,
    stream_url VARCHAR(500) NOT NULL,
    status ENUM('active', 'inactive', 'maintenance') NOT NULL DEFAULT 'inactive',
    created_by_user_id INT UNSIGNED NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_cameras_created_by
        FOREIGN KEY (created_by_user_id) REFERENCES users(user_id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS detection_log (
    detection_log_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    camera_id INT UNSIGNED NOT NULL,
    detected_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    model_name VARCHAR(120) NULL,
    model_version VARCHAR(60) NULL,
    confidence_score DECIMAL(5,4) NULL,
    source_frame_path VARCHAR(500) NULL,
    notes TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_detection_confidence CHECK (confidence_score IS NULL OR confidence_score BETWEEN 0 AND 1),
    CONSTRAINT fk_detection_log_camera
        FOREIGN KEY (camera_id) REFERENCES cameras(camera_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    INDEX idx_detection_log_camera_detected (camera_id, detected_at)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS accident_event (
    accident_event_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    detection_log_id BIGINT UNSIGNED NOT NULL UNIQUE,
    severity_level_id TINYINT UNSIGNED NOT NULL,
    event_status ENUM('detected', 'verified', 'resolved', 'false_positive') NOT NULL DEFAULT 'detected',
    occurred_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    verified_by_user_id INT UNSIGNED NULL,
    verified_at TIMESTAMP NULL,
    resolved_at TIMESTAMP NULL,
    snapshot_path VARCHAR(500) NULL,
    description TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_accident_event_detection
        FOREIGN KEY (detection_log_id) REFERENCES detection_log(detection_log_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_accident_event_severity
        FOREIGN KEY (severity_level_id) REFERENCES severity_level(severity_level_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_accident_event_verified_by
        FOREIGN KEY (verified_by_user_id) REFERENCES users(user_id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_accident_event_status_time (event_status, occurred_at),
    INDEX idx_accident_event_severity (severity_level_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS emergency_contacts (
    emergency_contact_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNSIGNED NULL,
    contact_name VARCHAR(120) NOT NULL,
    organization VARCHAR(120) NULL,
    phone_number VARCHAR(30) NOT NULL,
    email VARCHAR(255) NULL,
    contact_type ENUM('police', 'ambulance', 'fire', 'hospital', 'administrator', 'other') NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_emergency_contacts_user
        FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS alerts (
    alert_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    accident_event_id BIGINT UNSIGNED NOT NULL,
    emergency_contact_id INT UNSIGNED NULL,
    alert_channel ENUM('sms', 'email', 'call', 'dashboard') NOT NULL,
    alert_status ENUM('pending', 'sent', 'delivered', 'failed', 'acknowledged') NOT NULL DEFAULT 'pending',
    alert_message TEXT NOT NULL,
    sent_at TIMESTAMP NULL,
    acknowledged_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_alerts_accident_event
        FOREIGN KEY (accident_event_id) REFERENCES accident_event(accident_event_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_alerts_emergency_contact
        FOREIGN KEY (emergency_contact_id) REFERENCES emergency_contacts(emergency_contact_id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_alerts_event_status (accident_event_id, alert_status)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS notification_log (
    notification_log_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    alert_id BIGINT UNSIGNED NOT NULL,
    emergency_contact_id INT UNSIGNED NULL,
    delivery_status ENUM('queued', 'sent', 'delivered', 'failed') NOT NULL DEFAULT 'queued',
    provider_message_id VARCHAR(255) NULL,
    provider_response TEXT NULL,
    attempted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    delivered_at TIMESTAMP NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notification_log_alert
        FOREIGN KEY (alert_id) REFERENCES alerts(alert_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_notification_log_contact
        FOREIGN KEY (emergency_contact_id) REFERENCES emergency_contacts(emergency_contact_id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    INDEX idx_notification_log_alert (alert_id, attempted_at)
) ENGINE=InnoDB;

-- Reference configuration only; no accident, detection, alert, or notification records are added.
INSERT INTO severity_level (level_name, priority_order, description) VALUES
    ('Low', 1, 'Minor incident requiring observation.'),
    ('Medium', 2, 'Incident requiring prompt review.'),
    ('High', 3, 'Serious incident requiring immediate action.')
ON DUPLICATE KEY UPDATE
    description = VALUES(description);
