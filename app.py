from flask import Flask, request, jsonify, render_template, send_file
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from selenium.webdriver.chrome.service import Service
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import os

app = Flask(__name__)

driver_path = '/opt/homebrew/bin/chromedriver'
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--incognito")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# 検索順位を確認する関数
def check_rank(keyword, article_id):
    target_url = f"https://digmee.jp/article/{article_id}"
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

    return {'keyword': keyword, 'rank': l_value, 'article_id': article_id}

# フォームを表示するエンドポイント
@app.route('/')
def index():
    return '''
        <form action="/check_rank" method="post">
            キーワード: <input type="text" name="keyword"><br>
            記事ID: <input type="text" name="article_id"><br>
            <input type="submit" value="検索">
        </form>
    '''

# 順位を確認して結果をCSVとして返すエンドポイント
@app.route('/check_rank', methods=['POST'])
def check_rank_route():
    keyword = request.form['keyword']
    article_id = request.form['article_id']

    # 順位を計測
    result = check_rank(keyword, article_id)

    # 結果をCSVに書き込む
    csv_file = 'rank_result.csv'
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['キーワード', '順位', '記事ID'])
        writer.writerow([result['keyword'], result['rank'], result['article_id']])

    # CSVファイルをダウンロードとして返す
    return send_file(csv_file, mimetype='text/csv', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)