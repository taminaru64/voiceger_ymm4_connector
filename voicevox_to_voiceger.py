import uvicorn
import httpx
import urllib.parse
from fastapi import FastAPI, Request, Query
from fastapi.responses import Response
from typing import Dict, Any
import os
import json

# FastAPIアプリケーションのインスタンスを作成
app = FastAPI()

# Voiceger API v2の設定
VOICEGER_API_URL = "http://127.0.0.1:9880/tts"

# 参照音声ファイルのベースパスと拡張子
COMMON_PROMPT_TEXT = "私はいつもミネラルウォーターを持ち歩いています。"
VOICEGER_LANGUAGE = "ja" #この中から選べます"auto", "auto_yue", "en", "zh", "ja", "yue", "ko", "all_zh", "all_ja", "all_yue", "all_ko"

# 各スタイルに対応する参照音声とテキストを設定
STYLES = {
    0: { "name": "ノーマル", "prompt_text": COMMON_PROMPT_TEXT, "file_name": "reference_audios/01_ref_emoNormal026.wav" },
    1: { "name": "あまあま", "prompt_text": COMMON_PROMPT_TEXT, "file_name": "reference_audios/02_ref_emoAma026.wav" },
    2: { "name": "ツンツン", "prompt_text": COMMON_PROMPT_TEXT, "file_name": "reference_audios/03_ref_emoTsun026.wav" },
    3: { "name": "セクシー", "prompt_text": COMMON_PROMPT_TEXT, "file_name": "reference_audios/04_ref_emoSexy026.wav" },
    4: { "name": "ささやき", "prompt_text": COMMON_PROMPT_TEXT, "file_name": "reference_audios/05_ref_emoSasa026.wav" },
    5: { "name": "ヒソヒソ", "prompt_text": COMMON_PROMPT_TEXT, "file_name": "reference_audios/06_ref_emoMurmur026.wav" },
    6: { "name": "ヘロヘロ", "prompt_text": COMMON_PROMPT_TEXT, "file_name": "reference_audios/07_ref_emoHero026.wav" },
    7: { "name": "なみだめ", "prompt_text": COMMON_PROMPT_TEXT, "file_name": "reference_audios/08_ref_emoSobbing026.wav" },
}

# YMM4から受け取ったテキストを一時的に保存する変数
last_text = ""

# VOICEVOX互換のダミースピーカー情報
@app.get("/speakers")
async def get_speakers():
    """YMM4がスピーカー情報を取得するためのエンドポイント"""
    styles_list = [{"name": style["name"], "id": id} for id, style in STYLES.items()]
    return [
        {
            "name": "Voicegerずんだもん",
            "speaker_uuid": "f290518f-a90a-4712-9c40-1a7428f6d6c8",
            "styles": styles_list
        },
    ]

# YMM4がスピーカーの詳細情報を取得するエンドポイント
@app.get("/speaker_info")
async def get_speaker_info(speaker_uuid: str):
    """YMM4がスピーカー詳細情報を取得するためのエンドポイント"""
    if speaker_uuid == "f290518f-a90a-4712-9c40-1a7428f6d6c8":
        return {
            "speaker_uuid": "f290518f-a90a-4712-9c40-1a7428f6d6c8",
            "name": "Voicegerずんだもん",
            "speaker_info": {
                "policy": "APIを通じて利用",
                "portrait_url": "",
                "terms_of_service": "利用規約はVoicegerに準じます"
            }
        }
    return Response(status_code=404)

# YMM4がスピーカー初期化を確認するエンドポイント
@app.get("/is_initialized_speaker")
async def is_initialized_speaker(speaker: int):
    """YMM4がスピーカーの初期化状態を確認するためのエンドポイント"""
    if speaker == 0:
        return True
    return False

# YMM4がテキストからクエリを生成するエンドポイント
@app.post("/accent_phrases")
async def accent_phrases(text: str = Query(...)):
    """YMM4からのテキストを受け取り、ダミーのアクセントフレーズを返すエンドポイント"""
    global last_text
    last_text = text
    return [{"moras": [], "accent": 0, "pause_mora": None}]

# カタカナをひらがなに変換する関数
def convert_katakana_to_hiragana(text: str) -> str:
    """カタカナをひらがなに変換する関数"""
    return "".join([chr(ord(c) - 96) if 'ァ' <= c <= 'ン' else c for c in text])

# 修正: VOICEVOXの標準形式に合わせたaudio_queryレスポンス
@app.post("/audio_query")
async def audio_query(text: str = Query(...)):
    """YMM4からのテキストを受け取り、VOICEVOX互換の音声クエリを返すエンドポイント"""
    global last_text
    last_text = text
    # VOICEVOX互換のダミーレスポンス
    dummy_query = {
        "text": text,
        "speedScale": 100,
        "pitchScale": 100,
        "intonationScale": 100,
        "volumeScale": 1.0,
        "prePhonemeLength": 0.1,
        "postPhonemeLength": 0.1,
        "outputSamplingRate": 24000,
        "outputStereo": False,
        "kana": ""
    }
    return dummy_query

# YMM4が音声合成を要求するエンドポイント
@app.post("/synthesis")
async def synthesis(request: Request, speaker: int):
    """Voiceger APIを使用して音声合成を行うエンドポイント"""
    global last_text

    # YMM4から送られてくるJSONボディを解析
    try:
        body = await request.json()
        
        # VOICEVOX互換のパラメータを取得
        # Voiceger APIのパラメータにマッピング

        # 読み上げ速度：速度（0.5から2.0をそのまま）
        speed_factor = body.get("speedScale", 1.0)
        print(f"speed_factor:{speed_factor}")
        # 抑揚：ためる部分（0.0から2.0を0.5から2.0にマッピング）
        temperature = (body.get("intonationScale", 1.0) * (1.5 / 2.0) + 0.5)
        print(f"temperature:{temperature}")
        # 声の高さ：シード（-0.15から0.15の範囲を-1から29の整数にマッピング）
        seed = int((body.get("pitchScale", 0.0) + 0.15) * 100 - 1)
        print(f"seed:{seed}")

    except json.JSONDecodeError:
        return Response(content="Invalid JSON body", status_code=400)

    text_to_synthesize = last_text
    if not text_to_synthesize:
        return Response(content="No text provided from audio_query.", status_code=400)

    # YMM4から送られてきたカタカナのテキストをひらがなに変換
    processed_text = convert_katakana_to_hiragana(text_to_synthesize)

    style_info = STYLES.get(speaker)
    if not style_info:
        return Response(content=f"Invalid speaker ID: {speaker}", status_code=400)

    # Voiceger API v2に送信するパラメータ
    voiceger_params = {
        "text": processed_text,
        "text_lang": VOICEGER_LANGUAGE,
        "ref_audio_path": style_info["file_name"],
        "prompt_text": style_info["prompt_text"],
        "prompt_lang": VOICEGER_LANGUAGE,
        "top_k": 5,
        "top_p": 1,
        "temperature": temperature,
        "text_split_method": "cut5",
        "batch_size": 1,
        "batch_threshold": 0.75,
        "split_bucket": True,
        "speed_factor": speed_factor,
        "streaming_mode": False,
        "seed": seed,
        "parallel_infer": True,
        "repetition_penalty": 1.35
    }

    try:
        async with httpx.AsyncClient() as client:
            # urllib.parse.urlencodeを使ってクエリ文字列を作成
            query_string = urllib.parse.urlencode(voiceger_params, safe=':/\\')
            full_url = f"{VOICEGER_API_URL}?{query_string}"
            
            # 構築した完全なURLをログに出力
            print(f"Requesting URL: {full_url}")
            
            voiceger_response = await client.get(full_url, timeout=120.0)
            voiceger_response.raise_for_status()
            return Response(content=voiceger_response.content, media_type="audio/wav")
    except httpx.HTTPError as e:
        return Response(content=f"Error during Voiceger API call: {str(e)}", status_code=500)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=50022)
