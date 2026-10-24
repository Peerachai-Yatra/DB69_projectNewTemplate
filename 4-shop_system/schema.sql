-- ============================================================
--  schema.sql — ร้านค้าออนไลน์ (MySQL 8)
--  กติกา: 1 ออเดอร์มีหลายสินค้า (M:N: order × product ผ่าน order_line),
--         รีวิว = M:N (customer × product), การชำระเงิน 1:M จาก shop_order
-- ============================================================

DROP TABLE IF EXISTS payment;
DROP TABLE IF EXISTS review;
DROP TABLE IF EXISTS order_line;
DROP TABLE IF EXISTS shop_order;
DROP TABLE IF EXISTS product;
DROP TABLE IF EXISTS customer;

CREATE TABLE customer (
    cust_id INT AUTO_INCREMENT PRIMARY KEY,
    name    VARCHAR(100) NOT NULL,
    email   VARCHAR(150) NOT NULL UNIQUE,
    address VARCHAR(255) NULL,
    tier    ENUM('normal', 'silver', 'gold', 'vip') NOT NULL DEFAULT 'normal'
);

CREATE TABLE product (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(150) NOT NULL,
    category   VARCHAR(50)  NOT NULL,
    price      DECIMAL(10,2) NOT NULL CHECK (price >= 0),
    stock      INT NOT NULL DEFAULT 0 CHECK (stock >= 0)
);

CREATE TABLE shop_order (
    order_id   INT AUTO_INCREMENT PRIMARY KEY,
    cust_id    INT NOT NULL,
    order_date DATE NOT NULL DEFAULT (CURRENT_DATE),
    status     ENUM('pending','shipped') NOT NULL DEFAULT 'pending',
    -- ★ ไม่มีคอลัมน์ยอดรวม — คำนวณจาก order_line (ดู search_orders ใน db.py)
    CONSTRAINT fk_order_customer FOREIGN KEY (cust_id)
        REFERENCES customer(cust_id)
);

CREATE TABLE order_line (         -- M:N: shop_order × product
    order_id   INT NOT NULL,
    product_id INT NOT NULL,
    qty        INT NOT NULL CHECK (qty > 0),
    unit_price DECIMAL(10,2) NOT NULL CHECK (unit_price >= 0),  -- ราคา ณ วันที่ขาย
    PRIMARY KEY (order_id, product_id),
    
    CONSTRAINT fk_line_order FOREIGN KEY (order_id)
        REFERENCES shop_order(order_id),
    CONSTRAINT fk_line_product FOREIGN KEY (product_id)
        REFERENCES product(product_id)
);

CREATE TABLE review (             -- M:N: customer × product
    cust_id     INT NOT NULL,
    product_id  INT NOT NULL,
    rating      TINYINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment     VARCHAR(500) NULL,
    review_date DATE NOT NULL DEFAULT (CURRENT_DATE),
    PRIMARY KEY (cust_id, product_id),

    CONSTRAINT fk_review_customer FOREIGN KEY (cust_id)
        REFERENCES customer(cust_id) ON DELETE CASCADE,
    CONSTRAINT fk_review_product FOREIGN KEY (product_id)
        REFERENCES product(product_id) ON DELETE CASCADE
);

CREATE TABLE payment (            -- 1:M จาก shop_order
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id   INT NOT NULL,
    method     VARCHAR(30) NOT NULL,
    amount     DECIMAL(10,2) NOT NULL CHECK (amount > 0),
    paid_date  DATE NOT NULL DEFAULT (CURRENT_DATE),

    CONSTRAINT fk_payment_order FOREIGN KEY (order_id)
        REFERENCES shop_order(order_id)
);

-- ============================================================
--  ข้อมูลตัวอย่าง
-- ============================================================
INSERT INTO customer (name, email, address, tier) VALUES
('สมชาย ใจดี',      'somchai@example.com', '12 ถ.สุขุมวิท กรุงเทพฯ',  'vip'),
('สมหญิง รักช้อป',  'somying@example.com', '45 ถ.นิมมาน เชียงใหม่',   'vip'),
('วีระ มั่นคง',      'weera@example.com',   '8 ถ.มิตรภาพ ขอนแก่น',     'normal'),
('นภา ฟ้าใส',        'napa@example.com',    '99 ถ.เพชรเกษม หาดใหญ่',   'normal'),
('ธนา เก่งกล้า',     'thana@example.com',   NULL,                       'normal');

INSERT INTO product (name, category, price, stock) VALUES
('หูฟังบลูทูธ',        'electronics', 1290.00, 50),   -- 1
('เมาส์ไร้สาย',        'electronics',  450.00, 120),  -- 2
('เสื้อยืดคอกลม',      'fashion',      290.00, 200),  -- 3
('กระติกน้ำสแตนเลส',   'home',         350.00, 80),   -- 4
('สมุดโน้ต A5',        'stationery',    79.00, 500),  -- 5
('รองเท้าวิ่ง',        'fashion',     1890.00, 30);   -- 6

INSERT INTO shop_order (cust_id, order_date, status) VALUES
(1, '2026-09-01', 'shipped'),   -- 1 ชำระแล้ว (จ่าย 2 งวด) + จัดส่งแล้ว
(1, '2026-09-20', 'pending'),   -- 2 ยังไม่ชำระ
(2, '2026-09-05', 'shipped'),   -- 3 ชำระแล้ว + จัดส่งแล้ว
(3, '2026-09-28', 'pending'),   -- 4 ชำระแล้ว แต่ยังไม่จัดส่ง (ใช้ทดสอบการจัดส่ง)
(4, '2026-10-02', 'pending'),   -- 5 ยังไม่ชำระ
(2, '2026-10-05', 'pending');   -- 6 ยังไม่ชำระ

INSERT INTO order_line (order_id, product_id, qty, unit_price) VALUES
(1, 1, 2, 1290.00),
(1, 3, 1,  290.00),             -- ยอดออเดอร์ 1 = 2,870
(2, 2, 1,  450.00),             -- ยอดออเดอร์ 2 = 450
(3, 1, 1, 1290.00),
(3, 4, 3,  350.00),             -- ยอดออเดอร์ 3 = 2,340
(4, 5, 2,   79.00),             -- ยอดออเดอร์ 4 = 158
(5, 6, 1, 1890.00),
(5, 2, 2,  450.00),             -- ยอดออเดอร์ 5 = 2,790
(6, 3, 1,  290.00);             -- ยอดออเดอร์ 6 = 290

INSERT INTO payment (order_id, method, amount, paid_date) VALUES
(1, 'credit_card', 2000.00, '2026-09-02'),
(1, 'promptpay',    870.00, '2026-09-03'),
(3, 'promptpay',   2340.00, '2026-09-06'),
(4, 'transfer',     158.00, '2026-09-29');

INSERT INTO review (cust_id, product_id, rating, comment, review_date) VALUES
(1, 1, 5, 'เสียงดีมาก',            '2026-09-10'),
(2, 1, 4, 'แบตอึดแต่ราคาสูง',      '2026-09-12'),
(1, 3, 3, 'ผ้าบางไปนิด',           '2026-09-11'),
(2, 4, 5, 'เก็บความเย็นได้ดี',      '2026-09-14'),
(3, 5, 4, 'กระดาษดี เขียนลื่น',     '2026-10-01');
