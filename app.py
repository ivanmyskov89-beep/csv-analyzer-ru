import streamlit as st
import pandas as pd
from yookassa import Configuration, Payment
import uuid
import os
import io
import sqlite3
from dotenv import load_dotenv
from datetime import datetime, timedelta

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
    </style>
""", unsafe_allow_html=True)

# ========== ИНИЦИАЛИЗАЦИЯ СЕССИИ ==========
if 'user_id' not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

# ========== РАБОТА С БАЗОЙ ДАННЫХ ==========
def init_db():
    """Создаёт таблицу пользователей, если её нет"""
    conn = sqlite3.connect('premium_users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            premium_type TEXT,
            expires_at TEXT,
            payment_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def check_premium(user_id):
    """
    Проверяет, активен ли Premium у пользователя.
    Возвращает словарь с информацией о подписке или None
    """
    try:
        conn = sqlite3.connect('premium_users.db')
        c = conn.cursor()
        now = datetime.now().isoformat()
        
        c.execute('''
            SELECT premium_type, expires_at FROM users 
            WHERE user_id = ? AND expires_at > ?
            ORDER BY expires_at DESC LIMIT 1
        ''', (user_id, now))
        
        result = c.fetchone()
        conn.close()
        
        if result:
            premium_type = result[0]
            expires_at_str = result[1]
            expires_at = datetime.fromisoformat(expires_at_str)
            now = datetime.now()
            
            # Рассчитываем оставшееся время
            if premium_type == 'single':
                hours_left = int((expires_at - now).total_seconds() // 3600)
                return {
                    'type': premium_type,
                    'expires_at': expires_at_str,
                    'time_left': f"{hours_left} ч.",
                    'is_active': True
                }
            else:
                days_left = (expires_at - now).days
                return {
                    'type': premium_type,
                    'expires_at': expires_at_str,
                    'time_left': f"{days_left} дн.",
                    'is_active': True
                }
        return None
    except Exception as e:
        print(f"[DB ERROR] check_premium: {e}")
        return None

def activate_premium(user_id, premium_type, payment_id):
    """Активирует Premium в базе данных"""
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
        
        # Сохраняем в ISO формате для надёжного сравнения
        expires_at_str = expires_at.isoformat()
        created_at_str = now.isoformat()
        
        c.execute('''
            INSERT OR REPLACE INTO users (user_id, premium_type, expires_at, payment_id, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, premium_type, expires_at_str, payment_id, created_at_str))
        
        conn.commit()
        conn.close()
        
        # Логируем в консоль (будет видно в логах Render)
        print(f"[DB] Premium activated for {user_id[:8]}...: {premium_type} until {expires_at_str}")
        return True
    except Exception as e:
        print(f"[DB ERROR] activate_premium: {e}")
        return False

# Инициализируем базу данных при старте
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

# ========== НАСТРОЙКИ ==========
MAX_FREE_ROWS = 50000
PRICE_SINGLE = 200
PRICE_MONTHLY = 1000

def is_premium_active():
    """Проверяет Premium через базу данных"""
    premium_info = check_premium(st.session_state.user_id)
    if premium_info and premium_info.get('is_active'):
        return True
    return False

# ========== ВОЗВРАТ ПОСЛЕ ОПЛАТЫ ==========
query_params = st.query_params
if query_params.get("success") == "true":
    payment_type = query_params.get("type", "unknown")
    payment_id = query_params.get("payment_id", "")
    
    if payment_type in ["single", "monthly"]:
        activate_premium(st.session_state.user_id, payment_type, payment_id)
    
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
st.title("🚀 CSV Анализатор")
st.markdown("### Мгновенный анализ больших CSV-файлов")

with st.sidebar:
    st.header("💎 Тарифы")
    st.markdown("**Бесплатно** — до 50 000 строк")
    st.markdown("**🎫 Разовый доступ** — 200 ₽ (24 часа)")
    st.markdown("**👑 Premium** — 1000 ₽ (30 дней)")
    
    premium_info = check_premium(st.session_state.user_id)
    if premium_info and premium_info.get('is_active'):
        if premium_info['type'] == 'single':
            st.success(f"⭐ Разовый доступ активен (ещё {premium_info['time_left']})")
        else:
            st.success(f"⭐ Premium активен (ещё {premium_info['time_left']})")
    st.caption(f"🆔 Ваш ID: {st.session_state.user_id[:8]}...")

# ========== ЗАГРУЗКА ФАЙЛА ==========
uploaded_file = st.file_uploader("📂 Выберите CSV файл", type="csv")

if uploaded_file is not None:
    with st.spinner("🔄 Чтение файла..."):
        df = pd.read_csv(uploaded_file)
        rows = len(df)
    
    # Проверяем статус Premium
    premium_info = check_premium(st.session_state.user_id)
    is_premium = premium_info and premium_info.get('is_active')
    
    st.caption(f"📊 Отладка: строк {rows:,} | лимит {MAX_FREE_ROWS:,} | Premium: {'Да' if is_premium else 'Нет'}")
    
    # ========== ПРОВЕРКА ЛИМИТА ==========
    if not is_premium and rows > MAX_FREE_ROWS:
        st.warning(f"⚠️ Ваш файл содержит **{rows:,} строк** (бесплатно до {MAX_FREE_ROWS:,})")
        
        st.markdown("## 💳 Выберите способ оплаты:")
        
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
                st.markdown(f"[👉 ОПЛАТИТЬ 200 ₽ 👈]({payment.confirmation.confirmation_url})")
        
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
                st.markdown(f"[👉 ОПЛАТИТЬ 1000 ₽ 👈]({payment.confirmation.confirmation_url})")
        
        st.info("💡 После оплаты страница обновится автоматически")
        st.stop()
    
    # ========== АНАЛИЗ ==========
    st.success(f"✅ Файл загружен: **{rows:,} строк**" + (" (Premium активен)" if is_premium else ""))
    
    st.markdown("---")
    st.markdown("## 📊 Предпросмотр")
    st.dataframe(df.head(100), use_container_width=True)
    
    st.markdown("---")
    st.markdown("## 📈 Статистика")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📊 Всего строк", f"{rows:,}")
    col2.metric("📋 Столбцов", len(df.columns))
    col3.metric("🔍 Пустых ячеек", df.isnull().sum().sum())
    col4.metric("🎯 Типов данных", len(df.dtypes.unique()))
    
    with st.expander("📋 Детальная информация по столбцам"):
        dtype_df = pd.DataFrame({
            "Столбец": df.columns,
            "Тип данных": [str(d) for d in df.dtypes.values],
            "Уникальных значений": [df[col].nunique() for col in df.columns],
            "Пустых значений": [df[col].isnull().sum() for col in df.columns]
        })
        st.dataframe(dtype_df, use_container_width=True)
    
    # ========== ЭКСПОРТ ==========
    st.markdown("---")
    st.markdown("## 💾 Экспорт")
    
    export_format = st.radio("Выберите формат:", ["CSV", "Excel (XLSX)", "JSON"], horizontal=True)
    
    if export_format == "CSV":
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Скачать CSV",
            data=csv_data,
            file_name="analyzed_data.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    elif export_format == "Excel (XLSX)":
        try:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Data')
            excel_data = output.getvalue()
            st.download_button(
                label="📥 Скачать Excel",
                data=excel_data,
                file_name="analyzed_data.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Excel не поддерживается: {e}")
    
    elif export_format == "JSON":
        json_data = df.to_json(orient='records', indent=2, force_ascii=False).encode('utf-8')
        st.download_button(
            label="📥 Скачать JSON",
            data=json_data,
            file_name="analyzed_data.json",
            mime="application/json",
            use_container_width=True
        )

else:
    st.info("👈 Загрузите CSV файл для анализа")
