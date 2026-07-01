import os
import requests
import xml.etree.ElementTree as ET

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
CHAT_ID = os.environ.get('CHAT_ID')

def load_keywords():
    if os.path.exists("keywords.txt"):
        with open("keywords.txt", "r", encoding="utf-8") as f:
            kws = [line.strip().lower() for line in f if line.strip()]
            print(f"【步驟 1】成功載入關鍵字過濾清單: {kws}")
            return kws
    print("【提示】找不到 keywords.txt，將預設發送該帳號的所有推文（不進行關鍵字過濾）")
    return []

def fetch_rss_with_fallback():
    # 多個穩定的 X/Twitter RSS 鏡像站備用清單，依序嘗試，大幅提升穩定度
    urls = [
        "https://xcancel.com/fansign_info/rss",
        "https://nitter.poast.org/fansign_info/rss",
        "https://nitter.privacydev.net/fansign_info/rss"
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    
    for url in urls:
        print(f"【步驟 2】正在嘗試連線至來源站: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=15)
            print(f" -> 伺服器回應狀態碼: {response.status_code}")
            if response.status_code == 200 and response.content:
                # 確保返回的是 XML 格式，而不是網頁錯誤
                if b"<rss" in response.content or b"<feed" in response.content:
                    print(f" -> [成功] 已成功從該站獲取資料！")
                    return response.content
                print(" -> [提示] 該站返回了無效的格式，自動切換至下一站...")
        except Exception as e:
            print(f" -> [連線失敗] 錯誤原因: {e}，自動切換至下一站...")
    return None

def check_tweets():
    keywords = load_keywords()
    rss_content = fetch_rss_with_fallback()
    
    if not rss_content:
        print("【⚠️ 警告】所有備用來源暫時無法連線（可能遭 X 暫時封鎖網頁），本次執行安全結束。")
        return

    try:
        root = ET.fromstring(rss_content)
        items = root.findall('.//item')
        print(f"【步驟 3】成功抓取到 {len(items)} 條最新推文，開始比對...")
        
        match_count = 0
        for item in items:
            title = item.find('title').text if item.find('title') is not None else ""
            description = item.find('description').text if item.find('description') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            
            # 將網址還原為標準的 x.com 方便手機直接點開
            link = link.replace("xcancel.com", "x.com").replace("nitter.poast.org", "x.com").replace("nitter.privacydev.net", "x.com")
            content_lower = (title + " " + description).lower()
            
            # 比對邏輯：如果關鍵字清單為空，就代表全發（如同您的 IFTTT 設定）；若有關鍵字則進行過濾
            is_match = False
            if not keywords:
                is_match = True
            else:
                is_match = any(kw in content_lower for kw in keywords)
                
            if is_match:
                match_count += 1
                if not is_already_sent(link):
                    print(f"✨ 偵測到全新公告: {title[:30]}...")
                    send_telegram_message(f"🚨 【Fansign 新公告！】\n\n{title}\n\n傳送門：{link}")
                    save_sent_link(link)
                else:
                    print(f" 歷史公告（先前已發送過，跳過）: {title[:30]}...")
                    
        print(f"【步驟 4】比對結束。本次共處理了 {match_count} 條符合條件的推文。")
                    
    except Exception as e:
        print(f"【錯誤】解析 XML 資料時發生異常: {e}")

def is_already_sent(link):
    if os.path.exists("sent_links.txt"):
        with open("sent_links.txt", "r", encoding="utf-8") as f:
            return link in f.read()
    return False

def save_sent_link(link):
    with open("sent_links.txt", "a", encoding="utf-8") as f:
        f.write(link + "\n")

def send_telegram_message(msg):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("【錯誤】缺少 TELEGRAM_TOKEN 或 CHAT_ID 環境變數，請檢查 Secrets 設定。")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    try:
        res = requests.post(url, json=payload, timeout=10)
        print(f"【Telegram 發送反饋】狀態碼: {res.status_code}, 回應內容: {res.text}")
    except Exception as e:
        print(f"【錯誤】發送 Telegram 訊息時發生網路異常: {e}")

if __name__ == "__main__":
    check_tweets()
