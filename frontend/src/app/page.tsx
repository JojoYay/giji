"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

const PRICE_JPY = parseInt(process.env.NEXT_PUBLIC_PRICE_JPY ?? "200", 10);

export default function LandingPage() {
  const { user } = useAuth();
  const ctaHref = "/upload";

  return (
    <main className="bg-white text-neutral-900">
      {/* ──────── Hero ──────── */}
      <section className="border-b border-neutral-200">
        <div className="max-w-6xl mx-auto px-6 pt-24 pb-20 md:pt-32 md:pb-28">
          <div className="max-w-3xl">
            <p className="text-sm text-neutral-500 mb-6 tracking-wide">
              AI Meeting Minutes
            </p>
            <h1 className="text-5xl md:text-7xl font-semibold tracking-tight leading-[1.05] mb-8">
              会議の録音を、
              <br />
              そのまま議事録に。
            </h1>
            <p className="text-lg md:text-xl text-neutral-600 leading-relaxed max-w-2xl mb-10">
              音声・動画ファイルをアップロードするだけ。
              文字起こしから議事録の構造化まで、自動で完了します。
              手作業の議事録づくりから、解放される。
            </p>
            <div className="flex flex-wrap items-center gap-4">
              <Link
                href={ctaHref}
                className="inline-flex items-center gap-2 bg-neutral-900 hover:bg-neutral-800 text-white font-medium px-6 py-3 rounded-full transition-colors"
              >
                はじめる
                <span aria-hidden>→</span>
              </Link>
              {!user && (
                <Link
                  href="/login"
                  className="inline-flex items-center gap-2 text-neutral-900 hover:text-neutral-600 font-medium px-2 py-3 transition-colors"
                >
                  ログイン
                </Link>
              )}
            </div>
            <p className="text-sm text-neutral-500 mt-8">
              1 件 ¥{PRICE_JPY.toLocaleString()}・登録不要・サブスクリプションなし
            </p>
          </div>
        </div>

        {/* Mock preview — minimal */}
        <div className="max-w-6xl mx-auto px-6 pb-20">
          <div className="border border-neutral-200 rounded-2xl overflow-hidden bg-neutral-50">
            <div className="px-6 py-3 border-b border-neutral-200 bg-white flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-neutral-300" />
              <span className="w-2.5 h-2.5 rounded-full bg-neutral-300" />
              <span className="w-2.5 h-2.5 rounded-full bg-neutral-300" />
              <span className="ml-3 text-xs text-neutral-500 font-mono">
                2026-05-05_strategy.mp4 — 議事録
              </span>
            </div>
            <div className="grid md:grid-cols-2 divide-y md:divide-y-0 md:divide-x divide-neutral-200">
              <div className="p-8">
                <p className="text-xs uppercase tracking-widest text-neutral-400 mb-4">
                  Transcript
                </p>
                <div className="space-y-3 text-sm text-neutral-700 leading-relaxed font-mono">
                  <p>
                    <span className="text-neutral-400">10:02</span>{" "}
                    山田: 今日の議題は二つ、Q2 のレビューと新機能のリリース計画です。
                  </p>
                  <p>
                    <span className="text-neutral-400">10:04</span>{" "}
                    吉田: Q2 は前年比 18% 増で着地見込み。詳細は資料の 3 ページ目を…
                  </p>
                  <p>
                    <span className="text-neutral-400">10:08</span>{" "}
                    渡辺: 営業資料の更新は 5/15 までに反映してほしい。
                  </p>
                </div>
              </div>
              <div className="p-8">
                <p className="text-xs uppercase tracking-widest text-neutral-400 mb-4">
                  Minutes
                </p>
                <div className="space-y-4 text-sm leading-relaxed">
                  <div>
                    <h4 className="font-semibold mb-1">アジェンダ</h4>
                    <ul className="text-neutral-600 space-y-0.5 list-disc list-inside">
                      <li>Q2 売上レビュー</li>
                      <li>新機能リリース計画</li>
                    </ul>
                  </div>
                  <div>
                    <h4 className="font-semibold mb-1">決定事項</h4>
                    <ul className="text-neutral-600 space-y-0.5 list-disc list-inside">
                      <li>5/15 までに営業資料を更新</li>
                    </ul>
                  </div>
                  <div>
                    <h4 className="font-semibold mb-1">アクション</h4>
                    <ul className="text-neutral-600 space-y-0.5 list-disc list-inside">
                      <li>山田 — 顧客分析（〜5/10）</li>
                      <li>吉田 — レビュー資料配布（〜5/8）</li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ──────── Why now ──────── */}
      <section className="border-b border-neutral-200">
        <div className="max-w-6xl mx-auto px-6 py-24 md:py-32">
          <div className="grid md:grid-cols-12 gap-10">
            <div className="md:col-span-5">
              <p className="text-sm text-neutral-500 mb-4 tracking-wide">Why</p>
              <h2 className="text-3xl md:text-4xl font-semibold tracking-tight leading-tight">
                議事録に、
                <br />
                時間を奪われない。
              </h2>
            </div>
            <div className="md:col-span-7 space-y-8 text-neutral-700">
              <p className="text-lg leading-relaxed">
                1 時間の会議に対して、議事録づくりに 1〜2 時間かけているチームは少なくありません。
                聞き直し、整形、共有 — そのすべてを AI に任せる時代です。
              </p>
              <div className="grid sm:grid-cols-3 gap-8 pt-4 border-t border-neutral-200">
                <div>
                  <p className="text-3xl font-semibold tracking-tight mb-1">最短 5 分</p>
                  <p className="text-sm text-neutral-500">音声から議事録まで</p>
                </div>
                <div>
                  <p className="text-3xl font-semibold tracking-tight mb-1">4 言語</p>
                  <p className="text-sm text-neutral-500">日・英・中・マレー</p>
                </div>
                <div>
                  <p className="text-3xl font-semibold tracking-tight mb-1">¥{PRICE_JPY}</p>
                  <p className="text-sm text-neutral-500">1 件あたり</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ──────── Features ──────── */}
      <section className="border-b border-neutral-200">
        <div className="max-w-6xl mx-auto px-6 py-24 md:py-32">
          <div className="mb-16">
            <p className="text-sm text-neutral-500 mb-4 tracking-wide">Features</p>
            <h2 className="text-3xl md:text-4xl font-semibold tracking-tight max-w-2xl">
              シンプルでありながら、必要な機能を。
            </h2>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 border-t border-l border-neutral-200">
            {[
              {
                t: "高精度な文字起こし",
                d: "Google Gemini の最新モデルが、話者の発言を高精度で文字化します。",
              },
              {
                t: "構造化された議事録",
                d: "アジェンダ・決定事項・アクションを整理。すぐに共有できる形で出力。",
              },
              {
                t: "多言語対応",
                d: "日本語・英語・中国語・マレー語で出力可能。グローバルな会議にも。",
              },
              {
                t: "5 種類のテンプレート",
                d: "標準・アクション重視・エグゼクティブ向け・詳細版・1on1。",
              },
              {
                t: "参考資料による精度向上",
                d: "PDF・Word・PowerPoint を一緒にアップロードすると専門用語の認識が向上。",
              },
              {
                t: "Google Cloud で稼働",
                d: "決済は Stripe、認証は Firebase Authentication。安心して利用可能。",
              },
            ].map((f) => (
              <div
                key={f.t}
                className="border-r border-b border-neutral-200 p-8"
              >
                <h3 className="font-semibold mb-2">{f.t}</h3>
                <p className="text-sm text-neutral-600 leading-relaxed">{f.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ──────── How it works ──────── */}
      <section className="border-b border-neutral-200">
        <div className="max-w-6xl mx-auto px-6 py-24 md:py-32">
          <div className="mb-16">
            <p className="text-sm text-neutral-500 mb-4 tracking-wide">How it works</p>
            <h2 className="text-3xl md:text-4xl font-semibold tracking-tight max-w-2xl">
              3 ステップで完了。
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-px bg-neutral-200">
            {[
              {
                n: "01",
                t: "アップロード",
                d: "MP4・M4A・MP3・WAV など、主要な音声・動画形式に対応。複数ファイルも可。",
              },
              {
                n: "02",
                t: "情報入力（任意）",
                d: "テーマ・参加者・キーワード・専門用語辞書を入力すると、精度が向上します。",
              },
              {
                n: "03",
                t: "ダウンロード",
                d: "数分〜十数分で文字起こしと議事録が完成。テキスト / Markdown 形式で取得。",
              },
            ].map((s) => (
              <div key={s.n} className="bg-white p-10">
                <p className="text-sm font-mono text-neutral-400 mb-6">{s.n}</p>
                <h3 className="text-xl font-semibold mb-3">{s.t}</h3>
                <p className="text-sm text-neutral-600 leading-relaxed">{s.d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ──────── Use cases ──────── */}
      <section className="border-b border-neutral-200">
        <div className="max-w-6xl mx-auto px-6 py-24 md:py-32">
          <div className="grid md:grid-cols-12 gap-10">
            <div className="md:col-span-5">
              <p className="text-sm text-neutral-500 mb-4 tracking-wide">Use cases</p>
              <h2 className="text-3xl md:text-4xl font-semibold tracking-tight leading-tight">
                あらゆる会議に。
              </h2>
            </div>
            <div className="md:col-span-7">
              <ul className="divide-y divide-neutral-200 border-y border-neutral-200">
                {[
                  "社内定例会議",
                  "顧客との打ち合わせ",
                  "セミナー・講演",
                  "研修・勉強会",
                  "1on1 ミーティング",
                  "オンライン会議",
                  "海外チームとの会議",
                  "インタビュー収録",
                ].map((u) => (
                  <li
                    key={u}
                    className="py-4 flex items-center justify-between text-neutral-800"
                  >
                    <span>{u}</span>
                    <span className="text-neutral-300" aria-hidden>—</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* ──────── Pricing ──────── */}
      <section className="border-b border-neutral-200">
        <div className="max-w-3xl mx-auto px-6 py-24 md:py-32 text-center">
          <p className="text-sm text-neutral-500 mb-4 tracking-wide">Pricing</p>
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight mb-12">
            使った分だけ、シンプルに。
          </h2>

          <div className="border border-neutral-200 rounded-2xl p-12">
            <p className="text-sm text-neutral-500 mb-3">1 会議あたり</p>
            <div className="flex items-baseline justify-center gap-1 mb-10">
              <span className="text-6xl md:text-7xl font-semibold tracking-tight">
                ¥{PRICE_JPY.toLocaleString()}
              </span>
              <span className="text-neutral-500 ml-2">/ 件</span>
            </div>
            <ul className="text-left space-y-3 max-w-sm mx-auto mb-10 text-sm">
              {[
                "ファイルサイズ・時間制限なし",
                "文字起こし & 議事録 両方含む",
                "5 種類のテンプレート選択可",
                "多言語対応 (4 言語)",
                "参考資料の同時アップロード",
              ].map((b) => (
                <li key={b} className="flex items-center gap-3 text-neutral-700">
                  <span className="text-neutral-300" aria-hidden>—</span>
                  {b}
                </li>
              ))}
            </ul>
            <Link
              href={ctaHref}
              className="inline-flex items-center gap-2 bg-neutral-900 hover:bg-neutral-800 text-white font-medium px-6 py-3 rounded-full transition-colors"
            >
              はじめる
              <span aria-hidden>→</span>
            </Link>
            <p className="text-xs text-neutral-400 mt-6">
              決済は Stripe で安全に処理されます
            </p>
          </div>
        </div>
      </section>

      {/* ──────── FAQ ──────── */}
      <section className="border-b border-neutral-200">
        <div className="max-w-3xl mx-auto px-6 py-24 md:py-32">
          <p className="text-sm text-neutral-500 mb-4 tracking-wide">FAQ</p>
          <h2 className="text-3xl md:text-4xl font-semibold tracking-tight mb-12">
            よくある質問
          </h2>
          <div className="divide-y divide-neutral-200 border-y border-neutral-200">
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
              <details key={f.q} className="group py-5">
                <summary className="cursor-pointer flex justify-between items-center font-medium list-none">
                  <span>{f.q}</span>
                  <span
                    className="text-neutral-400 group-open:rotate-45 transition-transform text-xl shrink-0 ml-4"
                    aria-hidden
                  >
                    +
                  </span>
                </summary>
                <p className="mt-3 text-sm text-neutral-600 leading-relaxed">
                  {f.a}
                </p>
              </details>
            ))}
          </div>
        </div>
      </section>

      {/* ──────── Final CTA ──────── */}
      <section className="bg-neutral-900 text-white">
        <div className="max-w-4xl mx-auto px-6 py-24 md:py-32 text-center">
          <h2 className="text-4xl md:text-5xl font-semibold tracking-tight mb-6">
            議事録を、自動化する。
          </h2>
          <p className="text-neutral-400 mb-10 max-w-xl mx-auto">
            最初の 1 件、まずはお試しください。登録もサブスクリプションも必要ありません。
          </p>
          <Link
            href={ctaHref}
            className="inline-flex items-center gap-2 bg-white text-neutral-900 hover:bg-neutral-100 font-medium px-8 py-4 rounded-full transition-colors"
          >
            はじめる
            <span aria-hidden>→</span>
          </Link>
        </div>
      </section>

      {/* ──────── Footer ──────── */}
      <footer className="bg-white border-t border-neutral-200">
        <div className="max-w-6xl mx-auto px-6 py-12 flex flex-col md:flex-row justify-between items-start md:items-center gap-6">
          <div>
            <p className="font-semibold mb-1">議事録生成</p>
            <p className="text-xs text-neutral-500">
              Powered by Google Gemini · operated by JITTEE PTE. LTD.
            </p>
          </div>
          <p className="text-xs text-neutral-500">
            © {new Date().getFullYear()} jittee. All rights reserved.
          </p>
        </div>
      </footer>
    </main>
  );
}
