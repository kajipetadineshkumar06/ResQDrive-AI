-- PROPOSED ONLY: fresh, empty database baseline; not executed or verified.
-- Run before the existing 001_agent_events.sql only in the fresh-database sequence.
-- Generated from backend/models/ with SQLAlchemy 2.0.51 MySQL dialect.
-- Do not apply this baseline retroactively to an existing database.
-- REQUIRES VERIFICATION before execution: target MySQL version and SQL mode,
-- including JSON support and acceptance of the generated NOW() defaults.
-- REQUIRES VERIFICATION: ORM models do not declare table engine or charset.
-- This baseline omits ENGINE/CHARSET; the existing 001 migration uses
-- InnoDB/utf8mb4 for agent_events only. Confirm a consistent target policy.
-- Client-side SQLAlchemy defaults are intentionally not database DEFAULT clauses.
-- See database/SCHEMA_MIGRATION_PLAN.md for staging and existing-database gates.

-- Table: admins

CREATE TABLE admins (
	admin_id INTEGER NOT NULL AUTO_INCREMENT,
	name VARCHAR(100) NOT NULL,
	email VARCHAR(100) NOT NULL,
	password VARCHAR(255) NOT NULL,
	is_active BOOL,
	created_at TIMESTAMP NULL DEFAULT now(),
	PRIMARY KEY (admin_id),
	UNIQUE (email)
);

CREATE INDEX ix_admins_admin_id ON admins (admin_id);

-- Table: coupons

CREATE TABLE coupons (
	coupon_id INTEGER NOT NULL AUTO_INCREMENT,
	coupon_code VARCHAR(50) NOT NULL,
	description VARCHAR(255),
	discount_type ENUM('percentage','fixed') NOT NULL,
	discount_value DECIMAL(10, 2) NOT NULL,
	minimum_amount DECIMAL(10, 2),
	maximum_discount DECIMAL(10, 2),
	expiry_date DATETIME NOT NULL,
	is_active BOOL,
	created_at TIMESTAMP NULL DEFAULT now(),
	PRIMARY KEY (coupon_id),
	UNIQUE (coupon_code)
);

CREATE INDEX ix_coupons_coupon_id ON coupons (coupon_id);

-- Table: providers

CREATE TABLE providers (
	provider_id INTEGER NOT NULL AUTO_INCREMENT,
	provider_name VARCHAR(100) NOT NULL,
	service_type VARCHAR(50) NOT NULL,
	phone VARCHAR(15) NOT NULL,
	email VARCHAR(100),
	latitude DECIMAL(10, 7) NOT NULL,
	longitude DECIMAL(10, 7) NOT NULL,
	city VARCHAR(100),
	rating DECIMAL(2, 1),
	availability BOOL,
	created_at TIMESTAMP NULL DEFAULT now(),
	PRIMARY KEY (provider_id)
);

CREATE INDEX ix_providers_provider_id ON providers (provider_id);

-- Table: users

CREATE TABLE users (
	user_id INTEGER NOT NULL AUTO_INCREMENT,
	full_name VARCHAR(100) NOT NULL,
	email VARCHAR(255) NOT NULL,
	phone VARCHAR(20),
	password_hash VARCHAR(255) NOT NULL,
	created_at DATETIME,
	PRIMARY KEY (user_id)
);

CREATE UNIQUE INDEX ix_users_email ON users (email);

CREATE INDEX ix_users_user_id ON users (user_id);

-- Table: fcm_tokens

CREATE TABLE fcm_tokens (
	token_id INTEGER NOT NULL AUTO_INCREMENT,
	user_id INTEGER NOT NULL,
	token VARCHAR(500) NOT NULL,
	PRIMARY KEY (token_id),
	UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (user_id),
	UNIQUE (token)
);

CREATE INDEX ix_fcm_tokens_token_id ON fcm_tokens (token_id);

-- Table: service_providers

CREATE TABLE service_providers (
	provider_id INTEGER NOT NULL AUTO_INCREMENT,
	name VARCHAR(100) NOT NULL,
	service_type VARCHAR(50) NOT NULL,
	phone VARCHAR(20) NOT NULL,
	location_lat NUMERIC(10, 7),
	location_lng NUMERIC(10, 7),
	rating_avg NUMERIC(3, 2) NOT NULL,
	is_available BOOL NOT NULL,
	provider_image VARCHAR(255),
	experience_years INTEGER,
	verified BOOL NOT NULL,
	created_at DATETIME,
	is_tracking BOOL NOT NULL,
	user_id INTEGER,
	PRIMARY KEY (provider_id),
	CONSTRAINT fk_provider_user FOREIGN KEY(user_id) REFERENCES users (user_id)
);

CREATE INDEX ix_service_providers_provider_id ON service_providers (provider_id);

-- Table: sos_alerts

CREATE TABLE sos_alerts (
	alert_id INTEGER NOT NULL AUTO_INCREMENT,
	user_id INTEGER NOT NULL,
	latitude DECIMAL(10, 7) NOT NULL,
	longitude DECIMAL(10, 7) NOT NULL,
	status ENUM('sent','received','acknowledged'),
	PRIMARY KEY (alert_id),
	FOREIGN KEY(user_id) REFERENCES users (user_id)
);

CREATE INDEX ix_sos_alerts_alert_id ON sos_alerts (alert_id);

-- Table: vehicles

CREATE TABLE vehicles (
	vehicle_id INTEGER NOT NULL AUTO_INCREMENT,
	user_id INTEGER NOT NULL,
	plate_number VARCHAR(50) NOT NULL,
	make VARCHAR(100) NOT NULL,
	model VARCHAR(100) NOT NULL,
	year INTEGER NOT NULL,
	vehicle_type VARCHAR(50),
	fuel_type VARCHAR(50),
	vehicle_color VARCHAR(50),
	PRIMARY KEY (vehicle_id),
	FOREIGN KEY(user_id) REFERENCES users (user_id)
);

CREATE INDEX ix_vehicles_vehicle_id ON vehicles (vehicle_id);

-- Table: emergencies

CREATE TABLE emergencies (
	emergency_id INTEGER NOT NULL AUTO_INCREMENT,
	user_id INTEGER NOT NULL,
	vehicle_id INTEGER,
	emergency_type VARCHAR(100) NOT NULL,
	description VARCHAR(500),
	location_lat FLOAT NOT NULL,
	location_lng FLOAT NOT NULL,
	status VARCHAR(30),
	priority VARCHAR(20),
	recommended_service VARCHAR(100),
	created_at TIMESTAMP NULL DEFAULT now(),
	resolved_at TIMESTAMP NULL,
	PRIMARY KEY (emergency_id),
	FOREIGN KEY(user_id) REFERENCES users (user_id),
	FOREIGN KEY(vehicle_id) REFERENCES vehicles (vehicle_id)
);

CREATE INDEX ix_emergencies_emergency_id ON emergencies (emergency_id);

-- Table: provider_locations

CREATE TABLE provider_locations (
	location_id INTEGER NOT NULL AUTO_INCREMENT,
	provider_id INTEGER NOT NULL,
	latitude DECIMAL(10, 7) NOT NULL,
	longitude DECIMAL(10, 7) NOT NULL,
	updated_at TIMESTAMP NULL DEFAULT now(),
	PRIMARY KEY (location_id),
	FOREIGN KEY(provider_id) REFERENCES service_providers (provider_id)
);

CREATE INDEX ix_provider_locations_location_id ON provider_locations (location_id);

-- Table: notifications

CREATE TABLE notifications (
	notification_id INTEGER NOT NULL AUTO_INCREMENT,
	user_id INTEGER NOT NULL,
	emergency_id INTEGER,
	provider_id INTEGER,
	title VARCHAR(255) NOT NULL,
	message VARCHAR(500) NOT NULL,
	status VARCHAR(30) NOT NULL DEFAULT 'sent',
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (notification_id),
	FOREIGN KEY(user_id) REFERENCES users (user_id),
	FOREIGN KEY(emergency_id) REFERENCES emergencies (emergency_id),
	FOREIGN KEY(provider_id) REFERENCES service_providers (provider_id)
);

CREATE INDEX ix_notifications_notification_id ON notifications (notification_id);

-- Table: service_requests

CREATE TABLE service_requests (
	request_id INTEGER NOT NULL AUTO_INCREMENT,
	emergency_id INTEGER NOT NULL,
	provider_id INTEGER,
	excluded_provider_ids JSON,
	user_id INTEGER NOT NULL,
	request_status VARCHAR(50) NOT NULL,
	estimated_arrival INTEGER,
	notes VARCHAR(500),
	requested_at DATETIME DEFAULT now(),
	accepted_at DATETIME,
	started_at DATETIME,
	arrived_at DATETIME,
	completed_at DATETIME,
	cancelled_at DATETIME,
	PRIMARY KEY (request_id),
	FOREIGN KEY(emergency_id) REFERENCES emergencies (emergency_id),
	FOREIGN KEY(provider_id) REFERENCES service_providers (provider_id),
	FOREIGN KEY(user_id) REFERENCES users (user_id)
);

CREATE INDEX ix_service_requests_request_id ON service_requests (request_id);

-- Table: payments

CREATE TABLE payments (
	payment_id INTEGER NOT NULL AUTO_INCREMENT,
	request_id INTEGER NOT NULL,
	user_id INTEGER NOT NULL,
	amount DECIMAL(10, 2) NOT NULL,
	payment_method ENUM('upi','card','cash','wallet'),
	payment_status ENUM('pending','success','failed','refunded'),
	transaction_id VARCHAR(100),
	invoice_number VARCHAR(100),
	paid_at TIMESTAMP NULL,
	created_at TIMESTAMP NULL DEFAULT now(),
	PRIMARY KEY (payment_id),
	FOREIGN KEY(request_id) REFERENCES service_requests (request_id),
	FOREIGN KEY(user_id) REFERENCES users (user_id)
);

CREATE INDEX ix_payments_payment_id ON payments (payment_id);

-- Table: ratings

CREATE TABLE ratings (
	rating_id INTEGER NOT NULL AUTO_INCREMENT,
	request_id INTEGER,
	user_id INTEGER,
	provider_id INTEGER,
	rating_value INTEGER,
	review_text TEXT,
	created_at TIMESTAMP NULL DEFAULT now(),
	PRIMARY KEY (rating_id),
	FOREIGN KEY(request_id) REFERENCES service_requests (request_id),
	FOREIGN KEY(user_id) REFERENCES users (user_id),
	FOREIGN KEY(provider_id) REFERENCES service_providers (provider_id)
);

CREATE INDEX ix_ratings_rating_id ON ratings (rating_id);

-- Table: invoices

CREATE TABLE invoices (
	invoice_id INTEGER NOT NULL AUTO_INCREMENT,
	payment_id INTEGER NOT NULL,
	invoice_number VARCHAR(100) NOT NULL,
	invoice_date TIMESTAMP NULL DEFAULT now(),
	total_amount DECIMAL(10, 2) NOT NULL,
	tax_amount DECIMAL(10, 2),
	discount_amount DECIMAL(10, 2),
	final_amount DECIMAL(10, 2) NOT NULL,
	pdf_path VARCHAR(255),
	PRIMARY KEY (invoice_id),
	FOREIGN KEY(payment_id) REFERENCES payments (payment_id),
	UNIQUE (invoice_number)
);

CREATE INDEX ix_invoices_invoice_id ON invoices (invoice_id);
