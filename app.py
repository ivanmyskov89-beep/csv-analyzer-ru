import streamlit as st
import pandas as pd
from yookassa import Configuration, Payment
import uuid
import os
import io
from dotenv import load_dotenv
from datetime import datetime, timedelta

# ========== СТИЛИ И ОФОРМЛЕНИЕ ==========
st.set_page_config(page_title="CSV Анализатор Pro", layout="wide", page_icon="🚀")

st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Стиль для кнопки Premium (красно-оранжевый) */
    .stButton > button {
        background: linear-gradient(90deg, #FF512F 0%, #DD2475 100%);
        color: white;
        font-size: 18px;
        font-weight: bold;
        border-radius: 40px;
        transition: all 0.3s ease;
        width: 100%;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.3);
    }
    
    /* Стиль для кнопки "Разовый доступ" (зелёный) */
    button[kind="single"] {
        background: linear-gradient(90deg, #00b09b 0%, #96c93d 100%) !important;
        color: white !important;
    }
    button[kind="single"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.3);
    }
    
    h1 {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    </style>
""", unsafe_allow_html=True)

# ========== ИНИЦИАЛИЗАЦИЯ ПЕРЕМЕННЫХ СЕССИИ ==========
if 'uploaded_data' not in st.session_state:
    st.session_state.uploaded_data = None
if 'uploaded_filename' not in st.session_state:
    st.session_state.uploaded_filename = None
if 'premium' not in st.session_state:
    st.session_state.premium = False
if 'temp_premium' not in st.session_state:
    st.session_state.temp_premium = False
if 'premium_expiry' not in st.session_state:
    st.session_state.premium_expiry = None

# ========== ЗАГРУЗКА ПЕРЕМЕННЫХ ИЗ .env ==========
load_dotenv()

SHOP_ID = os.getenv("SHOP_ID")
SECRET_KEY = os.getenv("SECRET_KEY")

if not SHOP_ID or not SECRET_KEY:
    st.error("⚠️ Ошибка: Не найдены ключи ЮKassa")
    st.stop()

Configuration.account_id = SHOP_ID
Configuration.secret_key = SECRET_KEY

# ========== НАСТРОЙКИ ==========
MAX_FREE_ROWS = 50000
MAX_FREE_SIZE_MB = 10
PRICE_SINGLE = 200
PRICE_MONTHLY = 1000

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

# ========== ОБРАБОТКА ВОЗВРАТА ПОСЛЕ ОПЛАТЫ ==========
query_params = st.query_params

if query_params.get("success") == "true":
    st.title("🎉 Оплата прошла успешно!")
    st.balloons()
    
    payment_type = query_params.get("type", "unknown")
    if payment_type == "single":
        st.markdown("## ✅ Разовый доступ активирован!")
        st.info("✨ Доступ действует 24 часа. Теперь загрузите ваш файл снова — он будет обработан без ограничений.")
        st.session_state.temp_premium = True
        st.session_state.premium_expiry = datetime.now() + timedelta(hours=24)
    elif payment_type == "monthly":
        st.markdown("## 👑 Premium на месяц активирован!")
        st.info("✨ Теперь вы можете загружать файлы любого размера. Просто загрузите файл снова!")
        st.session_state.premium = True
        st.session_state.premium_expiry = datetime.now() + timedelta(days=30)
    
    # Очищаем параметры URL
    st.query_params.clear()
    
    if st.button("🚀 Продолжить работу", type="primary"):
        st.rerun()
    st.stop()

# ========== ОСНОВНОЙ ИНТЕРФЕЙС ==========
st.title("🚀 CSV Анализатор")
st.markdown("### Мгновенный анализ больших CSV-файлов без зависаний")
st.markdown("---")

# Боковая панель
with st.sidebar:
    st.markdown("## 💎 Тарифы")
    st.markdown("---")
    st.markdown("### 🆓 Бесплатно")
    st.markdown("- До 50 000 строк")
    st.markdown("- До 10 МБ")
    st.markdown("---")
    st.markdown("### 🎫 Разовый доступ")
    st.markdown("- **200 ₽** (24 часа)")
    st.markdown("---")
    st.markdown("### 👑 Premium")
    st.markdown("- **1000 ₽/мес** (30 дней)")
    st.markdown("- Неограниченно файлов")
    st.markdown("- Экспорт в CSV")
    
    if is_premium_active():
        st.success("⭐ Premium активен")
        if st.session_state.premium_expiry:
            days_left = (st.session_state.premium_expiry - datetime.now()).days
            st.caption(f"📅 Осталось {days_left} дн.")

# Загрузка файла
st.markdown("### 📂 Загрузите ваш CSV файл")

uploaded_file = st.file_uploader("", type="csv", label_visibility="collapsed")

if uploaded_file is not None:
    # Сохраняем данные в сессию
    st.session_state.uploaded_data = uploaded_file.getvalue()
    st.session_state.uploaded_filename = uploaded_file.name
    st.rerun()

# Работа с данными из сессии
if st.session_state.uploaded_data is not None:
    try:
        df = pd.read_csv(io.BytesIO(st.session_state.uploaded_data))
        row_count = len(df)
        file_size_mb = len(st.session_state.uploaded_data) / (1024 * 1024)
        
        # Проверка лимитов
        if not is_premium_active():
            if row_count > MAX_FREE_ROWS or file_size_mb > MAX_FREE_SIZE_MB:
                st.warning(f"⚠️ Ваш файл содержит **{row_count:,} строк** ({file_size_mb:.1f} МБ) и превышает бесплатный лимит")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Строк в файле", f"{row_count:,}")
                    st.metric("Бесплатно до", f"{MAX_FREE_ROWS:,}")
                with col2:
                    st.metric("Размер файла", f"{file_size_mb:.1f} МБ")
                    st.metric("Бесплатно до", f"{MAX_FREE_SIZE_MB} МБ")
                
                st.markdown("---")
                st.markdown("## 💳 Выберите способ оплаты:")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Кнопка с кастомным атрибутом kind="single"
                    if st.button("🎫 Разовый доступ (200 ₽)", type="primary", use_container_width=True, key="single_btn"):
                        payment = Payment.create({
                            "amount": {"value": str(PRICE_SINGLE), "currency": "RUB"},
                            "payment_method_data": {"type": "bank_card"},
                            "confirmation": {
                                "type": "redirect",
                                "return_url": "https://csv-analyzer-ru.onrender.com/?success=true&type=single"
                            },
                            "description": f"Разовый доступ - {uuid.uuid4()}"
                        })
                        st.markdown(f"[Оплатить 200 ₽]({payment.confirmation.confirmation_url})")
                        st.info("💡 После оплаты нажмите 'Продолжить работу' и загрузите файл снова")
                    
                    # Добавляем JavaScript для применения стиля к кнопке
                    st.markdown("""
                        <script>
                            const btn = document.querySelector('button[key="single_btn"]');
                            if (btn) {
                                btn.setAttribute('kind', 'single');
                            }
                        </script>
                    """, unsafe_allow_html=True)
                
                with col2:
                    if st.button("👑 Premium на месяц (1000 ₽)", use_container_width=True):
                        payment = Payment.create({
                            "amount": {"value": str(PRICE_MONTHLY), "currency": "RUB"},
                            "payment_method_data": {"type": "bank_card"},
                            "confirmation": {
                                "type": "redirect",
                                "return_url": "https://csv-analyzer-ru.onrender.com/?success=true&type=monthly"
                            },
                            "description": f"Premium подписка - {uuid.uuid4()}"
                        })
                        st.markdown(f"[Оплатить 1000 ₽]({payment.confirmation.confirmation_url})")
                        st.info("💡 После оплаты нажмите 'Продолжить работу' и загрузите файл снова")
                
                st.stop()
        
        # Анализ данных (Premium активен или лимит не превышен)
        st.success(f"✅ Файл **{st.session_state.uploaded_filename}** загружен! **{row_count:,} строк**, **{file_size_mb:.1f} МБ**")
        
        st.markdown("---")
        st.markdown("## 📊 Предпросмотр данных")
        st.dataframe(df.head(100), use_container_width=True)
        
        st.markdown("---")
        st.markdown("## 📈 Статистика")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Всего строк", f"{row_count:,}")
        with col2:
            st.metric("Столбцов", len(df.columns))
        with col3:
            st.metric("Пустых ячеек", df.isnull().sum().sum())
        with col4:
            st.metric("Типов данных", len(df.dtypes.unique()))
        
        with st.expander("📋 Типы данных по столбцам"):
            dtype_df = pd.DataFrame({
                "Столбец": df.columns,
                "Тип данных": [str(dtype) for dtype in df.dtypes.values],
                "Уникальных значений": [df[col].nunique() for col in df.columns],
                "Пустых значений": [df[col].isnull().sum() for col in df.columns]
            })
            st.dataframe(dtype_df, use_container_width=True)
        
        st.markdown("---")
        st.markdown("## 💾 Экспорт")
        
        csv_export = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Скачать CSV",
            data=csv_export,
            file_name="analyzed_data.csv",
            mime="text/csv",
            use_container_width=True
        )
        
        # Кнопка для очистки файла
        if st.button("🗑️ Очистить и загрузить другой файл"):
            st.session_state.uploaded_data = None
            st.session_state.uploaded_filename = None
            st.rerun()
        
    except Exception as e:
        st.error(f"❌ Ошибка при обработке файла: {e}")
        st.session_state.uploaded_data = None
else:
    st.info("👈 Загрузите CSV файл, чтобы начать анализ")
    
    with st.expander("ℹ️ Как это работает"):
        st.markdown("""
        **1️⃣ Загрузите CSV файл** (до 50 000 строк — бесплатно)
        
        **2️⃣ Если файл больше** — выберите тариф:
        - **Разовый доступ (200 ₽)** — 24 часа на один файл
        - **Premium (1000 ₽)** — 30 дней безлимит
        
        **3️⃣ После оплаты** — загрузите файл снова (Premium уже активен)
        
        **4️⃣ Получите анализ** 📊
        """)
