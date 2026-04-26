import streamlit as st
import pandas as pd
from yookassa import Configuration, Payment
import uuid
import os
from dotenv import load_dotenv

# ========== ЗАГРУЗКА ПЕРЕМЕННЫХ ИЗ .env ==========
load_dotenv()

SHOP_ID = os.getenv("SHOP_ID")
SECRET_KEY = os.getenv("SECRET_KEY")

# Проверка, что ключи загрузились
if not SHOP_ID or not SECRET_KEY:
    st.error("⚠️ Ошибка: Не найдены ключи ЮKassa. Проверьте файл .env")
    st.info("Создайте файл .env в корне проекта с содержимым:\nSHOP_ID=ваш_id\nSECRET_KEY=ваш_ключ")
    st.stop()

# Настройка ЮKassa
Configuration.account_id = SHOP_ID
Configuration.secret_key = SECRET_KEY

# ========== НАСТРОЙКИ ==========
MAX_FREE_ROWS = 50000
MAX_FREE_SIZE_MB = 10
PRICE_RUB = 1000  # Цена подписки в рублях

# ========== ОБРАБОТКА ВОЗВРАТА ПОСЛЕ ОПЛАТЫ ==========
# Получаем параметры из адресной строки
query_params = st.query_params

# Если в адресе есть параметр success, значит, пользователь вернулся после оплаты
if query_params.get("success") == "true":
    st.set_page_config(page_title="Оплата успешна", layout="centered")
    st.title("🎉 Оплата прошла успешно!")
    st.balloons()  # Эффект для радости
    
    st.markdown("""
    ### ✅ Ваш Premium-доступ активирован!
    
    Теперь вы можете:
    - 📁 Загружать файлы любого размера
    - 🔄 Обрабатывать неограниченное количество строк
    - 💾 Экспортировать результаты в любых форматах
    
    **Спасибо, что пользуетесь нашим сервисом!**
    """)
    
    # Активируем Premium в сессии
    st.session_state.premium = True
    
    # Кнопка для перехода к анализу
    if st.button("🚀 Перейти к анализу CSV"):
        st.query_params.clear()  # Очищаем параметры
        st.rerun()
    
    st.stop()  # Останавливаем дальнейшее выполнение

# ========== ОСНОВНОЙ ИНТЕРФЕЙС ==========
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
        st.balloons()
    
    # Отладочная информация (только для разработчика)
    with st.expander("🔧 Отладка (только для разработчика)"):
        st.write(f"Shop ID: {SHOP_ID[:4]}...{SHOP_ID[-4:] if len(SHOP_ID) > 8 else ''}")
        st.write(f"Secret Key: {SECRET_KEY[:8]}...")

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
                st.subheader("💳 Оплатить Premium")
                st.caption("Тестовый режим: используйте карту 5555 5555 5555 4477, любой срок и CVC")
                
                if st.button("🚀 Получить Premium за 1000 ₽", type="primary"):
                    try:
                        # Создаём платёж
                        payment = Payment.create({
                            "amount": {"value": str(PRICE_RUB), "currency": "RUB"},
                            "payment_method_data": {"type": "bank_card"},
                            "confirmation": {
                                "type": "redirect",
                                "return_url": "https://csv-analyzer-ru.onrender.com/?success=true"
                            },
                            "description": f"Premium подписка CSV Analyzer - {uuid.uuid4()}"
                        })
                        
                        # Показываем ссылку на оплату
                        st.success("✅ Платёж создан! Нажмите на ссылку ниже:")
                        st.markdown(f"[Оплатить картой]({payment.confirmation.confirmation_url})")
                        st.info("💳 **Тестовые карты:** 5555 5555 5555 4477 (любые срок/CVC) или 2200 0000 0000 0001")
                        
                        # Сохраняем ID платежа в сессию для проверки статуса
                        st.session_state.payment_id = payment.id
                        
                    except Exception as e:
                        st.error(f"❌ Ошибка при создании платежа: {e}")
                        st.info("Проверьте подключение к интернету и правильность ключей в .env")
                
                st.stop()  # Останавливаем выполнение, пока не оплатят
        
        # Анализ данных (если лимит не превышен или Premium активен)
        st.success(f"✅ Загружено: {row_count:,} строк, {file_size_mb:.1f} МБ")
        
        # Основная информация
        st.subheader("📊 Предпросмотр (первые 100 строк)")
        st.dataframe(df.head(100))
        
        # Статистика
        st.subheader("📈 Статистика")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Всего строк", f"{row_count:,}")
        col2.metric("Столбцов", len(df.columns))
        col3.metric("Пустых ячеек", df.isnull().sum().sum())
        col4.metric("Типов данных", len(df.dtypes.unique()))
        
        # Типы данных по столбцам
        with st.expander("📋 Типы данных по столбцам"):
            dtype_df = pd.DataFrame({
                "Столбец": df.columns,
                "Тип данных": [str(dtype) for dtype in df.dtypes.values],
                "Уникальных значений": [df[col].nunique() for col in df.columns],
                "Пустых значений": [df[col].isnull().sum() for col in df.columns]
            })
            st.dataframe(dtype_df)
        
        # Экспорт результата
        st.subheader("💾 Экспорт")
        csv_export = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 Скачать CSV",
            data=csv_export,
            file_name="analyzed_data.csv",
            mime="text/csv"
        )
        
    except Exception as e:
        st.error(f"❌ Ошибка при обработке файла: {e}")
        st.info("Убедитесь, что файл имеет правильный формат CSV (разделитель - запятая)")
else:
    st.info("👈 Загрузите CSV файл, чтобы начать анализ")
    
    # Примеры использования
    with st.expander("📖 Примеры использования"):
        st.markdown("""
        **Кому пригодится:**
        - 📊 **Маркетологи** — анализ данных о клиентах
        - 📈 **Аналитики** — быстрая очистка и разведка данных
        - 💻 **Разработчики** — проверка экспортов из БД
        - 🎓 **Студенты** — обработка больших датасетов для курсовых
        
        **Примеры CSV файлов для теста:**
        - Данные о продажах (дата, товар, количество, сумма)
        - Клиентская база (имя, телефон, email, город)
        - Логи сервера (время, IP, запрос, статус)
        """)

# ========== ПРОВЕРКА СТАТУСА ПЛАТЕЖА (простая версия) ==========
if 'payment_id' in st.session_state and not st.session_state.premium:
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔄 Проверить оплату")
    if st.sidebar.button("Проверить статус платежа"):
        try:
            payment = Payment.find_one(st.session_state.payment_id)
            if payment.status == "succeeded":
                st.session_state.premium = True
                st.sidebar.success("✅ Оплата подтверждена! Premium активирован")
                st.rerun()
            else:
                st.sidebar.info(f"Статус платежа: {payment.status}")
        except Exception as e:
            st.sidebar.error(f"Ошибка проверки: {e}")
