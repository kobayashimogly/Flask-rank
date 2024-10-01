from flask import Flask, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from selenium.webdriver.chrome.service import Service
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

driver_path = '/opt/homebrew/bin/chromedriver'
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--incognito")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# 検索順位を確認する関数
def check_rank(row, i):
    keyword = row[0].strip()
    target_url = f"https://digmee.jp/article/{row[1].strip()}"
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

    # l_valueの計算（順位の出力）
    if isinstance(rank, int):
        if rank <= 4:
            l_value = rank
        elif rank == 5:
            l_value = 1
        elif rank == 6:
            l_value = 2
        elif rank == 7:
            l_value = 3
        else:
            l_value = rank - 4
    else:
        l_value = '圏外'

    return {'keyword': keyword, 'rank': l_value}

# 順位を確認して結果を返すエンドポイント
@app.route('/check_rank', methods=['POST'])
def check_rank_route():
    data = request.json
    rows = data.get('rows', [])
    results = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_row = {executor.submit(check_rank, row, i): row for i, row in enumerate(rows, start=3)}
        for future in as_completed(future_to_row):
            results.append(future.result())

    return jsonify({'status': 'success', 'results': results})

if __name__ == '__main__':
    app.run(debug=True)
