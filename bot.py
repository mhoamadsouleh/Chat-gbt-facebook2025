import requests
import json
import random
import threading
import time
import os

# إعدادات الفيسبوك
FACEBOOK_PAGE_ACCESS_TOKEN = os.environ.get('FACEBOOK_TOKEN', 'EAARRlvmJ1MMBP8tnkpw0CgjZAgfGq9H2ekxQl8yClhzcMHNNWvgdwlBL3zNZAg8bzs3NBmQ9VDNronmCAQwG3zApXM7u0WtEzIgigyBkRUgg3MCQKL8oYyqKmPf5Ff1Rq23Qc5njfpc2X2hIhZC2ZCLawvlxeaJVBfeKe2y0H9jjMxZAj89ZCpL8H2ebE1MzRwkMhz5qAaowZDZD')
FACEBOOK_GRAPH_API_URL = 'https://graph.facebook.com/v11.0/me/messages'

# إعدادات توليد الصور
GETIMG_API_URL = "https://api.getimg.ai/v1/stable-diffusion-xl/text-to-image"
GETIMG_API_KEY = os.environ.get('GETIMG_KEY', "key-3XbWkFO34FVCQUnJQ6A3qr702Eu7DDR1dqoJOyhMHqhruEhs22KUzR7w631ZFiA5OFZIba7i44qDQEMpKxzegOUm83vCfILb")

# التخزين المحلي
user_sessions = {}
processed_message_ids = set()

# ردود سريعة
QUICK_RESPONSES = {
    'hello': ['مرحبا! 😊', 'أهلاً وسهلاً! 🌟', 'مرحباً بك! 👋'],
    'how are you': ['أنا بخير الحمدلله! 😄', 'بخير وشكراً! 🙏', 'الحمدلله دائماً! 🌺'],
    'thanks': ['العفو! 😊', 'لا شكر على واجب! 🙏', 'أنت الأفضل! 🌟'],
    'name': ['أنا مساعدك الذكي! 🤖', 'أنا بوت فيسبوك! 🚀', 'مساعدك الشخصي! 💫'],
    'help': ['يمكنني مساعدتك في المحادثات والرد على استفساراتك! 💬', 'أنا هنا لأجيب على أسئلتك! ❓'],
    'bye': ['مع السلامة! 👋', 'إلى اللقاء! 🌟', 'كانت محادثة جميلة! 💫'],
    'صور': ['أحب إنشاء الصور! 🎨', 'يمكنني إنشاء صور رائعة لك! 🌟', 'أخبرني ماذا تريد أن أرسم! ✨'],
    'ارسم': ['ماذا تريد أن أرسم؟ 🎨', 'أخبرني بالتفاصيل وسأرسمها لك! 🌟'],
    'رسم': ['الرسم متعة! ما الذي تريد رسمه؟ 🖌️']
}

# كلمات توليد الصور
IMAGE_KEYWORDS = ['اصنع لي صورة', 'ارسم لي', 'انشئ صورة', 'صور', 'رسم', 'ارسم', 'انشئ لي', 'اصنع صورة']

# ردود الإيموجي
EMOJI_RESPONSES = {
    '😂': ['😂😂', 'ههههه ضحكتني!', 'والله مضحك!'],
    '😍': ['😍😍', 'يا جميل!', 'الله على الجمال!'],
    '❤️': ['❤️❤️', 'الله يسلمك!', 'يا قلبو!'],
    '👍': ['👍👍', 'تم يا بطل!', 'الله يقويك!'],
    '😢': ['لا تحزن 😢', 'الله يعين!', 'كل شيء سيكون بخير!'],
    '🎉': ['🎉🎉', 'مبروك!', 'فرحانين من أجلك!'],
    '🔥': ['🔥🔥', 'والله نار!', 'متميز!'],
    '🤔': ['فكر معي 🤔', 'شاركنا رأيك!'],
    '🙏': ['🙏🙏', 'الله يستجيب!', 'آمين!'],
    '🎨': ['🎨🎨', 'الرسم متعة!', 'ماذا تريد أن أرسم؟']
}

def send_facebook_message(recipient_id, message_text):
    """إرسال رسالة سريعة للفيسبوك"""
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text}
    }
    
    try:
        response = requests.post(
            FACEBOOK_GRAPH_API_URL,
            params={"access_token": FACEBOOK_PAGE_ACCESS_TOKEN},
            json=data,
            timeout=5
        )
        return response.status_code == 200
    except:
        return False

def send_facebook_image(recipient_id, image_url):
    """إرسال صورة للفيسبوك"""
    try:
        # تحميل الصورة
        img_response = requests.get(image_url, timeout=10)
        if img_response.status_code == 200:
            image_data = img_response.content
            
            # إرسال الصورة
            files = {
                'recipient': (None, json.dumps({"id": recipient_id})),
                'message': (None, json.dumps({"attachment": {"type": "image", "payload": {}}})),
                'access_token': (None, FACEBOOK_PAGE_ACCESS_TOKEN),
                'attachment': ('image.jpg', image_data, 'image/jpeg')
            }
            
            response = requests.post(FACEBOOK_GRAPH_API_URL, files=files, timeout=10)
            return response.status_code == 200
    except Exception as e:
        print(f"خطأ في إرسال الصورة: {e}")
    return False

def send_typing_indicator(recipient_id, typing_status=True):
    """إرسال مؤشر الكتابة"""
    action = "typing_on" if typing_status else "typing_off"
    data = {
        "recipient": {"id": recipient_id},
        "sender_action": action
    }
    
    try:
        response = requests.post(
            FACEBOOK_GRAPH_API_URL,
            params={"access_token": FACEBOOK_PAGE_ACCESS_TOKEN},
            json=data,
            timeout=3
        )
        return response.status_code == 200
    except:
        return False

def get_quick_response(message_text):
    """البحث عن رد سريع"""
    message_lower = message_text.lower().strip()
    
    # البحث في الردود السريعة
    for key, responses in QUICK_RESPONSES.items():
        if key in message_lower:
            return random.choice(responses)
    
    # البحث في الإيموجي
    for emoji, responses in EMOJI_RESPONSES.items():
        if emoji in message_text:
            return random.choice(responses)
    
    return None

def generate_image(prompt):
    """توليد صورة باستخدام الذكاء الاصطناعي"""
    try:
        headers = {
            'Authorization': f'Bearer {GETIMG_API_KEY}',
            'Content-Type': 'application/json',
        }
        
        data = {
            'model': 'stable-diffusion-xl',
            'prompt': prompt + ", high quality, detailed, professional",
            'negative_prompt': 'blurry, low quality, distorted, ugly',
            'width': 1024,
            'height': 1024,
            'steps': 20  # تقليل الخطوات للسرعة
        }
        
        response = requests.post(GETIMG_API_URL, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result.get('url')
        else:
            print(f"خطأ في توليد الصورة: {response.status_code}")
    except Exception as e:
        print(f"خطأ في توليد الصورة: {e}")
    
    return None

def generate_ai_response(message_text, user_id):
    """إنشاء رد بالذكاء الاصطناعي (سريع)"""
    # إذا كان الطلب متعلقاً بالصور
    message_lower = message_text.lower()
    for keyword in IMAGE_KEYWORDS:
        if keyword in message_lower:
            return "image_generation_request"
    
    # ردود ذكية سريعة
    smart_responses = {
        'كيف': ['أنا برنامج حاسوبي، لكني أحاول مساعدتك بأفضل شكل! 🤖', 'أعمل بشكل جيد وشكراً لسؤالك! 😊'],
        'لماذا': ['هذا سؤال عميق! دعني أفكر... 🤔', 'هناك أسباب متعددة، أي جانب تقصد تحديداً؟ 💭'],
        'متى': ['الوقت يتوقف على الظروف! ⏰', 'هذا يعتمد على عدة عوامل... 📅'],
        'اين': ['الأماكن تتغير باستمرار! 🌍', 'هذا يعتمد على ما تبحث عنه تحديداً! 🗺️'],
        'ماذا': ['هناك العديد من الاحتمالات! 💫', 'دعني أعرف المزيد لأجيب بدقة! ❓']
    }
    
    for key, responses in smart_responses.items():
        if key in message_lower:
            return random.choice(responses)
    
    # رد افتراضي ذكي
    default_responses = [
        "أهلاً بك! هذا مثير للاهتمام! 🌟",
        "شكراً لمشاركة هذا معي! 💫",
        "أفهم ما تقصد! هل يمكنك توضيح المزيد؟ 🤔",
        "هذا رائع! أخبرني المزيد! 🎉",
        "أحب طريقة تفكيرك! 💭",
        "هذا يجعلني أفكر... 🤔 ماذا تعتقد؟"
    ]
    return random.choice(default_responses)

def handle_image_generation(sender_id, prompt):
    """معالجة طلب توليد الصور"""
    def generate_and_send():
        send_typing_indicator(sender_id, True)
        send_facebook_message(sender_id, "🔄 جاري إنشاء صورتك... هذا قد يستغرق بضع ثوانٍ ⏳")
        
        # توليد الصورة
        image_url = generate_image(prompt)
        
        if image_url:
            send_facebook_message(sender_id, "✅ تم إنشاء صورتك بنجاح! جاري الإرسال...")
            
            # إرسال الصورة
            if send_facebook_image(sender_id, image_url):
                send_facebook_message(sender_id, "🎨 هذه هي الصورة التي طلبتها! أتمنى أن تعجبك! 💫")
            else:
                send_facebook_message(sender_id, "⚠️ تم إنشاء الصورة ولكن هناك مشكلة في الإرسال. جرب مرة أخرى!")
        else:
            send_facebook_message(sender_id, "❌ عذراً، لم أتمكن من إنشاء الصورة. جرب مرة أخرى أو غيّر الوصف!")
        
        send_typing_indicator(sender_id, False)
    
    # تشغيل في thread منفصل لعدم تأخير الردود الأخرى
    thread = threading.Thread(target=generate_and_send)
    thread.daemon = True
    thread.start()

def extract_image_prompt(message_text):
    """استخراج وصف الصورة من الرسالة"""
    message_lower = message_text.lower()
    
    # إزالة الكلمات المفتاحية
    for keyword in IMAGE_KEYWORDS:
        message_lower = message_lower.replace(keyword, "")
    
    # تنظيف النص
    prompt = message_lower.strip()
    if not prompt or len(prompt) < 3:
        return None
    
    return prompt

def handle_message(sender_id, message):
    """معالجة الرسالة بشكل سريع"""
    # إرسال مؤشر الكتابة بسرعة
    send_typing_indicator(sender_id, True)
    
    # الحصول على نص الرسالة
    if 'text' not in message:
        send_facebook_message(sender_id, "أهلاً! يمكنني فهم الرسائل النصية وتوليد الصور حالياً 😊")
        send_typing_indicator(sender_id, False)
        return
    
    message_text = message['text']
    
    # البحث عن رد سريع أولاً
    quick_response = get_quick_response(message_text)
    if quick_response:
        send_facebook_message(sender_id, quick_response)
        send_typing_indicator(sender_id, False)
        return
    
    # التحقق من طلب توليد الصور
    message_lower = message_text.lower()
    is_image_request = any(keyword in message_lower for keyword in IMAGE_KEYWORDS)
    
    if is_image_request:
        prompt = extract_image_prompt(message_text)
        if prompt:
            send_facebook_message(sender_id, f"🎨 فهمت أنك تريد صورة عن: '{prompt}'")
            handle_image_generation(sender_id, prompt)
        else:
            send_facebook_message(sender_id, "❌ لم أستطع فهم ما تريد رسمه. رجاءً اشرح بالتفصيل! 💬")
        send_typing_indicator(sender_id, False)
        return
    
    # إذا كانت الرسالة عادية، استخدم الذكاء الاصطناعي السريع
    ai_response = generate_ai_response(message_text, sender_id)
    
    if ai_response == "image_generation_request":
        send_facebook_message(sender_id, "🎨 أرغب في إنشاء صورة لك! أخبرني ماذا تريد أن أرسم؟ 💫")
    else:
        send_facebook_message(sender_id, ai_response)
    
    send_typing_indicator(sender_id, False)

def keep_alive():
    """إبقاء البوت نشطاً على Render"""
    while True:
        print(f"🤖 البوت يعمل... {time.ctime()}")
        time.sleep(300)  # طباعة كل 5 دقائق

def poll_facebook_messages():
    """سحب الرسائل من الفيسبوك"""
    global processed_message_ids
    
    print("🚀 البوت يعمل الآن! ينتظر الرسائل...")
    print("🎨 المميزات: ردود سريعة + توليد الصور + ذكاء اصطناعي")
    
    # بدء thread إبقاء البوت نشطاً
    threading.Thread(target=keep_alive, daemon=True).start()
    
    while True:
        try:
            # الحصول على المحادثات الحديثة
            url = f"https://graph.facebook.com/v11.0/me/conversations?fields=messages{{message,from,id}}&limit=10&access_token={FACEBOOK_PAGE_ACCESS_TOKEN}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                for conversation in data.get('data', []):
                    messages = conversation.get('messages', {}).get('data', [])
                    
                    for msg in messages:
                        message_id = msg.get('id')
                        sender_id = msg.get('from', {}).get('id')
                        message_content = msg.get('message', '')
                        
                        if (message_id and message_id not in processed_message_ids and 
                            sender_id and message_content):
                            
                            print(f"📩 رسالة جديدة من {sender_id}: {message_content}")
                            
                            # معالجة الرسالة
                            message_data = {'text': message_content}
                            handle_message(sender_id, message_data)
                            
                            processed_message_ids.add(message_id)
                            
                            # تنظيف الذاكرة إذا كبرت
                            if len(processed_message_ids) > 1000:
                                processed_message_ids = set()
            
            # انتظار قصير بين الدورات
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ خطأ: {e}")
            time.sleep(5)

def start_bot():
    """بدء تشغيل البوت"""
    try:
        poll_facebook_messages()
    except KeyboardInterrupt:
        print("⏹️ إيقاف البوت...")
    except Exception as e:
        print(f"💥 خطأ كبير: {e}")

if __name__ == "__main__":
    start_bot()
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

# ذاكرة التخزين المؤقت للطلبات
@lru_cache(maxsize=100)
def cached_chat_request(message_hash):
    """تخزين مؤقت للطلبات المتكررة"""
    return None

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
            json=data,
            timeout=5
        )
        return response.status_code == 200
    except:
        return False

def wait_seconds(seconds):
    """انتظار سريع بدون استخدام time"""
    for i in range(seconds * 100000):
        pass

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
            wait_seconds(2 ** attempt)
    
    print("Failed to get access token")
    return None

def token_refresh_scheduler():
    global running
    while running:
        wait_seconds(600)  # 10 دقائق فقط لتحديث أسرع
        if running:
            print("🔄 Refreshing token...")
            get_access_token(force_refresh=True)

def send_chat_request(messages, retry_count=0):
    global current_access_token
    
    if not current_access_token:
        current_access_token = get_access_token()
        if not current_access_token:
            return None

    # تحقق من الذاكرة المؤقتة أولاً
    message_hash = hash(str(messages))
    cached_response = cached_chat_request(message_hash)
    if cached_response:
        return cached_response

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
        response = session.post(CHAT_API_URL, headers=headers, json=payload, timeout=10)  # وقت أقل
        if response.status_code == 401 and retry_count < 2:
            print("Token expired, refreshing...")
            current_access_token = get_access_token(force_refresh=True)
            if current_access_token:
                return send_chat_request(messages, retry_count + 1)
        
        if response.status_code == 200:
            result = response.json()
            # تخزين في الذاكرة المؤقتة
            cached_chat_request.cache_clear()  # تنظيف القديم
            return result
        return None
    except Exception as e:
        print(f"Chat request error: {e}")
        return None

def quick_transcribe_audio(audio_url):
    """نسخة سريعة من تحويل الصوت"""
    try:
        # تحميل الملف أولاً
        audio_response = session.get(audio_url, timeout=10)
        if audio_response.status_code != 200:
            return None
            
        # استخدام خدمة أسرع (اختياري)
        files = {'file': ('audio.mp3', audio_response.content, 'audio/mpeg')}
        response = session.post(
            "https://api.assemblyai.com/v2/upload",
            headers={"authorization": ASSEMBLYAI_API_KEY},
            files=files,
            timeout=10
        )
        
        if response.status_code == 200:
            upload_url = response.json().get('upload_url')
            data = {"audio_url": upload_url, "language_code": "ar"}
            
            transcript_response = session.post(
                "https://api.assemblyai.com/v2/transcript",
                json=data,
                headers={"authorization": ASSEMBLYAI_API_KEY, "content-type": "application/json"},
                timeout=10
            )
            
            if transcript_response.status_code == 200:
                transcript_id = transcript_response.json().get("id")
                # انتظار قصير للنتيجة
                for _ in range(10):
                    poll_response = session.get(
                        f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                        headers={"authorization": ASSEMBLYAI_API_KEY},
                        timeout=5
                    )
                    result = poll_response.json()
                    if result['status'] == 'completed':
                        return result['text']
                    elif result['status'] == 'error':
                        return None
                    wait_seconds(1)
        return None
    except:
        return None

def text_to_speech(text, sender_id):
    try:
        payload = {'text': text[:500]}  # تقليل النص للسرعة
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        
        response = session.post(TTS_SERVICE_URL, data=payload, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        
        result = response.json()
        if 'audio_url' in result:
            audio_response = session.get(result['audio_url'], timeout=10)
            if audio_response.status_code == 200:
                return audio_response.content
        return None
    except:
        return None

def process_image_fast(image_url, sender_id):
    """نسخة سريعة لمعالجة الصور"""
    global current_access_token
    
    try:
        send_typing_indicator(sender_id, True)
        
        image_response = session.get(image_url, timeout=10)
        if image_response.status_code != 200:
            send_facebook_message(sender_id, "❌ لم أتمكن من تحميل الصورة")
            return None
        
        # استخدام نموذج أسرع
        image_data = image_response.content
        boundary = "44cb511a-c1d4-4f51-a017-1352f87db948"
        headers = {
            "Host": "api.vulcanlabs.co",
            "x-auth-token": VISION_AUTH_TOKEN,
            "authorization": f"Bearer {current_access_token}",
            "x-vulcan-application-id": "com.smartwidgetlabs.chatgpt",
            "accept": "application/json",
            "content-type": f"multipart/form-data; boundary={boundary}",
        }
        
        data_part = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="data"\r\n\r\n'
            '{"model":"gpt-4o-mini","user":"F75FA09A4ECFF631","messages":[{"role":"user","content":"ما هذا وعلى ما يحتوي"}],"nsfw_check":true}\r\n'
        )
        
        image_part = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="images[]"; filename="image.jpg"\r\n'
            f"Content-Type: image/jpeg\r\n\r\n"
        )
        
        end_boundary = f"\r\n--{boundary}--\r\n"
        
        body = data_part.encode() + image_part.encode() + image_data + end_boundary.encode()
        
        response = session.post(VISION_API_URL, headers=headers, data=body, timeout=15)
        if response.status_code == 200:
            result = response.json()
            return next((choice.get('Message', {}).get('content', '') for choice in result.get('choices', [])), None)
        return None
    except Exception as e:
        print(f"Image processing error: {e}")
        return None
    finally:
        send_typing_indicator(sender_id, False)

def generate_images_fast(prompt):
    """نسخة سريعة لإنشاء الصور"""
    headers = {
        'Authorization': f'Bearer {GETIMG_API_KEY}',
        'Content-Type': 'application/json',
    }
    
    data = {
        'model': 'stable-diffusion-xl',  # نموذج أسرع
        'prompt': prompt,
        'negative_prompt': 'nude, naked',
        'response_format': 'url',
        'steps': 20,  # خطوات أقل للسرعة
        'height': 512,  # دقة أقل
        'width': 512
    }
    
    try:
        response = session.post(GETIMG_API_URL, headers=headers, json=data, timeout=20)
        if response.status_code == 200:
            result = response.json()
            return result.get('url')
    except:
        pass
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
            json=data,
            timeout=5
        )
    except:
        pass

def send_facebook_image(recipient_id, image_url):
    try:
        img_response = session.get(image_url, timeout=10)
        if img_response.status_code == 200:
            files = {
                'recipient': (None, json.dumps({"id": recipient_id})),
                'message': (None, json.dumps({"attachment": {"type": "image", "payload": {}}})),
                'access_token': (None, FACEBOOK_PAGE_ACCESS_TOKEN),
                'filedata': ('image.jpg', img_response.content, 'image/jpeg')
            }
            
            session.post(FACEBOOK_GRAPH_API_URL, files=files, timeout=10)
    except:
        pass

def send_facebook_audio(recipient_id, audio_bytes):
    try:
        files = {
            'recipient': (None, json.dumps({"id": recipient_id})),
            'message': (None, json.dumps({"attachment": {"type": "audio", "payload": {}}})),
            'access_token': (None, FACEBOOK_PAGE_ACCESS_TOKEN),
            'filedata': ('audio.mp3', audio_bytes, 'audio/mpeg')
        }
        
        session.post(FACEBOOK_GRAPH_API_URL, files=files, timeout=10)
    except:
        pass

def keep_alive_server():
    """إبقاء الخادم نشطاً لمنع إيقافه"""
    while running:
        try:
            # طلب بسيط لإبقاء الخادم نشطاً
            session.get("https://httpbin.org/get", timeout=5)
            print("🫀 Server heartbeat...")
        except:
            pass
        wait_seconds(300)  # كل 5 دقائق

def handle_message_fast(sender_id, message):
    """نسخة سريعة لمعالجة الرسائل"""
    
    # معالجة الملصقات
    if 'attachments' in message:
        attachments = message['attachments']['data']
        for attachment in attachments:
            if attachment.get('type') == 'sticker':
                send_facebook_message(sender_id, get_random_response(STICKER_RESPONSES))
                return
                
            mime_type = attachment.get('mime_type', '').lower()
            
            if 'image' in mime_type:
                image_url = attachment.get('url') or attachment.get('payload', {}).get('url')
                if image_url:
                    threading.Thread(target=process_image_fast, args=(image_url, sender_id)).start()
                return
                
            elif 'audio' in mime_type:
                audio_url = attachment.get('url') or attachment.get('payload', {}).get('url')
                if audio_url:
                    threading.Thread(target=process_audio_fast, args=(audio_url, sender_id)).start()
                return
    
    # معالجة النص والإيموجي
    if 'text' in message and message['text']:
        message_text = message['text']
        message_lower = message_text.lower()
        
        # ردود فورية
        if any(x in message_text for x in ['฿', '👍']) or 'جام ثاني' in message_lower:
            send_facebook_message(sender_id, "👍")
            return
            
        if any(x in message_text for x in ['ฯ', '﷼']):
            send_facebook_message(sender_id, "أنا بخير، الحمدلله وأنت ")
            return
            
        if any(message_lower.startswith(x) for x in ["من انت", "من أنت", "من مطورك"]):
            send_facebook_message(sender_id, "تم تطويري من قبل مطور بوتات")
            return
            
        if any(x in message_lower for x in ["اسرائيل", "إسرائيل", "israel"]):
            send_facebook_message(sender_id, "عذرا انا لا اعرف ما تقول انا اعرف دولة فلسطين 🇵🇸 عاصمتها القدس")
            return
        
        # ردود الإيموجي
        for emoji, responses in EMOJI_RESPONSES.items():
            if emoji in message_text:
                send_facebook_message(sender_id, get_random_response(responses))
                return
        
        # محادثة عادية
        threading.Thread(target=process_text_message, args=(sender_id, message_text)).start()

def process_audio_fast(audio_url, sender_id):
    """معالجة الصوت في thread منفصل"""
    send_facebook_message(sender_id, "⏳ جاري الاستماع...")
    text = quick_transcribe_audio(audio_url)
    
    if text:
        send_facebook_message(sender_id, f"📝 لقد قلت:\n{text}")
        process_text_message(sender_id, text)
    else:
        send_facebook_message(sender_id, "❌ لم أتمكن من فهم الصوت")

def process_text_message(sender_id, message_text):
    """معالجة الرسائل النصية"""
    send_typing_indicator(sender_id, True)
    
    conversation_history = user_conversations.get(sender_id, [])
    new_messages = conversation_history + [{"role": "user", "content": message_text}]
    
    response = send_chat_request(new_messages)
    send_typing_indicator(sender_id, False)
    
    if response:
        for choice in response.get('choices', []):
            if choice.get('Message', {}).get('function_call', {}).get('name') == 'create_ai_art':
                try:
                    args = json.loads(choice['Message']['function_call']['arguments'])
                    prompt = args.get('prompt', '')
                    if prompt:
                        threading.Thread(target=generate_and_send_images, args=(prompt, sender_id)).start()
                        return
                except:
                    pass
                break
        
        response_message = next(
            (choice.get('Message', {}).get('content', '') for choice in response.get('choices', [])),
            "عذرًا، حدث خطأ في معالجة طلبك."
        )
        send_facebook_message(sender_id, response_message)
        
        # تحويل النص إلى كلام في الخلفية
        threading.Thread(target=send_audio_response, args=(response_message, sender_id)).start()
        
        user_conversations[sender_id] = new_messages + [{"role": "assistant", "content": response_message}]
    else:
        send_facebook_message(sender_id, "❌ حدث خطأ في معالجة رسالتك")

def generate_and_send_images(prompt, sender_id):
    """إنشاء وإرسال الصور"""
    send_facebook_message(sender_id, "⏳ جاري إنشاء الصور...")
    send_typing_indicator(sender_id, True)
    
    # إنشاء صورتين فقط للسرعة
    urls = []
    for _ in range(2):
        url = generate_images_fast(prompt)
        if url:
            urls.append(url)
    
    send_typing_indicator(sender_id, False)
    
    for url in urls:
        send_facebook_image(sender_id, url)
    
    if urls:
        send_facebook_message(sender_id, "✅ تم إنشاء الصور!")
    else:
        send_facebook_message(sender_id, "❌ فشل في إنشاء الصور")

def send_audio_response(text, sender_id):
    """إرسال رد صوتي"""
    audio_bytes = text_to_speech(text, sender_id)
    if audio_bytes:
        send_facebook_audio(sender_id, audio_bytes)

def poll_facebook_messages_fast():
    """نسخة سريعة لسحب الرسائل"""
    global running, processed_message_ids
    
    # بدء الخدمات الخلفية
    threading.Thread(target=token_refresh_scheduler, daemon=True).start()
    threading.Thread(target=keep_alive_server, daemon=True).start()
    
    last_check = None
    
    while running:
        try:
            url = f"https://graph.facebook.com/v11.0/me/conversations?fields=messages.limit(5){{message,attachments,from,id}}&access_token={FACEBOOK_PAGE_ACCESS_TOKEN}"
            if last_check:
                url += f"&since={last_check}"
            
            response = session.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                for conversation in data.get('data', []):
                    for message in conversation['messages']['data']:
                        msg_id = message['id']
                        if msg_id not in processed_message_ids:
                            sender_id = message['from']['id']
                            message_content = message.get('message', {})
                            
                            if isinstance(message_content, str):
                                message_content = {'text': message_content}
                            
                            if 'attachments' in message:
                                message_content['attachments'] = message['attachments']
                            
                            print(f"📩 New message from {sender_id}")
                            handle_message_fast(sender_id, message_content)
                            processed_message_ids.add(msg_id)
                
                last_check = int(wait_seconds(1) * 1000)
            wait_seconds(1)  # فحص أسرع
        except Exception as e:
            print(f"Polling error: {e}")
            wait_seconds(2)

def stop_bot():
    global running
    running = False
    print("🛑 Bot is stopping...")

def main():
    try:
        print("🚀 Starting FAST Facebook Bot...")
        print("⚡ Optimized for speed and reliability")
        print("🫀 Keep-alive system activated")
        print("📱 Bot is now monitoring messages...")
        
        poll_facebook_messages_fast()
    except KeyboardInterrupt:
        stop_bot()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        stop_bot()

if __name__ == "__main__":
    main()    '😢': ['لا تحزن 😢', 'الله يعين', 'كل شيء سيكون بخير'],
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

def wait_seconds(seconds):
    """انتظار عدد من الثواني بدون استخدام time"""
    for i in range(seconds * 1000):
        # عملية حسابية بسيطة للانتظار
        _ = i * i

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
            wait_seconds(2 ** attempt)
    
    print("Failed to get access token")
    return None

def token_refresh_scheduler():
    global running
    while running:
        wait_seconds(900)  # انتظار 15 دقيقة
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
            wait_seconds(1)
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
                
                wait_seconds(1)  # انتظار ثانية بين الدورات
        except Exception as e:
            print(f"Polling error: {e}")
            wait_seconds(3)  # زيادة زمن الانتظار عند حدوث خطأ

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
