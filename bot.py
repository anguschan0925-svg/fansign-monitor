import os
import requests
import urllib.parse

# 讀取設定好的環境變數
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def load_keywords():
    if os.path.exists("keywords.txt"):
        with open("keywords.txt", "r", encoding="utf-8") as f:
            return [line.strip().lower() for line in f if line.strip()]
    return []

def check_tweets():
    keywords = load_keywords()
    if not keywords:
        print("沒有設定關鍵字。")
        return

    # 由於 X 限制，這裡使用公開的免登入 Nitter 鏡像站來抓取 fansign_info 的 RSS 資訊流
    rss_url = "https://nitter.net/fansign_info/rss"
    
    try:
        # 使用一個免費的 XML 轉 JSON API 來解析 RSS，完全不需要寫複雜的解析程式
        api_url = f"https://api.rss2json.com/v1/api.json?rss_url={urllib.parse.quote(rss_url)}"
        response = requests.get(api_url).json()
        
        if response.get("status") == "ok":
            for item in response.get("items", []):
                title = item.get("title", "")
                content = item.get("content", "").lower()
                link = item.get("link", "").replace("nitter.net", "x.com") # 把網址還原成 x.com
                
                # 檢查是否包含任何關鍵字
                if any(kw in content or kw in title.lower() for kw in keywords):
                    # 檢查這條推文是不是之前發送過（避免重複通知）
                    if not is_already_sent(link):
                        send_telegram_message(f"🚨 【Fansign 新公告！】\n\n{title}\n\n傳送門：{link}")
                        save_sent_link(link)
    except Exception as e:
        print(f"執行出錯: {e}")

def is_already_sent(link):
    if os.path.exists("sent_links.txt"):
        with open("sent_links.txt", "r") as f:
            return link in f.read()
    return False

def save_sent_link(link):
    with open("sent_links.txt", "a") as f:
        f.write(link + "\n")

def send_telegram_message(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, json=payload)

if __name__ == "__main__":
    check_tweets()
