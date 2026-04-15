"""
会議録音 文字起こし・議事録生成 Streamlit UI（社内版）
起動: streamlit run app.py
"""

import os
import re
import tempfile
import datetime
import time as _time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from gemini_transcribe_v2 import (
    run_pipeline, MODEL_PRICING, SUPPORTED_LANGUAGES, DEFAULT_SUMMARY_GUIDELINES,
)

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

    model = st.selectbox("🤖 モデル", ["gemini-2.5-flash", "gemini-2.5-pro"], index=0)

    lang = st.selectbox(
        "🌐 出力言語",
        options=list(SUPPORTED_LANGUAGES.keys()),
        format_func=lambda k: SUPPORTED_LANGUAGES[k],
        index=0,
    )

    output_dir = st.text_input("📂 出力先フォルダ", value="output")
    output_prefix = st.text_input("📝 出力ファイル名（プレフィックス）", value="")

    st.divider()
    st.markdown(
        "**出力ファイル:**\n"
        "- `{プレフィックス}_transcript.txt`\n"
        "- `{プレフィックス}_minutes.md`"
    )

# ───────── メインエリア ─────────
uploaded_file = st.file_uploader(
    "🎤 音声/動画ファイルを選択",
    type=["mp4", "m4a", "wav", "mp3", "webm", "ogg", "flac"],
)

if uploaded_file:
    file_size_mb = uploaded_file.size / (1024 * 1024)
    st.info(f"📁 **{uploaded_file.name}** ({file_size_mb:.1f} MB)")

# ───────── 処理前オプション ─────────
with st.expander("🔧 詳細オプション（キーワード・要約指示）", expanded=False):
    st.markdown("##### 🏷️ 重要キーワード")
    st.caption("固有名詞・専門用語など、正確に書き起こしたいキーワードを入力してください（文字起こし精度が向上します）")
    keywords = st.text_area(
        "キーワード",
        placeholder="例: MJS, シンガポール, 住宅手当, 内部通報",
        height=68,
        label_visibility="collapsed",
    )

    st.markdown("##### 📋 要約の方針")
    guidelines = DEFAULT_SUMMARY_GUIDELINES.get(lang, DEFAULT_SUMMARY_GUIDELINES["ja"])
    st.caption(f"**デフォルトの要約方針:**\n{guidelines}")
    custom_instructions = st.text_area(
        "追加の要約指示",
        placeholder="例: ですます調で記載してください / アクションプランを詳細に記載 / 発言の要点を箇条書きで整理",
        height=100,
        label_visibility="collapsed",
    )

# 実行ボタン
run_button = st.button(
    "▶ 文字起こし・要約 開始",
    type="primary",
    disabled=not uploaded_file,
    use_container_width=True,
)

if run_button:
    if not api_key or api_key == "your_api_key_here":
        st.error("サイドバーで Gemini API キーを設定してください")
        st.stop()

    # 一時ファイルに保存
    suffix = Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name

    # 推定完了時刻
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

    start_time = _time.time()
    progress_bar = st.progress(0, text="準備中...")
    status_text = st.empty()

    step_progress = {"[前処理]": 5, "[1/4]": 10, "[2/4]": 40, "[3/4]": 70, "[4/4]": 90}

    def on_progress(kind, msg):
        elapsed = int(_time.time() - start_time)
        elapsed_str = f"{elapsed // 60}分{elapsed % 60:02d}秒"
        if kind == "step":
            for key, val in step_progress.items():
                if msg.startswith(key):
                    progress_bar.progress(val, text=msg)
                    break
            m = re.match(r"\[(\d+)/(\d+)\]", msg)
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
            keywords=keywords,
            custom_instructions=custom_instructions,
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

        # session_stateに結果を保存（編集用）
        st.session_state["transcript"] = transcript
        st.session_state["summary"] = summary
        st.session_state["t_path"] = t_path
        st.session_state["s_path"] = s_path
        st.session_state["usage"] = usage
        st.session_state["model"] = model

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"エラーが発生しました: {e}")

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

# ───────── 結果表示（session_state から）─────────
if "transcript" in st.session_state and "summary" in st.session_state:
    transcript = st.session_state["transcript"]
    summary = st.session_state["summary"]
    t_path = st.session_state["t_path"]
    s_path = st.session_state["s_path"]
    usage = st.session_state["usage"]
    used_model = st.session_state.get("model", "gemini-2.5-flash")

    # コストレポート
    total_cost = usage.calc_cost(used_model, has_audio=True)
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

    # ─── 話者名の置換 ───
    st.divider()
    st.subheader("👥 話者名の紐づけ")
    st.caption("文字起こし中の「話者A」「話者B」等を実際の参加者名に置換できます。")

    # 文字起こしから話者ラベルを自動抽出
    speaker_labels = sorted(set(re.findall(r"(話者[A-Z]|Speaker [A-Z])", transcript)))

    if speaker_labels:
        speaker_map = {}
        cols = st.columns(min(len(speaker_labels), 4))
        for i, label in enumerate(speaker_labels):
            with cols[i % len(cols)]:
                name = st.text_input(f"{label}", key=f"speaker_{label}", placeholder="名前を入力")
                if name.strip():
                    speaker_map[label] = name.strip()

        if speaker_map and st.button("🔄 話者名を置換", use_container_width=True):
            for old, new in speaker_map.items():
                transcript = transcript.replace(old, new)
                summary = summary.replace(old, new)
            st.session_state["transcript"] = transcript
            st.session_state["summary"] = summary
            # ファイルも更新
            Path(t_path).write_text(transcript, encoding="utf-8")
            Path(s_path).write_text(summary, encoding="utf-8")
            st.success("✅ 話者名を置換しました！")
            st.rerun()
    else:
        st.info("話者ラベル（話者A, Speaker A 等）が見つかりませんでした。")

    # ─── 結果タブ（編集可能）───
    st.divider()
    tab1, tab2 = st.tabs(["📄 文字起こし（編集可能）", "📋 議事録（編集可能）"])

    with tab1:
        edited_transcript = st.text_area(
            "文字起こし",
            value=transcript,
            height=500,
            key="edit_transcript",
            label_visibility="collapsed",
        )
        col1, col2 = st.columns([1, 1])
        with col1:
            st.download_button(
                "💾 ダウンロード (.txt)",
                data=edited_transcript,
                file_name=Path(t_path).name,
                mime="text/plain",
            )
        with col2:
            if st.button("💾 編集を保存", key="save_transcript"):
                st.session_state["transcript"] = edited_transcript
                Path(t_path).write_text(edited_transcript, encoding="utf-8")
                st.success(f"保存しました → {t_path}")

    with tab2:
        edited_summary = st.text_area(
            "議事録",
            value=summary,
            height=500,
            key="edit_summary",
            label_visibility="collapsed",
        )

        # プレビュー
        with st.expander("📖 Markdownプレビュー", expanded=True):
            st.markdown(edited_summary)

        col1, col2 = st.columns([1, 1])
        with col1:
            st.download_button(
                "💾 ダウンロード (.md)",
                data=edited_summary,
                file_name=Path(s_path).name,
                mime="text/markdown",
            )
        with col2:
            if st.button("💾 編集を保存", key="save_summary"):
                st.session_state["summary"] = edited_summary
                Path(s_path).write_text(edited_summary, encoding="utf-8")
                st.success(f"保存しました → {s_path}")
