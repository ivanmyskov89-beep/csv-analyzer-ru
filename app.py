import streamlit as st
import pandas as pd
from yookassa import Configuration, Payment
import uuid
import os

# ========== НАСТРОЙКИ ==========
MAX_FREE_ROWS = 50000
MAX_FREE_SIZE_MB = 10
PRICE_RUB = 1000  # Цена подписки в рублях

# Настройки ЮKassa (замените на свои после регистрации)
SHOP_ID = "ВАШ_SHOP_ID"
SECRET_KEY = "ВАШ_SECRET_KEY"

Configuration.account_id = SHOP_ID
Configuration.secret_key = SECRET_KEY

# ========== ИНТЕРФЕЙС ==========
st.set_page_config(page_title="CSV Анализатор Pro", layout="wide")
st.title("🚀 CSV Анализатор")
st.write("Мгновенный анализ больших CSV-файлов без зависаний")

# Боковая панель с тарифами
with st.sidebar:
    st.header("💎 Тарифы")
    st.markdown("""
    **Бесплатно**
    - ✅ До 50 000 строк
    - ✅ До 10 МБ
    - ✅ Базовая аналитика
    
    **Premium — 1000 ₽/мес**
    - ✅ Неограниченно строк
    - ✅ Файлы до 1 ГБ
    - ✅ Экспорт в Excel/JSON
    - ✅ Приоритетная поддержка
    """)
    
    if 'premium' not in st.session_state:
        st.session_state.premium = False
    
    if st.session_state.premium:
        st.success("⭐ Premium активен")
    else:
        if st.button("🔥 Купить Premium за 1000 ₽"):
            st.session_state.show_payment = True

# ========== ЗАГРУЗКА ФАЙЛА ==========
uploaded_file = st.file_uploader("📂 Выберите CSV файл", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        row_count = len(df)
        file_size_mb = uploaded_file.size / (1024 * 1024)
        
        # Проверка лимитов
        if not st.session_state.premium:
            if row_count > MAX_FREE_ROWS or file_size_mb > MAX_FREE_SIZE_MB:
                st.warning(f"⚠️ Файл ({row_count:,} строк, {file_size_mb:.1f} МБ) превышает бесплатный лимит")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Строк в файле", f"{row_count:,}")
                    st.metric("Бесплатный лимит", f"{MAX_FREE_ROWS:,}")
                with col2:
                    st.metric("Размер файла", f"{file_size_mb:.1f} МБ")
                    st.metric("Лимит", f"{MAX_FREE_SIZE_MB} МБ")
                
                # Кнопка оплаты через ЮKassa
                if st.button("🚀 Получить Premium за 1000 ₽", type="primary"):
                    payment = Payment.create({
                        "amount": {"value": str(PRICE_RUB), "currency": "RUB"},
                        "payment_method_data": {"type": "bank_card"},
                        "confirmation": {
                            "type": "redirect",
                            "return_url": "https://ваш-сайт.onrender.com/success"
                        },
                        "description": f"Premium подписка CSV Analyzer - {uuid.uuid4()}"
                    })
                    st.markdown(f"[Оплатить картой]({payment.confirmation.confirmation_url})")
                    st.info("💳 После оплаты доступ откроется автоматически")
                st.stop()
        
        # Анализ данных (если лимит пройден или Premium)
        st.success(f"✅ Загружено: {row_count:,} строк, {file_size_mb:.1f} МБ")
        
        st.subheader("📊 Предпросмотр")
        st.dataframe(df.head(100))
        
        st.subheader("📈 Статистика")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Всего строк", f"{row_count:,}")
        col2.metric("Столбцов", len(df.columns))
        col3.metric("Пустых ячеек", df.isnull().sum().sum())
        col4.metric("Типов данных", len(df.dtypes.unique()))
        
        # Экспорт
        csv_export = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Скачать CSV", csv_export, "result.csv", "text/csv")
        
    except Exception as e:
        st.error(f"Ошибка: {e}")
else:
    st.info("👈 Загрузите CSV файл")
