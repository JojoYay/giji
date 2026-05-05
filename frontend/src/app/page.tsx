"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

const PRICE_JPY = parseInt(process.env.NEXT_PUBLIC_PRICE_JPY ?? "200", 10);

export default function LandingPage() {
  const { user } = useAuth();
  const ctaHref = "/upload";

  return (
    <main className="bg-white text-gray-800">
      {/* ──────── Hero ──────── */}
      <section className="relative overflow-hidden bg-gradient-to-br from-red-50 via-white to-orange-50">
        <div className="max-w-6xl mx-auto px-6 py-20 md:py-28 grid md:grid-cols-2 gap-10 items-center">
          <div>
            <span className="inline-block bg-red-100 text-red-700 text-xs font-semibold px-3 py-1 rounded-full mb-4">
              AI 議事録生成サービス
            </span>
            <h1 className="text-4xl md:text-5xl font-extrabold leading-tight mb-5">
              会議の録音を、<br />
              <span className="text-red-500">そのまま議事録に。</span>
            </h1>
            <p className="text-lg text-gray-600 mb-8 leading-relaxed">
              音声・動画ファイルをアップロードするだけで、AI が文字起こしと議事録を自動生成。
              <br />
              手作業の議事録づくりから解放されます。
            </p>
            <div className="flex flex-col sm:flex-row gap-3">
              <Link
                href={ctaHref}
                className="inline-block bg-red-500 hover:bg-red-600 text-white font-bold px-8 py-4 rounded-2xl shadow-md text-center transition-colors"
              >
                🚀 今すぐ試す
              </Link>
              {!user && (
                <Link
                  href="/login"
                  className="inline-block bg-white border border-gray-300 hover:bg-gray-50 text-gray-800 font-medium px-8 py-4 rounded-2xl text-center transition-colors"
                >
                  ログイン / 新規登録
                </Link>
              )}
            </div>
            <p className="text-xs text-gray-500 mt-4">
              ✅ 登録なしでも使えます ・ ✅ 1 件 ¥{PRICE_JPY.toLocaleString()} ・ ✅ 多言語対応
            </p>
          </div>

          {/* モックアップ */}
          <div className="relative">
            <div className="bg-white rounded-2xl shadow-xl border border-gray-200 p-6">
              <div className="flex gap-1.5 mb-4">
                <span className="w-3 h-3 rounded-full bg-red-400"></span>
                <span className="w-3 h-3 rounded-full bg-yellow-400"></span>
                <span className="w-3 h-3 rounded-full bg-green-400"></span>
              </div>
              <div className="space-y-3">
                <div className="bg-green-50 border border-green-200 rounded-lg p-3 flex items-center gap-2">
                  <span>✅</span>
                  <span className="text-sm">2026-04-24_定例会議.mp4</span>
                </div>
                <div className="bg-gray-50 rounded-lg p-3 text-sm space-y-1">
                  <div className="text-gray-400 text-xs">▼ 議事録（AI 生成）</div>
                  <div className="font-bold">📋 アジェンダ</div>
                  <div className="text-gray-600 ml-3">・Q2 売上レビュー</div>
                  <div className="text-gray-600 ml-3">・新機能リリース計画</div>
                  <div className="font-bold mt-2">✅ 決定事項</div>
                  <div className="text-gray-600 ml-3">・5/15 までに営業資料更新</div>
                  <div className="font-bold mt-2">🎯 アクションプラン</div>
                  <div className="text-gray-600 ml-3">・山田: 顧客分析（〜5/10）</div>
                </div>
              </div>
            </div>
            <div className="absolute -z-10 -top-6 -right-6 w-32 h-32 bg-red-200 rounded-full blur-3xl opacity-60"></div>
            <div className="absolute -z-10 -bottom-8 -left-8 w-40 h-40 bg-orange-200 rounded-full blur-3xl opacity-60"></div>
          </div>
        </div>
      </section>

      {/* ──────── 課題提起 ──────── */}
      <section className="py-20 bg-gray-50">
        <div className="max-w-5xl mx-auto px-6 text-center">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            こんな悩み、ありませんか？
          </h2>
          <p className="text-gray-500 mb-12">議事録は会議より時間がかかる、なんて本末転倒。</p>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { icon: "⏰", title: "議事録に時間がかかる", desc: "1 時間の会議で、議事録作成に 1〜2 時間かかってしまう。" },
              { icon: "📝", title: "聞き直しが面倒", desc: "重要な発言を聞き逃すと、録音を何度も巻き戻す手間が発生。" },
              { icon: "🌐", title: "多言語の会議に対応できない", desc: "海外メンバーとの会議で、議事録作成の負担が倍増。" },
            ].map((item) => (
              <div key={item.title} className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                <div className="text-4xl mb-3">{item.icon}</div>
                <h3 className="font-bold mb-2">{item.title}</h3>
                <p className="text-sm text-gray-600">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ──────── 機能 ──────── */}
      <section className="py-20">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-14">
            <span className="text-red-500 font-semibold text-sm uppercase tracking-wide">Features</span>
            <h2 className="text-3xl md:text-4xl font-bold mt-2 mb-3">
              本サービスの特徴
            </h2>
            <p className="text-gray-500">最新の Google Gemini AI が、議事録づくりを劇的に効率化します。</p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                icon: "🎙️",
                title: "高精度な自動文字起こし",
                desc: "音声・動画ファイルをアップロードするだけ。話者の発言を高精度に文字化します。",
              },
              {
                icon: "🤖",
                title: "AI による議事録自動生成",
                desc: "アジェンダ・決定事項・アクションプランを構造化して整理。すぐに共有可能な形式で出力。",
              },
              {
                icon: "🌐",
                title: "多言語対応",
                desc: "日本語・英語・中国語・マレー語に対応。グローバル会議の議事録もスマートに。",
              },
              {
                icon: "📑",
                title: "5 種類のテンプレート",
                desc: "標準・アクション重視・エグゼクティブ向け・詳細版・1on1。用途に合わせて選択。",
              },
              {
                icon: "📚",
                title: "参考資料で精度向上",
                desc: "会議資料 (PDF/Word/PowerPoint) を一緒にアップすると、専門用語の認識精度が向上。",
              },
              {
                icon: "🔒",
                title: "セキュアなインフラ",
                desc: "Google Cloud 上で処理・保存。決済は Stripe、認証は Firebase Authentication。",
              },
            ].map((f) => (
              <div
                key={f.title}
                className="bg-white border border-gray-100 rounded-2xl p-6 hover:shadow-md transition-shadow"
              >
                <div className="text-4xl mb-3">{f.icon}</div>
                <h3 className="font-bold text-lg mb-2">{f.title}</h3>
                <p className="text-sm text-gray-600 leading-relaxed">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ──────── 使い方 ──────── */}
      <section className="py-20 bg-gradient-to-b from-gray-50 to-white">
        <div className="max-w-5xl mx-auto px-6">
          <div className="text-center mb-14">
            <span className="text-red-500 font-semibold text-sm uppercase tracking-wide">How it works</span>
            <h2 className="text-3xl md:text-4xl font-bold mt-2 mb-3">
              たった 3 ステップ
            </h2>
            <p className="text-gray-500">録音から議事録まで、最短 5 分。</p>
          </div>

          <div className="space-y-6">
            {[
              {
                step: "1",
                title: "ファイルをアップロード",
                desc: "MP4・M4A・MP3・WAV など、主要な音声・動画形式に対応。最大数 GB まで対応。",
              },
              {
                step: "2",
                title: "会議情報を入力（任意）",
                desc: "テーマ・参加者・キーワード・専門用語辞書を入力すると、議事録の精度がさらに向上します。",
              },
              {
                step: "3",
                title: "AI が議事録を生成 → ダウンロード",
                desc: "数分〜十数分で文字起こしと議事録 (Markdown) が完成。テキストファイルでダウンロード可能。",
              },
            ].map((s) => (
              <div
                key={s.step}
                className="bg-white rounded-2xl border border-gray-100 p-6 flex items-start gap-5 shadow-sm"
              >
                <div className="bg-red-500 text-white font-bold text-2xl w-12 h-12 rounded-xl flex items-center justify-center shrink-0">
                  {s.step}
                </div>
                <div>
                  <h3 className="font-bold text-lg mb-1">{s.title}</h3>
                  <p className="text-sm text-gray-600">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ──────── 利用シーン ──────── */}
      <section className="py-20">
        <div className="max-w-6xl mx-auto px-6">
          <div className="text-center mb-14">
            <span className="text-red-500 font-semibold text-sm uppercase tracking-wide">Use cases</span>
            <h2 className="text-3xl md:text-4xl font-bold mt-2 mb-3">こんな場面で活躍</h2>
          </div>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { icon: "💼", t: "社内定例会議" },
              { icon: "🤝", t: "顧客との打ち合わせ" },
              { icon: "🎤", t: "セミナー・講演" },
              { icon: "🎓", t: "研修・勉強会" },
              { icon: "👥", t: "1on1 ミーティング" },
              { icon: "📞", t: "オンライン会議" },
              { icon: "🌍", t: "海外チームとの会議" },
              { icon: "📺", t: "インタビュー収録" },
            ].map((u) => (
              <div
                key={u.t}
                className="bg-white border border-gray-100 rounded-xl p-5 text-center hover:border-red-200 transition-colors"
              >
                <div className="text-3xl mb-1">{u.icon}</div>
                <div className="text-sm font-medium">{u.t}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ──────── 料金 ──────── */}
      <section className="py-20 bg-gradient-to-br from-red-50 to-orange-50">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <span className="text-red-500 font-semibold text-sm uppercase tracking-wide">Pricing</span>
          <h2 className="text-3xl md:text-4xl font-bold mt-2 mb-3">シンプルな料金体系</h2>
          <p className="text-gray-500 mb-10">使った分だけ。サブスク不要。</p>

          <div className="bg-white rounded-3xl shadow-lg border border-gray-100 p-10">
            <div className="text-sm text-gray-500 mb-2">1 会議あたり</div>
            <div className="flex items-baseline justify-center gap-1 mb-6">
              <span className="text-5xl font-extrabold text-gray-900">¥{PRICE_JPY.toLocaleString()}</span>
              <span className="text-gray-500">/ 件</span>
            </div>
            <ul className="text-left space-y-3 mb-8 max-w-xs mx-auto">
              {[
                "ファイルサイズ・時間制限なし",
                "文字起こし & 議事録 両方含む",
                "5 種類のテンプレート選択可",
                "多言語対応 (4 言語)",
                "参考資料の同時アップロード",
              ].map((b) => (
                <li key={b} className="flex items-center gap-2 text-sm">
                  <span className="text-green-500">✓</span>
                  {b}
                </li>
              ))}
            </ul>
            <Link
              href={ctaHref}
              className="block bg-red-500 hover:bg-red-600 text-white font-bold py-4 rounded-2xl transition-colors"
            >
              今すぐ始める
            </Link>
            <p className="text-xs text-gray-400 mt-4">
              決済は Stripe で安全に処理されます
            </p>
          </div>
        </div>
      </section>

      {/* ──────── FAQ ──────── */}
      <section className="py-20">
        <div className="max-w-3xl mx-auto px-6">
          <div className="text-center mb-12">
            <span className="text-red-500 font-semibold text-sm uppercase tracking-wide">FAQ</span>
            <h2 className="text-3xl md:text-4xl font-bold mt-2">よくある質問</h2>
          </div>
          <div className="space-y-3">
            {[
              {
                q: "対応している音声・動画フォーマットは？",
                a: "MP4・M4A・MP3・WAV・WEBM・OGG・FLAC・MKV・AVI・MOV など主要な形式に対応しています。",
              },
              {
                q: "会員登録は必要ですか？",
                a: "登録なしでもご利用いただけます。ログインすると過去の議事録が履歴として保存され、再ダウンロードが可能になります。",
              },
              {
                q: "アップロードしたファイルは保存されますか？",
                a: "処理完了後、入力された音声・動画ファイルは自動削除されます。生成された文字起こし・議事録は、ログインユーザーの履歴にのみ保存されます。",
              },
              {
                q: "再生成は可能ですか？",
                a: "完了済みのジョブから再度議事録を生成する場合は、再度料金が発生します（毎回 AI 処理が必要なため）。",
              },
              {
                q: "処理にはどれくらい時間がかかりますか？",
                a: "ファイルの長さによりますが、1 時間の会議録音で通常 3〜10 分程度です。",
              },
              {
                q: "領収書は発行できますか？",
                a: "Stripe の決済完了メールが領収書としてご利用いただけます。",
              },
            ].map((f) => (
              <details
                key={f.q}
                className="group bg-white border border-gray-100 rounded-xl p-5 open:shadow-sm"
              >
                <summary className="cursor-pointer font-medium flex justify-between items-center">
                  <span>Q. {f.q}</span>
                  <span className="text-red-500 group-open:rotate-45 transition-transform text-xl">+</span>
                </summary>
                <p className="mt-3 text-sm text-gray-600 leading-relaxed">A. {f.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ──────── 最終CTA ──────── */}
      <section className="py-16 bg-red-500">
        <div className="max-w-3xl mx-auto px-6 text-center text-white">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            議事録づくりを、今日から自動化。
          </h2>
          <p className="text-red-100 mb-8">
            最初の 1 件、まずはお試しください。
          </p>
          <Link
            href={ctaHref}
            className="inline-block bg-white text-red-500 hover:bg-red-50 font-bold px-10 py-4 rounded-2xl shadow-lg transition-colors"
          >
            🚀 議事録を作成する
          </Link>
        </div>
      </section>

      {/* ──────── Footer ──────── */}
      <footer className="bg-gray-900 text-gray-400 py-10 text-sm">
        <div className="max-w-5xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-4">
          <div>
            <div className="font-bold text-white mb-1">📝 議事録生成</div>
            <div className="text-xs">Powered by Google Gemini API</div>
          </div>
          <div className="text-xs">
            © {new Date().getFullYear()} jittee. All rights reserved.
          </div>
        </div>
      </footer>
    </main>
  );
}
