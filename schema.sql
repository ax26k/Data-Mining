CREATE TABLE IF NOT EXISTS stores (
    store_id VARCHAR(10) PRIMARY KEY,
    store_name VARCHAR(150),
    address_line TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    region VARCHAR(100),
    floor_area_sqft INTEGER,
    opened_on DATE
);

CREATE TABLE IF NOT EXISTS product_categories (
    category_id VARCHAR(50) PRIMARY KEY,
    category_name VARCHAR(150)
);

CREATE TABLE IF NOT EXISTS products (
    product_code VARCHAR(50) PRIMARY KEY,
    product_name TEXT,
    category_id VARCHAR(50),
    brand VARCHAR(150),
    unit_price NUMERIC(12,2)
);

CREATE TABLE IF NOT EXISTS price_revisions (
    revision_id SERIAL PRIMARY KEY,
    product_code VARCHAR(50),
    old_price NUMERIC(12,2),
    new_price NUMERIC(12,2),
    effective_date DATE
);