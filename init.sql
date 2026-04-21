-- Создаем таблицу пользователей
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(100) NOT NULL,
    phone VARCHAR(20),                -- НОВОЕ
    sms_code VARCHAR(6),              -- НОВОЕ
    is_verified BOOLEAN DEFAULT FALSE, -- НОВОЕ
    balance DECIMAL(15, 2) DEFAULT 0.00
);


-- Создаем таблицу заявок на кредит
CREATE TABLE IF NOT EXISTS loans (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    loan_type VARCHAR(50),
    amount DECIMAL(15, 2),
    status VARCHAR(20) DEFAULT 'На рассмотрении'
);


CREATE TABLE IF NOT EXISTS credit_requests (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    type TEXT NOT NULL,
    amount TEXT DEFAULT '500 000',
    term_months INTEGER,
    comment TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT NOW(),
    status TEXT DEFAULT 'На рассмотрении'
);

ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS sms_code VARCHAR(6); -- Код для проверки
ALTER TABLE credit_requests ADD COLUMN IF NOT EXISTS term_months INTEGER;
ALTER TABLE credit_requests ADD COLUMN IF NOT EXISTS comment TEXT DEFAULT '';
ALTER TABLE credit_requests ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();
