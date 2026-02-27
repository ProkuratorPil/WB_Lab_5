# Импортируем нужные модули
from fastapi import FastAPI
from datetime import date

# Создаём экземпляр приложения FastAPI
app = FastAPI()

# Говорим, что по адресу /info (GET-запрос) будет вызываться эта функция
@app.get("/info")
async def get_info():
    # Получаем сегодняшнюю дату
    today = date.today()
    # Создаём дату следующего Нового года (1 января следующего года)
    new_year = date(today.year + 1, 1, 1)
    # Вычисляем разницу в днях
    days_left = (new_year - today).days
    # Возвращаем словарь, который FastAPI автоматически превратит в JSON
    return {"days_before_new_year": days_left}