SELECT * FROM stores LIMIT 5;

SELECT * FROM product_categories LIMIT 5;

SELECT * FROM products LIMIT 5;

SELECT * FROM price_revisions LIMIT 5;

SELECT COUNT(*) AS total_stores
FROM stores;

SELECT COUNT(*) AS total_categories
FROM product_categories;

SELECT COUNT(*) AS total_products
FROM products;

SELECT COUNT(*) AS total_price_revisions
FROM price_revisions;