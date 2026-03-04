"""Gemini API entegrasyonu test scripti - çalıştıktan sonra silinebilir"""
import os
from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import types as genai_types

api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print('HATA: GEMINI_API_KEY .env dosyasında bulunamadı!')
    exit(1)

print(f'API Key: {api_key[:10]}...{api_key[-4:]}')

client = genai.Client(api_key=api_key)

system_prompt = """Sen AI-zen, rahat ve samimi bir arkadaşsın. Normal bir insan gibi konuş, doğal ve akıcı.
KURALLAR:
1. Cevapların 15-250 karakter arası olsun. Kısa ama anlamlı ve tam cümle olsun.
2. ASLA SORU SORMA! Hiçbir şekilde karşı soru yok. Sadece ifade et, bildir, yorum yap.
3. ASLA klişe ifadeler kullanma.
4. Emoji az kullan (max 1-2 tane).
5. Tam cümle kur, anlamlı cevap ver. Tek kelime yeterli değil.
6. Mükemmel Türkçe, günlük dil, argo serbest."""

cfg = genai_types.GenerateContentConfig(
    system_instruction=system_prompt,
    temperature=0.8,
    max_output_tokens=2048,
    thinking_config=genai_types.ThinkingConfig(
        thinking_budget=1024  # Düşünme token bütçesi
    ),
)

# Test 1: Basit sohbet
print('\n=== TEST 1: Basit sohbet ===')
r1 = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[genai_types.Content(role='user', parts=[genai_types.Part(text='naber nasılsın')])],
    config=cfg,
)
print(f'Cevap: {r1.text.strip()}')
print(f'Len: {len(r1.text.strip())} karakter')

# Test 2: Conversation history (karakter tutarlılığı)
print('\n=== TEST 2: Conversation history ===')
r2 = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[
        genai_types.Content(role='user', parts=[genai_types.Part(text='sen kimsin')]),
        genai_types.Content(role='model', parts=[genai_types.Part(text="Ben AI-zen, aizen'in AI botuyum! Sohbet ederiz 😊")]),
        genai_types.Content(role='user', parts=[genai_types.Part(text='bugün çok yorgunum ya')]),
    ],
    config=cfg,
)
print(f'Cevap: {r2.text.strip()}')
print(f'Len: {len(r2.text.strip())} karakter')

# Test 3: Zaman context
print('\n=== TEST 3: Zaman context ===')
r3 = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[
        genai_types.Content(role='user', parts=[genai_types.Part(text='saat kaç şimdi\n\n[GÜNCEL BİLGİ - Türkiye saati: 14:30, Tarih: 24 Şubat 2026 Salı]')]),
    ],
    config=cfg,
)
print(f'Cevap: {r3.text.strip()}')

# Test 4: Soru sormama kontrolü (3 deneme)
print('\n=== TEST 4: Soru sormama kontrolü (3 deneme) ===')
test_msgs = ['canım sıkılıyor', 'bi film izliyom', 'bugün hava güzel']
for test in test_msgs:
    r = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=[genai_types.Content(role='user', parts=[genai_types.Part(text=test)])],
        config=cfg,
    )
    cevap = r.text.strip()
    has_q = '?' in cevap
    status = 'UYARI' if has_q else 'OK'
    print(f'  "{test}" -> "{cevap}" [soru:{status}]')

# Test 5: Hava durumu context
print('\n=== TEST 5: Hava durumu context ===')
r5 = client.models.generate_content(
    model='gemini-2.5-flash',
    contents=[
        genai_types.Content(role='user', parts=[genai_types.Part(text="istanbul hava durumu nasıl\n\n[GÜNCEL BİLGİ - Türkiye saati: 15:00, Tarih: 24 Şubat 2026 Salı]\n\n[HAVA DURUMU - Istanbul: 12°C, Hissedilen: 9°C, Parçalı bulutlu, Nem: %72, Rüzgar: 15 km/h]")])
    ],
    config=cfg,
)
print(f'Cevap: {r5.text.strip()}')

print('\n✅ TÜM TESTLER TAMAMLANDI!')
print(f'Provider: gemini | Model: gemini-2.5-flash')
