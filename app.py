from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from google.oauth2 import service_account
from googleapiclient.discovery import build
import time
from selenium.webdriver.chrome.service import Service
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

SERVICE_ACCOUNT_FILE = '/Users/kobayashitsubasa/Downloads/auto-ranking-afa8cab936ec.json'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
sheet_service = build('sheets', 'v4', credentials=creds)

SPREADSHEET_ID = '105tByjbR3uxrHkS0vUDNTDlqB8BguVs6fQPkX95keLc'
RANGE_NAME = '企画!C3:H'

driver_path = '/opt/homebrew/bin/chromedriver'
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--incognito")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

def check_rank(row, i):
    keyword = row[0].strip()
    target_url = row[5].strip()
    driver = webdriver.Chrome(service=Service(driver_path), options=options)

    try:
        driver.get('https://www.google.com')
        search_box = driver.find_element(By.NAME, 'q')
        search_box.send_keys(keyword)
        search_box.send_keys(Keys.RETURN)
        time.sleep(10)
        results = driver.find_elements(By.CSS_SELECTOR, 'div.g')
        rank = next((index + 1 for index, result in enumerate(results[:15])
                    if target_url in result.find_element(By.TAG_NAME, 'a').get_attribute('href')), '圏外')
    except Exception as e:
        rank = 'エラー'
        print(f"Error processing {keyword}: {e}")
    finally:
        driver.quit()

    k_value = rank
    if isinstance(k_value, int):
        if k_value <= 4:
            l_value = k_value
        elif k_value == 5:
            l_value = 1
        elif k_value == 6:
            l_value = 2
        elif k_value == 7:
            l_value = 3
        else:
            l_value = k_value - 4
    else:
        l_value = '圏外'

    return [
        {'range': f'企画!K{i}', 'values': [[str(k_value)]]},
        {'range': f'企画!L{i}', 'values': [[str(l_value)]]}
    ]

def update_sheet(updates):
    body = {'valueInputOption': 'RAW', 'data': updates}
    try:
        sheet_service.spreadsheets().values().batchUpdate(
            spreadsheetId=SPREADSHEET_ID, body=body).execute()
    except Exception as e:
        print(f"Failed to update sheet: {e}")

@app.route('/check_rank', methods=['POST'])
def check_rank_route():
    data = request.json
    rows = data.get('rows', [])
    updates = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_row = {executor.submit(check_rank, row, i): row for i, row in enumerate(rows, start=3) if len(row) >= 6}
        for future in as_completed(future_to_row):
            updates.extend(future.result())
            if len(updates) >= 6:
                update_sheet(updates)
                updates = []
    if updates:
        update_sheet(updates)

    return jsonify({'status': 'success'})

if __name__ == '__main__':
    app.run(debug=True)
