import re
import os
import time
from collections import defaultdict
from modules.module import Module
from groq import Groq

class AIzen(Module):
    def __init__(self, bot):
        super().__init__(bot)
        
        # Groq API key - .env dosyasından veya environment variable'dan al
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            print("⚠️  UYARI: GROQ_API_KEY bulunamadı!")
            print("   Lütfen environment variable olarak ayarlayın:")
            print("   1. https://console.groq.com adresinden ücretsiz API key alın")
            print("   2. Windows: set GROQ_API_KEY=your-api-key-here")
            print("   3. Linux/Mac: export GROQ_API_KEY=your-api-key-here")
        
        self.client = Groq(api_key=api_key) if api_key else None
        
        # Owner şifresi
        self.owner_password = os.getenv('OWNER_PASSWORD')
        
        # Şifre bekleyen kullanıcılar (user_id: user_name)
        self.pending_password = {}
        
        # Doğrulanmış owner'lar (user_id set)
        self.authenticated_owners = set()
        
        # İlk kontrol yapıldı mı? (sadece bir kere çalışması için)
        self.initial_check_done = False
        
        # Konuşma geçmişini sakla (her kullanıcı için ayrı)
        self.conversation_history = {}
        
        # Maksimum conversation history uzunluğu
        self.max_history = 10
        
        # Rate limiting (user_id: [timestamp, timestamp, ...])
        self.rate_limit_tracker = defaultdict(list)
        self.max_requests_per_minute = 5
        
        # İstatistikler
        self.stats = {
            'total_messages': 0,
            'total_users': set(),
            'start_time': time.time(),
            'user_message_count': defaultdict(int)
        }
        
        # Son aktivite zamanı (auto-clear için)
        self.last_activity = defaultdict(lambda: time.time())
        self.inactivity_timeout = 3600  # 1 saat
        
        # AI personality
        self.system_prompt = """Sen AI-zen, rahat ve samimi bir arkadaşsın. Normal bi insan gibi konuş, çok basit ve kısa.

KURALLAR:
1. Maksimum 100 karakter! Kesinlikle aşma.
2. Minimum 10 karakter! Çok kısa cevaplar yasak.
3. ASLA SORU SORMA! Hiçbir şekilde karşı soru sorma. Soru kelimesi bile kullanma.
4. ASLA "sabahları", "günler", "hoş geldin" gibi klişe ifadeler kullanma.
5. Emoji az kullan (max 1-2 tane).
6. Mükemmel Türkçe, günlük dil, argo serbest.

DOĞRU CEVAP ÖRNEKLERİ:
"naber" → "iyiyim ya" / "iyi kanka" / "iyidir abi" / "idare eder"
"nasılsın" → "iyiyim ya" / "fena değil" / "idare eder kanka" / "eh işte"
"napıyosun" → "takılıyom burada" / "öyle işte" / "hiç boş boş" / "redditte takılıyom"
"görüşürüz" → "görüşürüz 👋" / "hadi bay" / "görüşürüz kanka" / "bayyy"
"iyi günler" → "sana da" / "eyvallah" / "sağol" / "sağolasın"
"teşekkürler" → "rica ederim" / "np" / "sorun değil" / "önemli değil"
"çok sıkıldım" → "valla ya" / "he ya normal" / "geçer artık" / "ben de sıkılıyom"

YANLIŞ ÖRNEKLER (YAPMA):
❌ "in!" (çok kısa)
❌ "sabahı iyi olsun" (klişe)
❌ "ne yapıyorsun?" (SORU YASAK)
❌ "sen nasılsın" (SORU YASAK)
❌ "ne yaparız lan" (SORU YASAK, soru işareti olmasa da)
❌ "kahve içtin mi?" (SORU YASAK)
❌ "güzel günler dilerim" (yapay)
❌ "neden sıkıldın" (SORU YASAK)
❌ "nasıl geçer" (SORU YASAK)

Cevabın sadece ifade olsun, açıklama değil. Bağlama uygun, doğal ve kesinlikle soru içermeyen cevaplar ver."""
        
        # Groq modelleri: llama-3.1-8b-instant, llama-3.3-70b-versatile, mixtral-8x7b-32768
        self.model = "llama-3.3-70b-versatile"  # Daha güçlü model, daha doğal cevaplar
        self.temperature = 0.7  # Daha tutarlı cevaplar için optimize edildi

    @property
    def cmds(self):
        cmd_dict = {
            'handle_mention': r'@AI-zen',  # @AI-zen ile etiketlendiğinde
            'help_cmd': r'!yardım|!help',
            'time_cmd': r'!saat',
            'forget_me': r'!unutbeni',
            'stats_cmd': r'!stats',
            'clear_cmd': r'!clear @?(\w+)',
            'model_cmd': r'!model (\S+)',
            'temp_cmd': r'!temp ([0-9.]+)',
        }
        return cmd_dict
    
    def handler(self, msg):
        """Override handler to catch mentions, joins, leaves, room_profile, and special DMs"""
        import popyo
        
        # İlk mesaj geldiğinde (herhangi bir tip olabilir) kullanıcıları kontrol et
        if not self.initial_check_done:
            self.initial_check_done = True
            self.check_existing_aizen_users()
        
        # Room profile mesajını handle et
        if msg.type == popyo.Message_Type.room_profile:
            self.check_existing_aizen_users()
            return
        
        # Join mesajlarını handle et
        if msg.type == popyo.Message_Type.join:
            self.handle_join(msg)
            return
        
        # Leave mesajlarını handle et
        if msg.type == popyo.Message_Type.leave:
            self.handle_leave(msg)
            return
        
        # DM'leri handle et (sadece şifre kontrolü için)
        if msg.type == popyo.Message_Type.dm:
            self.handle_dm_password(msg)
            return
        
        # Bot kendi mesajlarını işlemesin (sonsuz döngü önlemi)
        bot_user_id = self.bot.own_user.id if self.bot.own_user else None
        sender_user_id = msg.user.id if hasattr(msg, 'user') and msg.user else None
        if bot_user_id and sender_user_id == bot_user_id:
            return  # Bot kendi mesajlarını görmezden gel
        
        # Otherwise use normal command matching
        super().handler(msg)
    
    def handle_mention(self, msg):
        """@AI-zen ile etiketlendiğinde çağrılır"""
        # Bot kendi mesajlarına cevap vermesin!
        bot_user_id = self.bot.own_user.id if self.bot.own_user else None
        sender_user_id = msg.user.id if hasattr(msg, 'user') and msg.user else None
        
        if bot_user_id and sender_user_id == bot_user_id:
            return  # Bot kendine cevap vermesin
        
        if not self.client:
            self.bot.send("⚠️ Groq API key ayarlanmamış! https://console.groq.com")
            return
        
        # @AI-zen'i mesajdan çıkar
        question = re.sub(r'@AI-zen\s*', '', msg.message, flags=re.IGNORECASE).strip()
        
        if not question:
            self.bot.send("Evet? Nasıl yardımcı olabilirim? 😊")
            return
        
        # "Sen kimsin" gibi sorulara özel cevap
        if re.search(r'(sen kim(sin)?|kim olduğun|ne(sin)?|nedir(sin)?|kendin(i )?(tanıt|anlat)|bot mu(sun)?)', question, re.IGNORECASE):
            user_name = msg.user.name if hasattr(msg, 'user') and msg.user else "Bilinmeyen"
            intro = f"@{user_name} Ben @aizen'in AI botuyum! 🤖 Sohbet ederiz, !yardım yaz 😊"
            self.bot.send(intro)
            return
        
        # Kullanıcı bilgisi
        user_name = msg.user.name if hasattr(msg, 'user') and msg.user else "Bilinmeyen"
        user_id = msg.user.id if hasattr(msg, 'user') and msg.user else "unknown"
        
        # Rate limit kontrolü
        if not self.check_rate_limit(user_id):
            self.bot.send(f"@{user_name} ⏰ Yavaşla! Dakikada max {self.max_requests_per_minute} soru sorabilirsin.")
            return
        
        # İstatistik güncelle
        self.stats['total_messages'] += 1
        self.stats['total_users'].add(user_id)
        self.stats['user_message_count'][user_id] += 1
        self.last_activity[user_id] = time.time()
        
        # Eski geçmişi temizle
        self.cleanup_old_history()
        
        # Cevap üret
        response = self.get_ai_response(question, user_id, user_name)
        
        # Cevabı gönder ve kullanıcıyı etiketle
        self.bot.send(f"@{user_name} {response}")
    
    def handle_dm(self, msg):
        """Direct mesajlara cevap verir"""
        if not self.client:
            self.bot.dm(msg.user.id, "⚠️ Groq API key ayarlanmamış!")
            return
        
        question = msg.message.strip()
        user_name = msg.user.name if hasattr(msg, 'user') and msg.user else "Bilinmeyen"
        user_id = msg.user.id if hasattr(msg, 'user') and msg.user else "unknown"
        
        # Cevap üret
        response = self.get_ai_response(question, user_id, user_name)
        
        # Private mesaj olarak cevapla
        self.bot.dm(msg.user.id, response)
    
    def get_ai_response(self, question, user_id, user_name):
        """Groq API ile cevap üretir"""
        try:
            # Güncel tarih ve saat bilgisini al (Türkiye saati)
            import datetime
            
            # UTC+3 için Türkiye timezone
            turkey_offset = datetime.timezone(datetime.timedelta(hours=3))
            now = datetime.datetime.now(turkey_offset)
            
            date_str = now.strftime('%d %B %Y')  # 22 February 2026
            time_str = now.strftime('%H:%M')     # 03:00
            day_name = now.strftime('%A')        # Saturday
            
            # Türkçe ay ve gün isimleri
            months_tr = {
                'January': 'Ocak', 'February': 'Şubat', 'March': 'Mart', 'April': 'Nisan',
                'May': 'Mayıs', 'June': 'Haziran', 'July': 'Temmuz', 'August': 'Ağustos',
                'September': 'Eylül', 'October': 'Ekim', 'November': 'Kasım', 'December': 'Aralık'
            }
            days_tr = {
                'Monday': 'Pazartesi', 'Tuesday': 'Salı', 'Wednesday': 'Çarşamba',
                'Thursday': 'Perşembe', 'Friday': 'Cuma', 'Saturday': 'Cumartesi', 'Sunday': 'Pazar'
            }
            
            for eng, tr in months_tr.items():
                date_str = date_str.replace(eng, tr)
            for eng, tr in days_tr.items():
                day_name = day_name.replace(eng, tr)
            
            # Context bilgisi
            time_context = f"\n\n[GÜNCEL BİLGİ - Türkiye saati: {time_str}, Tarih: {date_str} {day_name}]"
            
            # Kullanıcı için conversation history oluştur
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            
            # Kullanıcı mesajını history'e ekle (tarih/saat context ile)
            self.conversation_history[user_id].append({
                "role": "user",
                "content": question + time_context
            })
            
            # History çok uzunsa eski mesajları sil (system prompt hariç)
            if len(self.conversation_history[user_id]) > self.max_history * 2:
                self.conversation_history[user_id] = self.conversation_history[user_id][-(self.max_history * 2):]
            
            # Groq API çağrısı (çok hızlı!)
            messages = [
                {"role": "system", "content": self.system_prompt}
            ] + self.conversation_history[user_id]
            
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=150,  # AI'ın düşünme alanı (cevap yine 100 char'la sınırlı)
                temperature=self.temperature,
            )
            
            response = completion.choices[0].message.content.strip()
            
            # Debug: AI'ın ürettiği cevabı göster
            print(f"🤖 AI Response for {user_name}: '{response}'")
            
            # Cevap validasyonu
            is_valid, reason = self.validate_response(response)
            
            if not is_valid:
                print(f"⚠️  INVALID RESPONSE: {reason}")
                # Fallback cevaplar (nasılsın/naber sorularına uygun)
                fallbacks = [
                    "iyiyim ya 😊",
                    "fena değil kanka",
                    "idare eder 👍",
                    "iyidir abi",
                    "eh işte",
                    "normal işte",
                    "iyi iyi",
                    "iyiyim valla"
                ]
                response = fallbacks[hash(user_id) % len(fallbacks)]
                print(f"🔄 Fallback kullanıldı: '{response}'")
            
            # AI cevabını history'e ekle
            self.conversation_history[user_id].append({
                "role": "assistant",
                "content": response
            })
            
            return response
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Groq API hatası: {error_msg}")
            
            if "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower():
                return "⚠️ API key hatası. https://console.groq.com adresinden key alın."
            elif "rate_limit" in error_msg.lower():
                return "⚠️ Rate limit aşıldı. Biraz bekleyin ve tekrar deneyin."
            else:
                return f"⚠️ Üzgünüm, bir hata oluştu: {error_msg[:100]}"
    
    def handle_join(self, msg):
        """Kullanıcı odaya katıldığında çağrılır"""
        if not msg.user:
            return
        
        user_name = msg.user.name
        user_name_lower = user_name.lower()
        user_id = msg.user.id
        
        # Bot'un kendi user ID'sini al
        bot_user_id = self.bot.own_user.id if self.bot.own_user else None
        
        # Bot kendine selam vermesin!
        if user_id == bot_user_id:
            return
        
        # Odaya katılan kullanıcıyı selamla
        self.bot.send(f"@{user_name} Hoş geldin! 👋😊")
        
        # "aizen" kullanıcı adıyla gelen kullanıcılara şifre sor
        if user_name_lower == "aizen":
            if user_id not in self.authenticated_owners and user_id not in self.pending_password:
                self.pending_password[user_id] = user_name
                self.bot.dm(user_id, "🔐 Sen gerçek aizen misin? Şifreni söyle!")
                print(f"🔐 Şifre soruldu: {user_name}")
    
    def handle_leave(self, msg):
        """Kullanıcı odadan ayrıldığında çağrılır"""
        if not msg.user:
            return
        
        user_id = msg.user.id
        
        # Kullanıcı ayrılıyorsa authenticated listeden çıkar
        if user_id in self.authenticated_owners:
            self.authenticated_owners.remove(user_id)
            print(f"👋 Owner ayrıldı: {msg.user.name} (ID: {user_id})")
        
        # Pending password listesinden de çıkar
        if user_id in self.pending_password:
            del self.pending_password[user_id]
    
    def check_existing_aizen_users(self):
        """Odada zaten var olan 'aizen' kullanıcılarını kontrol eder"""
        if not self.bot.room or not self.bot.room.users:
            return
        
        # Bot'un kendi user ID'sini al
        bot_user_id = self.bot.own_user.id if self.bot.own_user else None
        
        # Odadaki tüm kullanıcıları kontrol et
        for user_id, user in self.bot.room.users.items():
            if user and hasattr(user, 'name'):
                # Bot kendine şifre sormamalı!
                if user_id == bot_user_id:
                    continue
                
                if user.name.lower() == "aizen":
                    # Bu kullanıcıya daha önce şifre sorulmadıysa ve doğrulanmadıysa sor
                    if user_id not in self.pending_password and user_id not in self.authenticated_owners:
                        self.pending_password[user_id] = user.name
                        self.bot.dm(user_id, "🔐 Sen gerçek aizen misin? Şifreni söyle!")
                        print(f"🔐 Şifre soruldu: {user.name}")
    
    def handle_dm_password(self, msg):
        """DM'lerde şifre kontrolü yapar"""
        if not msg.user:
            return
        
        user_id = msg.user.id
        user_name = msg.user.name
        
        # Eğer bu kullanıcı şifre bekliyorsa
        if user_id in self.pending_password:
            password_attempt = msg.message.strip()
            
            if password_attempt == self.owner_password:
                # Doğru şifre!
                self.bot.dm(user_id, "✅ Hoş geldin baba! 👑")
                # Herkese görünsün
                self.bot.send(f"✅ Hoş geldin @{user_name} baba! 👑🎉")
                self.authenticated_owners.add(user_id)  # Doğrulanmış listeye ekle
                del self.pending_password[user_id]
                print(f"✅ Owner doğrulandı: {user_name} (ID: {user_id})")
            else:
                # Yanlış şifre!
                self.bot.dm(user_id, "❌ Sen babam değilsin, dolandırıcı! 🚫")
                # Herkese görünsün
                self.bot.send(f"🚨 @{user_name} SEN GERÇEK AIZEN DEĞİLSİN PİÇ KURUSU! 🚨")
                del self.pending_password[user_id]
                print(f"⚠️  Yanlış şifre: {user_name}")
        else:
            # Şifre beklemeyen birisinden DM geldi, görmezden gel
            pass
    
    # ==================== YENİ KOMUTLAR ====================
    
    def help_cmd(self, msg):
        """Yardım komutu"""
        help_text = """📖 AI-zen Kullanım Rehberi:
@AI-zen [soru] - Bana soru sor
!yardım - Bu mesajı göster
!saat - Güncel saat
!unutbeni - Konuşma geçmişini sil"""
        self.bot.send(help_text)
    
    def time_cmd(self, msg):
        """Saat komutu"""
        import datetime
        turkey_offset = datetime.timezone(datetime.timedelta(hours=3))
        now = datetime.datetime.now(turkey_offset)
        
        time_str = now.strftime('%H:%M')
        date_str = now.strftime('%d %B %Y')
        day_name = now.strftime('%A')
        
        # Türkçe çeviri
        months_tr = {'January': 'Ocak', 'February': 'Şubat', 'March': 'Mart', 'April': 'Nisan',
                     'May': 'Mayıs', 'June': 'Haziran', 'July': 'Temmuz', 'August': 'Ağustos',
                     'September': 'Eylül', 'October': 'Ekim', 'November': 'Kasım', 'December': 'Aralık'}
        days_tr = {'Monday': 'Pazartesi', 'Tuesday': 'Salı', 'Wednesday': 'Çarşamba',
                   'Thursday': 'Perşembe', 'Friday': 'Cuma', 'Saturday': 'Cumartesi', 'Sunday': 'Pazar'}
        
        for eng, tr in months_tr.items():
            date_str = date_str.replace(eng, tr)
        for eng, tr in days_tr.items():
            day_name = day_name.replace(eng, tr)
        
        self.bot.send(f"🕐 Saat: {time_str} | 📅 {date_str} {day_name}")
    
    def forget_me(self, msg):
        """Kullanıcının kendi geçmişini silmesini sağlar"""
        user_id = msg.user.id if msg.user else None
        user_name = msg.user.name if msg.user else "Bilinmeyen"
        
        if user_id and user_id in self.conversation_history and len(self.conversation_history[user_id]) > 0:
            del self.conversation_history[user_id]
            self.bot.send(f"@{user_name} 🗑️ Konuşma geçmişin silindi!")
        else:
            self.bot.send(f"@{user_name} Zaten kayıtlı bir geçmişin yok.")
    
    def stats_cmd(self, msg):
        """İstatistikler (Sadece owner)"""
        user_id = msg.user.id if msg.user else None
        
        if user_id not in self.authenticated_owners:
            self.bot.send("🚫 Bu komutu sadece owner kullanabilir!")
            return
        
        uptime = int(time.time() - self.stats['start_time'])
        hours = uptime // 3600
        minutes = (uptime % 3600) // 60
        
        stats_text = f"""📊 Bot İstatistikleri:
✅ Toplam mesaj: {self.stats['total_messages']}
👥 Toplam kullanıcı: {len(self.stats['total_users'])}
⏰ Uptime: {hours}s {minutes}d"""
        self.bot.send(stats_text)
    
    def clear_cmd(self, msg):
        """Bir kullanıcının geçmişini temizle (Sadece owner)"""
        user_id = msg.user.id if msg.user else None
        
        if user_id not in self.authenticated_owners:
            self.bot.send("🚫 Bu komutu sadece owner kullanabilir!")
            return
        
        target_name = msg.groups[0] if msg.groups else None
        if target_name:
            # Basit clear (isime göre değil, owner sonra geliştirebilir)
            self.bot.send(f"🗑️ Komut alındı ama user ID gerekli. Şimdilik !unutbeni kullanın.")
        else:
            self.bot.send("Kullanım: !clear @kullanıcı")
    
    def model_cmd(self, msg):
        """AI modelini değiştir (Sadece owner)"""
        user_id = msg.user.id if msg.user else None
        
        if user_id not in self.authenticated_owners:
            self.bot.send("🚫 Bu komutu sadece owner kullanabilir!")
            return
        
        new_model = msg.groups[0] if msg.groups else None
        if new_model:
            self.model = new_model
            self.bot.send(f"🤖 Model değiştirildi: {new_model}")
        else:
            self.bot.send("Kullanım: !model llama-3.1-8b-instant")
    
    def temp_cmd(self, msg):
        """Temperature ayarla (Sadece owner)"""
        user_id = msg.user.id if msg.user else None
        
        if user_id not in self.authenticated_owners:
            self.bot.send("🚫 Bu komutu sadece owner kullanabilir!")
            return
        
        temp_str = msg.groups[0] if msg.groups else None
        if temp_str:
            try:
                new_temp = float(temp_str)
                if 0.0 <= new_temp <= 2.0:
                    self.temperature = new_temp
                    self.bot.send(f"🌡️ Temperature: {new_temp}")
                else:
                    self.bot.send("Temperature 0.0-2.0 arası olmalı!")
            except ValueError:
                self.bot.send("Geçersiz değer!")
        else:
            self.bot.send("Kullanım: !temp 0.8")
    
    # ==================== YARDIMCI FONKSİYONLAR ====================
    
    def check_rate_limit(self, user_id):
        """Rate limit kontrolü"""
        now = time.time()
        
        # Eski istekleri temizle (60 saniyeden eski)
        self.rate_limit_tracker[user_id] = [
            timestamp for timestamp in self.rate_limit_tracker[user_id]
            if now - timestamp < 60
        ]
        
        # Limit kontrolü
        if len(self.rate_limit_tracker[user_id]) >= self.max_requests_per_minute:
            return False
        
        # Yeni isteği kaydet
        self.rate_limit_tracker[user_id].append(now)
        return True
    
    def cleanup_old_history(self):
        """1 saatten uzun süredir aktif olmayan kullanıcıların geçmişini temizle"""
        now = time.time()
        to_remove = []
        
        for user_id, last_time in self.last_activity.items():
            if now - last_time > self.inactivity_timeout:
                to_remove.append(user_id)
        
        for user_id in to_remove:
            if user_id in self.conversation_history:
                del self.conversation_history[user_id]
            del self.last_activity[user_id]
    
    def validate_response(self, response):
        """AI cevabını validate et, sorunlu ise False döner"""
        response_lower = response.lower()
        
        # 1. Çok kısa cevaplar
        if len(response) < 10:
            return False, f"Too short ({len(response)} chars)"
        
        # 2. Çok uzun cevaplar (chunking'i önle)
        if len(response) > 100:
            return False, f"Too long ({len(response)} chars)"
        
        # 3. Soru içeren cevaplar (? karakteri veya soru kelimeleri)
        if '?' in response:
            return False, "Contains question mark"
        
        # Soru kelimeleri kontrolü (başta veya ortada)
        question_words = ['ne yap', 'nasıl', 'neden', 'niçin', 'niye', 'kim', 'nerede', 'ne zaman', 'kaç', 'hangi']
        for word in question_words:
            if word in response_lower:
                return False, f"Contains question word: '{word}'"
        
        # 4. Yasaklı kelimeler
        banned_phrases = [
            'sabahları', 'sabahı', 'güzel günler', 'hoş günler', 'iyi günler',
            'ne yapıyorsun', 'kahve', 'çay', 'yemek yedin', 'ne yaparız'
        ]
        for phrase in banned_phrases:
            if phrase in response_lower:
                return False, f"Contains banned phrase: '{phrase}'"
        
        # 5. Çok kısa tek kelimeler (emoji hariç)
        text_only = ''.join(c for c in response if c.isalnum() or c.isspace())
        if len(text_only.strip()) < 5:
            return False, "Text too short (excluding emoji)"
        
        return True, "OK"
    
    def clear_history(self, user_id):
        """Belirli bir kullanıcının conversation history'sini temizler"""
        if user_id in self.conversation_history:
            del self.conversation_history[user_id]
            print(f"🗑️  Cleared history for user: {user_id}")
