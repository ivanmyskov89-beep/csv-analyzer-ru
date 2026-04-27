import streamlit as st
import pandas as pd
from yookassa import Configuration, Payment
import uuid
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# ========== СТИЛИ И ОФОРМЛЕНИЕ ==========
st.set_page_config(page_title="CSV Анализатор Pro", layout="wide", page_icon="🚀")

# Красивые стили (тёмная тема с градиентом)
st.markdown("""
    <style>
    /* Главный фон приложения */
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Контейнер с содержимым */
    .main > div {
        background: rgba(255,255,255,0.95);
        border-radius: 20px;
        padding: 20px;
        margin: 10px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
    /* Кнопки */
    .stButton > button {
        background: linear-gradient(90deg, #FF512F 0%, #DD2475 100%);
        color: white;
        font-size: 18px;
        font-weight: bold;
        padding: 12px 28px;
        border-radius: 40px;
        border: none;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.3);
        background: linear-gradient(90deg, #FF6B4A 0%, #FF3B6B 100%);
    }
    
    /* Заголовки */
    h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3em !important;
        font-weight: bold !important;
    }
    
    /* Сайдбар */
    .css-1d391kg {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    
    /* Предупреждения */
    .stAlert {
        border-radius: 15px;
        border-left: 5px solid #FF512F;
    }
    
    /* Метрики */
    .stMetric {
        background: white;
        border-radius: 15px;
        padding: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

# ========== ЗАГРУЗКА ПЕРЕМЕННЫХ ИЗ .env ==========
load_dotenv()

SHOP_ID = os.getenv("SHOP_ID")
SECRET_KEY = os.getenv("SECRET_KEY")

if not SHOP_ID or not SECRET_KEY:
    st.error("⚠️ Ошибка: Не найдены ключи ЮKassa")
    st.info("Пожалуйста, добавьте переменные окружения SHOP_ID и SECRET_KEY в настройках Render")
    st.stop()

Configuration.account_id = SHOP_ID
Configuration.secret_key = SECRET_KEY

# ========== НАСТРОЙКИ ==========
MAX_FREE_ROWS = 50000
MAX_FREE_SIZE_MB = 10
PRICE_SINGLE = 200
PRICE_MONTHLY = 1000

# ========== ОБРАБОТКА ВОЗВРАТА ПОСЛЕ ОПЛАТЫ ==========
query_params = st.query_params

if query_params.get("success") == "true":
    st.title("🎉 Оплата прошла успешно!")
    st.balloons()
    
    payment_type = query_params.get("type", "unknown")
    if payment_type == "single":
        st.markdown("## ✅ Разовый доступ активирован!")
        st.info("✨ Доступ действует 24 часа. Вы можете обработать этот файл без ограничений.")
        st.session_state.temp_premium = True
        st.session_state.premium_expiry = datetime.now() + timedelta(hours=24)
    elif payment_type == "monthly":
        st.markdown("## 👑 Premium на месяц активирован!")
        st.info("✨ Теперь вы можете загружать файлы любого размера в течение 30 дней.")
        st.session_state.premium = True
        st.session_state.premium_expiry = datetime.now() + timedelta(days=30)
    
    if st.button("🚀 Перейти к анализу CSV", type="primary"):
        st.query_params.clear()
        st.rerun()
    st.stop()

# ========== ПРОВЕРКА АКТИВНОСТИ PREMIUM ==========
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

# ========== ОСНОВНОЙ ИНТЕРФЕЙС ==========
st.title("🚀 CSV Анализатор")
st.markdown("### Мгновенный анализ больших CSV-файлов без зависаний")
st.markdown("---")

# Боковая панель с тарифами
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/2331/2331941.png", width=80)
    st.markdown("## 💎 Тарифы")
    st.markdown("---")
    
    st.markdown("### 🆓 Бесплатно")
    st.markdown("- ✅ До 50 000 строк")
    st.markdown("- ✅ До 10 МБ")
    
    st.markdown("---")
    
    st.markdown("### 🎫 Разовый доступ")
    st.markdown("- **200 ₽**")
    st.markdown("- ✅ Один файл любого размера")
    st.markdown("- ✅ Доступ на 24 часа")
    
    st.markdown("---")
    
    st.markdown("### 👑 Premium")
    st.markdown("- **1000 ₽/мес**")
    st.markdown("- ✅ Неограниченное количество файлов")
    st.markdown("- ✅ Безлимит на 30 дней")
    st.markdown("- ✅ Экспорт в CSV/Excel/JSON")
    st.markdown("- ✅ Приоритетная поддержка")
    
    st.markdown("---")
    
    if is_premium_active():
        st.success("⭐ Premium активен")
        expiry = st.session_state.get("premium_expiry")
        if expiry:
            days_left = (expiry - datetime.now()).days
            st.caption(f"📅 Действует до: {expiry.strftime('%d.%m.%Y')} (осталось {days_left} дн.)")
    elif st.session_state.get("temp_premium", False):
        st.success("⭐ Разовый доступ активен")
        expiry = st.session_state.get("premium_expiry")
        if expiry:
            hours_left = (expiry - datetime.now()).seconds // 3600
            st.caption(f"⏰ Действует ещё {hours_left} часов")

# Загрузка файла
st.markdown("### 📂 Загрузите ваш CSV файл")
uploaded_file = st.file_uploader("", type="csv", label_visibility="collapsed")

if uploaded_file is not None:
    try:
        with st.spinner("🔄 Обработка файла..."):
            df = pd.read_csv(uploaded_file)
            row_count = len(df)
            file_size_mb = uploaded_file.size / (1024 * 1024)
        
        if not is_premium_active():
            if row_count > MAX_FREE_ROWS or file_size_mb > MAX_FREE_SIZE_MB:
                st.warning(f"⚠️ Ваш файл содержит **{row_count:,} строк** ({file_size_mb:.1f} МБ) и превышает бесплатный лимит в **{MAX_FREE_ROWS:,} строк**")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("📊 Строк в вашем файле", f"{row_count:,}")
                    st.metric("🎁 Бесплатно до", f"{MAX_FREE_ROWS:,}")
                with col2:
                    st.metric("📁 Размер файла", f"{file_size_mb:.1f} МБ")
                    st.metric("🎁 Бесплатно до", f"{MAX_FREE_SIZE_MB} МБ")
                
                st.markdown("---")
                st.markdown("## 💳 Выберите способ оплаты:")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("🎫 Разовый доступ (200 ₽)", type="primary", use_container_width=True):
                        with st.spinner("🔄 Перенаправление на оплату..."):
                            payment = Payment.create({
                                "amount": {"value": str(PRICE_SINGLE), "currency": "RUB"},
                                "payment_method_data": {"type": "bank_card"},
                                "confirmation": {
                                    "type": "redirect",
                                    "return_url": "https://csv-analyzer-ru.onrender.com/?success=true&type=single"
                                },
                                "description": f"Разовый доступ CSV Analyzer - {uuid.uuid4()}"
                            })
                            st.session_state.payment_id = payment.id
                            st.markdown(f"[Оплатить 200 ₽]({payment.confirmation.confirmation_url})")
                            st.info("📌 После оплаты вы вернётесь на эту страницу")
                
                with col2:
                    if st.button("👑 Premium на месяц (1000 ₽)", type="primary", use_container_width=True):
                        with st.spinner("🔄 Перенаправление на оплату..."):
                            payment = Payment.create({
                                "amount": {"value": str(PRICE_MONTHLY), "currency": "RUB"},
                                "payment_method_data": {"type": "bank_card"},
                                "confirmation": {
                                    "type": "redirect",
                                    "return_url": "https://csv-analyzer-ru.onrender.com/?success=true&type=monthly"
                                },
                                "description": f"Premium подписка CSV Analyzer - {uuid.uuid4()}"
                            })
                            st.session_state.payment_id = payment.id
                            st.markdown(f"[Оплатить 1000 ₽]({payment.confirmation.confirmation_url})")
                            st.info("📌 После оплаты вы вернётесь на эту страницу")
                
                st.caption("💳 Оплата проходит через защищённое соединение ЮKassa")
                st.stop()
        
        # Анализ данных
        st.success(f"✅ Файл успешно загружен! **{row_count:,} строк**, **{file_size_mb:.1f} МБ**")
        
        st.markdown("---")
        st.markdown("## 📊 Предпросмотр данных")
        st.dataframe(df.head(100), use_container_width=True)
        
        st.markdown("---")
        st.markdown("## 📈 Статистика")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 Всего строк", f"{row_count:,}")
        with col2:
            st.metric("📋 Столбцов", len(df.columns))
        with col3:
            st.metric("🔍 Пустых ячеек", df.isnull().sum().sum())
        with col4:
            st.metric("🎯 Типов данных", len(df.dtypes.unique()))
        
        with st.expander("📋 Детальная информация по столбцам"):
            dtype_df = pd.DataFrame({
                "Столбец": df.columns,
                "Тип данных": [str(dtype) for dtype in df.dtypes.values],
                "Уникальных значений": [df[col].nunique() for col in df.columns],
                "Пустых значений": [df[col].isnull().sum() for col in df.columns],
                "Заполнено (%)": [round((1 - df[col].isnull().sum()/len(df))*100, 1) for col in df.columns]
            })
            st.dataframe(dtype_df, use_container_width=True)
        
        st.markdown("---")
        st.markdown("## 💾 Экспорт данных")
        
        csv_export = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Скачать результат (CSV)",
            data=csv_export,
            file_name="analyzed_data.csv",
            mime="text/csv",
            use_container_width=True
        )
        
    except Exception as e:
        st.error(f"❌ Ошибка при обработке файла: {e}")
        st.info("Убедитесь, что файл имеет правильный формат CSV (разделитель - запятая)")
else:
    st.info("👈 Загрузите CSV файл, чтобы начать анализ")
    
    with st.expander("ℹ️ О сервисе"):
        st.markdown("""
        **CSV Analyzer — это инструмент для быстрого анализа больших CSV-файлов**
        
        **Возможности:**
        - Мгновенный просмотр данных (первые 100 строк)
        - Автоматическая статистика по всем столбцам
        - Определение типов данных
        - Поиск пустых значений
        - Экспорт обработанных данных
        
        **Тарифы:**
        - **Бесплатно** — для файлов до 50 000 строк
        - **Разовый доступ (200 ₽)** — для одного большого файла (24 часа)
        - **Premium (1000 ₽/мес)** — неограниченное количество файлов
        """)

if 'payment_id' in st.session_state and not is_premium_active():
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Проверить статус оплаты", use_container_width=True):
        with st.spinner("Проверка..."):
            try:
                payment = Payment.find_one(st.session_state.payment_id)
                if payment.status == "succeeded":
                    st.sidebar.success("✅ Оплата подтверждена!")
                    st.rerun()
                else:
                    st.sidebar.info(f"Статус платежа: {payment.status}")
            except Exception as e:
                st.sidebar.error(f"Ошибка: {e}")
