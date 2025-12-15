import requests

def translate_with_libre(text, target_lang="fr", source_lang="en"):
    url = "https://libretranslate.com/translate"
    response = requests.post(url, data={
        'q': text,
        'source': source_lang,
        'target': target_lang,
        'format': 'text'
    })

    if response.status_code == 200:
        return response.json()["translatedText"]
    else:
        return f"[Error] {response.text}"
