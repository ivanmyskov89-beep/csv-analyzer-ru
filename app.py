import streamlit as st
import pandas as pd
from yookassa import Configuration, Payment
import uuid
import os
import io
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

# ========== ИНИЦИАЛИЗАЦИЯ ==========
if 'premium' not in st.session_state:
    st.session_state.premium = False
if 'temp_premium' not in st.session_state:
    st.session_state.temp_premium = False
if 'df' not in st.session_state:
    st.session_state.df = None
if 'filename' not in st.session_state:
    st.session_state.filename = None

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
st.title("🚀 CSV Анализатор")
st.markdown("### Мгновенный анализ больших CSV-файлов")

with st.sidebar:
    st.header("💎 Тарифы")
    st.markdown("**Бесплатно** — до 50 000 строк")
    st.markdown("**🎫 Разовый доступ** — 200 ₽ (24 часа)")
    st.markdown("**👑 Premium** — 1000 ₽ (30 дней)")
    if is_premium_active():
        st.success("⭐ Premium активен")

# ========== ЗАГРУЗКА ФАЙЛА ==========
uploaded_file = st.file_uploader("📂 Выберите CSV файл", type="csv")

if uploaded_file is not None:
    # Загружаем файл ТОЛЬКО если изменился
    if st.session_state.df is None or st.session_state.filename != uploaded_file.name:
        with st.spinner("🔄 Чтение файла..."):
            st.session_state.df = pd.read_csv(uploaded_file)
            st.session_state.filename = uploaded_file.name

# ========== АНАЛИЗ (ЕСЛИ ФАЙЛ ЗАГРУЖЕН) ==========
if st.session_state.df is not None:
    df = st.session_state.df
    rows = len(df)
    
    # ОТЛАДКА: показываем количество строк всегда
    st.caption(f"📊 Отладка: в файле {rows:,} строк. Лимит: {MAX_FREE_ROWS:,}. Premium активен: {is_premium_active()}")
    
    # ========== ПРОВЕРКА ЛИМИТА И ОТОБРАЖЕНИЕ КНОПОК ==========
    if not is_premium_active() and rows > MAX_FREE_ROWS:
        st.warning(f"⚠️ Ваш файл содержит **{rows:,} строк** (бесплатно до {MAX_FREE_ROWS:,})")
        
        st.markdown("## 💳 Выберите способ оплаты:")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🎫 Разовый доступ (200 ₽)", use_container_width=True):
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
            if st.button("👑 Premium на месяц (1000 ₽)", use_container_width=True):
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
        st.stop()  # Останавливаем здесь, не показываем анализ
    
    # ========== АНАЛИЗ (ПРЕМИУМ ИЛИ БЕСПЛАТНЫЙ ФАЙЛ) ==========
    st.success(f"✅ Файл **{st.session_state.filename}** загружен: **{rows:,} строк**")
    
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
            file_name=f"{st.session_state.filename.replace('.csv', '')}_analyzed.csv",
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
                file_name=f"{st.session_state.filename.replace('.csv', '')}_analyzed.xlsx",
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
            file_name=f"{st.session_state.filename.replace('.csv', '')}_analyzed.json",
            mime="application/json",
            use_container_width=True
        )
    
    # Сброс
    st.markdown("---")
    if st.button("🗑️ Загрузить другой файл", use_container_width=True):
        st.session_state.df = None
        st.session_state.filename = None
        st.session_state.premium = False
        st.session_state.temp_premium = False
        st.rerun()
else:
    st.info("👈 Загрузите CSV файл для анализа")
