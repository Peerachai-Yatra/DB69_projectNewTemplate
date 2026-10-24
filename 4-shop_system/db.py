# ============================================================
#  db.py — ชั้นติดต่อฐานข้อมูล  ★★★ นิสิตเขียน SQL ในไฟล์นี้ ★★★
#  ใช้ %s เป็น placeholder เสมอ (กัน SQL injection)
# ============================================================
import mysql.connector
import config


def get_connection():
    return mysql.connector.connect(
        host=config.DB_HOST, user=config.DB_USER, password=config.DB_PASSWORD,
        database=config.DB_NAME, port=config.DB_PORT)


def run_query(sql, params=None):
    """รัน SELECT คืนผลเป็น list ของ dict"""
    conn = get_connection(); cur = conn.cursor(dictionary=True)
    cur.execute(sql, params or ()); rows = cur.fetchall()
    cur.close(); conn.close(); return rows


def run_command(sql, params=None):
    """รัน INSERT / UPDATE / DELETE แล้ว commit"""
    conn = get_connection(); cur = conn.cursor()
    cur.execute(sql, params or ()); conn.commit()
    out = {"new_id": cur.lastrowid, "affected": cur.rowcount}
    cur.close(); conn.close(); return out


def blank_to_none(value):
    """ช่องที่ไม่ได้กรอกในฟอร์มจะส่งมาเป็น "" — แปลงเป็น None (= NULL ใน SQL)
    ใช้กับคอลัมน์ที่ว่างได้ เช่น return_date, paid_date  เพราะ MySQL ไม่รับ '' เป็น DATE"""
    return None if value in ("", None) else value


def _todo(name):
    raise NotImplementedError(f"TODO: ยังไม่ได้เขียนฟังก์ชัน {name} ใน db.py")


# ---------- ลูกค้า (customer) ----------
def search_customers(filters):
    """ค้นหา ลูกค้า ตามเงื่อนไข (name, email, tier)"""
    sql = "SELECT * FROM customer WHERE 1=1"
    params = []
    if filters.get("name"):
        sql += " AND name LIKE %s"
        params.append("%" + filters["name"] + "%")
    if filters.get("email"):
        sql += " AND email LIKE %s"
        params.append("%" + filters["email"] + "%")
    if filters.get("tier"):
        sql += " AND tier = %s"
        params.append(filters["tier"])
    sql += " ORDER BY cust_id"
    return run_query(sql, params)


def get_customer(cust_id):
    """ดึง ลูกค้า 1 รายการตาม cust_id"""
    rows = run_query("SELECT * FROM customer WHERE cust_id = %s", (cust_id,))
    return rows[0] if rows else None


def create_customer(data):
    """เพิ่ม ลูกค้า ใหม่ — data มีคีย์: name, email, address, tier"""
    sql = ("INSERT INTO customer (name, email, address, tier) "
           "VALUES (%s, %s, %s, COALESCE(%s, 'regular'))")
    return run_command(sql, (data["name"], data["email"],
                             blank_to_none(data.get("address")),
                             blank_to_none(data.get("tier"))))


def update_customer(cust_id, data):
    """แก้ไข ลูกค้า ตาม cust_id"""
    sql = ("UPDATE customer SET name = %s, email = %s, address = %s, tier = %s "
           "WHERE cust_id = %s")
    return run_command(sql, (data["name"], data["email"],
                             blank_to_none(data.get("address")),
                             data["tier"], cust_id))


def delete_customer(cust_id):
    """ลบ ลูกค้า ตาม cust_id (รีวิวของลูกค้าถูกลบตาม CASCADE;
    ถ้ามีออเดอร์อยู่ MySQL จะไม่ยอมให้ลบ)"""
    return run_command("DELETE FROM customer WHERE cust_id = %s", (cust_id,))


# ---------- สินค้า (product) ----------
def search_products(filters):
    """ค้นหา สินค้า ตามเงื่อนไข (name, category)"""
    sql = "SELECT * FROM product WHERE 1=1"
    params = []
    if filters.get("name"):
        sql += " AND name LIKE %s"
        params.append("%" + filters["name"] + "%")
    if filters.get("category"):
        sql += " AND category = %s"
        params.append(filters["category"])
    sql += " ORDER BY product_id"
    return run_query(sql, params)


def get_product(product_id):
    """ดึง สินค้า 1 รายการตาม product_id"""
    rows = run_query("SELECT * FROM product WHERE product_id = %s", (product_id,))
    return rows[0] if rows else None


def create_product(data):
    """เพิ่ม สินค้า ใหม่ — data มีคีย์: name, category, price, stock"""
    sql = ("INSERT INTO product (name, category, price, stock) "
           "VALUES (%s, %s, %s, %s)")
    return run_command(sql, (data["name"], data["category"],
                             data["price"], data.get("stock") or 0))


def update_product(product_id, data):
    """แก้ไข สินค้า ตาม product_id"""
    sql = ("UPDATE product SET name = %s, category = %s, price = %s, stock = %s "
           "WHERE product_id = %s")
    return run_command(sql, (data["name"], data["category"],
                             data["price"], data.get("stock") or 0,
                             product_id))


def delete_product(product_id):
    """ลบ สินค้า ตาม product_id (รีวิวถูกลบตาม CASCADE;
    ถ้าสินค้าเคยถูกขายในออเดอร์ MySQL จะไม่ยอมให้ลบ)"""
    return run_command("DELETE FROM product WHERE product_id = %s", (product_id,))


# ---------- ออเดอร์ (shop_order) ----------
def search_orders(filters):
    """ค้นหา ออเดอร์ ตามเงื่อนไข (cust_id, status)"""
    sql = """
        SELECT o.order_id, o.cust_id, c.name AS customer_name,
               o.order_date, o.status,
               IFNULL(ROUND(t.gross * (1 - IFNULL(c.discount, 0) / 100), 2), 0)
                   AS total
        FROM shop_order o
        INNER JOIN customer c ON o.cust_id = c.cust_id
        LEFT JOIN (SELECT ol.order_id, SUM(ol.qty * ol.unit_price) AS gross
                   FROM order_line ol
                   GROUP BY ol.order_id) t ON o.order_id = t.order_id
        WHERE 1=1
    """
    params = []
    if filters.get("cust_id"):
        sql += " AND o.cust_id = %s"
        params.append(filters["cust_id"])
    if filters.get("status"):
        sql += " AND o.status = %s"
        params.append(filters["status"])
    sql += " ORDER BY o.order_id"
    return run_query(sql, params)


def get_order(order_id):
    """ดึง ออเดอร์ 1 รายการตาม order_id"""
    rows = run_query("SELECT * FROM shop_order WHERE order_id = %s", (order_id,))
    return rows[0] if rows else None


def check_can_ship(order_id):
    """ตรวจก่อนเปลี่ยนสถานะเป็น 'shipped' — จัดส่งได้เฉพาะออเดอร์ที่ชำระเงินแล้ว"""
    rows = run_query(
        "SELECT EXISTS (SELECT 1 FROM payment WHERE order_id = %s) AS paid",
        (order_id,))
    if not rows[0]["paid"]:
        raise ValueError("ออเดอร์นี้ยังไม่ได้ชำระเงิน จัดส่งไม่ได้")


def create_order(data):
    """เพิ่ม ออเดอร์ ใหม่ — data มีคีย์: cust_id, order_date, status"""
    # ออเดอร์ใหม่ยังไม่มีการชำระเงิน จึงตั้งเป็น shipped ไม่ได้
    if data.get("status") == "shipped":
        raise ValueError("ออเดอร์ใหม่ยังไม่ได้ชำระเงิน จัดส่งไม่ได้")

    product_id = blank_to_none(data.get("product_id"))
    try:
        qty = int(blank_to_none(data.get("qty")) or 1)
    except (TypeError, ValueError):
        raise ValueError("จำนวนสินค้าต้องเป็นตัวเลข")
    if product_id is not None and qty <= 0:
        raise ValueError("จำนวนสินค้าต้องมากกว่า 0")

    # ใช้ connection เดียวกันทุกคำสั่ง เพื่อให้ "สำเร็จทั้งหมด หรือไม่ทำเลย"
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        # 1 สร้างออเดอร์ (shop_order)
        cur.execute(
            "INSERT INTO shop_order (cust_id, order_date, status) "
            "VALUES (%s, COALESCE(%s, CURRENT_DATE), COALESCE(%s, 'pending'))",
            (data["cust_id"], blank_to_none(data.get("order_date")),
             blank_to_none(data.get("status"))))
        order_id = cur.lastrowid

        # 2 ถ้าเลือกสินค้ามาด้วย -> เพิ่มแถวใน order_line
        if product_id is not None:
            cur.execute("SELECT price, stock FROM product "
                        "WHERE product_id = %s FOR UPDATE", (product_id,))
            p = cur.fetchone()
            if p is None:
                raise ValueError("ไม่พบสินค้านี้")
            if p["stock"] < qty:
                raise ValueError(f"สินค้าในสต็อกไม่พอ (เหลือ {p['stock']} ชิ้น)")
            # unit_price = ราคา ณ วันที่ขาย (เก็บไว้แม้ราคาสินค้าเปลี่ยนทีหลัง)
            cur.execute(
                "INSERT INTO order_line (order_id, product_id, qty, unit_price) "
                "VALUES (%s, %s, %s, %s)",
                (order_id, product_id, qty, p["price"]))
            # 3 ตัดสต็อก
            cur.execute("UPDATE product SET stock = stock - %s "
                        "WHERE product_id = %s", (qty, product_id))

        conn.commit()
        return {"new_id": order_id, "affected": 1}
    except Exception:
        conn.rollback()      # พลาดตรงไหน ย้อนกลับทั้งหมด (ไม่เหลือออเดอร์ค้าง)
        raise                # ส่ง error ต่อให้ app.py แสดงเป็น alert
    finally:
        cur.close()
        conn.close()
    
def update_order(order_id, data):
    """แก้ไข ออเดอร์ ตาม order_id"""
    if data.get("status") == "shipped":
        check_can_ship(order_id)
    sql = ("UPDATE shop_order SET cust_id = %s, order_date = %s, status = %s "
           "WHERE order_id = %s")
    return run_command(sql, (data["cust_id"], data["order_date"],
                             data["status"], order_id))


def delete_order(order_id):
    """ลบ ออเดอร์ ตาม order_id — ห้ามลบออเดอร์ที่ชำระเงินแล้ว"""
    rows = run_query(
        "SELECT EXISTS (SELECT 1 FROM payment WHERE order_id = %s) AS paid",
        (order_id,))
    if rows[0]["paid"]:
        raise ValueError("ออเดอร์นี้ชำระเงินแล้ว ลบไม่ได้")
    # ลบแถวลูกใน order_line ก่อน (FK) แล้วจึงลบ shop_order
    run_command("DELETE FROM order_line WHERE order_id = %s", (order_id,))
    return run_command("DELETE FROM shop_order WHERE order_id = %s", (order_id,))

def search_reviews(filters):
    """ค้นหา รีวิว ตามเงื่อนไข (product_id, rating)"""
    sql = "SELECT * FROM review WHERE 1=1"
    params = []
    if filters.get("product_id"):
        sql += " AND product_id = %s"
        params.append(filters["product_id"])
    if filters.get("rating"):
        sql += " AND rating = %s"
        params.append(filters["rating"])
    sql += " ORDER BY review_date DESC"
    return run_query(sql, params)

def get_review(review_id):
    """ดึง รีวิว 1 รายการตาม review_id"""
    rows = run_query("SELECT * FROM review WHERE review_id = %s", (review_id,))
    return rows[0] if rows else None

def create_review(data):
    """เพิ่ม รีวิว ใหม่ — data มีคีย์: cust_id, product_id, rating, comment, review_date"""
    sql = ("INSERT INTO review (cust_id, product_id, rating, comment, review_date) "
           "VALUES (%s, %s, %s, %s, COALESCE(%s, CURRENT_DATE))")
    return run_command(sql, (data["cust_id"], data["product_id"], data["rating"],
                             blank_to_none(data.get("comment")),
                             blank_to_none(data.get("review_date"))))

def update_review(review_id, data):
    """แก้ไข รีวิว ตาม review_id"""
    sql = ("UPDATE review SET cust_id = %s, product_id = %s, rating = %s, "
           "comment = %s, review_date = %s "
           "WHERE review_id = %s")
    return run_command(sql, (data["cust_id"], data["product_id"], data["rating"],
                             blank_to_none(data.get("comment")),
                             blank_to_none(data.get("review_date")), review_id))

def delete_review(review_id):
    """ลบ รีวิว ตาม review_id"""
    return run_command("DELETE FROM review WHERE review_id = %s", (review_id,))

def get_product_reviews(product_id):
    """ดึงรีวิวทั้งหมดของสินค้าตาม product_id"""
    sql = "SELECT * FROM review WHERE product_id = %s ORDER BY review_date DESC"
    return run_query(sql, (product_id,))

def search_payments(filters):
    """ค้นหา การชำระเงิน ตามเงื่อนไข (order_id, paid_date)"""
    sql = "SELECT * FROM payment WHERE 1=1"
    params = []
    if filters.get("order_id"):
        sql += " AND order_id = %s"
        params.append(filters["order_id"])
    if filters.get("paid_date"):
        sql += " AND paid_date = %s"
        params.append(filters["paid_date"])
    sql += " ORDER BY payment_id ASC"
    return run_query(sql, tuple(params))

def get_payment(payment_id):
    """ดึง การชำระเงิน 1 รายการตาม payment_id"""
    rows = run_query("SELECT * FROM payment WHERE payment_id = %s", (payment_id,))
    return rows[0] if rows else None

def create_payment(data):
    """เพิ่ม การชำระเงิน ใหม่ — data มีคีย์: order_id, amount, paid_date"""
    sql = ("INSERT INTO payment (order_id, amount, paid_date) "
           "VALUES (%s, %s, COALESCE(%s, CURRENT_DATE))")
    return run_command(sql, (data["order_id"], data["amount"],
                             blank_to_none(data.get("paid_date"))))

def update_payment(payment_id, data):
    """แก้ไข การชำระเงิน ตาม payment_id"""
    sql = ("UPDATE payment SET order_id = %s, amount = %s, paid_date = %s "
           "WHERE payment_id = %s")
    return run_command(sql, (data["order_id"], data["amount"],
                             blank_to_none(data.get("paid_date")), payment_id))

def delete_payment(payment_id):
    """ลบ การชำระเงิน ตาม payment_id"""
    return run_command("DELETE FROM payment WHERE payment_id = %s", (payment_id,))

def get_product_reviews(product_id):
    """ดึงรีวิวทั้งหมดของสินค้าตาม product_id"""
    sql = "SELECT * FROM review WHERE product_id = %s ORDER BY review_date DESC"
    return run_query(sql, (product_id,))

# ============================================================
#  REPORT (รายงาน — ใช้ JOIN + GROUP BY + subquery)
#  ★ ชื่อคอลัมน์ใน SELECT จะกลายเป็นหัวตารางบนเว็บ — ใช้ AS 'ชื่อภาษาไทย' ได้
# ============================================================
def report_summary():
    """ตัวเลขสรุปบนการ์ด dashboard — 1 คอลัมน์ = 1 การ์ด"""
    sql = """
        SELECT
            (SELECT COUNT(*) FROM customer)    AS 'ลูกค้า',
            (SELECT COUNT(*) FROM product)     AS 'สินค้า',
            (SELECT COUNT(*) FROM shop_order)  AS 'ออเดอร์',
            (SELECT COUNT(*) FROM review)      AS 'รีวิว',
            (SELECT IFNULL(SUM(amount), 0) FROM payment)
                                               AS 'รายได้ที่ชำระแล้ว (บาท)',
            (SELECT COUNT(*) FROM shop_order o
              WHERE NOT EXISTS (SELECT 1 FROM payment p
                                WHERE p.order_id = o.order_id))
                                               AS 'ออเดอร์ที่ยังไม่ชำระ'
    """
    return run_query(sql)[0]


def report_best_selling():
    """📈 สินค้าขายดี (Best Sellers) — Top 5"""
    sql = """
        SELECT p.name AS 'สินค้า', p.category AS 'หมวดหมู่',
               SUM(ol.qty) AS 'จำนวนที่ขายได้'
        FROM order_line ol
        INNER JOIN product p ON ol.product_id = p.product_id
        GROUP BY p.product_id, p.name, p.category
        ORDER BY SUM(ol.qty) DESC, p.name
        LIMIT 5
    """
    return run_query(sql)


def report_customers_above_avg():
    """🏅 ลูกค้าที่ซื้อมากกว่าค่าเฉลี่ย (Above Average)
    ค่าเฉลี่ย = ยอดซื้อรวมต่อลูกค้า เฉลี่ยจากลูกค้าที่เคยสั่งซื้อ"""
    sql = """
        SELECT c.name AS 'ลูกค้า', c.tier AS 'ระดับ',
               SUM(ol.qty * ol.unit_price) AS 'ยอดซื้อรวม'
        FROM customer c
        INNER JOIN shop_order o ON c.cust_id = o.cust_id
        INNER JOIN order_line ol ON o.order_id = ol.order_id
        GROUP BY c.cust_id, c.name, c.tier
        HAVING SUM(ol.qty * ol.unit_price) > (
            SELECT AVG(per_cust.total)
            FROM (SELECT SUM(ol2.qty * ol2.unit_price) AS total
                  FROM shop_order o2
                  INNER JOIN order_line ol2 ON o2.order_id = ol2.order_id
                  GROUP BY o2.cust_id) per_cust
        )
        ORDER BY SUM(ol.qty * ol.unit_price) DESC
    """
    return run_query(sql)


def report_high_rated():
    """⭐ สินค้าคะแนนรีวิวเฉลี่ย ≥ 4 (HAVING)"""
    sql = """
        SELECT p.name AS 'สินค้า',
               ROUND(AVG(r.rating), 2) AS 'คะแนนเฉลี่ย',
               COUNT(*) AS 'จำนวนรีวิว'
        FROM review r
        INNER JOIN product p ON r.product_id = p.product_id
        GROUP BY p.product_id, p.name
        HAVING AVG(r.rating) >= 4
        ORDER BY AVG(r.rating) DESC, p.name
    """
    return run_query(sql)

def report_review():
    """📋 รายงานรีวิวสินค้า — ตัวอย่างการเพิ่มรายงานที่ 4"""
    sql = """
        SELECT p.name AS 'สินค้า',
               r.rating AS 'คะแนน',
               r.comment AS 'ความคิดเห็น',
               r.review_date AS 'วันที่รีวิว'
        FROM review r
        INNER JOIN product p ON r.product_id = p.product_id
        ORDER BY r.review_date DESC
    """
    return run_query(sql)
# ============================================================
#  รายการรายงานที่แสดงบนหน้า /report  (เรียงตามลำดับที่แสดง)
#  ★ รายการนี้ต้องอยู่ท้ายไฟล์ (หลังฟังก์ชันทั้งหมด)
#  ★ ห้ามตั้งชื่อ url ว่า "summary" (ใช้แล้วสำหรับการ์ดสรุป)
# ============================================================
REPORTS = [
    ("best-selling",  "📈 สินค้าขายดี (Best Sellers)",                    report_best_selling),
    ("top-customers", "🏅 ลูกค้าที่ซื้อมากกว่าค่าเฉลี่ย (Above Average)", report_customers_above_avg),
    ("high-rated",    "⭐ สินค้าคะแนนรีวิวเฉลี่ย ≥ 4 (HAVING)",           report_high_rated),
    ("review",        "📋 รายงานรีวิวสินค้า",                          report_review),
    # ("my-report", "📋 รายงานของฉัน", report_my_report),   ← ตัวอย่างการเพิ่มรายงานที่ 4
]
