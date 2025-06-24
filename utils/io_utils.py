import os.path
from googleapiclient.discovery import build
from google.oauth2 import service_account

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'credentials.json'  # Or your service account file

def get_sheets_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    return service

def write_to_sheet(service, spreadsheet_id, sheet_name, values):
    body = {
        'values': values
    }
    range_name = f"{sheet_name}!A1"
    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id, range=range_name,
        valueInputOption="RAW", body=body).execute()
    
def clear_sheet(service, spreadsheet_id, sheet_name):
    # Get the sheet ID from the sheet name
    spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_id = None
    for s in spreadsheet['sheets']:
        if s['properties']['title'] == sheet_name:
            sheet_id = s['properties']['sheetId']
            break
    if sheet_id is None:
        raise ValueError(f"Sheet '{sheet_name}' not found.")

    # Clear values
    service.spreadsheets().values().clear(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}"
    ).execute()

    # Clear formatting and filters
    requests_body = [
        {"updateCells": {
            "range": {"sheetId": sheet_id},
            "fields": "userEnteredFormat"
        }},
        {"clearBasicFilter": {"sheetId": sheet_id}}
    ]
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests_body}
    ).execute()
