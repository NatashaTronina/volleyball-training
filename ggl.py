import gspread
from google.oauth2.service_account import Credentials
import time

def authenticate_google_sheets(json_file):
    """Аутентификация и получение клиента для работы с Google Sheets."""
    try:
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_file(json_file, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        print(f"Ошибка при аутентификации в Google Sheets: {e}")
        return None  # Return None to signal failure

def write_name_to_google_sheet(client, spreadsheet_name, full_name, user_id):
    """Ищет в двух листах таблицы ФИО full_name и записывает user_id в ячейку справа от найденного имени."""
    print(f"write_name_to_google_sheet: Начало работы, full_name: {full_name}, user_id: {user_id}") # Log 1
    if client is None:
        print("write_name_to_google_sheet: Не удалось подключиться к Google Sheets.")
        return
    try:
        sheet = client.open(spreadsheet_name)
        sheets_to_check = ["В.Расход", "В.Приход"]  # Листы для проверки

        for sheet_name in sheets_to_check:
            print(f"write_name_to_google_sheet: Проверка листа '{sheet_name}'") # Log 3
            try:
                worksheet = sheet.worksheet(sheet_name)
                cell = worksheet.find(full_name)  # Поиск имени
                if cell:
                    print(f"write_name_to_google_sheet: Найдено имя '{full_name}' в листе '{sheet_name}' в строке {cell.row}, столбце {cell.col}") # Log 4
                    try:
                        worksheet.update_cell(cell.row, cell.col + 1, str(user_id))  # Запись user_id
                        print(f"Записан user_id {user_id} для '{full_name}' в листе '{sheet_name}'")
                    except Exception as e:
                        print(f"write_name_to_google_sheet: Не удалось обновить ячейку для '{full_name}' в листе '{sheet_name}': {e}")
            except gspread.exceptions.CellNotFound:
                print(f"write_name_to_google_sheet: ФИО '{full_name}' не найдено в листе '{sheet_name}'.")
                continue  # Переходим к следующему листу

    except gspread.exceptions.SpreadsheetNotFound:
        print(f"Ошибка: Таблица '{spreadsheet_name}' не найдена.")
    except Exception as e:
        print(f"Произошла общая ошибка при работе с Google Sheets: {e}")