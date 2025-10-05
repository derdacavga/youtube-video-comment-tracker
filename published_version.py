import threading
import time
import json
from flask import Flask, jsonify
import re
from youtube_comment_downloader import YoutubeCommentDownloader

VIDEO_URL = "https://www.youtube.com/shorts/1-4DglzTAp8"  # Change with your video link
FETCH_INTERVAL = 2.0  # Check new comment interval

app = Flask(__name__)

queue = []
seen = set()
lock = threading.Lock()
last_message_time = time.time()
auto_index = 0

auto_messages = [
    "Hello everyone :)",
    "Don't forget to subscribe :D",
    "Thanks for your support <3",
    "Enjoy the stream!"
]

def remove_emoji_shortnames(text):
    return re.sub(r':[a-zA-Z0-9_\-]+:', '', text)

def turkce_to_ascii(text):
    replacements = {
        'ç':'c', 'Ç':'C',
        'ğ':'g', 'Ğ':'G',
        'ı':'i', 'İ':'I',
        'ö':'o', 'Ö':'O',
        'ş':'s', 'Ş':'S',
        'ü':'u', 'Ü':'U'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

def poll_youtube():
    global last_message_time
    downloader = YoutubeCommentDownloader()

    while True: 
        try:
            comments = downloader.get_comments_from_url(VIDEO_URL, sort_by=1)  
            for c in comments:
                text = f"{c['author']}: {c['text']}"
                text = remove_emoji_shortnames(text)
                text = turkce_to_ascii(text).strip()
                with lock:
                    if text and text not in seen:
                        seen.add(text)
                        queue.append(text)
                        last_message_time = time.time()
                        print("New comment:", text)
                time.sleep(FETCH_INTERVAL)
        except Exception as e:
            print("Error fetching comments:", e)
            time.sleep(5)  

def auto_message_worker():
    global last_message_time, auto_index
    while True:
        now = time.time()
        if now - last_message_time > 10:  
            msg = auto_messages[auto_index]
            with lock:
                queue.append(msg)
            print("Auto Message:", msg)
            last_message_time = time.time()
            auto_index = (auto_index + 1) % len(auto_messages)
        time.sleep(1)

@app.route("/comments")
def get_comments():
    global queue
    with lock:
        if not queue:
            return jsonify([])
        out = list(queue)
        queue.clear()
    return jsonify(out)

def run_flask():
    app.run(host="0.0.0.0", port=8000)

if __name__ == "__main__": 
    t1 = threading.Thread(target=run_flask, daemon=True)
    t1.start()
 
    t2 = threading.Thread(target=auto_message_worker, daemon=True)
    t2.start()
 
    poll_youtube()
