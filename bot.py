import requests
import json
import threading
import random
import time
from functools import lru_cache
from collections import defaultdict

# إعدادات التطبيق
BOT_TOKEN = "7840468800:AAFZNDp0PiUcm-POl-XMJLyjc8oOcsQcgd8"
FACEBOOK_PAGE_ACCESS_TOKEN = 'EAARRlvmJ1MMBP8tnkpw0CgjZAgfGq9H2ekxQl8yClhzcMHNNWvgdwlBL3zNZAg8bzs3NBmQ9VDNronmCAQwG3zApXM7u0WtEzIgigyBkRUgg3MCQKL8oYyqKmPf5Ff1Rq23Qc5njfpc2X2hIhZC2ZCLawvlxeaJVBfeKe2y0H9jjMxZAj89ZCpL8H2ebE1MzRwkMhz5qAaowZDZD'
FACEBOOK_GRAPH_API_URL = 'https://graph.facebook.com/v11.0/me/messages'

# إعدادات APIs
CHAT_API_URL = "https://prod-smith.vulcanlabs.co/api/v7/chat_android"
VISION_API_URL = "https://api.vulcanlabs.co/smith-v2/api/v7/vision_android"
GETIMG_API_URL = "https://api.getimg.ai/v1/stable-diffusion-xl/text-to-image"
GETIMG_API_KEY = "key-3XbWkFO34FVCQUnJQ6A3qr702Eu7DDR1dqoJOyhMHqhruEhs22KUzR7w631ZFiA5OFZIba7i44qDQEMpKxzegOUm83vCfILb"
VISION_AUTH_TOKEN = "FOcsaJJf1A+Zh3Ku6EfaNYbo844Y7168Ak2lSmaxtNZVtD7vcaJUmTCayc1HgcXIILvdmnzsdPjuGwqYKKUFRLdUVQQZbfXHrBUSYrbHcMrmxXvDu/DHzrtkPqg90dX/rSmTRnx7sz7pHTOmZqLLfLUnaO2XTEZLD0deMpRdzQE="
ASSEMBLYAI_API_KEY = "771de44ac7644510a0df7e9a3b8a6b7c"
TTS_SERVICE_URL = "https://dev-yacingpt.pantheonsite.io/wp-admin/maint/Bot%20hosting/Textspeesh.php"

# التخزين المحلي للمستخدمين
user_conversations = {}
current_access_token = None
running = True
processed_message_ids = set()
# تخزين آخر وقت معالجة لكل مستخدم
user_last_activity = defaultdict(float)
# تخزين آخر رسالة معالجة لكل مستخدم
user_last_message = defaultdict(str)

# تجهيز الجلسة مع تحسينات الأداء
session = requests.Session()
session.headers.update({'Connection': 'keep-alive'})
adapter = requests.adapters.HTTPAdapter(pool_connections=100, pool_maxsize=100)
session.mount('https://', adapter)

# قائمة الإيموجي والملصقات التي يرد عليها
EMOJI_RESPONSES = {
    '😂': ['😂😂', 'ههههه ضحكتني', 'والله مضحك'],
    '😍': ['😍😍', 'يا جميل', 'الله على الجمال'],
    '😢': ['لا تحزن 😢', 'الله يعين', 'كل شيء سيكون بخير'],
    '😡': ['اهدأ 🫂', 'لا تغضب', 'الغضب لا يحل المشاكل'],
    '❤️': ['❤️❤️', 'الله يسلمك', 'يا قلبو'],
    '👍': ['👍👍', 'تم يا بطل', 'الله يقويك'],
    '👏': ['👏👏', 'برافو عليك', 'مبدع'],
    '🎉': ['🎉🎉', 'مبروك', 'فرحانين من أجلك'],
    '🔥': ['🔥🔥', 'والله نار', 'متميز'],
    '🤔': ['فكر معي 🤔', 'شاركنا رأيك', 'ما رأيك؟'],
    '🤣': ['🤣🤣', 'يضحك والله', 'ما أضحكك'],
    '🥰': ['🥰🥰', 'يا حلو', 'الله يسعدك'],
    '🙏': ['🙏🙏', 'الله يستجيب', 'آمين'],
    '💪': ['💪💪', 'قوي والله', 'الله يقويك'],
    '✨': ['✨✨', 'مشرق والله', 'متميز']
}

STICKER_RESPONSES = [
    "واو ملصق حلو! 😄",
    "يعجبني هذا الملصق! 🎯",
    "ملصق رائع! 👌",
    "الله على الملصق الجميل! 🌟",
    "شكراً على الملصق! 🤗"
]

def is_duplicate_message(sender_id, message_content):
    """فحص إذا كانت الرسالة مكررة لنفس المستخدم"""
    current_time = time.time()
    message_text = message_content.get('text', '') if isinstance(message_content, dict) else str(message_content)
    
    # إذا كانت نفس الرسالة ومر أقل من 5 ثواني منذ آخر نشاط
    if (user_last_message[sender_id] == message_text and 
        current_time - user_last_activity[sender_id] < 5):
        return True
    
    # تحديث آخر نشاط ورسالة
    user_last_activity[sender_id] = current_time
    user_last_message[sender_id] = message_text
    return False

def send_typing_indicator(recipient_id, typing_status=True):
    """إرسال مؤشر الكتابة للمستخدم"""
    action = "typing_on" if typing_status else "typing_off"
    data = {
        "recipient": {"id": recipient_id},
        "sender_action": action
    }
    
    try:
        response = session.post(
            FACEBOOK_GRAPH_API_URL,
            params={"access_token": FACEBOOK_PAGE_ACCESS_TOKEN},
            json=data
        )
        return response.status_code == 200
    except Exception as e:
        print(f"Typing indicator error: {e}")
        return False

def get_random_response(responses_list):
    """إرجاع رد عشوائي من القائمة"""
    return random.choice(responses_list)

def get_access_token(force_refresh=False):
    global current_access_token
    
    if not force_refresh and current_access_token:
        return current_access_token
        
    url = "https://chatgpt-au.vulcanlabs.co/api/v1/token"
    headers = {
        "Host": "chatgpt-au.vulcanlabs.co",
        "x-vulcan-application-id": "com.smartwidgetlabs.chatgpt",
        "accept": "application/json",
        "user-agent": "Chat Smith Android, Version 3.8.0(602)",
        "x-vulcan-request-id": "9149487891720485306508",
        "content-type": "application/json; charset=utf-8",
        "accept-encoding": "gzip"
    }
    payload = {
        "device_id": "F75FA09A4ECFF631",
        "order_id": "",
        "product_id": "",
        "purchase_token": "",
        "subscription_id": ""
    }
    
    for attempt in range(3):
        try:
            response = session.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                current_access_token = data.get('AccessToken')
                return current_access_token
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(2 ** attempt)
    
    print("Failed to get access token")
    return None

def token_refresh_scheduler():
    global running
    while running:
        time.sleep(900)  # انتظار 15 دقيقة
        if running:
            print("Refreshing token...")
            get_access_token(force_refresh=True)

def send_chat_request(messages, retry_count=0):
    global current_access_token
    
    if not current_access_token:
        current_access_token = get_access_token()
        if not current_access_token:
            return None

    headers = {
        "Host": "prod-smith.vulcanlabs.co",
        "authorization": f"Bearer {current_access_token}",
        "x-firebase-appcheck-error": "-2%3A+Integrity+API+error...",
        "x-vulcan-application-id": "com.smartwidgetlabs.chatgpt",
        "accept": "application/json",
        "user-agent": "Chat Smith Android, Version 3.8.0(602)",
        "x-vulcan-request-id": "9149487891720485379249",
        "content-type": "application/json; charset=utf-8",
        "accept-encoding": "gzip"
    }
    
    payload = {
        "model": "gpt-4",
        "user": "F75FA09A4ECFF631",
        "messages": messages,
        "nsfw_check": True,
        "functions": [
            {
                "name": "create_ai_art",
                "description": "Return this only if the user wants to create a photo or art...",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "The prompt to create art"
                        }
                    }
                }
            }
        ]
    }
    
    try:
        response = session.post(CHAT_API_URL, headers=headers, json=payload, timeout=15)
        if response.status_code == 401 and retry_count < 2:
            print("Token expired, refreshing...")
            current_access_token = get_access_token(force_refresh=True)
            if current_access_token:
                return send_chat_request(messages, retry_count + 1)
        
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"Chat request error: {e}")
        return None

def transcribe_audio(audio_url):
    try:
        data = {"audio_url": audio_url, "language_code": "ar", "speech_model": "nano"}
        headers = {"authorization": ASSEMBLYAI_API_KEY, "content-type": "application/json"}
        
        response = session.post("https://api.assemblyai.com/v2/transcript", json=data, headers=headers)
        if response.status_code != 200:
            return None
        
        transcript_id = response.json().get("id")
        if not transcript_id:
            return None
        
        polling_url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        while True:
            poll_response = session.get(polling_url, headers=headers)
            result = poll_response.json()
            if result['status'] == 'completed':
                return result['text']
            elif result['status'] == 'error':
                return None
            time.sleep(1)
    except Exception as e:
        print(f"Transcription error: {e}")
        return None

def text_to_speech(text, sender_id):
    try:
        payload = {'text': text}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        response = session.post(TTS_SERVICE_URL, data=payload, headers=headers)
        if response.status_code != 200:
            return None
        
        result = response.json()
        if 'audio_url' in result:
            audio_response = session.get(result['audio_url'])
            if audio_response.status_code == 200:
                return audio_response.content
        return None
    except Exception as e:
        print(f"TTS error: {e}")
        return None

def process_image(image_url, sender_id):
    global current_access_token
    
    try:
        # إرسال مؤشر الكتابة
        send_typing_indicator(sender_id, True)
        
        image_response = session.get(image_url)
        if image_response.status_code != 200:
            send_facebook_message(sender_id, "❌ لم أتمكن من تحميل الصورة")
            send_typing_indicator(sender_id, False)
            return None
        
        image_data = image_response.content
        boundary = "44cb511a-c1d4-4f51-a017-1352f87db948"
        headers = {
            "Host": "api.vulcanlabs.co",
            "x-auth-token": VISION_AUTH_TOKEN,
            "authorization": f"Bearer {current_access_token}",
            "x-firebase-appcheck-error": "-9%3A+Integrity+API",
            "x-vulcan-application-id": "com.smartwidgetlabs.chatgpt",
            "accept": "application/json",
            "user-agent": "Chat Smith Android, Version 3.9.11(720)",
            "x-vulcan-request-id": "9149487891748042373127",
            "content-type": f"multipart/form-data; boundary={boundary}",
            "accept-encoding": "gzip"
        }
        
        data_part = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="data"\r\n'
            f"Content-Length: 145\r\n\r\n"
            '{"model":"gpt-4o-mini","user":"F75FA09A4ECFF631","messages":[{"role":"user","content":"ما هذا وعلى ما يحتوي"}],"nsfw_check":true}\r\n'
        )
        
        image_part = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="images[]"; filename="uploaded_image.jpg"\r\n'
            f"Content-Type: image/jpeg\r\n\r\n"
        )
        
        end_boundary = f"\r\n--{boundary}--\r\n"
        
        body = data_part.encode() + image_part.encode() + image_data + end_boundary.encode()
        
        response = session.post(VISION_API_URL, headers=headers, data=body)
        if response.status_code == 401:
            current_access_token = get_access_token(force_refresh=True)
            if current_access_token:
                headers["authorization"] = f"Bearer {current_access_token}"
                new_response = session.post(VISION_API_URL, headers=headers, data=body)
                if new_response.status_code == 200:
                    result = new_response.json()
                    send_typing_indicator(sender_id, False)
                    return next((choice.get('Message', {}).get('content', '') for choice in result.get('choices', [])), None)
        
        if response.status_code == 200:
            result = response.json()
            send_typing_indicator(sender_id, False)
            return next((choice.get('Message', {}).get('content', '') for choice in result.get('choices', [])), None)
        
        send_typing_indicator(sender_id, False)
        return None
    except Exception as e:
        print(f"Image processing error: {e}")
        send_typing_indicator(sender_id, False)
        return None

def generate_images(prompt):
    headers = {
        'Authorization': f'Bearer {GETIMG_API_KEY}',
        'Content-Type': 'application/json',
    }
    
    data = {
        'model': 'realvis-xl-v4',
        'prompt': prompt,
        'negative_prompt': 'nude, naked, porn, sexual, explicit, adult, sex, xxx, erotic',
        'response_format': 'url',
        'steps': 30,
        'height': 1024,
        'width': 1024
    }
    
    try:
        response = session.post(GETIMG_API_URL, headers=headers, json=data)
        if response.status_code == 200:
            result = response.json()
            return result.get('url')
    except Exception as e:
        print(f"Image generation error: {e}")
    return None

def send_facebook_message(recipient_id, message_text):
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    
    try:
        response = session.post(
            FACEBOOK_GRAPH_API_URL,
            params={"access_token": FACEBOOK_PAGE_ACCESS_TOKEN},
            json=data
        )
        if response.status_code != 200:
            print(f"Message send error: {response.text}")
    except Exception as e:
        print(f"Message send exception: {e}")

def send_facebook_image(recipient_id, image_url):
    try:
        img_response = session.get(image_url)
        if img_response.status_code == 200:
            image_data = img_response.content
            
            files = {
                'recipient': (None, json.dumps({"id": recipient_id})),
                'message': (None, json.dumps({"attachment": {"type": "image", "payload": {}}})),
                'access_token': (None, FACEBOOK_PAGE_ACCESS_TOKEN),
                'attachment': ('image.jpg', image_data, 'image/jpeg')
            }
            
            response = session.post(FACEBOOK_GRAPH_API_URL, files=files)
            if response.status_code != 200:
                print(f"Image send error: {response.text}")
    except Exception as e:
        print(f"Image send exception: {e}")

def send_facebook_audio(recipient_id, audio_bytes):
    files = {
        'recipient': (None, json.dumps({"id": recipient_id})),
        'message': (None, json.dumps({"attachment": {"type": "audio", "payload": {}}})),
        'access_token': (None, FACEBOOK_PAGE_ACCESS_TOKEN),
        'attachment': ('audio.mp3', audio_bytes, 'audio/mpeg')
    }
    
    try:
        response = session.post(FACEBOOK_GRAPH_API_URL, files=files)
        if response.status_code != 200:
            print(f"Audio send error: {response.text}")
    except Exception as e:
        print(f"Audio send exception: {e}")

def handle_message_thread(sender_id, message):
    """معالجة الرسالة في thread منفصل"""
    def process_message():
        # فحص إذا كانت الرسالة مكررة
        if is_duplicate_message(sender_id, message):
            print(f"Ignoring duplicate message from {sender_id}")
            return
            
        # معالجة الملصقات
        if 'attachments' in message:
            attachments = message['attachments']['data']
            for attachment in attachments:
                # إذا كان ملصق
                if attachment.get('type') == 'sticker':
                    response = get_random_response(STICKER_RESPONSES)
                    send_facebook_message(sender_id, response)
                    return
                
                # معالجة الصور
                mime_type = attachment.get('mime_type', '').lower()
                
                if 'image' in mime_type:
                    image_url = None
                    if 'image_data' in attachment and 'url' in attachment['image_data']:
                        image_url = attachment['image_data']['url']
                    elif 'payload' in attachment and 'url' in attachment['payload']:
                        image_url = attachment['payload']['url']
                    elif 'url' in attachment:
                        image_url = attachment['url']
                    
                    if image_url:
                        send_facebook_message(sender_id, "⏳ جاري تحليل الصورة، الرجاء الانتظار...")
                        result = process_image(image_url, sender_id)
                        if result:
                            send_facebook_message(sender_id, result)
                        else:
                            send_facebook_message(sender_id, "❌ لم أتمكن من تحليل الصورة.")
                    return
                    
                # معالجة الصوت
                elif 'audio' in mime_type or 'voice' in mime_type or 'mpeg' in mime_type:
                    audio_url = None
                    if 'file_url' in attachment:
                        audio_url = attachment['file_url']
                    elif 'payload' in attachment and 'url' in attachment['payload']:
                        audio_url = attachment['payload']['url']
                    elif 'url' in attachment:
                        audio_url = attachment['url']
                    
                    if audio_url:
                        if 'facebook.com' in audio_url and '?' not in audio_url:
                            audio_url += "?access_token=" + FACEBOOK_PAGE_ACCESS_TOKEN
                        
                        send_facebook_message(sender_id, "⏳ جاري الاستماع 👂...")
                        # إرسال مؤشر الكتابة أثناء التحويل
                        send_typing_indicator(sender_id, True)
                        text = transcribe_audio(audio_url)
                        send_typing_indicator(sender_id, False)
                        
                        if text:
                            send_facebook_message(sender_id, f"📝 لقد قلت:\n{text}")
                            
                            conversation_history = user_conversations.get(sender_id, [])
                            new_messages = conversation_history + [{"role": "user", "content": text}]
                            
                            # إرسال مؤشر الكتابة أثناء معالجة الرد
                            send_typing_indicator(sender_id, True)
                            response = send_chat_request(new_messages)
                            send_typing_indicator(sender_id, False)
                            
                            if response:
                                response_message = next(
                                    (choice.get('Message', {}).get('content', '') for choice in response.get('choices', [])),
                                    "خطا من المصدر"
                                )
                                send_facebook_message(sender_id, response_message)
                                
                                audio_bytes = text_to_speech(response_message, sender_id)
                                if audio_bytes:
                                    send_facebook_audio(sender_id, audio_bytes)
                                
                                user_conversations[sender_id] = new_messages + [{"role": "assistant", "content": response_message}]
                        else:
                            send_facebook_message(sender_id, "❌ لم أتمكن من تحويل الصوت إلى نص.")
                    return
        
        # معالجة الرسائل النصية والإيموجي
        if 'text' in message and isinstance(message['text'], str):
            message_text = message['text']
            
            # معالجة سريعة للردود الداخلية
            message_lower = message_text.lower()
            
            if '฿' in message_text or '👍' in message_text or 'جام ثاني' in message_lower:
                send_facebook_message(sender_id, "👍")
                return
            elif 'ฯ' in message_text or '﷼' in message_text:
                send_facebook_message(sender_id, "أنا بخير، الحمدلله وأنت ")
                return
            elif message_lower.startswith(("من انت", "من أنت", "من مطورك", "من صانعك", "من صاحبك")):
                response = "تم تطويري من قبل مطور بوتات"
                send_facebook_message(sender_id, response)
                return
            elif "اسرائيل" in message_lower or "إسرائيل" in message_lower or 'israel' in message_lower:
                send_facebook_message(sender_id, "عذرا انا لا اعرف ما تقول انا اعرف دولة فلسطين 🇵🇸 عاصمتها القدس")
                return
            
            # معالجة الإيموجي
            for emoji, responses in EMOJI_RESPONSES.items():
                if emoji in message_text:
                    response = get_random_response(responses)
                    send_facebook_message(sender_id, response)
                    return
        
        # إذا كانت الرسالة نصية عادية
        if 'text' in message and message['text']:
            message_text = message['text']
            conversation_history = user_conversations.get(sender_id, [])
            new_messages = conversation_history + [{"role": "user", "content": message_text}]

            # إرسال مؤشر الكتابة
            send_typing_indicator(sender_id, True)
            response = send_chat_request(new_messages)
            send_typing_indicator(sender_id, False)
            
            if response:
                image_request = False
                for choice in response.get('choices', []):
                    if choice.get('Message', {}).get('function_call', {}).get('name') == 'create_ai_art':
                        try:
                            args = json.loads(choice['Message']['function_call']['arguments'])
                            prompt = args.get('prompt', '')
                            
                            if prompt:
                                image_request = True
                                send_facebook_message(sender_id, "⏳ جاري إنشاء الصور، الرجاء الانتظار...")
                                
                                # إرسال مؤشر الكتابة أثناء إنشاء الصور
                                send_typing_indicator(sender_id, True)
                                
                                # إنشاء 4 صور بشكل متوازي باستخدام threads
                                def generate_and_send_image(prompt, sender_id):
                                    image_url = generate_images(prompt)
                                    if image_url:
                                        send_facebook_image(sender_id, image_url)
                                
                                threads = []
                                for _ in range(4):
                                    thread = threading.Thread(target=generate_and_send_image, args=(prompt, sender_id))
                                    thread.start()
                                    threads.append(thread)
                                
                                for thread in threads:
                                    thread.join()
                                
                                send_typing_indicator(sender_id, False)
                                send_facebook_message(sender_id, "✅ تم إنشاء الصور بنجاح!")
                        except Exception as e:
                            print(f"Image generation error: {e}")
                            send_typing_indicator(sender_id, False)
                            send_facebook_message(sender_id, "❌ حدث خطأ أثناء إنشاء الصور")
                        break
                
                if not image_request:
                    response_message = next(
                        (choice.get('Message', {}).get('content', '') for choice in response.get('choices', [])),
                        "عذرًا، حدث خطأ في معالجة طلبك."
                    )
                    send_facebook_message(sender_id, response_message)
                    
                    audio_bytes = text_to_speech(response_message, sender_id)
                    if audio_bytes:
                        send_facebook_audio(sender_id, audio_bytes)
                    
                    user_conversations[sender_id] = new_messages + [{"role": "assistant", "content": response_message}]
            else:
                send_facebook_message(sender_id, "❌ حدث خطأ في معالجة رسالتك")
    
    # تشغيل المعالجة في thread جديد
    thread = threading.Thread(target=process_message)
    thread.daemon = True
    thread.start()

def poll_facebook_messages():
    global running, processed_message_ids
    
    # بدء مهام الخلفية في threads منفصلة
    refresh_thread = threading.Thread(target=token_refresh_scheduler, daemon=True)
    refresh_thread.start()
    
    while running:
        try:
            url = f"https://graph.facebook.com/v11.0/me/conversations?fields=messages.limit(10){{message,attachments,from,id}}&access_token={FACEBOOK_PAGE_ACCESS_TOKEN}"
            
            response = session.get(url)
            if response.status_code == 200:
                data = response.json()
                conversations = data.get('data', [])
                
                for conversation in conversations:
                    for message in conversation['messages']['data']:
                        msg_id = message['id']
                        if msg_id not in processed_message_ids:
                            sender_id = message['from']['id']
                            message_content = message.get('message', {})
                            if isinstance(message_content, str):
                                message_content = {'text': message_content}
                            
                            if 'attachments' in message:
                                message_content['attachments'] = message['attachments']
                            
                            print(f"New message from {sender_id}")
                            handle_message_thread(sender_id, message_content)
                            processed_message_ids.add(msg_id)
                
                time.sleep(1)  # انتظار ثانية بين الدورات
        except Exception as e:
            print(f"Polling error: {e}")
            time.sleep(3)  # زيادة زمن الانتظار عند حدوث خطأ

def stop_bot():
    global running
    running = False
    print("Bot is stopping...")

def main():
    try:
        print("🚀 Starting Facebook Bot...")
        print("🤖 Bot is now running and monitoring messages...")
        print("📱 Send a message to your Facebook Page to test!")
        poll_facebook_messages()
    except KeyboardInterrupt:
        stop_bot()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        stop_bot()

if __name__ == "__main__":
    main()
