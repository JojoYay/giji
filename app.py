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
    run_pipeline, MODEL_PRICING, SUPPORTED_LANGUAGES,
    DEFAULT_SUMMARY_GUIDELINES, MeetingContext, SUMMARY_TEMPLATES,
)

load_dotenv()

st.set_page_config(page_title="会議 文字起こし・議事録生成", page_icon="📝", layout="wide")
st.title("📝 会議 文字起こし・議事録生成")
st.caption("Gemini API を使って音声/動画ファイルから文字起こしと議事録を自動生成します")

# ───────── サイドバー ─────────
with st.sidebar:
    st.header("⚙️ 基本設定")
    api_key = st.text_input("🔑 Gemini API キー", value=os.environ.get("GEMINI_API_KEY", ""), type="password")
    model = st.selectbox("🤖 モデル", ["gemini-2.5-flash", "gemini-2.5-pro"], index=0)
    lang = st.selectbox("🌐 出力言語", options=list(SUPPORTED_LANGUAGES.keys()),
                        format_func=lambda k: SUPPORTED_LANGUAGES[k], index=0)
    output_dir = st.text_input("📂 出力先フォルダ", value="output")
    output_prefix = st.text_input("📝 出力ファイル名", value="", help="空欄=ファイル名を使用")

# ───────── 会議情報 ─────────
st.subheader("📅 会議情報")
col_date, col_time = st.columns(2)
with col_date:
    meeting_date = st.date_input("日付", value=datetime.date.today())
with col_time:
    meeting_time = st.text_input("時刻", placeholder="例: 10:00-12:00")

col_topic, col_participants = st.columns(2)
with col_topic:
    meeting_topic = st.text_input("🎯 会議テーマ・議題", placeholder="例: Q2売上レビューと下期計画策定")
with col_participants:
    meeting_participants = st.text_input("👥 参加者", placeholder="例: 山田, 吉田, 渡辺, 江坂")

# ───────── ファイルアップロード ─────────
st.subheader("📁 ファイル")
uploaded_file = st.file_uploader(
    "🎤 音声/動画ファイル",
    type=["mp4", "m4a", "wav", "mp3", "webm", "ogg", "flac"],
)
if uploaded_file:
    st.info(f"📁 **{uploaded_file.name}** ({uploaded_file.size / (1024*1024):.1f} MB)")

# 参考資料
ref_files = st.file_uploader(
    "📄 参考資料（任意）",
    type=["pdf", "txt", "docx", "pptx", "xlsx", "csv", "md"],
    accept_multiple_files=True,
    help="会議に関連するPDF・スライド等をアップロードすると文字起こし精度が向上します",
)

# ───────── 詳細オプション ─────────
# ───────── テンプレート選択 ─────────
st.subheader("📑 議事録テンプレート")
template_keys = list(SUMMARY_TEMPLATES.keys())
template_names = [SUMMARY_TEMPLATES[k]["name"].get(lang, SUMMARY_TEMPLATES[k]["name"]["ja"]) for k in template_keys]
template_descs = [SUMMARY_TEMPLATES[k]["description"].get(lang, SUMMARY_TEMPLATES[k]["description"]["ja"]) for k in template_keys]

selected_idx = st.selectbox(
    "テンプレートを選択",
    range(len(template_keys)),
    format_func=lambda i: f"{template_names[i]} — {template_descs[i]}",
    index=0,
    label_visibility="collapsed",
)
selected_template_key = template_keys[selected_idx]

# テンプレートプレビュー・編集
custom_template_text = ""
default_tpl = SUMMARY_TEMPLATES[selected_template_key]["template"].get(lang, "")
if selected_template_key == "custom":
    st.caption("自由にテンプレートを作成してください。Markdown形式の見出し（## ）でセクションを定義します。")
    custom_template_text = st.text_area("テンプレート編集", value="", height=300, key="custom_tpl")
else:
    with st.expander("📖 テンプレートをプレビュー・編集", expanded=False):
        edited_tpl = st.text_area("テンプレート", value=default_tpl, height=300, key="tpl_edit")
        if edited_tpl != default_tpl:
            selected_template_key = "custom"
            custom_template_text = edited_tpl
            st.info("テンプレートが編集されました。カスタムテンプレートとして使用します。")

with st.expander("🔧 詳細オプション（キーワード・用語辞書・要約指示）", expanded=False):
    st.markdown("##### 🏷️ 重要キーワード")
    st.caption("固有名詞・専門用語など、正確に書き起こしたいキーワード")
    keywords = st.text_area("キーワード", placeholder="例: MJS, シンガポール, 住宅手当, RPA",
                            height=68, label_visibility="collapsed")

    st.markdown("##### 📖 専門用語辞書")
    st.caption("略語や専門用語の正式名称を登録すると、文字起こし・校正で使われます")
    glossary = st.text_area("用語辞書", placeholder="例:\nMJS = ミロク情報サービス\nRPA = Robotic Process Automation\nKPI = Key Performance Indicator",
                            height=100, label_visibility="collapsed")

    st.markdown("##### 📋 要約の方針")
    guidelines = DEFAULT_SUMMARY_GUIDELINES.get(lang, DEFAULT_SUMMARY_GUIDELINES["ja"])
    st.caption(f"**デフォルト方針:**\n{guidelines}")
    custom_instructions = st.text_area("追加の要約指示",
        placeholder="例: ですます調で記載 / アクションプランを詳細に / 発言者ごとに意見を整理",
        height=100, label_visibility="collapsed")

    if ref_files or glossary:
        st.info("📌 参考資料または用語辞書が入力されているため、**2パス校正**が自動で有効になります（精度向上）")

# ───────── 実行 ─────────
run_button = st.button("▶ 文字起こし・要約 開始", type="primary", disabled=not uploaded_file, use_container_width=True)

if run_button:
    if not api_key or api_key == "your_api_key_here":
        st.error("サイドバーで Gemini API キーを設定してください")
        st.stop()

    # MeetingContext 構築
    ctx = MeetingContext(
        date=str(meeting_date),
        time=meeting_time,
        topic=meeting_topic,
        participants=meeting_participants,
        keywords=keywords,
        glossary=glossary,
        custom_instructions=custom_instructions,
    )

    # 一時ファイル保存
    suffix = Path(uploaded_file.name).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        tmp_path = tmp.name

    # 参考資料を一時保存
    ref_paths = []
    for rf in ref_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(rf.name).suffix, prefix="ref_") as rtmp:
            rtmp.write(rf.getbuffer())
            ref_paths.append(rtmp.name)

    # 推定完了時刻
    file_size_mb = uploaded_file.size / (1024 * 1024)
    if suffix.lower() in {".mp4", ".mkv", ".avi", ".mov", ".webm"}:
        est_audio_min = file_size_mb * 3 / 60
    else:
        est_audio_min = file_size_mb * 15 / 60
    est_chunks = max(1, int(est_audio_min / 15) + 1)
    est_total_sec = 40 + max(30, int(file_size_mb / 100 * 60)) + est_chunks * 120 + 60
    if ref_paths:
        est_total_sec += len(ref_paths) * 30  # 資料読み込み
    if glossary:
        est_total_sec += 60  # 2パス校正
    est_finish = datetime.datetime.now() + datetime.timedelta(seconds=est_total_sec)

    eta_placeholder = st.empty()
    eta_placeholder.info(
        f"⏱️ 推定完了時刻: **{est_finish.strftime('%H:%M')}** 頃 "
        f"（約{est_total_sec // 60}分 / {file_size_mb:.0f}MB / {est_chunks}チャンク"
        f"{' / 2パス校正' if (ref_paths or glossary) else ''}）"
    )

    start_time = _time.time()
    progress_bar = st.progress(0, text="準備中...")
    status_text = st.empty()
    step_map = {"[前処理]": 5, "[1/4]": 10, "[2/4]": 35, "[校正]": 55, "[3/4]": 70, "[議事録]": 70, "[4/4]": 90}

    def on_progress(kind, msg):
        elapsed = int(_time.time() - start_time)
        elapsed_str = f"{elapsed // 60}分{elapsed % 60:02d}秒"
        if kind == "step":
            for key, val in step_map.items():
                if msg.startswith(key):
                    progress_bar.progress(val, text=msg)
                    break
            m = re.match(r"\[(\d+)/(\d+)\]", msg)
            if m:
                cur, tot = int(m.group(1)), int(m.group(2))
                pct = int(10 + (cur / tot) * 50)
                progress_bar.progress(min(pct, 95), text=msg)
            status_text.text(f"{msg}  (経過: {elapsed_str})")
        elif kind == "processing":
            status_text.text(f"  処理待ち: {msg}  (経過: {elapsed_str})")
        elif kind == "upload_done":
            status_text.text(f"  アップロード完了: {msg}  (経過: {elapsed_str})")

    try:
        prefix = output_prefix.strip() if output_prefix.strip() else None
        transcript, summary, t_path, s_path, usage = run_pipeline(
            file_path=tmp_path,
            api_key=api_key,
            model=model,
            lang=lang,
            ctx=ctx,
            reference_files=ref_paths or None,
            template_key=selected_template_key,
            custom_template=custom_template_text,
            output_dir=output_dir,
            output_prefix=prefix or Path(uploaded_file.name).stem,
            on_progress=on_progress,
        )

        actual_sec = int(_time.time() - start_time)
        progress_bar.progress(100, text="完了!")
        status_text.empty()
        eta_placeholder.success(f"✅ 処理完了！ 所要時間: **{actual_sec // 60}分{actual_sec % 60:02d}秒**")

        st.session_state.update({
            "transcript": transcript, "summary": summary,
            "t_path": t_path, "s_path": s_path,
            "usage": usage, "model": model,
        })

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"エラー: {e}")

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass
        for rp in ref_paths:
            try:
                os.unlink(rp)
            except Exception:
                pass

# ───────── 結果表示 ─────────
if "transcript" in st.session_state and "summary" in st.session_state:
    transcript = st.session_state["transcript"]
    summary = st.session_state["summary"]
    t_path = st.session_state["t_path"]
    s_path = st.session_state["s_path"]
    usage = st.session_state["usage"]
    used_model = st.session_state.get("model", "gemini-2.5-flash")

    total_cost = usage.calc_cost(used_model, has_audio=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("入力トークン", f"{usage.input_tokens:,}")
    with c2:
        st.metric("出力トークン", f"{usage.output_tokens:,}")
    with c3:
        st.metric("合計コスト (USD)", f"${total_cost:.4f}")
    with st.expander("💰 コスト詳細"):
        for c in usage.calls:
            st.markdown(f"**{c['label']}** — 入力: {c['input']:,} / 出力: {c['output']:,}")

    # 話者名の置換
    st.divider()
    st.subheader("👥 話者名の紐づけ")
    st.caption("「話者A」「話者B」等を実際の参加者名に一括置換できます。")
    speaker_labels = sorted(set(re.findall(r"(話者[A-Z]|Speaker [A-Z])", transcript)))

    if speaker_labels:
        speaker_map = {}
        cols = st.columns(min(len(speaker_labels), 4))
        for i, label in enumerate(speaker_labels):
            with cols[i % len(cols)]:
                name = st.text_input(f"{label}", key=f"speaker_{label}", placeholder="名前")
                if name.strip():
                    speaker_map[label] = name.strip()
        if speaker_map and st.button("🔄 話者名を置換", use_container_width=True):
            for old, new in speaker_map.items():
                transcript = transcript.replace(old, new)
                summary = summary.replace(old, new)
            st.session_state["transcript"] = transcript
            st.session_state["summary"] = summary
            Path(t_path).write_text(transcript, encoding="utf-8")
            Path(s_path).write_text(summary, encoding="utf-8")
            st.success("✅ 話者名を置換しました！")
            st.rerun()

    # 結果タブ（編集可能）
    st.divider()
    tab1, tab2 = st.tabs(["📄 文字起こし（編集可能）", "📋 議事録（編集可能）"])

    with tab1:
        edited_transcript = st.text_area("文字起こし", value=transcript, height=500,
                                         key="edit_transcript", label_visibility="collapsed")
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("💾 ダウンロード (.txt)", data=edited_transcript,
                               file_name=Path(t_path).name, mime="text/plain")
        with c2:
            if st.button("💾 編集を保存", key="save_t"):
                st.session_state["transcript"] = edited_transcript
                Path(t_path).write_text(edited_transcript, encoding="utf-8")
                st.success(f"保存 → {t_path}")

    with tab2:
        edited_summary = st.text_area("議事録", value=summary, height=500,
                                       key="edit_summary", label_visibility="collapsed")
        with st.expander("📖 Markdownプレビュー", expanded=True):
            st.markdown(edited_summary)
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("💾 ダウンロード (.md)", data=edited_summary,
                               file_name=Path(s_path).name, mime="text/markdown")
        with c2:
            if st.button("💾 編集を保存", key="save_s"):
                st.session_state["summary"] = edited_summary
                Path(s_path).write_text(edited_summary, encoding="utf-8")
                st.success(f"保存 → {s_path}")
