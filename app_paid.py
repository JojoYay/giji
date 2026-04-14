"""
会議 文字起こし・議事録生成 — Stripe課金付き公開版
起動: streamlit run app_paid.py
"""

import os
import uuid
import shutil
import tempfile
from pathlib import Path

import streamlit as st
import stripe
from dotenv import load_dotenv

from gemini_transcribe_v2 import run_pipeline, MODEL_PRICING, SUPPORTED_LANGUAGES

# ───────── 設定読み込み ─────────
load_dotenv()

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
        payment_method_types=["card"],
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
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == "paid":
            return {
                "file_id": session.metadata.get("file_id"),
                "file_name": session.metadata.get("file_name"),
                "lang": session.metadata.get("lang", "ja"),
                "amount": session.amount_total,
                "currency": session.currency,
            }
    except Exception as e:
        st.error(f"決済確認エラー: {e}")
    return None


# ───────── メインフロー ─────────
query_params = st.query_params

# --- キャンセル時 ---
if query_params.get("cancelled"):
    st.warning("💳 決済がキャンセルされました。再度お試しください。")
    st.query_params.clear()

# --- 決済完了後の処理 ---
elif query_params.get("session_id") and query_params.get("file_id"):
    session_id = query_params["session_id"]
    file_id = query_params["file_id"]

    st.info("💳 決済を確認中...")
    payment = verify_payment(session_id)

    if payment is None:
        st.error("決済が確認できませんでした。お問い合わせください。")
        st.stop()

    st.success(f"✅ 決済完了！ ¥{payment['amount']:,} — 処理を開始します...")

    file_path = get_upload_path(file_id)
    if not file_path:
        st.error("ファイルが見つかりません。再度アップロードしてください。")
        st.stop()

    # 処理実行
    progress_bar = st.progress(0, text="準備中...")
    status_text = st.empty()

    step_progress = {"[前処理]": 5, "[1/4]": 10, "[2/4]": 40, "[3/4]": 70, "[4/4]": 90}

    def on_progress(kind, msg):
        if kind == "step":
            for key, val in step_progress.items():
                if msg.startswith(key):
                    progress_bar.progress(val, text=msg)
                    break
            status_text.text(msg)
        elif kind == "processing":
            status_text.text(f"  処理待ち: {msg}")
        elif kind == "upload_done":
            status_text.text(f"  アップロード完了: {msg}")

    try:
        transcript, summary, t_path, s_path, usage = run_pipeline(
            file_path=str(file_path),
            api_key=GEMINI_API_KEY,
            model=MODEL,
            lang=payment["lang"],
            output_dir="output",
            output_prefix=Path(payment["file_name"]).stem,
            on_progress=on_progress,
        )

        progress_bar.progress(100, text="完了!")
        status_text.empty()

        # コストレポート（内部参考用）
        total_cost = usage.calc_cost(MODEL, has_audio=True)

        st.divider()
        st.subheader("📊 結果")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("合計トークン", f"{usage.total_tokens:,}")
        with col2:
            st.metric("API原価 (USD)", f"${total_cost:.4f}")

        # 結果タブ
        tab1, tab2 = st.tabs(["📄 文字起こし", "📋 議事録"])

        with tab1:
            st.text_area("文字起こし", transcript, height=400, label_visibility="collapsed")
            st.download_button(
                "💾 ダウンロード (.txt)",
                data=transcript,
                file_name=Path(t_path).name,
                mime="text/plain",
            )

        with tab2:
            st.markdown(summary)
            st.divider()
            st.download_button(
                "💾 ダウンロード (.md)",
                data=summary,
                file_name=Path(s_path).name,
                mime="text/markdown",
            )

    except Exception as e:
        progress_bar.empty()
        status_text.empty()
        st.error(f"処理エラー: {e}")

    finally:
        cleanup_upload(file_id)
        st.query_params.clear()

# --- 通常（ファイルアップロード画面）---
else:
    st.markdown(f"""
    ### 使い方
    1. 音声/動画ファイルをアップロード
    2. 💳 **¥{PRICE_JPY:,}** でお支払い（クレジットカード）
    3. 文字起こし＋議事録が生成されます
    """)

    lang = st.selectbox(
        "🌐 出力言語 / Output Language",
        options=list(SUPPORTED_LANGUAGES.keys()),
        format_func=lambda k: SUPPORTED_LANGUAGES[k],
        index=0,
    )

    uploaded_file = st.file_uploader(
        "🎤 音声/動画ファイルを選択",
        type=["mp4", "m4a", "wav", "mp3", "webm", "ogg", "flac"],
        help="対応形式: mp4, m4a, wav, mp3, webm, ogg, flac",
    )

    if uploaded_file:
        file_size_mb = uploaded_file.size / (1024 * 1024)
        st.info(f"📁 **{uploaded_file.name}** ({file_size_mb:.1f} MB)")

        # ファイルを一時保存
        if "file_id" not in st.session_state or st.session_state.get("file_name") != uploaded_file.name:
            st.session_state.file_id = save_upload(uploaded_file)
            st.session_state.file_name = uploaded_file.name

        # 決済ボタン
        if st.button(
            f"💳 ¥{PRICE_JPY:,} で文字起こし・議事録を生成",
            type="primary",
            use_container_width=True,
        ):
            if not stripe.api_key or stripe.api_key.startswith("sk_test_ここに"):
                st.error("Stripe APIキーが設定されていません。.env を確認してください。")
                st.stop()

            with st.spinner("決済ページを準備中..."):
                checkout_url = create_checkout_session(
                    file_id=st.session_state.file_id,
                    file_name=uploaded_file.name,
                    lang=lang,
                )

            st.markdown(
                f'<meta http-equiv="refresh" content="0;url={checkout_url}">',
                unsafe_allow_html=True,
            )
            st.info("💳 Stripe決済ページに移動します... 自動で移動しない場合は下のボタンをクリック")
            st.link_button("💳 決済ページを開く", checkout_url, use_container_width=True)

    # フッター
    st.divider()
    st.caption("Powered by Google Gemini API | 決済: Stripe")
