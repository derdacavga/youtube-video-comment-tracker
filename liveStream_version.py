import threading
import time
import json
from flask import Flask, jsonify
import pytchat
import re

VIDEO_ID = "xC6P6_DFXow" ## Change with your Video id
POLL_INTERVAL = 1.0

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
    chat = pytchat.create(video_id=VIDEO_ID)
    while chat.is_alive():
        for item in chat.get().sync_items():
            text = f"{item.author.name}: {item.message}"
            text = remove_emoji_shortnames(text)
            text = turkce_to_ascii(text)
            text = text.strip()
            with lock:
                if text and text not in seen:
                    seen.add(text)
                    queue.append(text)
                    last_message_time = time.time() 
                    print("New comment:", text)
                    if len(seen) > 2000:
                        seen_list = list(seen)[-1000:]
                        seen.clear()
                        seen.update(seen_list)
        time.sleep(POLL_INTERVAL)

def auto_message_worker():
    global last_message_time, auto_index
    while True:
        now = time.time()
        if now - last_message_time > 9:  
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
