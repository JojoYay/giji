"""
会議録音 文字起こし・議事録生成 Streamlit UI
起動: streamlit run app.py
"""

import os
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from gemini_transcribe_v2 import run_pipeline, MODEL_PRICING, SUPPORTED_LANGUAGES

# .env 読み込み
load_dotenv()

st.set_page_config(
    page_title="会議 文字起こし・議事録生成",
    page_icon="📝",
    layout="wide",
)

st.title("📝 会議 文字起こし・議事録生成")
st.caption("Gemini API を使って音声/動画ファイルから文字起こしと議事録を自動生成します")

# ───────── サイドバー設定 ─────────
with st.sidebar:
    st.header("⚙️ 設定")

    api_key = st.text_input(
        "🔑 Gemini API キー",
        value=os.environ.get("GEMINI_API_KEY", ""),
        type="password",
        help=".env の GEMINI_API_KEY から自動読み込みされます",
    )

    model = st.selectbox(
        "🤖 モデル",
        ["gemini-2.5-flash", "gemini-2.5-pro"],
        index=0,
    )

    lang = st.selectbox(
        "🌐 出力言語",
        options=list(SUPPORTED_LANGUAGES.keys()),
        format_func=lambda k: f"{SUPPORTED_LANGUAGES[k]}",
        index=0,
    )

    output_dir = st.text_input(
        "📂 出力先フォルダ",
        value="output",
        help="結果ファイルの保存先（相対パスまたは絶対パス）",
    )

    output_prefix = st.text_input(
        "📝 出力ファイル名（プレフィックス）",
        value="",
        help="空欄の場合はアップロードファイル名を使用",
    )

    st.divider()
    st.markdown(
        "**出力ファイル:**\n"
        "- `{プレフィックス}_transcript.txt` — 文字起こし\n"
        "- `{プレフィックス}_minutes.md` — 議事録要約"
    )

# ───────── メインエリア ─────────
uploaded_file = st.file_uploader(
    "🎤 音声/動画ファイルを選択",
    type=["mp4", "m4a", "wav", "mp3", "webm", "ogg", "flac"],
    help="対応形式: mp4, m4a, wav, mp3, webm, ogg, flac",
)

if uploaded_file:
    file_size_mb = uploaded_file.size / (1024 * 1024)
    st.info(f"📁 **{uploaded_file.name}** ({file_size_mb:.1f} MB)")

# 実行ボタン
run_button = st.button(
    "▶ 文字起こし・要約 開始",
    type="primary",
    disabled=not uploaded_file,
    use_container_width=True,
)

if run_button:
    # バリデーション
    if not api_key or api_key == "your_api_key_here":
        st.error("サイドバーで Gemini API キーを設定してください")
        st.stop()

    if not uploaded_file:
        st.error("ファイルをアップロードしてください")
        st.stop()

    # 一時ファイルに保存
    suffix = Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name

    # 推定完了時刻
    import datetime
    import time as _time
    import re as _re

    file_size_mb = uploaded_file.size / (1024 * 1024)
    if suffix.lower() in {".mp4", ".mkv", ".avi", ".mov", ".webm"}:
        est_audio_min = file_size_mb * 3 / 60
    else:
        est_audio_min = file_size_mb * 15 / 60
    est_chunks = max(1, int(est_audio_min / 15) + 1)
    est_total_sec = 30 + max(30, int(file_size_mb / 100 * 60)) + est_chunks * 120 + 60
    est_finish = datetime.datetime.now() + datetime.timedelta(seconds=est_total_sec)

    eta_placeholder = st.empty()
    eta_placeholder.info(
        f"⏱️ 推定完了時刻: **{est_finish.strftime('%H:%M')}** 頃 "
        f"（約{est_total_sec // 60}分 / {file_size_mb:.0f}MB / 推定{est_chunks}チャンク）"
    )

    # 進捗表示
    start_time = _time.time()
    progress_bar = st.progress(0, text="準備中...")
    status_text = st.empty()

    step_progress = {
        "[前処理]": 5,
        "[1/4]": 10,
        "[2/4]": 40,
        "[3/4]": 70,
        "[4/4]": 90,
    }

    def on_progress(kind, msg):
        elapsed = int(_time.time() - start_time)
        elapsed_str = f"{elapsed // 60}分{elapsed % 60:02d}秒"
        if kind == "step":
            for key, val in step_progress.items():
                if msg.startswith(key):
                    progress_bar.progress(val, text=msg)
                    break
            m = _re.match(r"\[(\d+)/(\d+)\]", msg)
            if m:
                current, total = int(m.group(1)), int(m.group(2))
                pct = int(10 + (current / total) * 60)
                progress_bar.progress(min(pct, 95), text=msg)
            status_text.text(f"{msg}  (経過: {elapsed_str})")
        elif kind == "processing":
            status_text.text(f"  Gemini処理待ち: {msg}  (経過: {elapsed_str})")
        elif kind == "upload_done":
            status_text.text(f"  アップロード完了: {msg}  (経過: {elapsed_str})")

    try:
        prefix = output_prefix.strip() if output_prefix.strip() else None

        transcript, summary, t_path, s_path, usage = run_pipeline(
            file_path=tmp_path,
            api_key=api_key,
            model=model,
            lang=lang,
            output_dir=output_dir,
            output_prefix=prefix or Path(uploaded_file.name).stem,
            on_progress=on_progress,
        )

        actual_sec = int(_time.time() - start_time)
        progress_bar.progress(100, text="完了!")
        status_text.empty()
        eta_placeholder.success(
            f"✅ 処理完了！ 所要時間: **{actual_sec // 60}分{actual_sec % 60:02d}秒**"
        )

        st.success(f"ファイル保存先: `{output_dir}/`")

        # ───── コストレポート ─────
        total_cost = usage.calc_cost(model, has_audio=True)
        cost_col1, cost_col2, cost_col3 = st.columns(3)
        with cost_col1:
            st.metric("入力トークン", f"{usage.input_tokens:,}")
        with cost_col2:
            st.metric("出力トークン", f"{usage.output_tokens:,}")
        with cost_col3:
            st.metric("合計コスト (USD)", f"${total_cost:.4f}")

        with st.expander("💰 コスト詳細を表示"):
            for c in usage.calls:
                st.markdown(f"**{c['label']}** — 入力: {c['input']:,} / 出力: {c['output']:,} tokens")
            pricing = MODEL_PRICING.get(model, {})
            st.caption(
                f"料金: 入力 ${pricing.get('audio_input') or pricing.get('input', '?')}/1M tokens, "
                f"出力 ${pricing.get('output', '?')}/1M tokens (モデル: {model})"
            )

        # ───── 結果表示 ─────
        tab1, tab2 = st.tabs(["📄 文字起こし", "📋 議事録"])

        with tab1:
            st.text_area(
                "文字起こし結果",
                transcript,
                height=400,
                label_visibility="collapsed",
            )
            col1, col2 = st.columns([1, 3])
            with col1:
                st.download_button(
                    "💾 ダウンロード (.txt)",
                    data=transcript,
                    file_name=Path(t_path).name,
                    mime="text/plain",
                )
            with col2:
                st.caption(f"保存先: `{t_path}`")

        with tab2:
            st.markdown(summary)
            st.divider()
            col1, col2 = st.columns([1, 3])
            with col1:
                st.download_button(
                    "💾 ダウンロード (.md)",
                    data=summary,
                    file_name=Path(s_path).name,
                    mime="text/markdown",
                )
            with col2:
                st.caption(f"保存先: `{s_path}`")

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"エラーが発生しました: {e}")

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
