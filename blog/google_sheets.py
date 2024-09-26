import os
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

def get_google_sheets_data(spreadsheet_id, range_name):
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), 'path/to/your/service-account-file.json')

    credentials = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=credentials)
    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id, range=range_name).execute()
    values = result.get('values', [])

    if not values:
        print('No data found.')
        return pd.DataFrame()

    df = pd.DataFrame(values[1:], columns=values[0])  # Используем первую строку как названия столбцов
    return df
