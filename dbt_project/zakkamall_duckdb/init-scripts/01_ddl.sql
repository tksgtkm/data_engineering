/*
EC サイト「ZakkaMall」OLTP データベース（DuckDB 版）

PostgreSQL 版（オリジナルの chapter4/init-scripts/01_ddl.sql）からの主な変更点:
- GENERATED ALWAYS AS IDENTITY        → SEQUENCE + DEFAULT nextval(...)
- ENUM 型                             → VARCHAR + CHECK 制約
- LTREE（category_path）              → VARCHAR（'electronics.computers.laptops' 形式。02 で再帰 CTE により設定）
- JSONB                               → JSON
- TIMESTAMPTZ                         → TIMESTAMP（snapshot の updated_at と型を揃えるため）
- GENERATED ... STORED                → GENERATED ... VIRTUAL（DuckDB は仮想生成列のみ対応）
- FOREIGN KEY 制約                    → 省略（DuckDB は被参照行の UPDATE に制約があるため。
                                         参照整合性は dbt の relationships テストで検証する）
- インデックス（GiST / 部分インデックス含む） → 省略（列指向の DuckDB では不要）
- トリガー（updated_at 自動更新 / category_path / 注文番号採番）
                                      → 省略。DuckDB はトリガー非対応のため、
                                         updated_at や order_number は INSERT / UPDATE 側で明示する
*/

CREATE SCHEMA IF NOT EXISTS zakka_mall;
SET search_path = 'zakka_mall';

-- 採番用シーケンス（PostgreSQL の IDENTITY 列の代替）
CREATE SEQUENCE seq_customer_id START 1;
CREATE SEQUENCE seq_address_id START 1;
CREATE SEQUENCE seq_category_id START 1;
CREATE SEQUENCE seq_supplier_id START 1;
CREATE SEQUENCE seq_product_id START 1;
CREATE SEQUENCE seq_inventory_id START 1;
CREATE SEQUENCE seq_order_id START 1;
CREATE SEQUENCE seq_order_item_id START 1;
CREATE SEQUENCE seq_payment_id START 1;
CREATE SEQUENCE seq_shipment_id START 1;

CREATE TABLE customer (
    customer_id BIGINT PRIMARY KEY DEFAULT nextval('zakka_mall.seq_customer_id'),
    customer_name VARCHAR NOT NULL,
    email VARCHAR NOT NULL UNIQUE,
    phone VARCHAR,
    registration_date DATE NOT NULL DEFAULT current_date,
    status VARCHAR NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'suspended')),
    created_at TIMESTAMP NOT NULL DEFAULT localtimestamp,
    updated_at TIMESTAMP NOT NULL DEFAULT localtimestamp,
    external_id UUID DEFAULT gen_random_uuid()
);

CREATE TABLE customer_address (
    address_id BIGINT PRIMARY KEY DEFAULT nextval('zakka_mall.seq_address_id'),
    customer_id BIGINT NOT NULL,
    address_type VARCHAR NOT NULL CHECK (address_type IN ('shipping', 'billing', 'both')),
    postal_code VARCHAR NOT NULL,
    prefecture VARCHAR NOT NULL,
    city VARCHAR NOT NULL,
    address_line1 VARCHAR NOT NULL,
    address_line2 VARCHAR,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT localtimestamp,
    updated_at TIMESTAMP NOT NULL DEFAULT localtimestamp
);

CREATE TABLE category (
    category_id BIGINT PRIMARY KEY DEFAULT nextval('zakka_mall.seq_category_id'),
    category_name VARCHAR NOT NULL,
    category_code VARCHAR NOT NULL UNIQUE,
    parent_category_id BIGINT,
    description VARCHAR,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT localtimestamp,
    updated_at TIMESTAMP NOT NULL DEFAULT localtimestamp,
    category_path VARCHAR
);

CREATE TABLE supplier (
    supplier_id BIGINT PRIMARY KEY DEFAULT nextval('zakka_mall.seq_supplier_id'),
    supplier_name VARCHAR NOT NULL,
    supplier_code VARCHAR NOT NULL UNIQUE,
    contact_email VARCHAR,
    contact_phone VARCHAR,
    address VARCHAR,
    status VARCHAR NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'pending')),
    created_at TIMESTAMP NOT NULL DEFAULT localtimestamp,
    updated_at TIMESTAMP NOT NULL DEFAULT localtimestamp,
    contact_details JSON
);

CREATE TABLE product (
    product_id BIGINT PRIMARY KEY DEFAULT nextval('zakka_mall.seq_product_id'),
    product_name VARCHAR NOT NULL,
    product_code VARCHAR NOT NULL UNIQUE,
    sku VARCHAR NOT NULL UNIQUE,
    category_id BIGINT NOT NULL,
    supplier_id BIGINT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL CHECK (unit_price >= 0),
    description VARCHAR,
    status VARCHAR NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'discontinued')),
    created_at TIMESTAMP NOT NULL DEFAULT localtimestamp,
    updated_at TIMESTAMP NOT NULL DEFAULT localtimestamp,
    specifications JSON
);

CREATE TABLE inventory (
    inventory_id BIGINT PRIMARY KEY DEFAULT nextval('zakka_mall.seq_inventory_id'),
    product_id BIGINT NOT NULL UNIQUE,
    quantity_on_hand INTEGER NOT NULL DEFAULT 0 CHECK (quantity_on_hand >= 0),
    quantity_reserved INTEGER NOT NULL DEFAULT 0 CHECK (quantity_reserved >= 0),
    reorder_level INTEGER NOT NULL DEFAULT 0 CHECK (reorder_level >= 0),
    reorder_quantity INTEGER NOT NULL DEFAULT 0 CHECK (reorder_quantity >= 0),
    last_updated TIMESTAMP NOT NULL DEFAULT localtimestamp,
    CHECK (quantity_on_hand >= quantity_reserved)
);

CREATE TABLE "order" (
    order_id BIGINT PRIMARY KEY DEFAULT nextval('zakka_mall.seq_order_id'),
    customer_id BIGINT NOT NULL,
    order_number VARCHAR NOT NULL UNIQUE,
    order_date DATE NOT NULL DEFAULT current_date,
    order_status VARCHAR NOT NULL DEFAULT 'pending'
        CHECK (order_status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded')),
    subtotal DECIMAL(10, 2) NOT NULL CHECK (subtotal >= 0),
    tax_amount DECIMAL(10, 2) NOT NULL CHECK (tax_amount >= 0),
    shipping_fee DECIMAL(10, 2) NOT NULL CHECK (shipping_fee >= 0),
    total_amount DECIMAL(10, 2) GENERATED ALWAYS AS (subtotal + tax_amount + shipping_fee) VIRTUAL,
    shipping_address_id BIGINT NOT NULL,
    billing_address_id BIGINT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT localtimestamp,
    updated_at TIMESTAMP NOT NULL DEFAULT localtimestamp,
    order_metadata JSON
);

CREATE TABLE order_item (
    order_item_id BIGINT PRIMARY KEY DEFAULT nextval('zakka_mall.seq_order_item_id'),
    order_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price DECIMAL(10, 2) NOT NULL CHECK (unit_price >= 0),
    line_total DECIMAL(10, 2) GENERATED ALWAYS AS (quantity * unit_price) VIRTUAL,
    created_at TIMESTAMP NOT NULL DEFAULT localtimestamp,
    item_metadata JSON
);

CREATE TABLE payment (
    payment_id BIGINT PRIMARY KEY DEFAULT nextval('zakka_mall.seq_payment_id'),
    order_id BIGINT NOT NULL,
    payment_method VARCHAR NOT NULL
        CHECK (payment_method IN ('credit_card', 'bank_transfer', 'cash_on_delivery', 'digital_wallet')),
    payment_status VARCHAR NOT NULL DEFAULT 'pending'
        CHECK (payment_status IN ('pending', 'completed', 'failed', 'refunded')),
    payment_amount DECIMAL(10, 2) NOT NULL CHECK (payment_amount >= 0),
    payment_date DATE,
    transaction_id VARCHAR,
    gateway_response JSON,
    created_at TIMESTAMP NOT NULL DEFAULT localtimestamp,
    updated_at TIMESTAMP NOT NULL DEFAULT localtimestamp
);

CREATE TABLE shipment (
    shipment_id BIGINT PRIMARY KEY DEFAULT nextval('zakka_mall.seq_shipment_id'),
    order_id BIGINT NOT NULL,
    tracking_number VARCHAR,
    carrier VARCHAR,
    shipment_status VARCHAR NOT NULL DEFAULT 'preparing'
        CHECK (shipment_status IN ('preparing', 'shipped', 'in_transit', 'delivered', 'returned')),
    shipped_date DATE,
    estimated_delivery_date DATE,
    actual_delivery_date DATE,
    created_at TIMESTAMP NOT NULL DEFAULT localtimestamp,
    updated_at TIMESTAMP NOT NULL DEFAULT localtimestamp,
    tracking_details JSON,
    CHECK (
        (shipped_date IS NULL OR estimated_delivery_date IS NULL OR shipped_date <= estimated_delivery_date)
        AND (shipped_date IS NULL OR actual_delivery_date IS NULL OR shipped_date <= actual_delivery_date)
    )
);
