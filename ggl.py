import gspread
from google.oauth2.service_account import Credentials
import datetime
import re
from collections import defaultdict
import time
import numpy as np

cache = defaultdict(dict)

def authenticate_google_sheets(json_file, max_retries=3, retry_delay=2):
    """Аутентификация и получение клиента для работы с Google Sheets с повторными попытками."""
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive'
    ]
    for attempt in range(max_retries):
        try:
            creds = Credentials.from_service_account_file(json_file, scopes=scopes)
            client = gspread.authorize(creds)
            return client
        except Exception as e:
            print(f"authenticate_google_sheets: Ошибка аутентификации (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
    print("authenticate_google_sheets: Не удалось подключиться после нескольких попыток.")
    return None

def normalize_name(full_name):
    normalized = full_name.strip()
    parts = re.findall(r'(\w+\s+\w+)', full_name)
    brackets = re.findall(r'\((.*?)\)', full_name)
    for bracket in brackets:
        parts.append(bracket.strip())
    return normalized, parts

def write_name_to_google_sheet(client, spreadsheet_name, full_name, user_id, max_retries=3, retry_delay=2):
    if client is None:
        print("write_name_to_google_sheet: Не удалось подключиться к Google Sheets.")
        return

    normalized_name, name_parts = normalize_name(full_name)
    sheets_to_check = ["В.Расход", "В.Приход"]

    for sheet_name in sheets_to_check:
        for attempt in range(max_retries):
            try:
                worksheet = client.open(spreadsheet_name).worksheet(sheet_name)
                start_time = time.time()
                column_data = worksheet.col_values(1)
                end_time = time.time()
                print(f"write_name_to_google_sheet: Данные получены за {end_time - start_time:.4f} секунд (попытка {attempt + 1}/{max_retries})")

                name_found = False
                input_name_parts = normalized_name.split()
                input_first_name = input_name_parts[0]

                for i, table_name in enumerate(column_data):
                    table_name_without_brackets = re.sub(r'\s*\(.*?\)\s*', '', table_name).strip()
                    table_name_parts = table_name_without_brackets.split()

                    if len(table_name_parts) >= 1:
                        table_first_name = table_name_parts[0]

                        if input_first_name in table_first_name:
                            row_index = i + 1
                            worksheet.update_cell(row_index, 2, str(user_id))
                            name_found = True
                            break

                if not name_found:
                    for part in name_parts:
                        for i, table_name in enumerate(column_data):
                             if part in table_name:
                                row_index = i + 1
                                worksheet.update_cell(row_index, 2, str(user_id))
                                name_found = True
                                break
                        if name_found:
                            break
                if name_found:
                    break
                else:
                    print(f"write_name_to_google_sheet: Имя не найдено в {sheet_name} (попытка {attempt + 1}/{max_retries})")

            except Exception as e:
                print(f"write_name_to_google_sheet: Ошибка при записи в {sheet_name} (попытка {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)  
                    client = authenticate_google_sheets('vocal-circle-461812-m7-06081970720e.json', max_retries, retry_delay)
                    if client is None:
                       print("write_name_to_google_sheet: Не удалось восстановить подключение.")
                       return
                else:
                    print("write_name_to_google_sheet: Не удалось записать после нескольких попыток.")
                    return

        if name_found:
           break

def record_payment(client, spreadsheet_name, user_id, total_price, max_retries=3, retry_delay=2):
    if client is None:
        print("record_payment: Не удалось подключиться к Google Sheets.")
        return

    def remove_leading_zeros(date_string):
        parts = date_string.split('.')
        if len(parts) == 3:
            day = str(int(parts[0]))
            month = str(int(parts[1]))
            year = parts[2]
            return f"{day}.{month}.{year}"
        return date_string

    for attempt in range(max_retries):
        try:
            sheet = client.open(spreadsheet_name)
            worksheet = sheet.worksheet("В.Приход")

            start_time = time.time()
            dates = worksheet.row_values(2)
            user_ids = worksheet.col_values(2)

            end_time = time.time()
            print(f"record_payment: Данные получены за {end_time - start_time:.4f} секунд (попытка {attempt + 1}/{max_retries})")

            current_date = datetime.datetime.now().strftime("%d.%m.%y")
            current_date_no_zeros = remove_leading_zeros(current_date)

            if str(user_id) in user_ids:
                row_index = user_ids.index(str(user_id)) + 1

                dates_no_zeros = [remove_leading_zeros(date) for date in dates]

                date_column_index = None
                for i, date in enumerate(dates_no_zeros):
                    if date == current_date_no_zeros:
                        date_column_index = i + 1
                        break

                if date_column_index:
                    existing_amount_cell = worksheet.cell(row_index, date_column_index)
                    existing_amount = existing_amount_cell.value
                    if existing_amount:
                        try:
                            total_price = float(total_price) + float(existing_amount)
                        except ValueError:
                            total_price = float(total_price)
                    worksheet.update_cell(row_index, date_column_index, total_price)

                else:
                    last_filled_column = len(dates)
                    next_column_index = last_filled_column + 1
                    worksheet.update_cell(2, next_column_index, current_date_no_zeros)
                    worksheet.update_cell(row_index, next_column_index, total_price)

            else:
                last_filled_column = len(dates)
                next_column_index = last_filled_column + 1
                worksheet.update_cell(2, next_column_index, current_date_no_zeros)
                worksheet.update_cell(row_index, next_column_index, total_price)
            break 

        except Exception as e:
            print(f"record_payment: Ошибка при записи платежа (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                client = authenticate_google_sheets('vocal-circle-461812-m7-06081970720e.json', max_retries, retry_delay)
                if client is None:
                   print("record_payment: Не удалось восстановить подключение.")
                   return
            else:
                print("record_payment: Не удалось записать платеж после нескольких попыток.")
                return

def record_training_details(client, spreadsheet_name, training_date, training_price, max_retries=3, retry_delay=2):
    if client is None:
        print("record_training_details: Не удалось подключиться к Google Sheets.")
        return

    for attempt in range(max_retries):
        try:
            sheet = client.open(spreadsheet_name)
            worksheet = sheet.worksheet("В.Расход")

            start_time = time.time()
            dates_row = worksheet.row_values(4)

            end_time = time.time()
            print(f"record_training_details: Данные получены за {end_time - start_time:.4f} секунд (попытка {attempt + 1}/{max_retries})")

            next_col_index = len(dates_row) + 1

            worksheet.update_cell(4, next_col_index, training_date)
            worksheet.update_cell(3, next_col_index, str(training_price))
            break  

        except Exception as e:
            print(f"record_training_details: Ошибка при записи данных о тренировке (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                client = authenticate_google_sheets('vocal-circle-461812-m7-06081970720e.json', max_retries, retry_delay)
                if client is None:
                    print("record_training_details: Не удалось восстановить подключение.")
                    return
            else:
                print("record_training_details: Не удалось записать данные о тренировке после нескольких попыток.")
                return

def delete_training_details(client, spreadsheet_name, training_date, training_price, max_retries=3, retry_delay=2):
    if client is None:
        print("delete_training_details: Не удалось подключиться к Google Sheets.")
        return

    for attempt in range(max_retries):
        try:
            sheet = client.open(spreadsheet_name)
            worksheet = sheet.worksheet("В.Расход")

            header_row = worksheet.row_values(4)
            price_row = worksheet.row_values(3)

            col_index = None
            for i in reversed(range(len(header_row))):
                header = header_row[i]
                price = price_row[i] if i < len(price_row) else ""  

                if header == training_date and str(price) == str(training_price):
                    col_index = i + 1
                    break

            if col_index is None:
                return

            cell_list = worksheet.range(1, col_index, worksheet.row_count, col_index)
            for cell in cell_list:
                cell.value = ""
            worksheet.update_cells(cell_list)
            break  

        except Exception as e:
            print(f"delete_training_details: Ошибка при удалении данных о тренировке (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                client = authenticate_google_sheets('vocal-circle-461812-m7-06081970720e.json', max_retries, retry_delay)
                if client is None:
                    print("delete_training_details: Не удалось восстановить подключение.")
                    return
            else:
                print("delete_training_details: Не удалось удалить данные о тренировке после нескольких попыток.")
                return

def update_training_status(client, spreadsheet_name, user_id, training_info, status, max_retries=3, retry_delay=2):
    if client is None:
        print("update_training_status: Не удалось подключиться к Google Sheets.")
        return

    for attempt in range(max_retries):
        try:
            sheet = client.open(spreadsheet_name)
            worksheet = sheet.worksheet("В.Расход")

            start_time = time.time()

            user_ids = worksheet.col_values(2)
            header_row = worksheet.row_values(4)
            price_row = worksheet.row_values(3)

            end_time = time.time()
            print(f"update_training_status: Данные получены за {end_time - start_time:.4f} секунд (попытка {attempt + 1}/{max_retries})")

            if str(user_id) in user_ids:
                row_index = user_ids.index(str(user_id)) + 1

                training_date = training_info['date']
                training_price = str(training_info['price'])

                col_index = None
                for i in reversed(range(len(header_row))):
                    header = header_row[i]
                    if header == training_date:
                        if i < len(price_row) and str(price_row[i]) == training_price:
                            col_index = i + 1
                            break

                if col_index is None:
                    return

                if col_index:
                    current_value = worksheet.cell(row_index, col_index).value
                    if current_value != "#":
                        worksheet.update_cell(row_index, col_index, status)
            break  

        except Exception as e:
            print(f"update_training_status: Ошибка при обновлении статуса тренировки (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                client = authenticate_google_sheets('vocal-circle-461812-m7-06081970720e.json', max_retries, retry_delay)
                if client is None:
                    print("update_training_status: Не удалось восстановить подключение.")
                    return
            else:
                print("update_training_status: Не удалось обновить статус тренировки после нескольких попыток.")
                return

def get_participants_for_training(client, spreadsheet_name, training_date, training_price, max_retries=3, retry_delay=2):
    if client is None:
        print("get_participants_for_training: Не удалось подключиться к Google Sheets.")
        return []

    cache_key = f"{training_date}_{training_price}"

    cached_data = cache.get(cache_key)
    if cached_data and 'timestamp' in cached_data and \
            datetime.datetime.now() - cached_data['timestamp'] < datetime.timedelta(minutes=1):
        return cached_data['participants']

    for attempt in range(max_retries):
        try:
            sheet = client.open(spreadsheet_name)
            worksheet = sheet.worksheet("В.Расход")

            start_time = time.time()
            data = worksheet.get_all_values()
            data_array = np.array(data)

            header_row = data_array[3, :]
            price_row = data_array[2, :]
            names_col = data_array[4:, 0]
            status_col = data_array[4:, :]

            end_time = time.time()
            print(f"get_participants_for_training: Данные получены за {end_time - start_time:.4f} секунд (попытка {attempt + 1}/{max_retries})")

            date_col_index = -1
            for i in reversed(range(len(header_row))):
                if header_row[i] == training_date and str(price_row[i]) == training_price:
                    date_col_index = i
                    break

            if date_col_index == -1:
                return []

            participants = []
            for i, name in enumerate(names_col):
                if i < status_col.shape[0]:
                    status = status_col[i, date_col_index]
                    if status in ("*", "1", "0"):
                        participants.append({"name": name, "status": status})
                    elif status == "#":
                        participants.append({"name": f"{name} (Вернуть оплату)", "status": status})

            cache[cache_key] = {'participants': participants, 'timestamp': datetime.datetime.now()}
            return participants
            break  

        except Exception as e:
            print(f"get_participants_for_training: Ошибка при получении участников тренировки (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                client = authenticate_google_sheets('vocal-circle-461812-m7-06081970720e.json', max_retries, retry_delay)
                if client is None:
                    print("get_participants_for_training: Не удалось восстановить подключение.")
                    return []
            else:
                print("get_participants_for_training: Не удалось получить участников после нескольких попыток.")
                return []


def cancel_training_for_user(client, spreadsheet_name, training_date, training_price, user, new_status, max_retries=3, retry_delay=2):
    if client is None:
        print("cancel_training_for_user: Не удалось подключиться к Google Sheets.")
        return

    for attempt in range(max_retries):
        try:
            sheet = client.open(spreadsheet_name)
            worksheet = sheet.worksheet("В.Расход")

            start_time = time.time()

            names_col = worksheet.col_values(1)
            header_row = worksheet.row_values(4)
            price_row = worksheet.row_values(3)

            end_time = time.time()
            print(f"cancel_training_for_user: Данные получены за {end_time - start_time:.4f} секунд (попытка {attempt + 1}/{max_retries})")

            user_name = user['name']

            if " (Вернуть оплату)" in user_name:
                user_name_to_search = user_name.replace(" (Вернуть оплату)", "").strip()
            else:
                user_name_to_search = user_name

            row_index = None
            for i, name in enumerate(names_col):
                if name == user_name_to_search:
                    row_index = i + 1
                    break

            if row_index is None:
                return

            col_index = None
            for i in reversed(range(len(header_row))):
                header = header_row[i]
                if header == training_date:
                    if i < len(price_row) and str(price_row[i]) == training_price:
                        col_index = i + 1
                        break

            if col_index is None:
                return

            try:
                worksheet.update_cell(row_index, col_index, new_status)
                break  
            except Exception as e:
                print(f"cancel_training_for_user: Ошибка при обновлении ячейки (попытка {attempt + 1}/{max_retries}): {e}")
                break

        except Exception as e:
            print(f"cancel_training_for_user: Ошибка при отмене тренировки для пользователя (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                client = authenticate_google_sheets('vocal-circle-461812-m7-06081970720e.json', max_retries, retry_delay)
                if client is None:
                    print("cancel_training_for_user: Не удалось восстановить подключение.")
                    return
            else:
                print("cancel_training_for_user: Не удалось отменить тренировку для пользователя после нескольких попыток.")
                return
