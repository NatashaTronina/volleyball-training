import gspread
from google.oauth2.service_account import Credentials
import datetime
import re
import threading
from collections import defaultdict

# Кэш для хранения данных
cache = defaultdict(dict)


def authenticate_google_sheets(json_file):
    """Аутентификация и получение клиента для работы с Google Sheets."""
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive'
    ]
    creds = Credentials.from_service_account_file(json_file, scopes=scopes)
    client = gspread.authorize(creds)
    return client

def normalize_name(full_name):
    """Нормализует имя, возвращая нормализованное имя и все возможные варианты имен, включая те, что в скобках."""
    # Нормализуем имя, удаляя лишние пробелы
    normalized = full_name.strip()
    # Извлекаем все возможные варианты имен, включая те, что в скобках
    parts = re.findall(r'(\w+\s+\w+)', full_name)  # Находим все пары слов
    # Добавляем имена из скобок
    brackets = re.findall(r'\((.*?)\)', full_name)
    for bracket in brackets:
        parts.append(bracket.strip())
    return normalized, parts  # Возвращаем нормализованное имя и все части

def write_name_to_google_sheet(client, spreadsheet_name, full_name, user_id):
    if client is None:
        return

    sheet = client.open(spreadsheet_name)
    sheets_to_check = ["В.Расход", "В.Приход"]  # Листы для проверки

    normalized_name, name_parts = normalize_name(full_name)  # Нормализуем имя перед поиском

    for sheet_name in sheets_to_check:
        worksheet = sheet.worksheet(sheet_name)
        column_data = worksheet.col_values(1)  # Получаем данные из столбца A

        print(f"Проверяем в листе '{sheet_name}':")  # Отладочная информация

        found = False
        input_name_parts = normalized_name.split()
        input_first_name = input_name_parts[0]

        for i, table_name in enumerate(column_data):
            # Удаляем скобки из имени в таблице
            table_name_without_brackets = re.sub(r'\s*\(.*?\)\s*', '', table_name).strip()
            table_name_parts = table_name_without_brackets.split()

            # Получаем фамилию из имени в таблице
            if len(table_name_parts) >= 1:
                table_first_name = table_name_parts[0] # First Name

                # Проверяем имя пользователя и первое имя в таблице
                if input_first_name in table_first_name:
                    row_index = i + 1
                    worksheet.update_cell(row_index, 2, str(user_id))
                    print(f"Записан user_id '{user_id}' для '{table_name}' в строке {row_index}.")
                    found = True
                    break
        if not found: # Если имя не найдено, то проверяем остальные части
            for part in name_parts:
                for i, table_name in enumerate(column_data):
                     if part in table_name:
                        row_index = i + 1
                        worksheet.update_cell(row_index, 2, str(user_id))
                        print(f"Записан user_id '{user_id}' для '{table_name}' в строке {row_index}.")
                        found = True
                        break  # Если нашли соответствие, выходим из внутреннего цикла
                if found:
                    break

        if not found:
            print(f"ФИО '{full_name}' не найдено в листе '{sheet_name}'.")
def record_payment(client, spreadsheet_name, user_id, total_price):
    """Запись даты и суммы оплаты в лист 'В.Приход'."""
    if client is None:
        print("Ошибка: клиент Google Sheets не инициализирован.")
        return

    def remove_leading_zeros(date_string):
        """Удаляет ведущие нули из дня и месяца в дате."""
        parts = date_string.split('.')
        if len(parts) == 3:
            day = str(int(parts[0]))
            month = str(int(parts[1]))
            year = parts[2]
            return f"{day}.{month}.{year}"
        return date_string

    try:
        sheet = client.open(spreadsheet_name)
        worksheet = sheet.worksheet("В.Приход")

        # Получаем текущую дату в формате ДД.ММ.ГГ
        current_date = datetime.datetime.now().strftime("%d.%m.%y")
        current_date_no_zeros = remove_leading_zeros(current_date) # remove_leading_zeros

        # Находим строку с user_id
        user_ids = worksheet.col_values(2)  # Предполагаем, что user_id находится во втором столбце
        if str(user_id) in user_ids:
            row_index = user_ids.index(str(user_id)) + 1

            # Считываем все значения из второй строки (строки с датами)
            dates = worksheet.row_values(2)


            # Remove leading zeros from the existing dates in the sheet.
            dates_no_zeros = [remove_leading_zeros(date) for date in dates]

            # Находим колонку с текущей датой.
            date_column_index = None
            for i, date in enumerate(dates_no_zeros):
                if date == current_date_no_zeros:
                    date_column_index = i + 1
                    break

            if date_column_index:
                # Дата уже существует, суммируем сумму
                existing_amount_cell = worksheet.cell(row_index, date_column_index)
                existing_amount = existing_amount_cell.value
                if existing_amount:
                    try:
                        total_price = float(total_price) + float(existing_amount)
                    except ValueError:
                        print(f"Ошибка: Не удалось преобразовать существующую сумму '{existing_amount}' в число.")
                        total_price = float(total_price) # Use new total amount!
                worksheet.update_cell(row_index, date_column_index, total_price)

            else:
                # Дата не существует, создаем новую колонку
                last_filled_column = len(dates)
                next_column_index = last_filled_column + 1

                # Записываем дату в следующую свободную ячейку строки 2
                worksheet.update_cell(2, next_column_index, current_date_no_zeros) # Write no zeros
                # Записываем сумму в соответствующую ячейку в строке с user_id
                worksheet.update_cell(row_index, next_column_index, total_price)
                print(f"Сумма {total_price} записана в строку {row_index}, столбец {next_column_index} (создана новая дата).")
        else:
            print(f"User  ID '{user_id}' не найден в листе 'В.Приход'.")
    except Exception as e:
        print(f"Ошибка при записи платежа: {e}")