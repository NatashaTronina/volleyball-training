import datetime

def get_name_day_of_week(number_day):
    days = {
        1: "Понедельник",
        2: "Вторник",
        3: "Среда",
        4: "Четверг",
        5: "Пятница",
        6: "Суббота",
        7: "Воскресенье"
    }
    return days.get(number_day, "Некорректный день")

def get_day_of_week(date):
    arr = date.split(".")
    
    try:
        day, month = int(arr[0]), int(arr[1])
        year = datetime.date.today().year  # Используем текущий год

        # Проверка на корректность месяца
        if month < 1 or month > 12:
            return 'Некорректная дата. Месяц должен быть от 1 до 12.'

        # Проверка на количество дней в месяце
        if month == 2:
            if day < 1 or day > 29:
                return 'Некорректная дата. Февраль может иметь максимум 29 дней.'
            if day == 29 and not (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
                return 'Некорректная дата. Февраль имеет 28 дней в невисокосный год.'
        elif month in [4, 6, 9, 11] and (day < 1 or day > 30):
            return 'Некорректная дата. Месяцы с 30 днями: апрель, июнь, сентябрь, ноябрь.'
        elif month in [1, 3, 5, 7, 8, 10, 12] and (day < 1 or day > 31):
            return 'Некорректная дата. Месяцы с 31 днем: январь, март, май, июль, август, октябрь, декабрь.'

        # Если дата корректна, получаем название дня недели
        train_day_name = get_name_day_of_week(datetime.date(year, month, day).isoweekday())
        return train_day_name

    except (ValueError, IndexError):
        return 'Некорректный формат даты. Пожалуйста, введите дату в формате ДД.ММ.'
