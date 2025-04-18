import datetime

def get_name_day_of_week(number_day):
    if(number_day == 1): return "Понедельник"
    if(number_day == 2): return "Вторник"
    if(number_day == 3): return "Среда"
    if(number_day == 4): return "Четверг"
    if(number_day == 5): return "Пятница"
    if(number_day == 6): return "Суббота"
    if(number_day == 7): return "Воскресенье"

def get_day_of_week(date):
    arr = date.split(".")
    
    day, mounth, year = int(arr[0]), int(arr[1]), int(datetime.date.today().year)
    train_day_name = get_name_day_of_week(datetime.date(year, mounth, day).isoweekday())
    print(train_day_name)
    return train_day_name
