"""
会議録音 文字起こし → 要約・議事録生成スクリプト (google-genai v2対応)

使い方 (CLI):
  pip install google-genai python-dotenv
  python gemini_transcribe_v2.py --file meeting.mp4

APIキーは .env ファイルの GEMINI_API_KEY か --api_key 引数で指定。
"""

import argparse
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

# Windows コンソールで日本語出力を可能にする
if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
import google.genai as genai
from google.genai import types

# .env を読み込み（スクリプトと同じディレクトリの .env を明示指定）
load_dotenv(Path(__file__).parent / ".env")

# ───────── 多言語プロンプト ─────────

SUPPORTED_LANGUAGES = {
    "ja": "日本語",
    "en": "English",
    "zh": "中文",
    "ms": "Bahasa Melayu",
}

TRANSCRIPT_PROMPTS = {
    "ja": """\
この音声/動画ファイルはビジネスWeb会議の録音です。
以下の形式で完全な文字起こしを日本語で行ってください。

【出力形式】
[HH:MM:SS] 話者名または「話者A/B/C...」: 発言内容

【ルール】
- 発言はできる限り正確に書き起こしてください
- 話者が変わるたびに新しい行にしてください
- 聞き取りにくい箇所は (不明瞭) と記載してください
- 専門用語・固有名詞はそのまま記載してください
""",
    "en": """\
This audio/video file is a recording of a business web meeting.
Please provide a complete transcription in English in the following format.

[Output format]
[HH:MM:SS] Speaker name or "Speaker A/B/C...": Statement

[Rules]
- Transcribe statements as accurately as possible
- Start a new line each time the speaker changes
- Mark unclear parts as (inaudible)
- Keep technical terms and proper nouns as-is
""",
    "zh": """\
这是一段商务网络会议的录音文件。
请按照以下格式用中文进行完整的文字转录。

【输出格式】
[HH:MM:SS] 发言人姓名或"发言人A/B/C...": 发言内容

【规则】
- 请尽可能准确地转录发言内容
- 每当发言人更换时，请另起一行
- 听不清楚的部分请标注（不清楚）
- 专业术语和专有名词请保持原样
""",
    "ms": """\
Fail audio/video ini ialah rakaman mesyuarat web perniagaan.
Sila buat transkripsi lengkap dalam Bahasa Melayu mengikut format berikut.

[Format output]
[HH:MM:SS] Nama penutur atau "Penutur A/B/C...": Kandungan ucapan

[Peraturan]
- Transkripsi ucapan setepat mungkin
- Mulakan baris baharu setiap kali penutur bertukar
- Tandakan bahagian yang tidak jelas sebagai (tidak jelas)
- Kekalkan istilah teknikal dan nama khas seperti asal
""",
}

SUMMARY_PROMPTS = {
    "ja": """\
以下はビジネス会議の文字起こしです。これをもとに議事録を日本語で作成してください。

# 議事録

## 基本情報
- 日時（文字起こしから推定）
- 参加者（登場した話者）
- 会議形式: Web会議

## 議題・目的

## 討議内容

## 決定事項

## TODO・アクションアイテム
| 担当者 | 内容 | 期限 |
|--------|------|------|

## 次回予定

## その他・備考

---
文字起こし:
{transcript}
""",
    "en": """\
Below is a transcription of a business meeting. Please create meeting minutes in English based on this.

# Meeting Minutes

## Basic Information
- Date/Time (estimated from transcription)
- Participants (speakers identified)
- Format: Web meeting

## Agenda / Purpose

## Discussion

## Decisions Made

## Action Items
| Assignee | Task | Deadline |
|----------|------|----------|

## Next Meeting

## Notes

---
Transcription:
{transcript}
""",
    "zh": """\
以下是商务会议的文字记录。请据此用中文撰写会议纪要。

# 会议纪要

## 基本信息
- 日期时间（从文字记录推断）
- 参会人员（出现的发言人）
- 会议形式：网络会议

## 议题与目的

## 讨论内容

## 决定事项

## 待办事项
| 负责人 | 内容 | 截止日期 |
|--------|------|----------|

## 下次会议

## 其他备注

---
文字记录：
{transcript}
""",
    "ms": """\
Berikut ialah transkripsi mesyuarat perniagaan. Sila buat minit mesyuarat dalam Bahasa Melayu berdasarkan ini.

# Minit Mesyuarat

## Maklumat Asas
- Tarikh/Masa (dianggarkan daripada transkripsi)
- Peserta (penutur yang dikenal pasti)
- Format: Mesyuarat web

## Agenda / Tujuan

## Perbincangan

## Keputusan

## Tindakan Susulan
| Bertanggungjawab | Tugasan | Tarikh Akhir |
|------------------|---------|--------------|

## Mesyuarat Seterusnya

## Catatan

---
Transkripsi:
{transcript}
""",
}


def get_transcript_prompt(lang: str = "ja") -> str:
    return TRANSCRIPT_PROMPTS.get(lang, TRANSCRIPT_PROMPTS["ja"])


def get_summary_prompt(lang: str = "ja") -> str:
    return SUMMARY_PROMPTS.get(lang, SUMMARY_PROMPTS["ja"])

# ───────── 料金テーブル (USD per 1M tokens) ─────────
# https://ai.google.dev/gemini-api/docs/pricing
MODEL_PRICING = {
    "gemini-2.5-flash": {
        "input":  0.30,   # text/image/video per 1M tokens
        "output": 2.50,
        "audio_input": 1.00,  # audio per 1M tokens
    },
    "gemini-2.5-pro": {
        "input":  1.25,   # ≤200k context
        "output": 10.00,
        "audio_input": None,  # same as input
    },
}

# フォールバック料金（不明モデル用）
DEFAULT_PRICING = {"input": 1.25, "output": 10.00, "audio_input": None}


@dataclass
class UsageStats:
    """API呼び出しのトークン使用量とコストを蓄積する。"""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    calls: list = field(default_factory=list)  # 各呼び出しの詳細

    def add(self, label: str, usage_metadata):
        """レスポンスの usage_metadata から統計を加算する。"""
        inp = getattr(usage_metadata, "prompt_token_count", 0) or 0
        out = getattr(usage_metadata, "candidates_token_count", 0) or 0
        tot = getattr(usage_metadata, "total_token_count", 0) or (inp + out)
        self.input_tokens += inp
        self.output_tokens += out
        self.total_tokens += tot
        self.calls.append({"label": label, "input": inp, "output": out, "total": tot})

    def calc_cost(self, model: str, has_audio: bool = False) -> float:
        """合計コスト (USD) を計算する。"""
        pricing = MODEL_PRICING.get(model, DEFAULT_PRICING)
        # 音声入力がある呼び出しは audio_input 料金を適用
        input_rate = pricing.get("audio_input") if has_audio and pricing.get("audio_input") else pricing["input"]
        cost_in = (self.input_tokens / 1_000_000) * input_rate
        cost_out = (self.output_tokens / 1_000_000) * pricing["output"]
        return cost_in + cost_out

    def format_report(self, model: str, has_audio: bool = False) -> str:
        """コストレポートを文字列で返す。"""
        pricing = MODEL_PRICING.get(model, DEFAULT_PRICING)
        input_rate = pricing.get("audio_input") if has_audio and pricing.get("audio_input") else pricing["input"]
        output_rate = pricing["output"]

        cost_in = (self.input_tokens / 1_000_000) * input_rate
        cost_out = (self.output_tokens / 1_000_000) * output_rate
        total_cost = cost_in + cost_out

        lines = [
            "=" * 50,
            "💰 API使用量・コストレポート",
            "=" * 50,
            f"  モデル: {model}",
            f"  入力単価: ${input_rate:.2f} / 1M tokens",
            f"  出力単価: ${output_rate:.2f} / 1M tokens",
            "-" * 50,
        ]
        for c in self.calls:
            lines.append(f"  [{c['label']}]")
            lines.append(f"    入力: {c['input']:,} tokens")
            lines.append(f"    出力: {c['output']:,} tokens")
        lines += [
            "-" * 50,
            f"  合計入力: {self.input_tokens:,} tokens",
            f"  合計出力: {self.output_tokens:,} tokens",
            f"  合計トークン: {self.total_tokens:,} tokens",
            "-" * 50,
            f"  入力コスト: ${cost_in:.4f}",
            f"  出力コスト: ${cost_out:.4f}",
            f"  ★ 合計コスト: ${total_cost:.4f} USD",
            "=" * 50,
        ]
        return "\n".join(lines)


# ───────── ユーティリティ ─────────

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"}


def _get_ffmpeg() -> str | None:
    """利用可能なffmpegのパスを返す。"""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, RuntimeError):
        pass
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return "ffmpeg"
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def _extract_audio(file_path: str, on_progress=None) -> str | None:
    """動画ファイルからffmpegで音声のみ抽出し、一時ファイルのパスを返す。"""
    p = Path(file_path)
    if p.suffix.lower() not in VIDEO_EXTENSIONS:
        return None

    ffmpeg_bin = _get_ffmpeg()
    if not ffmpeg_bin:
        return None

    if on_progress:
        on_progress("step", "[前処理] 動画から音声を抽出中 (ffmpeg)...")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".m4a", prefix="audio_")
    tmp.close()

    cmd = [
        ffmpeg_bin, "-y", "-i", file_path,
        "-vn", "-acodec", "aac", "-b:a", "64k", "-ac", "1", "-ar", "16000",
        tmp.name,
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass
        return None

    size_mb = Path(tmp.name).stat().st_size / (1024 * 1024)
    if on_progress:
        on_progress("step", f"[前処理] 音声抽出完了 ({size_mb:.1f} MB)")
    return tmp.name


def _safe_copy_for_upload(file_path: str) -> str | None:
    """ファイル名に非ASCII文字が含まれる場合、一時ファイルにコピーして返す。"""
    p = Path(file_path)
    try:
        p.name.encode("ascii")
        return None
    except UnicodeEncodeError:
        suffix = p.suffix
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="upload_")
        tmp.close()
        shutil.copy2(file_path, tmp.name)
        return tmp.name


def upload_and_wait(client, file_path: str, on_progress=None):
    """ファイルをGeminiにアップロードし、処理完了まで待機する。"""
    tmp_copy = _safe_copy_for_upload(file_path)
    upload_path = tmp_copy or file_path
    try:
        uploaded = client.files.upload(file=upload_path)
    finally:
        if tmp_copy:
            try:
                os.unlink(tmp_copy)
            except Exception:
                pass
    if on_progress:
        on_progress("upload_done", uploaded.name)

    start = time.time()
    while uploaded.state.name == "PROCESSING":
        elapsed = int(time.time() - start)
        if on_progress:
            on_progress("processing", f"{elapsed}秒経過...")
        time.sleep(5)
        uploaded = client.files.get(name=uploaded.name)

    if uploaded.state.name != "ACTIVE":
        raise RuntimeError(f"ファイル処理エラー: 状態={uploaded.state.name}")
    return uploaded


# ───────── Gemini API 呼び出し ─────────

MAX_RETRIES = 5
RETRY_WAIT = 30  # 秒


def _generate_with_retry(client, model, contents, on_progress=None, label=""):
    """503/429 エラー時にリトライする generate_content ラッパー。
    response オブジェクトをそのまま返す（usage_metadata 取得のため）。"""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=model, contents=contents,
            )
            return response
        except Exception as e:
            code = getattr(e, "status_code", 0)
            is_retryable = (
                code in (503, 429, 500)
                or "high demand" in str(e).lower()
                or "unavailable" in str(e).lower()
            )
            if is_retryable and attempt < MAX_RETRIES:
                wait = RETRY_WAIT * attempt
                if on_progress:
                    on_progress("step", f"  {label} サーバー高負荷。{wait}秒後にリトライ ({attempt}/{MAX_RETRIES})...")
                time.sleep(wait)
            else:
                raise


def transcribe(client, uploaded, model, lang="ja", on_progress=None):
    """アップロード済みファイルから文字起こしを実行する。response を返す。"""
    return _generate_with_retry(
        client, model,
        contents=[
            types.Part.from_uri(file_uri=uploaded.uri, mime_type=uploaded.mime_type),
            get_transcript_prompt(lang),
        ],
        on_progress=on_progress,
        label="文字起こし",
    )


def summarize(client, transcript_text, model, lang="ja", on_progress=None):
    """文字起こしテキストから議事録要約を生成する。response を返す。"""
    return _generate_with_retry(
        client, model,
        contents=get_summary_prompt(lang).format(transcript=transcript_text),
        on_progress=on_progress,
        label="議事録生成",
    )


# ───────── メインパイプライン ─────────

def run_pipeline(
    file_path: str,
    api_key: str,
    model: str = "gemini-2.5-flash",
    lang: str = "ja",
    output_dir: str = ".",
    output_prefix: str | None = None,
    on_progress=None,
):
    """文字起こし→要約の全工程を実行し、ファイルに保存する。

    Args:
        lang: 出力言語コード ("ja", "en", "zh", "ms")

    Returns:
        (transcript_text, summary_text, transcript_path, summary_path, usage_stats)
    """
    client = genai.Client(api_key=api_key)
    fp = Path(file_path)
    usage = UsageStats()

    # 動画の場合、音声のみ抽出してアップロードサイズを削減
    audio_tmp = _extract_audio(str(fp), on_progress)
    upload_file = audio_tmp or str(fp)
    has_audio = True  # 文字起こしステップは音声入力

    if on_progress:
        on_progress("step", "[1/4] アップロード中...")

    try:
        uploaded = upload_and_wait(client, upload_file, on_progress)
    finally:
        if audio_tmp:
            try:
                os.unlink(audio_tmp)
            except Exception:
                pass

    lang_name = SUPPORTED_LANGUAGES.get(lang, lang)
    if on_progress:
        on_progress("step", f"[2/4] 文字起こし中 ({model} / {lang_name})...")

    resp1 = transcribe(client, uploaded, model, lang, on_progress)
    transcript = resp1.text
    if resp1.usage_metadata:
        usage.add("文字起こし", resp1.usage_metadata)

    if on_progress:
        on_progress("step", f"[3/4] 議事録生成中 ({lang_name})...")

    resp2 = summarize(client, transcript, model, lang, on_progress)
    summary = resp2.text
    if resp2.usage_metadata:
        usage.add("議事録生成", resp2.usage_metadata)

    if on_progress:
        on_progress("step", "[4/4] ファイル保存中...")

    # 出力ファイルパス
    prefix = output_prefix or fp.stem
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    transcript_path = out / f"{prefix}_transcript.txt"
    summary_path = out / f"{prefix}_minutes.md"

    transcript_path.write_text(transcript, encoding="utf-8")
    summary_path.write_text(summary, encoding="utf-8")

    # クリーンアップ
    try:
        client.files.delete(name=uploaded.name)
    except Exception:
        pass

    return transcript, summary, str(transcript_path), str(summary_path), usage


# ───────── CLI ─────────

def main():
    parser = argparse.ArgumentParser(
        description="会議録音から文字起こし・議事録を生成 (Gemini API)"
    )
    parser.add_argument("--file", required=True, help="音声/動画ファイルのパス")
    parser.add_argument("--api_key", default=None, help="Gemini APIキー")
    parser.add_argument("--model", default="gemini-2.5-flash", help="使用モデル")
    parser.add_argument("--lang", default="ja",
                        choices=list(SUPPORTED_LANGUAGES.keys()),
                        help="出力言語 (ja/en/zh/ms)")
    parser.add_argument("--output_dir", default=".", help="出力先フォルダ")
    parser.add_argument("--output_prefix", default=None, help="出力ファイル名プレフィックス")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("エラー: --api_key または環境変数 GEMINI_API_KEY (.env) が必要です")
        sys.exit(1)

    fp = Path(args.file)
    if not fp.exists():
        print(f"エラー: ファイルが見つかりません: {args.file}")
        sys.exit(1)

    size_mb = fp.stat().st_size / (1024 * 1024)
    print(f"対象: {fp.name} ({size_mb:.1f} MB)")
    print("=" * 60)

    def cli_progress(kind, msg):
        if kind == "step":
            print(msg)
        elif kind == "processing":
            print(f"      {msg}", end="\r")
        elif kind == "upload_done":
            print(f"      アップロード完了: {msg}")

    print(f"出力言語: {SUPPORTED_LANGUAGES.get(args.lang, args.lang)}")

    transcript, summary, t_path, s_path, usage = run_pipeline(
        file_path=str(fp),
        api_key=api_key,
        model=args.model,
        lang=args.lang,
        output_dir=args.output_dir,
        output_prefix=args.output_prefix,
        on_progress=cli_progress,
    )

    print(f"\n✅ 文字起こし → {t_path}")
    print(f"✅ 議事録     → {s_path}")

    # コストレポート
    print()
    print(usage.format_report(args.model, has_audio=True))

    print("\n--- 議事録プレビュー ---")
    print(summary[:800])


if __name__ == "__main__":
    main()
