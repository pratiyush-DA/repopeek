-- Oracle PL/SQL schema and query
CREATE TABLE invoices (
    invoice_id NUMBER PRIMARY KEY,
    customer_id NUMBER NOT NULL,
    amount NUMBER(10, 2) NOT NULL,
    status VARCHAR2(20) DEFAULT 'PENDING'
);

SELECT i.invoice_id, c.customer_name, i.amount
FROM invoices i
JOIN customers c ON i.customer_id = c.customer_id
WHERE i.status = 'PENDING';
