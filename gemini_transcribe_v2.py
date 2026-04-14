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

TRANSCRIPT_PROMPT = """\
この音声/動画ファイルは日本語のビジネスWeb会議の録音です。
以下の形式で完全な文字起こしを行ってください。

【出力形式】
[HH:MM:SS] 話者名または「話者A/B/C...」: 発言内容

【ルール】
- 発言はできる限り正確に書き起こしてください
- 話者が変わるたびに新しい行にしてください
- 聞き取りにくい箇所は (不明瞭) と記載してください
- 専門用語・固有名詞はそのまま記載してください
"""

SUMMARY_PROMPT = """\
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
"""


VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv"}


def _get_ffmpeg() -> str | None:
    """利用可能なffmpegのパスを返す。"""
    # まず imageio-ffmpeg の同梱バイナリを試す
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except (ImportError, RuntimeError):
        pass
    # PATHにあるffmpegを試す
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return "ffmpeg"
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None


def _extract_audio(file_path: str, on_progress=None) -> str | None:
    """動画ファイルからffmpegで音声のみ抽出し、一時ファイルのパスを返す。
    音声ファイルの場合やffmpegが無い場合は None を返す。
    """
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
        "-vn",                # 映像なし
        "-acodec", "aac",     # AAC エンコード
        "-b:a", "64k",        # 64kbps (会議音声なら十分)
        "-ac", "1",           # モノラル
        "-ar", "16000",       # 16kHz
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
        return None  # ASCII のみ → コピー不要
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


MAX_RETRIES = 5
RETRY_WAIT = 30  # 秒


def _generate_with_retry(client, model, contents, on_progress=None, label=""):
    """503/429 エラー時にリトライする generate_content ラッパー。
    SDKの内部リトライ後の例外もキャッチしてリトライする。"""
    from google.genai import types as gen_types

    # SDK内部リトライを最小化するための設定
    config = gen_types.GenerateContentConfig(
        http_options=types.HttpOptions(timeout=600_000),
    ) if hasattr(types, "HttpOptions") else None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            kwargs = {"model": model, "contents": contents}
            if config:
                kwargs["config"] = config
            response = client.models.generate_content(**kwargs)
            return response.text
        except Exception as e:
            code = getattr(e, "status_code", 0)
            is_retryable = code in (503, 429, 500) or "high demand" in str(e).lower() or "unavailable" in str(e).lower()
            if is_retryable and attempt < MAX_RETRIES:
                wait = RETRY_WAIT * attempt
                if on_progress:
                    on_progress("step", f"  {label} サーバー高負荷。{wait}秒後にリトライ ({attempt}/{MAX_RETRIES})...")
                time.sleep(wait)
            else:
                raise


def transcribe(client, uploaded, model: str = "gemini-2.5-pro", on_progress=None):
    """アップロード済みファイルから文字起こしを実行する。"""
    return _generate_with_retry(
        client, model,
        contents=[
            types.Part.from_uri(
                file_uri=uploaded.uri, mime_type=uploaded.mime_type
            ),
            TRANSCRIPT_PROMPT,
        ],
        on_progress=on_progress,
        label="文字起こし",
    )


def summarize(client, transcript: str, model: str = "gemini-2.5-pro", on_progress=None):
    """文字起こしテキストから議事録要約を生成する。"""
    return _generate_with_retry(
        client, model,
        contents=SUMMARY_PROMPT.format(transcript=transcript),
        on_progress=on_progress,
        label="議事録生成",
    )


def run_pipeline(
    file_path: str,
    api_key: str,
    model: str = "gemini-2.5-pro",
    output_dir: str = ".",
    output_prefix: str | None = None,
    on_progress=None,
):
    """文字起こし→要約の全工程を実行し、ファイルに保存する。

    Returns:
        (transcript_text, summary_text, transcript_path, summary_path)
    """
    client = genai.Client(api_key=api_key)
    fp = Path(file_path)

    # 動画の場合、音声のみ抽出してアップロードサイズを削減
    audio_tmp = _extract_audio(str(fp), on_progress)
    upload_file = audio_tmp or str(fp)

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

    if on_progress:
        on_progress("step", f"[2/4] 文字起こし中 ({model})...")

    transcript = transcribe(client, uploaded, model, on_progress)

    if on_progress:
        on_progress("step", "[3/4] 議事録生成中...")

    summary = summarize(client, transcript, model, on_progress)

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

    return transcript, summary, str(transcript_path), str(summary_path)


# --------------- CLI ---------------
def main():
    parser = argparse.ArgumentParser(
        description="会議録音から文字起こし・議事録を生成 (Gemini API)"
    )
    parser.add_argument("--file", required=True, help="音声/動画ファイルのパス")
    parser.add_argument("--api_key", default=None, help="Gemini APIキー")
    parser.add_argument("--model", default="gemini-2.5-flash", help="使用モデル")
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

    transcript, summary, t_path, s_path = run_pipeline(
        file_path=str(fp),
        api_key=api_key,
        model=args.model,
        output_dir=args.output_dir,
        output_prefix=args.output_prefix,
        on_progress=cli_progress,
    )

    print(f"\n✅ 文字起こし → {t_path}")
    print(f"✅ 議事録     → {s_path}")
    print("\n--- 議事録プレビュー ---")
    print(summary[:800])


if __name__ == "__main__":
    main()
