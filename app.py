import streamlit as st
import pandas as pd
from yookassa import Configuration, Payment
import uuid
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

SHOP_ID = os.getenv("SHOP_ID")
SECRET_KEY = os.getenv("SECRET_KEY")

if not SHOP_ID or not SECRET_KEY:
    st.error("Ошибка: Не найдены ключи ЮKassa")
    st.stop()

Configuration.account_id = SHOP_ID
Configuration.secret_key = SECRET_KEY

MAX_FREE_ROWS = 50000
MAX_FREE_SIZE_MB = 10
PRICE_SINGLE = 200
PRICE_MONTHLY = 1000

query_params = st.query_params

if query_params.get("success") == "true":
    st.set_page_config(page_title="Оплата успешна", layout="centered")
    st.title("Оплата прошла успешно!")
    st.balloons()
    
    payment_type = query_params.get("type", "unknown")
    if payment_type == "single":
        st.markdown("**Разовый доступ активирован!**")
        st.info("Доступ действует 24 часа.")
        st.session_state.temp_premium = True
        st.session_state.premium_expiry = datetime.now() + timedelta(hours=24)
    elif payment_type == "monthly":
        st.markdown("**Premium на месяц активирован!**")
        st.info("Доступ действует 30 дней.")
        st.session_state.premium = True
        st.session_state.premium_expiry = datetime.now() + timedelta(days=30)
    
    if st.button("Перейти к анализу"):
        st.query_params.clear()
        st.rerun()
    st.stop()

def is_premium_active():
    if st.session_state.get("premium", False):
        expiry = st.session_state.get("premium_expiry")
        if expiry and datetime.now() < expiry:
            return True
        else:
            st.session_state.premium = False
    if st.session_state.get("temp_premium", False):
        expiry = st.session_state.get("premium_expiry")
        if expiry and datetime.now() < expiry:
            return True
        else:
            st.session_state.temp_premium = False
    return False

st.set_page_config(page_title="CSV Анализатор Pro", layout="wide")
st.title("CSV Анализатор")
st.write("Мгновенный анализ больших CSV-файлов")

with st.sidebar:
    st.header("Тарифы")
    st.markdown("""
    **Бесплатно** - до 50000 строк
    **Разовый доступ** - 200 руб (24 часа)
    **Premium** - 1000 руб/мес
    """)

uploaded_file = st.file_uploader("Выберите CSV файл", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        row_count = len(df)
        file_size_mb = uploaded_file.size / (1024 * 1024)
        
        if not is_premium_active():
            if row_count > MAX_FREE_ROWS or file_size_mb > MAX_FREE_SIZE_MB:
                st.warning(f"Файл ({row_count:,} строк) превышает бесплатный лимит")
                
                st.subheader("Выберите способ оплаты:")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Разовый доступ (200 руб)", type="primary"):
                        payment = Payment.create({
                            "amount": {"value": str(PRICE_SINGLE), "currency": "RUB"},
                            "payment_method_data": {"type": "bank_card"},
                            "confirmation": {
                                "type": "redirect",
                                "return_url": "https://csv-analyzer-ru.onrender.com/?success=true&type=single"
                            },
                            "description": f"Разовый доступ - {uuid.uuid4()}"
                        })
                        st.markdown(f"[Оплатить 200 руб]({payment.confirmation.confirmation_url})")
                        st.session_state.payment_id = payment.id
                
                with col2:
                    if st.button("Premium на месяц (1000 руб)", type="primary"):
                        payment = Payment.create({
                            "amount": {"value": str(PRICE_MONTHLY), "currency": "RUB"},
                            "payment_method_data": {"type": "bank_card"},
                            "confirmation": {
                                "type": "redirect",
                                "return_url": "https://csv-analyzer-ru.onrender.com/?success=true&type=monthly"
                            },
                            "description": f"Premium подписка - {uuid.uuid4()}"
                        })
                        st.markdown(f"[Оплатить 1000 руб]({payment.confirmation.confirmation_url})")
                        st.session_state.payment_id = payment.id
                
                st.stop()
        
        st.success(f"Загружено: {row_count:,} строк")
        st.dataframe(df.head(100))
        
        st.subheader("Статистика")
        col1, col2 = st.columns(2)
        col1.metric("Всего строк", f"{row_count:,}")
        col2.metric("Столбцов", len(df.columns))
        
        csv_export = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("Скачать CSV", csv_export, "analyzed_data.csv")
        
    except Exception as e:
        st.error(f"Ошибка: {e}")
else:
    st.info("Загрузите CSV файл")

if 'payment_id' in st.session_state and not is_premium_active():
    if st.sidebar.button("Проверить оплату"):
        try:
            payment = Payment.find_one(st.session_state.payment_id)
            if payment.status == "succeeded":
                st.rerun()
        except Exception as e:
            st.sidebar.error(f"Ошибка: {e}")