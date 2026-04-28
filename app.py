import streamlit as st
import pandas as pd
from yookassa import Configuration, Payment
import uuid
import os
import io
import sqlite3
import hashlib
import re
from dotenv import load_dotenv
from datetime import datetime, timedelta
import time

# ========== СТИЛИ ==========
st.set_page_config(page_title="CSV Анализатор Pro", layout="wide", page_icon="🚀")

st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .stButton > button {
        background: linear-gradient(90deg, #FF512F 0%, #DD2475 100%);
        color: white;
        font-size: 18px;
        font-weight: bold;
        border-radius: 40px;
        width: 100%;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.3);
    }
    /* Отключаем автозаполнение */
    input {
        autocomplete: off !important;
    }
    </style>
""", unsafe_allow_html=True)

# ========== ИНИЦИАЛИЗАЦИЯ СЕССИИ ==========
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = None

# ========== РАБОТА С БАЗОЙ ДАННЫХ ==========
def init_db():
    """Создаёт таблицы пользователей и подписок"""
    conn = sqlite3.connect('premium_users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password_hash TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT,
            premium_type TEXT,
            expires_at TEXT,
            payment_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (email) REFERENCES users(email)
        )
    ''')
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def register_user(email, password):
    if not validate_email(email):
        return False, "Неверный формат email"
    
    conn = sqlite3.connect('premium_users.db')
    c = conn.cursor()
    
    c.execute('SELECT email FROM users WHERE email = ?', (email,))
    if c.fetchone():
        conn.close()
        return False, "Пользователь с таким email уже существует"
    
    password_hash = hash_password(password)
    c.execute('INSERT INTO users (email, password_hash) VALUES (?, ?)', (email, password_hash))
    conn.commit()
    conn.close()
    return True, "Регистрация успешна"

def login_user(email, password):
    conn = sqlite3.connect('premium_users.db')
    c = conn.cursor()
    password_hash = hash_password(password)
    c.execute('SELECT email FROM users WHERE email = ? AND password_hash = ?', (email, password_hash))
    result = c.fetchone()
    conn.close()
    
    if result:
        return True, result[0]
    return False, None

def check_premium(email):
    try:
        conn = sqlite3.connect('premium_users.db')
        c = conn.cursor()
        now = datetime.now().isoformat()
        
        c.execute('''
            SELECT premium_type, expires_at FROM subscriptions 
            WHERE email = ? AND expires_at > ?
            ORDER BY expires_at DESC LIMIT 1
        ''', (email, now))
        
        result = c.fetchone()
        conn.close()
        
        if result:
            premium_type = result[0]
            expires_at_str = result[1]
            expires_at = datetime.fromisoformat(expires_at_str)
            now = datetime.now()
            
            if premium_type == 'single':
                hours_left = int((expires_at - now).total_seconds() // 3600)
                return {'type': premium_type, 'time_left': f"{hours_left} ч.", 'is_active': True}
            else:
                days_left = (expires_at - now).days
                return {'type': premium_type, 'time_left': f"{days_left} дн.", 'is_active': True}
        return None
    except Exception as e:
        print(f"[DB ERROR] check_premium: {e}")
        return None

def activate_premium(email, premium_type, payment_id):
    try:
        conn = sqlite3.connect('premium_users.db')
        c = conn.cursor()
        
        now = datetime.now()
        if premium_type == 'single':
            expires_at = now + timedelta(hours=24)
        elif premium_type == 'monthly':
            expires_at = now + timedelta(days=30)
        else:
            expires_at = now
        
        expires_at_str = expires_at.isoformat()
        
        c.execute('''
            INSERT INTO subscriptions (email, premium_type, expires_at, payment_id)
            VALUES (?, ?, ?, ?)
        ''', (email, premium_type, expires_at_str, payment_id))
        
        conn.commit()
        conn.close()
        
        print(f"[DB] Premium activated for {email}: {premium_type} until {expires_at_str}")
        return True
    except Exception as e:
        print(f"[DB ERROR] activate_premium: {e}")
        return False

init_db()

# ========== КЛЮЧИ ЮKASSA ==========
load_dotenv()
SHOP_ID = os.getenv("SHOP_ID")
SECRET_KEY = os.getenv("SECRET_KEY")

if not SHOP_ID or not SECRET_KEY:
    st.error("Ошибка: Не найдены ключи ЮKassa")
    st.stop()

Configuration.account_id = SHOP_ID
Configuration.secret_key = SECRET_KEY

MAX_FREE_ROWS = 50000
PRICE_SINGLE = 200
PRICE_MONTHLY = 1000

# ========== ФОРМА ВХОДА/РЕГИСТРАЦИИ ==========
def show_auth_form():
    """Показывает форму входа/регистрации"""
    st.title("🚀 CSV Анализатор Pro")
    st.markdown("### Добро пожаловать!")
    
    # Отключаем автозаполнение через HTML
    st.markdown("""
        <style>
            input[type=password] {
                -webkit-text-security: disc !important;
            }
            input {
                autocomplete: off !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔐 Вход", "📝 Регистрация"])
    
    with tab1:
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email", key="login_email", autocomplete="off")
            password = st.text_input("Пароль", type="password", key="login_password", autocomplete="new-password")
            submitted = st.form_submit_button("Войти", use_container_width=True)
            
            if submitted:
                if not email or not password:
                    st.error("Заполните все поля")
                else:
                    success, user_email = login_user(email, password)
                    if success:
                        st.session_state.logged_in = True
                        st.session_state.user_email = user_email
                        st.success(f"Добро пожаловать, {user_email}!")
                        st.rerun()
                    else:
                        st.error("Неверный email или пароль")
    
    with tab2:
        with st.form("register_form", clear_on_submit=False):
            email = st.text_input("Email", key="reg_email", autocomplete="off")
            password = st.text_input("Пароль", type="password", key="reg_password", autocomplete="new-password")
            password_confirm = st.text_input("Подтвердите пароль", type="password", key="reg_confirm", autocomplete="new-password")
            submitted = st.form_submit_button("Зарегистрироваться", use_container_width=True)
            
            if submitted:
                if not email or not password:
                    st.error("Заполните все поля")
                elif password != password_confirm:
                    st.error("Пароли не совпадают")
                elif len(password) < 4:
                    st.error("Пароль должен содержать минимум 4 символа")
                else:
                    success, message = register_user(email, password)
                    if success:
                        st.success(message)
                        # Автоматически входим после регистрации
                        st.session_state.logged_in = True
                        st.session_state.user_email = email
                        st.rerun()
                    else:
                        st.error(message)

# ========== ВОЗВРАТ ПОСЛЕ ОПЛАТЫ ==========
query_params = st.query_params
if query_params.get("success") == "true":
    payment_type = query_params.get("type", "unknown")
    payment_id = query_params.get("payment_id", "")
    
    if st.session_state.logged_in and payment_type in ["single", "monthly"]:
        activate_premium(st.session_state.user_email, payment_type, payment_id)
    
    st.title("✅ Оплата прошла успешно!")
    st.balloons()
    if payment_type == "single":
        st.markdown("**🎫 Разовый доступ активирован на 24 часа!**")
    elif payment_type == "monthly":
        st.markdown("**👑 Premium активирован на 30 дней!**")
    
    st.query_params.clear()
    if st.button("🚀 Продолжить работу"):
        st.rerun()
    st.stop()

# ========== ОСНОВНОЙ ИНТЕРФЕЙС ==========
if not st.session_state.logged_in:
    show_auth_form()
else:
    st.title("🚀 CSV Анализатор")
    st.markdown("### Мгновенный анализ больших CSV-файлов")
    
    with st.sidebar:
        st.header(f"👤 {st.session_state.user_email}")
        st.markdown("---")
        st.header("💎 Тарифы")
        st.markdown("**Бесплатно** — до 50 000 строк")
        st.markdown("**🎫 Разовый доступ** — 200 ₽ (24 часа)")
        st.markdown("**👑 Premium** — 1000 ₽ (30 дней)")
        
        premium_info = check_premium(st.session_state.user_email)
        if premium_info and premium_info.get('is_active'):
            if premium_info['type'] == 'single':
                st.success(f"⭐ Разовый доступ активен (ещё {premium_info['time_left']})")
            else:
                st.success(f"⭐ Premium активен (ещё {premium_info['time_left']})")
        
        st.markdown("---")
        if st.button("🚪 Выйти", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_email = None
            st.rerun()
    
    uploaded_file = st.file_uploader("📂 Выберите CSV файл", type="csv")
    
    if uploaded_file is not None:
        with st.spinner("🔄 Чтение файла..."):
            df = pd.read_csv(uploaded_file)
            rows = len(df)
        
        premium_info = check_premium(st.session_state.user_email)
        is_premium = premium_info and premium_info.get('is_active') if premium_info else False
        
        if not is_premium and rows > MAX_FREE_ROWS:
            st.warning(f"⚠️ Ваш файл содержит **{rows:,} строк** (бесплатно до {MAX_FREE_ROWS:,})")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🎫 Разовый доступ (200 ₽)", use_container_width=True):
                    payment_id = str(uuid.uuid4())
                    payment = Payment.create({
                        "amount": {"value": "200", "currency": "RUB"},
                        "payment_method_data": {"type": "bank_card"},
                        "confirmation": {
                            "type": "redirect",
                            "return_url": f"https://csv-analyzer-ru.onrender.com/?success=true&type=single&payment_id={payment_id}"
                        },
                        "description": f"Разовый доступ - {payment_id}"
                    })
                    st.markdown(f"[Оплатить 200 ₽]({payment.confirmation.confirmation_url})")
            with col2:
                if st.button("👑 Premium на месяц (1000 ₽)", use_container_width=True):
                    payment_id = str(uuid.uuid4())
                    payment = Payment.create({
                        "amount": {"value": "1000", "currency": "RUB"},
                        "payment_method_data": {"type": "bank_card"},
                        "confirmation": {
                            "type": "redirect",
                            "return_url": f"https://csv-analyzer-ru.onrender.com/?success=true&type=monthly&payment_id={payment_id}"
                        },
                        "description": f"Premium - {payment_id}"
                    })
                    st.markdown(f"[Оплатить 1000 ₽]({payment.confirmation.confirmation_url})")
            st.stop()
        
        st.success(f"✅ Файл загружен: **{rows:,} строк**")
        st.dataframe(df.head(100), use_container_width=True)
        
        st.markdown("## 📈 Статистика")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📊 Всего строк", f"{rows:,}")
        col2.metric("📋 Столбцов", len(df.columns))
        col3.metric("🔍 Пустых ячеек", df.isnull().sum().sum())
        col4.metric("🎯 Типов данных", len(df.dtypes.unique()))
        
        st.markdown("## 💾 Экспорт")
        export_format = st.radio("Формат:", ["CSV", "Excel (XLSX)", "JSON"], horizontal=True)
        
        if export_format == "CSV":
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 Скачать CSV", csv_data, "analyzed_data.csv", "text/csv", use_container_width=True)
        
        elif export_format == "Excel (XLSX)":
            st.info("⏳ Создание Excel-файла может занять 30-60 секунд. Пожалуйста, подождите...")
            progress_bar = st.progress(0)
            for i in range(100):
                time.sleep(0.01)
                progress_bar.progress(i + 1)
            try:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Data')
                excel_data = output.getvalue()
                progress_bar.progress(100)
                st.download_button("📥 Скачать Excel", excel_data, "analyzed_data.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            except Exception as e:
                st.error(f"Ошибка: {e}")
        
        elif export_format == "JSON":
            json_data = df.to_json(orient='records', indent=2, force_ascii=False).encode('utf-8')
            st.download_button("📥 Скачать JSON", json_data, "analyzed_data.json", "application/json", use_container_width=True)
    
    else:
        st.info("👈 Загрузите CSV файл для анализа")
