import streamlit as st
import pandas as pd
from yookassa import Configuration, Payment
import uuid
import os
import io
from dotenv import load_dotenv
from datetime import datetime, timedelta

# ========== СТИЛИ ==========
st.set_page_config(page_title="CSV Анализатор", layout="wide")
st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    .stButton > button {
        background: linear-gradient(90deg, #FF512F 0%, #DD2475 100%);
        color: white;
        font-size: 18px;
        font-weight: bold;
        border-radius: 40px;
        width: 100%;
    }
    .stButton > button:hover { transform: translateY(-2px); }
    </style>
""", unsafe_allow_html=True)

# ========== СЕССИЯ ==========
if 'uploaded_data' not in st.session_state:
    st.session_state.uploaded_data = None
if 'premium' not in st.session_state:
    st.session_state.premium = False
if 'temp_premium' not in st.session_state:
    st.session_state.temp_premium = False

# ========== КЛЮЧИ ==========
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
    return st.session_state.get("premium", False) or st.session_state.get("temp_premium", False)

# ========== ВОЗВРАТ ПОСЛЕ ОПЛАТЫ ==========
query_params = st.query_params
if query_params.get("success") == "true":
    st.title("✅ Оплата прошла успешно!")
    st.balloons()
    if query_params.get("type") == "single":
        st.session_state.temp_premium = True
    elif query_params.get("type") == "monthly":
        st.session_state.premium = True
    st.query_params.clear()
    if st.button("🚀 Продолжить работу"):
        st.rerun()
    st.stop()

# ========== ОСНОВНОЙ ИНТЕРФЕЙС ==========
st.title("📊 CSV Анализатор")
st.markdown("### Мгновенный анализ больших CSV файлов")

with st.sidebar:
    st.header("💎 Тарифы")
    st.markdown("**Бесплатно** - до 50 000 строк")
    st.markdown("**🎫 Разовый доступ** - 200 ₽ (24 часа)")
    st.markdown("**👑 Premium** - 1000 ₽ (30 дней)")
    if is_premium_active():
        st.success("⭐ Premium активен")

# Загрузка файла
uploaded_file = st.file_uploader("📂 Выберите CSV файл", type="csv")

if uploaded_file is not None:
    st.session_state.uploaded_data = uploaded_file.getvalue()
    st.rerun()

# Анализ
if st.session_state.uploaded_data is not None:
    try:
        df = pd.read_csv(io.BytesIO(st.session_state.uploaded_data))
        rows = len(df)
        
        # Проверка лимита
        if not is_premium_active() and rows > MAX_FREE_ROWS:
            st.warning(f"⚠️ Файл содержит {rows:,} строк (бесплатно до {MAX_FREE_ROWS:,})")
            
            st.markdown("### 💳 Оплатите доступ:")
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🎫 Разовый доступ (200 ₽)"):
                    payment = Payment.create({
                        "amount": {"value": "200", "currency": "RUB"},
                        "payment_method_data": {"type": "bank_card"},
                        "confirmation": {
                            "type": "redirect",
                            "return_url": "https://csv-analyzer-ru.onrender.com/?success=true&type=single"
                        },
                        "description": f"Разовый доступ - {uuid.uuid4()}"
                    })
                    st.markdown(f"[👉 ОПЛАТИТЬ 200 ₽ 👈]({payment.confirmation.confirmation_url})")
            
            with col2:
                if st.button("👑 Premium на месяц (1000 ₽)"):
                    payment = Payment.create({
                        "amount": {"value": "1000", "currency": "RUB"},
                        "payment_method_data": {"type": "bank_card"},
                        "confirmation": {
                            "type": "redirect",
                            "return_url": "https://csv-analyzer-ru.onrender.com/?success=true&type=monthly"
                        },
                        "description": f"Premium - {uuid.uuid4()}"
                    })
                    st.markdown(f"[👉 ОПЛАТИТЬ 1000 ₽ 👈]({payment.confirmation.confirmation_url})")
            
            st.info("💡 После оплаты нажмите 'Продолжить работу'")
            st.stop()
        
        # Результат
        st.success(f"✅ Загружено: {rows:,} строк")
        st.dataframe(df.head(100))
        
        st.markdown("### 💾 Экспорт")
        fmt = st.selectbox("Формат:", ["CSV", "Excel", "JSON"])
        
        if fmt == "CSV":
            data = df.to_csv(index=False).encode('utf-8-sig')
            mime = "text/csv"
            ext = "csv"
        elif fmt == "Excel":
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            data = buf.getvalue()
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ext = "xlsx"
        else:
            data = df.to_json(orient='records', indent=2, force_ascii=False).encode('utf-8')
            mime = "application/json"
            ext = "json"
        
        st.download_button(f"📥 Скачать {fmt}", data, f"data.{ext}", mime)
        
        if st.button("🗑️ Новый файл"):
            st.session_state.uploaded_data = None
            st.rerun()
            
    except Exception as e:
        st.error(f"Ошибка: {e}")
        st.session_state.uploaded_data = None
else:
    st.info("👈 Загрузите CSV файл")
