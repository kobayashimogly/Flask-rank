from flask import Flask, request, jsonify, render_template, send_file
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
from selenium.webdriver.chrome.service import Service
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import os
import logging
from werkzeug.utils import secure_filename

# ロギングの設定
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
RESULT_FOLDER = 'results'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

driver_path = '/opt/homebrew/bin/chromedriver'
options = webdriver.ChromeOptions()
options.add_argument("--headless")
options.add_argument("--incognito")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")

# 検索順位を確認する関数
def check_rank(keyword, article_id):
    logging.info(f"Checking rank for keyword: {keyword}, article_id: {article_id}")
    target_url = f"https://digmee.jp/article/{article_id}"
    
    # ドライバーを起動しようとするところで詳細なログを追加
    try:
        driver = webdriver.Chrome(service=Service(driver_path), options=options)
        logging.info("Webdriver successfully started.")
    except Exception as e:
        logging.error(f"Failed to start webdriver: {e}")
        return {'keyword': keyword, 'rank': 'WebDriver起動エラー', 'article_id': article_id}
    
    try:
        driver.get('https://www.google.com')
        search_box = driver.find_element(By.NAME, 'q')
        search_box.send_keys(keyword)
        search_box.send_keys(Keys.RETURN)
        time.sleep(10)

        results = driver.find_elements(By.CSS_SELECTOR, 'div.g')
        logging.info(f"Number of search results found: {len(results)}")

        rank = next((index + 1 for index, result in enumerate(results[:15])
                    if target_url in result.find_element(By.TAG_NAME, 'a').get_attribute('href')), '圏外')

    except Exception as e:
        rank = 'エラー'
        logging.error(f"Error processing {keyword}: {e}")
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

    logging.info(f"Rank for {keyword}: {l_value}")
    return {'keyword': keyword, 'rank': l_value, 'article_id': article_id}

# フォームを表示するエンドポイント
@app.route('/')
def index():
    return '''
        <h1>CSVファイルをアップロードして検索順位を確認</h1>
        <form action="/upload_csv" method="post" enctype="multipart/form-data">
            <input type="file" name="file"><br><br>
            <input type="submit" value="アップロードして実行">
        </form>
        <h3 id="status"></h3>
    '''

# CSVファイルをアップロードして順位を確認するエンドポイント
@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    logging.info("CSV upload initiated.")
    if 'file' not in request.files:
        logging.error("No file part in the request.")
        return "ファイルが見つかりませんでした", 400

    file = request.files['file']
    if file.filename == '':
        logging.error("No file selected.")
        return "ファイルが選択されていません", 400

    if file:
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            logging.info(f"File saved to {filepath}")

            # アップロードされたCSVを処理
            results = []
            with open(filepath, newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                next(reader)  # ヘッダーをスキップ
                for row in reader:
                    if len(row) < 2:
                        logging.warning(f"Row {row} is malformed.")
                        continue
                    keyword = row[0]
                    article_id = row[1]
                    result = check_rank(keyword, article_id)
                    results.append(result)

            # 結果を新しいCSVファイルに保存
            result_file = os.path.join(RESULT_FOLDER, 'rank_results.csv')
            with open(result_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['キーワード', '順位', '記事ID'])
                for result in results:
                    writer.writerow([result['keyword'], result['rank'], result['article_id']])

            logging.info(f"Results saved to {result_file}")
            # 結果のCSVファイルをダウンロードとして返す
            return send_file(result_file, mimetype='text/csv', as_attachment=True, download_name='rank_results.csv')

        except Exception as e:
            logging.error(f"Error processing file: {e}")
            return f"エラーが発生しました: {e}", 500

# エラーハンドリングの追加
@app.errorhandler(500)
def internal_error(error):
    logging.error(f"500 Error: {error}")
    return "サーバー内部エラーが発生しました。詳細はログを確認してください。", 500

if __name__ == '__main__':
    app.run(debug=True)
