"""
会議 文字起こし・議事録生成 — Stripe課金付き公開版
起動: streamlit run app_paid.py
"""

import json
import os
import uuid
import shutil
import tempfile
from pathlib import Path

import streamlit as st
import stripe
from dotenv import load_dotenv

from gemini_transcribe_v2 import (
    run_pipeline, MODEL_PRICING, SUPPORTED_LANGUAGES,
    DEFAULT_SUMMARY_GUIDELINES, MeetingContext, SUMMARY_TEMPLATES,
)

# ───────── 設定読み込み ─────────
load_dotenv(Path(__file__).parent / ".env")

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")
PRICE_JPY = int(os.environ.get("STRIPE_PRICE_JPY", "500"))
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = "gemini-2.5-flash"

# 一時ファイル保存ディレクトリ
UPLOAD_DIR = Path(tempfile.gettempdir()) / "giji_uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# ───────── ページ設定 ─────────
st.set_page_config(
    page_title="会議 文字起こし・議事録生成",
    page_icon="📝",
    layout="wide",
)

st.title("📝 会議 文字起こし・議事録生成")
st.caption("音声/動画ファイルから文字起こしと議事録を自動生成します")


# ───────── ユーティリティ ─────────
def save_upload(uploaded_file) -> str:
    """アップロードファイルを一時ディレクトリに保存し、一意のIDを返す。"""
    file_id = uuid.uuid4().hex[:12]
    ext = Path(uploaded_file.name).suffix
    dest = UPLOAD_DIR / f"{file_id}{ext}"
    dest.write_bytes(uploaded_file.getbuffer())
    return file_id


def get_upload_path(file_id: str) -> Path | None:
    """file_id から保存済みファイルのパスを取得。"""
    for p in UPLOAD_DIR.iterdir():
        if p.stem == file_id:
            return p
    return None


def cleanup_upload(file_id: str):
    """一時ファイルを削除。"""
    p = get_upload_path(file_id)
    if p and p.exists():
        p.unlink()


# ───────── Stripe決済 ─────────
def create_checkout_session(file_id: str, file_name: str, lang: str = "ja") -> str:
    """Stripe Checkout Session を作成し、URLを返す。"""
    # 現在のStreamlit URLからベースURLを構築
    base_url = st.context.headers.get("Origin", "http://localhost:8501")

    session = stripe.checkout.Session.create(
        # payment_method_types 省略 = Stripe が Apple Pay / Google Pay / カード等を自動有効化
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "jpy",
                "unit_amount": PRICE_JPY,  # JPY はゼロデシマル
                "product_data": {
                    "name": "会議 文字起こし・議事録生成",
                    "description": f"ファイル: {file_name}",
                },
            },
            "quantity": 1,
        }],
        metadata={
            "file_id": file_id,
            "file_name": file_name,
            "lang": lang,
        },
        success_url=f"{base_url}?session_id={{CHECKOUT_SESSION_ID}}&file_id={file_id}&lang={lang}",
        cancel_url=f"{base_url}?cancelled=1",
    )
    return session.url


def verify_payment(session_id: str) -> dict | None:
    """Stripe Session の決済状態を確認。paid なら metadata を返す。"""
    try:
        if not stripe.api_key:
            st.error("Stripe APIキーが設定されていません")
            return None
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == "paid":
            meta = session.metadata.to_dict() if hasattr(session.metadata, "to_dict") else {}
            return {
                "file_id": meta.get("file_id"),
                "file_name": meta.get("file_name"),
                "lang": meta.get("lang", "ja"),
                "amount": session.amount_total,
                "currency": session.currency,
            }
        else:
            st.warning(f"決済ステータス: {session.payment_status}（未完了）")
    except Exception as e:
        import traceback
        st.error(f"決済確認エラー: {type(e).__name__}: {e}")
        st.code(traceback.format_exc())
    return None


# ───────── メインフロー ─────────
def _get_param(key: str) -> str | None:
    """query_params から安全にパラメータを取得する。"""
    try:
        val = st.query_params.get(key, None)
        if val:
            return str(val)
    except Exception:
        pass
    try:
        params = dict(st.query_params)
        return params.get(key)
    except Exception:
        pass
    return None

param_cancelled = _get_param("cancelled")
param_session_id = _get_param("session_id")
param_file_id = _get_param("file_id")

# --- キャンセル時 ---
if param_cancelled:
    st.warning("💳 決済がキャンセルされました。再度お試しください。")
    st.query_params.clear()

# --- 決済完了後の処理 ---
elif param_session_id and param_file_id:
    session_id = param_session_id
    file_id = param_file_id

    st.info("💳 決済を確認中...")
    payment = verify_payment(session_id)

    if payment is None:
        st.error("決済が確認できませんでした。お問い合わせください。")
        st.stop()

    st.success(f"✅ 決済完了！ ¥{payment['amount']:,} — 処理を開始します...")

    # GCSモード: blobからダウンロード / ローカルモード: 一時ファイルから取得
    _gcs_tmp = None
    if file_id.startswith("uploads/"):
        try:
            from gcs_upload import download_from_gcs
            _gcs_tmp = download_from_gcs(file_id)
            file_path = Path(_gcs_tmp)
        except Exception as e:
            st.error(f"GCSからのダウンロードに失敗: {e}")
            st.stop()
    else:
        file_path = get_upload_path(file_id)

    if not file_path or not Path(file_path).exists():
        st.error("ファイルが見つかりません。再度アップロードしてください。")
        st.stop()

    # 推定完了時刻を計算・表示
    import datetime
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    # 目安: 音声抽出 ~30秒, アップロード ~1分/100MB, 文字起こし ~2分/15分チャンク, 議事録 ~1分
    est_audio_sec = 30 if file_size_mb > 50 else 10
    est_upload_sec = max(30, int(file_size_mb / 100 * 60))
    # 推定音声長（分）: 動画1MBあたり約3秒、音声1MBあたり約15秒
    if file_path.suffix.lower() in {".mp4", ".mkv", ".avi", ".mov", ".webm"}:
        est_audio_min = file_size_mb * 3 / 60  # 動画
    else:
        est_audio_min = file_size_mb * 15 / 60  # 音声
    est_chunks = max(1, int(est_audio_min / 15) + 1)
    est_transcribe_sec = est_chunks * 120  # 1チャンク約2分
    est_summary_sec = 60
    est_total_sec = est_audio_sec + est_upload_sec + est_transcribe_sec + est_summary_sec
    est_finish = datetime.datetime.now() + datetime.timedelta(seconds=est_total_sec)

    eta_placeholder = st.empty()
    eta_placeholder.info(
        f"⏱️ 推定完了時刻: **{est_finish.strftime('%H:%M')}** 頃 "
        f"（約{est_total_sec // 60}分 / ファイル {file_size_mb:.0f}MB / 推定{est_chunks}チャンク）"
    )

    # 処理実行
    import time as _time
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
            # チャンク処理の進捗を動的に反映
            import re
            m = re.match(r"\[(\d+)/(\d+)\]", msg)
            if m:
                current, total = int(m.group(1)), int(m.group(2))
                pct = int(10 + (current / total) * 60)  # 10%〜70%
                progress_bar.progress(min(pct, 95), text=msg)
            status_text.text(f"{msg}  (経過: {elapsed_str})")
        elif kind == "processing":
            status_text.text(f"  処理待ち: {msg}  (経過: {elapsed_str})")
        elif kind == "upload_done":
            status_text.text(f"  アップロード完了: {msg}  (経過: {elapsed_str})")

    # session_stateからMeetingContext・参考資料を取得
    ctx = st.session_state.get("paid_ctx", MeetingContext())
    ref_paths = st.session_state.get("paid_ref_paths", [])
    tpl_key = st.session_state.get("paid_template_key", "standard")
    tpl_custom = st.session_state.get("paid_custom_template", "")

    # GCSモードの参考資料をダウンロード
    _ref_gcs_tmps = []
    ref_blobs = st.session_state.get("paid_ref_blobs", [])
    if ref_blobs:
        from gcs_upload import download_from_gcs as _dl_ref
        for rb in ref_blobs:
            try:
                tmp = _dl_ref(rb)
                ref_paths.append(tmp)
                _ref_gcs_tmps.append(tmp)
            except Exception as e:
                st.warning(f"参考資料のダウンロードに失敗: {rb}: {e}")

    try:
        transcript, summary, t_path, s_path, usage = run_pipeline(
            file_path=str(file_path),
            api_key=GEMINI_API_KEY,
            model=MODEL,
            lang=payment["lang"],
            ctx=ctx,
            reference_files=ref_paths or None,
            template_key=tpl_key,
            custom_template=tpl_custom,
            output_dir="output",
            output_prefix=Path(payment["file_name"]).stem,
            on_progress=on_progress,
        )

        actual_sec = int(_time.time() - start_time)
        actual_min = actual_sec // 60
        actual_sec_rem = actual_sec % 60
        progress_bar.progress(100, text="完了!")
        status_text.empty()
        eta_placeholder.success(
            f"✅ 処理完了！ 所要時間: **{actual_min}分{actual_sec_rem:02d}秒**"
        )

        # session_stateに保存（編集・話者置換用）
        st.session_state["result_transcript"] = transcript
        st.session_state["result_summary"] = summary
        st.session_state["result_t_path"] = t_path
        st.session_state["result_s_path"] = s_path
        st.session_state["result_usage"] = usage
        st.session_state["result_ready"] = True

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"処理エラー: {e}")

    finally:
        # メインファイルのクリーンアップ
        if file_id.startswith("uploads/"):
            try:
                from gcs_upload import delete_from_gcs
                delete_from_gcs(file_id)
            except Exception:
                pass
        else:
            cleanup_upload(file_id)
        if _gcs_tmp and os.path.exists(_gcs_tmp):
            try:
                os.unlink(_gcs_tmp)
            except Exception:
                pass
        # 参考資料のクリーンアップ
        for _rt in _ref_gcs_tmps:
            try:
                os.unlink(_rt)
            except Exception:
                pass
        for rb in ref_blobs:
            try:
                from gcs_upload import delete_from_gcs as _del
                _del(rb)
            except Exception:
                pass
        st.query_params.clear()

# ───── 結果表示（処理完了後）─────
if st.session_state.get("result_ready"):
    import re

    transcript = st.session_state["result_transcript"]
    summary = st.session_state["result_summary"]
    t_path = st.session_state["result_t_path"]
    s_path = st.session_state["result_s_path"]
    usage = st.session_state["result_usage"]

    total_cost = usage.calc_cost(MODEL, has_audio=True)

    st.divider()
    st.subheader("📊 結果")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("合計トークン", f"{usage.total_tokens:,}")
    with col2:
        st.metric("API原価 (USD)", f"${total_cost:.4f}")
    with col3:
        st.metric("所要時間", f"{st.session_state.get('actual_min', 0)}分")

    # ─── 話者名の置換 ───
    st.divider()
    st.subheader("👥 話者名の紐づけ")
    st.caption("「話者A」「話者B」等を実際の参加者名に置換できます。")

    speaker_labels = sorted(set(re.findall(r"(話者[A-Z]|Speaker [A-Z])", transcript)))

    if speaker_labels:
        speaker_map = {}
        cols = st.columns(min(len(speaker_labels), 4))
        for i, label in enumerate(speaker_labels):
            with cols[i % len(cols)]:
                name = st.text_input(f"{label}", key=f"spk_{label}", placeholder="名前を入力")
                if name.strip():
                    speaker_map[label] = name.strip()

        if speaker_map and st.button("🔄 話者名を置換", use_container_width=True):
            for old, new in speaker_map.items():
                transcript = transcript.replace(old, new)
                summary = summary.replace(old, new)
            st.session_state["result_transcript"] = transcript
            st.session_state["result_summary"] = summary
            st.success("✅ 話者名を置換しました！")
            st.rerun()

    # ─── 結果タブ（編集可能）───
    st.divider()
    tab1, tab2 = st.tabs(["📄 文字起こし（編集可能）", "📋 議事録（編集可能）"])

    with tab1:
        edited_transcript = st.text_area(
            "文字起こし", value=transcript, height=500,
            key="paid_edit_transcript", label_visibility="collapsed",
        )
        st.download_button(
            "💾 ダウンロード (.txt)",
            data=edited_transcript,
            file_name=Path(t_path).name,
            mime="text/plain",
        )

    with tab2:
        edited_summary = st.text_area(
            "議事録", value=summary, height=500,
            key="paid_edit_summary", label_visibility="collapsed",
        )
        with st.expander("📖 Markdownプレビュー", expanded=True):
            st.markdown(edited_summary)
        st.download_button(
            "💾 ダウンロード (.md)",
            data=edited_summary,
            file_name=Path(s_path).name,
            mime="text/markdown",
        )

# --- 通常（ファイルアップロード画面）---
else:
    import datetime as _dt

    st.markdown(f"""
    ### 使い方
    1. 会議情報を入力 → 音声/動画ファイルをアップロード
    2. 💳 **¥{PRICE_JPY:,}** でお支払い（クレジットカード）
    3. 高精度な文字起こし＋議事録が生成されます
    """)

    # 会議情報
    st.subheader("📅 会議情報")
    col_date, col_time = st.columns(2)
    with col_date:
        meeting_date = st.date_input("日付", value=_dt.date.today(), key="pd_date")
    with col_time:
        meeting_time = st.text_input("時刻", placeholder="例: 10:00-12:00", key="pd_time")

    col_topic, col_participants = st.columns(2)
    with col_topic:
        meeting_topic = st.text_input("🎯 会議テーマ", placeholder="例: Q2売上レビュー", key="pd_topic")
    with col_participants:
        meeting_participants = st.text_input("👥 参加者", placeholder="例: 山田, 吉田, 渡辺", key="pd_parts")

    lang = st.selectbox("🌐 出力言語", options=list(SUPPORTED_LANGUAGES.keys()),
                        format_func=lambda k: SUPPORTED_LANGUAGES[k], index=0, key="pd_lang")

    # テンプレート選択
    st.subheader("📑 議事録テンプレート")
    _tpl_keys = list(SUMMARY_TEMPLATES.keys())
    _tpl_names = [SUMMARY_TEMPLATES[k]["name"].get(lang, SUMMARY_TEMPLATES[k]["name"]["ja"]) for k in _tpl_keys]
    _tpl_descs = [SUMMARY_TEMPLATES[k]["description"].get(lang, SUMMARY_TEMPLATES[k]["description"]["ja"]) for k in _tpl_keys]
    _sel_idx = st.selectbox("テンプレート", range(len(_tpl_keys)),
        format_func=lambda i: f"{_tpl_names[i]} — {_tpl_descs[i]}",
        index=0, label_visibility="collapsed", key="pd_tpl")
    paid_template_key = _tpl_keys[_sel_idx]
    paid_custom_template = ""
    _def_tpl = SUMMARY_TEMPLATES[paid_template_key]["template"].get(lang, "")
    if paid_template_key == "custom":
        paid_custom_template = st.text_area("テンプレート編集", value="", height=300, key=f"pd_ctpl_{lang}")
    else:
        with st.expander("📖 テンプレートプレビュー・編集"):
            _ed_tpl = st.text_area("テンプレート", value=_def_tpl, height=250, key=f"pd_tpl_edit_{lang}_{paid_template_key}")
            if _ed_tpl != _def_tpl:
                paid_template_key = "custom"
                paid_custom_template = _ed_tpl
                st.info("カスタムテンプレートとして使用します。")

    # ファイル — GCSダイレクトアップロード対応
    st.subheader("📁 ファイル")
    _use_gcs = os.environ.get("GCS_BUCKET", "")

    if _use_gcs:
        # Cloud Run環境: 専用アップロードページへ誘導
        # (Cloud Run 32MB制限のため、別ページからGCSに直接アップロード)

        # アップロード完了後のリダイレクトでblob情報を受け取る
        _gcs_blob = _get_param("gcs_blob")
        _gcs_fn = _get_param("gcs_fn")
        _gcs_refs = _get_param("gcs_refs")
        if _gcs_blob:
            import urllib.parse
            st.session_state["gcs_blob"] = urllib.parse.unquote(_gcs_blob)
            st.session_state["gcs_filename"] = urllib.parse.unquote(_gcs_fn) if _gcs_fn else "recording.mp4"
            if _gcs_refs:
                st.session_state["gcs_ref_blobs"] = [b.strip() for b in urllib.parse.unquote(_gcs_refs).split(",") if b.strip()]
            st.query_params.clear()
            st.rerun()

        if st.session_state.get("gcs_blob"):
            _fn = st.session_state.get("gcs_filename", "")
            _ref_blobs = st.session_state.get("gcs_ref_blobs", [])

            _col1, _col2 = st.columns([3, 1])
            with _col1:
                st.success(f"✅ **{_fn}** — アップロード済み")
                if _ref_blobs:
                    st.info(f"📄 参考資料 **{len(_ref_blobs)}件** アップロード済み")
                else:
                    st.caption("📄 参考資料: なし")
            with _col2:
                st.link_button("🔄 やり直す", "/upload", use_container_width=True)
        else:
            st.link_button(
                "📤 音声/動画ファイル＆参考資料をアップロード",
                "/upload",
                use_container_width=True,
            )
            st.caption("大容量ファイル対応。音声ファイルと参考資料をまとめてアップロードできます。")

        uploaded_file = None
    else:
        # ローカル環境: 通常のStreamlitアップローダー
        uploaded_file = st.file_uploader("🎤 音声/動画ファイル",
            type=["mp4", "m4a", "wav", "mp3", "webm", "ogg", "flac"], key="pd_audio")
        if uploaded_file:
            st.info(f"📁 **{uploaded_file.name}** ({uploaded_file.size / (1024*1024):.1f} MB)")

    if not _use_gcs:
        ref_files = st.file_uploader("📄 参考資料（任意）",
            type=["pdf", "txt", "docx", "pptx", "xlsx", "csv", "md"],
            accept_multiple_files=True, key="pd_refs",
            help="会議関連のPDF・スライド等 → 文字起こし精度が向上")
    else:
        ref_files = []  # GCSモードではアップロードページで処理済み

    # 詳細オプション
    with st.expander("🔧 詳細オプション", expanded=False):
        st.markdown("##### 🏷️ 重要キーワード")
        paid_keywords = st.text_area("キーワード", placeholder="例: 住宅手当, RPA, KPI",
                                     height=68, label_visibility="collapsed", key="pd_kw")
        st.markdown("##### 📖 専門用語辞書")
        paid_glossary = st.text_area("用語辞書", placeholder="例:\nRPA = Robotic Process Automation\nKPI = Key Performance Indicator",
                                     height=100, label_visibility="collapsed", key="pd_gls")
        st.markdown("##### 📋 要約の方針")
        guidelines = DEFAULT_SUMMARY_GUIDELINES.get(lang, DEFAULT_SUMMARY_GUIDELINES["ja"])
        st.caption(f"**デフォルト:** {guidelines}")
        paid_instructions = st.text_area("追加の要約指示",
            placeholder="例: ですます調 / アクションプラン詳細 / 箇条書き",
            height=100, label_visibility="collapsed", key="pd_ci")
        if ref_files or paid_glossary:
            st.info("📌 参考資料/用語辞書 → **2パス校正が自動有効化**されます")

    # 設定エクスポート/インポート
    with st.expander("💾 設定の保存・読み込み（チーム共有用）", expanded=False):
        st.caption("テンプレート・キーワード・用語辞書・要約指示をJSON形式で保存・共有できます。")
        config_data = {
            "version": 1,
            "template_key": paid_template_key,
            "custom_template": paid_custom_template if paid_template_key == "custom" else "",
            "keywords": paid_keywords,
            "glossary": paid_glossary,
            "custom_instructions": paid_instructions,
            "lang": lang,
        }
        st.download_button("📤 設定をエクスポート (.json)",
            data=json.dumps(config_data, ensure_ascii=False, indent=2),
            file_name="giji_config.json", mime="application/json",
            use_container_width=True, key="pd_export")
        st.markdown("---")
        _imp = st.file_uploader("📥 設定を読み込み", type=["json"], key="pd_import")
        if _imp:
            try:
                _imp_data = json.loads(_imp.read().decode("utf-8"))
                st.success(f"✅ 読み込み完了（テンプレート: {_imp_data.get('template_key', '?')}）")
                st.json(_imp_data)
            except Exception as e:
                st.error(f"読み込みエラー: {e}")

    # 参考資料を一時保存（小さいファイルなのでCloud Runでも直接受信可能）
    ref_paths = []
    for rf in ref_files:
        ref_id = uuid.uuid4().hex[:8]
        dest = UPLOAD_DIR / f"ref_{ref_id}{Path(rf.name).suffix}"
        dest.write_bytes(rf.getbuffer())
        ref_paths.append(str(dest))

    # 💳 決済ボタン
    if st.button(f"💳 ¥{PRICE_JPY:,} で文字起こし・議事録を生成",
                 type="primary", use_container_width=True):

        if not stripe.api_key or stripe.api_key.startswith("sk_test_ここに"):
            st.error("Stripe APIキーが設定されていません")
            st.stop()

        # GCSモード: session_stateにblob_nameがあるか確認
        if _use_gcs:
            _blob = st.session_state.get("gcs_blob", "")
            if not _blob:
                st.error("⬆️ まず「音声/動画ファイルをアップロード」ボタンからファイルをアップロードしてください。")
                st.stop()
            st.session_state.file_id = _blob
            st.session_state.file_name = st.session_state.get("gcs_filename", "recording.mp4")
        elif uploaded_file:
            if "file_id" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
                st.session_state.file_id = save_upload(uploaded_file)
                st.session_state.file_name = uploaded_file.name
        else:
            st.error("ファイルをアップロードしてください")
            st.stop()

        # session_stateに全パラメータ保存
        st.session_state["paid_template_key"] = paid_template_key
        st.session_state["paid_custom_template"] = paid_custom_template
        st.session_state["paid_ctx"] = MeetingContext(
            date=str(meeting_date), time=meeting_time,
            topic=meeting_topic, participants=meeting_participants,
            keywords=paid_keywords, glossary=paid_glossary,
            custom_instructions=paid_instructions,
        )
        # GCSモードの場合、参考資料のblob_nameも保存
        if _use_gcs:
            st.session_state["paid_ref_blobs"] = st.session_state.get("gcs_ref_blobs", [])
        st.session_state["paid_ref_paths"] = ref_paths

        with st.spinner("決済ページを準備中..."):
            checkout_url = create_checkout_session(
                file_id=st.session_state.file_id,
                file_name=st.session_state.file_name, lang=lang,
            )

        st.markdown(f'<meta http-equiv="refresh" content="0;url={checkout_url}">', unsafe_allow_html=True)
        st.info("💳 Stripe決済ページに移動します...")
        st.link_button("💳 決済ページを開く", checkout_url, use_container_width=True)

    st.divider()
    st.caption("Powered by Google Gemini API | 決済: Stripe")
