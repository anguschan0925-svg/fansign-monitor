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
    # 擴大戰線：整合全球精選 Nitter 鏡像站 + 高穩定度社群 RSSHub 實例，共計 11 個防禦節點
    endpoints = [
        {"url": "https://rsshub.rssforever.com/twitter/user/fansign_info", "name": "RSSHub (RssForever 實例)"},
        {"url": "https://rsshub.moeyy.xyz/twitter/user/fansign_info", "name": "RSSHub (Moeyy 實例)"},
        {"url": "https://twitt.re/fansign_info/rss", "name": "Nitter (twitt.re)"},
        {"url": "https://nitter.pussthecat.org/fansign_info/rss", "name": "Nitter (pussthecat)"},
        {"url": "https://nitter.fdn.fr/fansign_info/rss", "name": "Nitter (fdn.fr)"},
        {"url": "https://nitter.unixfox.eu/fansign_info/rss", "name": "Nitter (unixfox)"},
        {"url": "https://nitter.kavin.rocks/fansign_info/rss", "name": "Nitter (kavin.rocks)"},
        {"url": "https://nitter.moomoo.me/fansign_info/rss", "name": "Nitter (moomoo.me)"},
        {"url": "https://nitter.catsarch.com/fansign_info/rss", "name": "Nitter (catsarch)"},
        {"url": "https://xcancel.com/fansign_info/rss", "name": "Xcancel 鏡像"},
        {"url": "https://rsshub.app/twitter/user/fansign_info", "name": "RSSHub (官方示範站)"}
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    }
    
    for ep in endpoints:
        print(f"【步驟 2】正在嘗試連線至來源: {ep['name']}")
        try:
            response = requests.get(ep['url'], headers=headers, timeout=12)
            print(f" -> 伺服器回應狀態碼: {response.status_code}")
            if response.status_code == 200 and response.content:
                # 相容 Nitter 和 RSSHub 的 XML 特徵檢測
                if b"<rss" in response.content or b"<feed" in response.content or b"<channel" in response.content:
                    print(f" -> 🎉 [成功] 已成功從 {ep['name']} 獲取有效的 XML 資料！")
                    return response.content
                print(" -> [提示] 返回內容非有效的 RSS 格式，自動切換至下一站...")
        except Exception as e:
            print(f" -> [連線失敗] 錯誤原因: {e}，自動切換至下一站...")
    return None

def check_tweets():
    keywords = load_keywords()
    rss_content = fetch_rss_with_fallback()
    
    if not rss_content:
        print("【⚠️ 嚴重警告】全線崩潰！今天所有 Nitter 和 RSSHub 備用節點皆無法突破 X 的封鎖或 GitHub IP 的限制。請稍後再試。")
        return

    try:
        root = ET.fromstring(rss_content)
        items = root.findall('.//item')
        print(f"【步驟 3】成功抓取到 {len(items)} 條最新推文，開始進行比對...")
        
        match_count = 0
        for item in items:
            title = item.find('title').text if item.find('title') is not None else ""
            description = item.find('description').text if item.find('description') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            
            # 統一將各式各樣的鏡像站/舊網址，還原為標準的 x.com 方便手機與電腦直接點開
            domains_to_replace = [
                "xcancel.com", "nitter.poast.org", "nitter.privacydev.net", "twitt.re", 
                "nitter.pussthecat.org", "nitter.fdn.fr", "nitter.unixfox.eu", 
                "nitter.kavin.rocks", "nitter.moomoo.me", "nitter.catsarch.com", "twitter.com"
            ]
            for domain in domains_to_replace:
                link = link.replace(domain, "x.com")
                
            content_lower = (title + " " + description).lower()
            
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
        print(f"【Telegram 發送反饋】狀態碼: {res.status_code}")
    except Exception as e:
        print(f"【錯誤】發送 Telegram 訊息時發生網路異常: {e}")

if __name__ == "__main__":
    check_tweets()
