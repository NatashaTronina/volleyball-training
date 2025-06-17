import gspread
from google.oauth2.service_account import Credentials
import datetime
import re
from collections import defaultdict
import time

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
    normalized = full_name.strip()
    parts = re.findall(r'(\w+\s+\w+)', full_name)  
    brackets = re.findall(r'\((.*?)\)', full_name)
    for bracket in brackets:
        parts.append(bracket.strip())
    return normalized, parts  

def write_name_to_google_sheet(client, spreadsheet_name, full_name, user_id):
    if client is None:
        return

    sheet = client.open(spreadsheet_name)
    sheets_to_check = ["В.Расход"]

    normalized_name, name_parts = normalize_name(full_name)

    for sheet_name in sheets_to_check:
        worksheet = sheet.worksheet(sheet_name)
        column_data = worksheet.col_values(1) 

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

def record_payment(client, spreadsheet_name, user_id, total_price):
    if client is None:
        return

    def remove_leading_zeros(date_string):
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

        current_date = datetime.datetime.now().strftime("%d.%m.%y")
        current_date_no_zeros = remove_leading_zeros(current_date) 


        user_ids = worksheet.col_values(2) 
        if str(user_id) in user_ids:
            row_index = user_ids.index(str(user_id)) + 1

            dates = worksheet.row_values(2)

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
    except Exception as e:
        print(f"Ошибка при записи платежа: {e}")


def record_training_details(client, spreadsheet_name, training_date, training_price):
    if client is None:
        return

    try:
        sheet = client.open(spreadsheet_name)
        worksheet = sheet.worksheet("В.Расход")

        dates_row = worksheet.row_values(4)

        next_col_index = len(dates_row) + 1 


        worksheet.update_cell(4, next_col_index, training_date)

        worksheet.update_cell(3, next_col_index, str(training_price))

    except Exception as e:
        print(f"Ошибка при записи данных о тренировке: {e}")


def update_training_status(client, spreadsheet_name, user_id, training_info, status):
    if client is None:
        return

    try:
        sheet = client.open(spreadsheet_name)
        worksheet = sheet.worksheet("В.Расход")

        user_ids = worksheet.col_values(2)
        if str(user_id) in user_ids:
            row_index = user_ids.index(str(user_id)) + 1

            training_date = training_info['date']
            training_price = str(training_info['price'])
            header_row = worksheet.row_values(4)
            
            col_index = None

            for i in reversed(range(len(header_row))):
                header = header_row[i]
                if header == training_date:
                    price_row = worksheet.row_values(3)
                    if i < len(price_row) and str(price_row[i]) == training_price:
                        col_index = i + 1
                        break

            if col_index is None:
                return

            if col_index:
                worksheet.update_cell(row_index, col_index, status)
    except Exception as e:
        print(f"Ошибка при обновлении статуса тренировки в OpenAI Sheets: {e}")



def get_participants_for_training(client, spreadsheet_name, training_date, training_price):
    if client is None:
        return []

    cache_key = f"{training_date}_{training_price}"

    cached_data = cache.get(cache_key)
    if cached_data and 'timestamp' in cached_data and \
            datetime.datetime.now() - cached_data['timestamp'] < datetime.timedelta(minutes=1):
        return cached_data['participants']
    else:
        print(f"get_participants_for_training: Кэш не найден или устарел")

    try:
        sheet = client.open(spreadsheet_name)
        worksheet = sheet.worksheet("В.Расход")
        
        all_data = worksheet.get_all_values()[4:]
        header_row = worksheet.row_values(4)
        
        col_index = None
        for i in reversed(range(len(header_row))):
            header = header_row[i]
            if header == training_date:
                price_row = worksheet.row_values(3)
                if i < len(price_row) and str(price_row[i]) == training_price:
                    col_index = i + 1
                    break

        if col_index is None:
            return []

        participants = []
        for i, row in enumerate(all_data):
            if len(row) > col_index - 1:
                status = row[col_index - 1]
                name = row[0]
                if status in ("*", "1", "0"):
                    participants.append({"name": name, "status": status})
            time.sleep(0.1)

        cache[cache_key] = {'participants': participants, 'timestamp': datetime.datetime.now()}
        return participants

    except Exception as e:
        print(f"get_participants_for_training: Произошла ошибка: {e}")
        return []
    
def cancel_training_for_user(client, spreadsheet_name, training_date, training_price, user):
    try:
        sheet = client.open(spreadsheet_name)
        worksheet = sheet.worksheet("В.Расход")
        names_col = worksheet.col_values(1)
        header_row = worksheet.row_values(4)

        user_name = user['name']
        row_index = None
        for i, name in enumerate(names_col):
            if name == user_name:
                row_index = i + 1
                break
        if row_index is None:
            return
        
        col_index = None
        for i in reversed(range(len(header_row))):
            header = header_row[i]
            if header == training_date:
                price_row = worksheet.row_values(3)
                if i < len(price_row) and str(price_row[i]) == training_price:
                    col_index = i + 1
                    break

        if col_index is None:
            return
        
        cell_value = worksheet.cell(row_index, col_index).value
        if cell_value == "1":
            worksheet.update_cell(row_index, col_index, "0")
        elif cell_value == "*":
            worksheet.update_cell(row_index, col_index, "")
 
    except Exception as e:
        print(f"Error during cancelling training for user in Google Sheets: {e}")