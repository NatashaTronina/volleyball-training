import gspread
from google.oauth2.service_account import Credentials

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


def write_name_to_google_sheet(client, spreadsheet_name, full_name, user_id):
    if client is None:
        return

    sheet = client.open(spreadsheet_name)
    sheets_to_check = ["В.Расход", "В.Приход"]  # Листы для проверки

    for sheet_name in sheets_to_check:
        worksheet = sheet.worksheet(sheet_name)
        column_data = worksheet.col_values(1)  # Получаем данные из столбца A

        if full_name in column_data:
            row_index = column_data.index(full_name) + 1  # Индекс строки (плюс 1, так как индексация начинается с 0)
            print(f"Найдено имя '{full_name}' в листе '{sheet_name}' в строке {row_index}")
            worksheet.update_cell(row_index, 2, str(user_id))  # Запись user_id в столбец B
        else:
            print(f"ФИО '{full_name}' не найдено в листе '{sheet_name}'.")

