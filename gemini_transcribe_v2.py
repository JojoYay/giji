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

# ───────── 要約テンプレート ─────────

SUMMARY_TEMPLATES = {
    "standard": {
        "name": {"ja": "📋 標準議事録", "en": "📋 Standard Minutes", "zh": "📋 标准会议纪要", "ms": "📋 Minit Standard"},
        "description": {"ja": "基本情報・討議内容・決定事項・TODOを網羅した標準フォーマット",
                        "en": "Comprehensive format covering basic info, discussion, decisions, and action items",
                        "zh": "涵盖基本信息、讨论、决定和行动项的标准格式",
                        "ms": "Format komprehensif merangkumi maklumat asas, perbincangan, keputusan dan tindakan"},
        "template": {
            "ja": """# 議事録

## 基本情報
- 日時:
- 参加者:
- 会議形式: Web会議

## 議題・目的

## 討議内容

## 決定事項

## TODO・アクションアイテム
| 担当者 | 内容 | 期限 |
|--------|------|------|

## 次回予定

## その他・備考""",
            "en": """# Meeting Minutes

## Basic Information
- Date/Time:
- Participants:
- Format: Web meeting

## Agenda / Purpose

## Discussion

## Decisions Made

## Action Items
| Assignee | Task | Deadline |
|----------|------|----------|

## Next Meeting

## Notes""",
            "zh": """# 会议纪要

## 基本信息
- 日期时间:
- 参会人员:
- 会议形式: 网络会议

## 议题与目的

## 讨论内容

## 决定事项

## 待办事项
| 负责人 | 内容 | 截止日期 |
|--------|------|----------|

## 下次会议

## 其他备注""",
            "ms": """# Minit Mesyuarat

## Maklumat Asas
- Tarikh/Masa:
- Peserta:
- Format: Mesyuarat web

## Agenda / Tujuan

## Perbincangan

## Keputusan

## Tindakan Susulan
| Bertanggungjawab | Tugasan | Tarikh Akhir |
|------------------|---------|--------------|

## Mesyuarat Seterusnya

## Catatan""",
        },
    },
    "action_focused": {
        "name": {"ja": "🎯 アクション重視", "en": "🎯 Action-Focused", "zh": "🎯 行动导向", "ms": "🎯 Fokus Tindakan"},
        "description": {"ja": "決定事項とアクションアイテムを最上部に配置。実行管理向け",
                        "en": "Decisions and action items at the top. Best for execution tracking",
                        "zh": "决定事项和行动项置顶，适合执行管理",
                        "ms": "Keputusan dan tindakan di atas. Terbaik untuk pengurusan pelaksanaan"},
        "template": {
            "ja": """# 議事録（アクション重視）

## 🎯 決定事項（即時対応）

## 📋 アクションアイテム
| # | 担当者 | タスク内容 | 期限 | 優先度 |
|---|--------|-----------|------|--------|

## 📅 次回予定
- 日時:
- 議題:

---

## 基本情報
- 日時:
- 参加者:

## 討議サマリー

## 保留事項・リスク""",
            "en": """# Meeting Minutes (Action-Focused)

## 🎯 Decisions (Immediate)

## 📋 Action Items
| # | Assignee | Task | Deadline | Priority |
|---|----------|------|----------|----------|

## 📅 Next Meeting
- Date:
- Agenda:

---

## Basic Information
- Date/Time:
- Participants:

## Discussion Summary

## Open Items / Risks""",
            "zh": """# 会议纪要（行动导向）

## 🎯 决定事项（立即执行）

## 📋 行动项
| # | 负责人 | 任务内容 | 截止日期 | 优先级 |
|---|--------|---------|----------|--------|

## 📅 下次会议
- 日期:
- 议题:

---

## 基本信息
- 日期时间:
- 参会人员:

## 讨论摘要

## 待定事项/风险""",
            "ms": """# Minit Mesyuarat (Fokus Tindakan)

## 🎯 Keputusan (Segera)

## 📋 Tindakan Susulan
| # | Bertanggungjawab | Tugasan | Tarikh Akhir | Keutamaan |
|---|------------------|---------|--------------|-----------|

## 📅 Mesyuarat Seterusnya
- Tarikh:
- Agenda:

---

## Maklumat Asas
- Tarikh/Masa:
- Peserta:

## Ringkasan Perbincangan

## Perkara Tertangguh / Risiko""",
        },
    },
    "executive": {
        "name": {"ja": "📊 エグゼクティブサマリー", "en": "📊 Executive Summary", "zh": "📊 高管摘要", "ms": "📊 Ringkasan Eksekutif"},
        "description": {"ja": "経営層向け。要点を簡潔にまとめた短い報告形式",
                        "en": "For leadership. Brief, high-level summary format",
                        "zh": "面向管理层，简洁的高层摘要格式",
                        "ms": "Untuk kepimpinan. Ringkasan ringkas peringkat tinggi"},
        "template": {
            "ja": """# エグゼクティブサマリー

## 会議概要
**日時:** / **参加者:** / **テーマ:**

## 要旨（3行以内）

## 主要な決定事項
1.
2.
3.

## 経営判断が必要な事項

## 次のステップ

## リスク・懸念事項""",
            "en": """# Executive Summary

## Meeting Overview
**Date:** / **Participants:** / **Topic:**

## Key Takeaways (3 lines max)

## Major Decisions
1.
2.
3.

## Items Requiring Leadership Decision

## Next Steps

## Risks / Concerns""",
            "zh": """# 高管摘要

## 会议概要
**日期:** / **参会人员:** / **主题:**

## 要点（3行以内）

## 主要决定
1.
2.
3.

## 需要管理层决策的事项

## 下一步

## 风险/关注事项""",
            "ms": """# Ringkasan Eksekutif

## Gambaran Mesyuarat
**Tarikh:** / **Peserta:** / **Topik:**

## Perkara Utama (3 baris maks)

## Keputusan Utama
1.
2.
3.

## Perkara Memerlukan Keputusan Kepimpinan

## Langkah Seterusnya

## Risiko / Kebimbangan""",
        },
    },
    "detailed": {
        "name": {"ja": "📝 詳細記録", "en": "📝 Detailed Record", "zh": "📝 详细记录", "ms": "📝 Rekod Terperinci"},
        "description": {"ja": "発言者ごとの意見を詳細に記録。証跡・監査向け",
                        "en": "Detailed record with per-speaker opinions. For audit/compliance",
                        "zh": "按发言人详细记录意见，适合审计/合规",
                        "ms": "Rekod terperinci mengikut penutur. Untuk audit/pematuhan"},
        "template": {
            "ja": """# 詳細議事録

## 基本情報
- 日時:
- 参加者:
- 記録形式: 詳細記録

## 議題

## 発言記録
### 議題1:
- **[発言者名]**: （意見・発言の要約）
- **[発言者名]**: （意見・発言の要約）
→ **結論:**

### 議題2:
- **[発言者名]**: （意見・発言の要約）
→ **結論:**

## 全体の決定事項

## アクションアイテム
| 担当者 | 内容 | 期限 | 関連議題 |
|--------|------|------|----------|

## 未解決事項

## 次回予定""",
            "en": """# Detailed Meeting Record

## Basic Information
- Date/Time:
- Participants:
- Record Type: Detailed

## Agenda

## Discussion Record
### Topic 1:
- **[Speaker]**: (summary of opinion)
- **[Speaker]**: (summary of opinion)
→ **Conclusion:**

### Topic 2:
- **[Speaker]**: (summary of opinion)
→ **Conclusion:**

## Overall Decisions

## Action Items
| Assignee | Task | Deadline | Related Topic |
|----------|------|----------|---------------|

## Unresolved Items

## Next Meeting""",
            "zh": """# 详细会议记录

## 基本信息
- 日期时间:
- 参会人员:
- 记录类型: 详细记录

## 议题

## 发言记录
### 议题1:
- **[发言人]**: （意见摘要）
- **[发言人]**: （意见摘要）
→ **结论:**

### 议题2:
- **[发言人]**: （意见摘要）
→ **结论:**

## 整体决定事项

## 行动项
| 负责人 | 内容 | 截止日期 | 相关议题 |
|--------|------|----------|----------|

## 未解决事项

## 下次会议""",
            "ms": """# Rekod Mesyuarat Terperinci

## Maklumat Asas
- Tarikh/Masa:
- Peserta:
- Jenis Rekod: Terperinci

## Agenda

## Rekod Perbincangan
### Topik 1:
- **[Penutur]**: (ringkasan pendapat)
- **[Penutur]**: (ringkasan pendapat)
→ **Kesimpulan:**

### Topik 2:
- **[Penutur]**: (ringkasan pendapat)
→ **Kesimpulan:**

## Keputusan Keseluruhan

## Tindakan Susulan
| Bertanggungjawab | Tugasan | Tarikh Akhir | Topik Berkaitan |
|------------------|---------|--------------|-----------------|

## Perkara Belum Selesai

## Mesyuarat Seterusnya""",
        },
    },
    "oneonone": {
        "name": {"ja": "👤 1on1 ミーティング", "en": "👤 1-on-1 Meeting", "zh": "👤 一对一会议", "ms": "👤 Mesyuarat 1-on-1"},
        "description": {"ja": "上司と部下の1on1面談向け。フィードバック・目標・次回フォロー",
                        "en": "For manager-report 1:1s. Feedback, goals, follow-ups",
                        "zh": "上下级一对一面谈，反馈、目标、跟进",
                        "ms": "Untuk mesyuarat 1:1 pengurus. Maklum balas, matlamat, susulan"},
        "template": {
            "ja": """# 1on1 ミーティングノート

## 基本情報
- 日時:
- 参加者:

## 前回のフォローアップ

## 今回の議題
### 業務状況・進捗

### 課題・困っていること

### フィードバック（双方向）

### キャリア・成長

## 合意事項・ネクストアクション
| 誰が | 何を | いつまでに |
|------|------|-----------|

## 次回1on1
- 日時:
- フォローアップ項目:""",
            "en": """# 1-on-1 Meeting Notes

## Basic Information
- Date/Time:
- Participants:

## Follow-up from Last Meeting

## Today's Topics
### Work Status / Progress

### Challenges / Blockers

### Feedback (Bidirectional)

### Career / Growth

## Agreements & Next Actions
| Who | What | By When |
|-----|------|---------|

## Next 1-on-1
- Date:
- Follow-up Items:""",
            "zh": """# 一对一会议记录

## 基本信息
- 日期时间:
- 参会人员:

## 上次会议跟进

## 本次议题
### 工作状态/进展

### 挑战/障碍

### 反馈（双向）

### 职业发展

## 共识与下一步行动
| 负责人 | 任务 | 截止日期 |
|--------|------|----------|

## 下次一对一
- 日期:
- 跟进事项:""",
            "ms": """# Nota Mesyuarat 1-on-1

## Maklumat Asas
- Tarikh/Masa:
- Peserta:

## Susulan Mesyuarat Lepas

## Topik Hari Ini
### Status Kerja / Kemajuan

### Cabaran / Halangan

### Maklum Balas (Dua Hala)

### Kerjaya / Pertumbuhan

## Persetujuan & Tindakan Seterusnya
| Siapa | Apa | Bila |
|-------|-----|------|

## 1-on-1 Seterusnya
- Tarikh:
- Perkara Susulan:""",
        },
    },
    "custom": {
        "name": {"ja": "✏️ カスタム", "en": "✏️ Custom", "zh": "✏️ 自定义", "ms": "✏️ Tersuai"},
        "description": {"ja": "自由にテンプレートを編集できます",
                        "en": "Freely edit the template",
                        "zh": "自由编辑模板",
                        "ms": "Edit templat secara bebas"},
        "template": {"ja": "", "en": "", "zh": "", "ms": ""},
    },
}


def _build_summary_instruction(lang: str, template_text: str) -> str:
    """テンプレートをもとに要約指示文を生成する。"""
    placeholder = "{transcript}"
    base = {
        "ja": "以下はビジネス会議の文字起こしです。以下のテンプレートの構造・見出しに厳密に従って議事録を日本語で作成してください。テンプレートの各セクションに該当する内容を文字起こしから抽出して記入してください。該当内容がないセクションは「特になし」と記載してください。",
        "en": 'Below is a meeting transcription. Create meeting minutes in English strictly following the structure and headings of the template below. Fill each section with relevant content from the transcription. If a section has no relevant content, write "N/A".',
        "zh": "以下是会议的文字记录。请严格按照以下模板的结构和标题用中文撰写会议纪要。将文字记录中的相关内容填入各部分。如某部分无相关内容，请写「无」。",
        "ms": 'Berikut ialah transkripsi mesyuarat. Sila buat minit mesyuarat dalam Bahasa Melayu mengikut struktur dan tajuk templat berikut dengan ketat. Isi setiap bahagian dengan kandungan berkaitan daripada transkripsi. Jika tiada kandungan berkaitan, tulis "Tiada".',
    }
    tpl_label = {"ja": "テンプレート", "en": "Template", "zh": "模板", "ms": "Templat"}
    txt_label = {"ja": "文字起こし", "en": "Transcription", "zh": "文字记录", "ms": "Transkripsi"}
    instruction = base.get(lang, base["ja"])
    tl = tpl_label.get(lang, "テンプレート")
    xl = txt_label.get(lang, "文字起こし")
    return f"{instruction}\n\n【{tl}】\n{template_text}\n\n---\n{xl}:\n{placeholder}"


# 後方互換のため残す（テンプレートなしの場合のフォールバック）
SUMMARY_PROMPTS = {}
for _lang_code in SUPPORTED_LANGUAGES:
    _tpl = SUMMARY_TEMPLATES["standard"]["template"].get(_lang_code, "")
    SUMMARY_PROMPTS[_lang_code] = _build_summary_instruction(_lang_code, _tpl)


# デフォルト要約方針（UIでユーザーに見せる）
DEFAULT_SUMMARY_GUIDELINES = {
    "ja": (
        "・基本情報（日時・参加者）、議題、討議内容、決定事項、TODOを構造化して記載\n"
        "・アクションアイテムは表形式（担当者・内容・期限）で記載\n"
        "・客観的・簡潔な文体で記載"
    ),
    "en": (
        "• Structured format: basic info, agenda, discussion, decisions, action items\n"
        "• Action items in table format (assignee, task, deadline)\n"
        "• Objective and concise writing style"
    ),
    "zh": (
        "・基本信息、议题、讨论内容、决定事项、待办事项以结构化方式记载\n"
        "・待办事项以表格形式（负责人、内容、截止日期）记载\n"
        "・客观简洁的文体"
    ),
    "ms": (
        "• Format berstruktur: maklumat asas, agenda, perbincangan, keputusan, tindakan\n"
        "• Tindakan susulan dalam format jadual (bertanggungjawab, tugasan, tarikh akhir)\n"
        "• Gaya penulisan objektif dan ringkas"
    ),
}


@dataclass
class MeetingContext:
    """会議のメタ情報と追加コンテキスト。"""
    date: str = ""              # "2024-04-14"
    time: str = ""              # "10:00-12:00"
    topic: str = ""             # "住宅手当の減額に関する協議"
    participants: str = ""      # "山田, 吉田, 渡辺"
    keywords: str = ""          # "住宅手当, RPA, KPI"
    glossary: str = ""          # "RPA=Robotic Process Automation\nKPI=Key Performance Indicator"
    custom_instructions: str = ""  # "ですます調で / アクションプランを詳細に"
    reference_texts: list = field(default_factory=list)  # 参考資料のテキスト抽出結果


def _build_context_block(ctx: MeetingContext, lang: str = "ja") -> str:
    """MeetingContext から追加プロンプトブロックを構築する。"""
    parts = []

    if lang == "ja":
        if ctx.date or ctx.time:
            dt = f"{ctx.date} {ctx.time}".strip()
            parts.append(f"【会議日時】{dt}")
        if ctx.topic:
            parts.append(f"【会議テーマ・議題】{ctx.topic}")
        if ctx.participants:
            parts.append(f"【参加者】{ctx.participants}\n※ 音声の話者をできる限りこの参加者名に紐づけてください。")
        if ctx.keywords:
            parts.append(f"【重要キーワード】\n以下の用語が登場する可能性があります。正確に書き起こしてください:\n{ctx.keywords}")
        if ctx.glossary:
            parts.append(f"【専門用語辞書】\n以下の略語・専門用語を正しく使用してください:\n{ctx.glossary}")
        if ctx.reference_texts:
            parts.append("【参考資料の内容（抜粋）】\n以下は会議に関連する参考資料です。この中の用語・固有名詞を正確に使用してください:")
            for i, txt in enumerate(ctx.reference_texts, 1):
                parts.append(f"--- 資料{i} ---\n{txt[:3000]}")
    else:
        labels = {
            "en": {"dt": "Meeting Date/Time", "topic": "Meeting Topic", "participants": "Participants",
                   "kw": "Key Terms", "glossary": "Glossary", "ref": "Reference Materials",
                   "participant_note": "Please try to match speakers to these participant names.",
                   "kw_note": "The following terms may appear. Transcribe them accurately:",
                   "glossary_note": "Use these abbreviations/terms correctly:",
                   "ref_note": "Below are excerpts from reference materials. Use the terms and proper nouns from these accurately:"},
            "zh": {"dt": "会议日期时间", "topic": "会议主题", "participants": "参会人员",
                   "kw": "重要术语", "glossary": "专业术语表", "ref": "参考资料",
                   "participant_note": "请尽量将发言人与以上参会人员对应。",
                   "kw_note": "以下术语可能出现，请准确转录:", "glossary_note": "请正确使用以下缩写/术语:",
                   "ref_note": "以下是参考资料摘录，请准确使用其中的术语和专有名词:"},
            "ms": {"dt": "Tarikh/Masa Mesyuarat", "topic": "Topik Mesyuarat", "participants": "Peserta",
                   "kw": "Istilah Penting", "glossary": "Glosari", "ref": "Bahan Rujukan",
                   "participant_note": "Sila padankan penutur dengan nama peserta ini.",
                   "kw_note": "Istilah berikut mungkin muncul. Transkripsi dengan tepat:",
                   "glossary_note": "Gunakan singkatan/istilah ini dengan betul:",
                   "ref_note": "Berikut adalah petikan bahan rujukan. Gunakan istilah dan nama khas dengan tepat:"},
        }
        L = labels.get(lang, labels["en"])
        if ctx.date or ctx.time:
            parts.append(f"[{L['dt']}] {ctx.date} {ctx.time}".strip())
        if ctx.topic:
            parts.append(f"[{L['topic']}] {ctx.topic}")
        if ctx.participants:
            parts.append(f"[{L['participants']}] {ctx.participants}\n{L['participant_note']}")
        if ctx.keywords:
            parts.append(f"[{L['kw']}]\n{L['kw_note']}\n{ctx.keywords}")
        if ctx.glossary:
            parts.append(f"[{L['glossary']}]\n{L['glossary_note']}\n{ctx.glossary}")
        if ctx.reference_texts:
            parts.append(f"[{L['ref']}]\n{L['ref_note']}")
            for i, txt in enumerate(ctx.reference_texts, 1):
                parts.append(f"--- Doc {i} ---\n{txt[:3000]}")

    return "\n\n".join(parts)


def get_transcript_prompt(lang: str = "ja", ctx: MeetingContext | None = None) -> str:
    prompt = TRANSCRIPT_PROMPTS.get(lang, TRANSCRIPT_PROMPTS["ja"])
    if ctx:
        block = _build_context_block(ctx, lang)
        if block:
            prompt += "\n" + block + "\n"
    return prompt


def get_summary_prompt(lang: str = "ja", ctx: MeetingContext | None = None,
                       template_key: str = "standard", custom_template: str = "") -> str:
    """テンプレートに基づいた要約プロンプトを生成する。"""
    # テンプレートテキストを決定
    if template_key == "custom" and custom_template:
        template_text = custom_template
    elif template_key in SUMMARY_TEMPLATES:
        template_text = SUMMARY_TEMPLATES[template_key]["template"].get(lang, "")
    else:
        template_text = SUMMARY_TEMPLATES["standard"]["template"].get(lang, "")

    if template_text:
        prompt = _build_summary_instruction(lang, template_text)
    else:
        prompt = SUMMARY_PROMPTS.get(lang, SUMMARY_PROMPTS["ja"])

    if ctx:
        meta_parts = []
        if ctx.date or ctx.time:
            meta_parts.append(f"日時: {ctx.date} {ctx.time}".strip())
        if ctx.topic:
            meta_parts.append(f"テーマ: {ctx.topic}")
        if ctx.participants:
            meta_parts.append(f"参加者: {ctx.participants}")
        if meta_parts:
            prompt = prompt.replace("{transcript}", "\n".join(meta_parts) + "\n\n{transcript}")
        if ctx.custom_instructions:
            injection = {
                "ja": f"\n【追加の要約指示】\n以下の指示にも従ってください:\n{ctx.custom_instructions}\n",
                "en": f"\n[Additional Instructions]\nPlease also follow these instructions:\n{ctx.custom_instructions}\n",
                "zh": f"\n【额外要约指示】\n请同时遵循以下指示:\n{ctx.custom_instructions}\n",
                "ms": f"\n[Arahan Tambahan]\nSila ikut juga arahan berikut:\n{ctx.custom_instructions}\n",
            }
            prompt += injection.get(lang, injection["ja"])
    return prompt


# ───────── 2パス校正プロンプト ─────────

CORRECTION_PROMPTS = {
    "ja": """\
以下は会議音声の粗い文字起こしです。参考資料・会議コンテキスト・専門用語辞書をもとに校正してください。

【校正ルール】
- 専門用語・固有名詞を参考資料の表記に統一する
- 話者名をできる限り参加者名に紐づける
- 明らかな聞き間違い・誤変換を修正する
- タイムスタンプと発言のフォーマットは維持する
- 修正できない不明瞭な箇所はそのまま残す

{context_block}

--- 粗い文字起こし ---
{raw_transcript}
""",
    "en": """\
Below is a rough transcription of a meeting. Please correct it using the reference materials, meeting context, and glossary.

[Correction Rules]
- Unify technical terms and proper nouns to match reference materials
- Map speaker labels to participant names where possible
- Fix obvious mishearings and transcription errors
- Maintain timestamp and speaker format
- Keep unclear parts as-is if they cannot be resolved

{context_block}

--- Rough Transcription ---
{raw_transcript}
""",
    "zh": """\
以下是会议录音的初步转录。请根据参考资料、会议背景和术语表进行校正。

【校正规则】
- 将专业术语和专有名词统一为参考资料中的表述
- 尽可能将发言人与参会人员对应
- 修正明显的听错和转录错误
- 保持时间戳和发言格式
- 无法解决的不清楚部分保持原样

{context_block}

--- 初步转录 ---
{raw_transcript}
""",
    "ms": """\
Berikut ialah transkripsi kasar rakaman mesyuarat. Sila betulkan menggunakan bahan rujukan, konteks mesyuarat, dan glosari.

[Peraturan Pembetulan]
- Seragamkan istilah teknikal dan nama khas mengikut bahan rujukan
- Padankan label penutur dengan nama peserta jika boleh
- Betulkan kesilapan pendengaran dan transkripsi yang jelas
- Kekalkan format cap masa dan penutur
- Kekalkan bahagian yang tidak jelas jika tidak dapat diselesaikan

{context_block}

--- Transkripsi Kasar ---
{raw_transcript}
"""
}

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


def _normalize_audio(file_path: str, on_progress=None) -> str | None:
    """音声のノイズ除去と音量正規化を行い、一時ファイルのパスを返す。"""
    ffmpeg_bin = _get_ffmpeg()
    if not ffmpeg_bin:
        return None

    if on_progress:
        on_progress("step", "[前処理] 音声ノイズ除去・音量正規化中...")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".m4a", prefix="norm_")
    tmp.close()

    # highpass: 低周波ノイズ除去, afftdn: FFTベースノイズ除去, loudnorm: 音量正規化
    cmd = [
        ffmpeg_bin, "-y", "-i", file_path,
        "-af", "highpass=f=80,afftdn=nf=-25,loudnorm=I=-16:TP=-1.5:LRA=11",
        "-acodec", "aac", "-b:a", "64k", "-ac", "1", "-ar", "16000",
        tmp.name,
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        # フィルター非対応の場合は loudnorm のみ
        cmd = [
            ffmpeg_bin, "-y", "-i", file_path,
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-acodec", "aac", "-b:a", "64k", "-ac", "1", "-ar", "16000",
            tmp.name,
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass
            return None

    if on_progress:
        on_progress("step", "[前処理] 音声正規化完了")
    return tmp.name


# ───────── 音声分割 ─────────

CHUNK_DURATION_SEC = 15 * 60  # 15分ごとに分割
AUDIO_EXTENSIONS = {".m4a", ".wav", ".mp3", ".ogg", ".flac", ".aac", ".wma"}


def _get_audio_duration(file_path: str, ffmpeg_bin: str) -> float | None:
    """ffprobeで音声ファイルの長さ（秒）を取得する。"""
    # ffprobe は ffmpeg と同じディレクトリにある
    ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe")
    if not Path(ffprobe_bin).exists() and ffmpeg_bin != "ffmpeg":
        ffprobe_bin = str(Path(ffmpeg_bin).parent / "ffprobe")
    try:
        result = subprocess.run(
            [ffprobe_bin, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            capture_output=True, text=True, timeout=30,
        )
        return float(result.stdout.strip())
    except Exception:
        # ffprobe が無い場合は ffmpeg で取得
        try:
            result = subprocess.run(
                [ffmpeg_bin, "-i", file_path, "-f", "null", "-"],
                capture_output=True, text=True, timeout=300,
            )
            # stderr から "Duration: HH:MM:SS.xx" を探す
            import re
            m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", result.stderr)
            if m:
                return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
        except Exception:
            pass
    return None


def _split_audio(file_path: str, chunk_sec: int = CHUNK_DURATION_SEC,
                 on_progress=None) -> list[str] | None:
    """音声ファイルを chunk_sec 秒ごとに分割し、一時ファイルのパスリストを返す。
    分割不要（短い）場合は None を返す。"""
    ffmpeg_bin = _get_ffmpeg()
    if not ffmpeg_bin:
        return None

    duration = _get_audio_duration(file_path, ffmpeg_bin)
    if duration is None or duration <= chunk_sec:
        return None  # 分割不要

    num_chunks = int(duration // chunk_sec) + (1 if duration % chunk_sec > 0 else 0)
    if on_progress:
        on_progress("step", f"[前処理] 音声を{num_chunks}チャンクに分割中 (計{int(duration//60)}分)...")

    suffix = Path(file_path).suffix or ".m4a"
    chunks = []

    for i in range(num_chunks):
        start_sec = i * chunk_sec
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix=f"chunk{i:03d}_")
        tmp.close()
        cmd = [
            ffmpeg_bin, "-y", "-i", file_path,
            "-ss", str(start_sec), "-t", str(chunk_sec),
            "-acodec", "copy",
            tmp.name,
        ]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode != 0:
            # コピーが失敗したら再エンコード
            cmd = [
                ffmpeg_bin, "-y", "-i", file_path,
                "-ss", str(start_sec), "-t", str(chunk_sec),
                "-acodec", "aac", "-b:a", "64k", "-ac", "1", "-ar", "16000",
                tmp.name,
            ]
            subprocess.run(cmd, capture_output=True)
        chunks.append(tmp.name)

    if on_progress:
        on_progress("step", f"[前処理] {num_chunks}チャンクに分割完了")

    return chunks


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


def transcribe(client, uploaded, model, lang="ja", ctx=None, on_progress=None):
    """アップロード済みファイルから文字起こしを実行する。response を返す。"""
    return _generate_with_retry(
        client, model,
        contents=[
            types.Part.from_uri(file_uri=uploaded.uri, mime_type=uploaded.mime_type),
            get_transcript_prompt(lang, ctx),
        ],
        on_progress=on_progress,
        label="文字起こし",
    )


def correct_transcript(client, raw_transcript, model, lang="ja", ctx=None, on_progress=None):
    """2パス目: 粗い文字起こしを参考資料・辞書で校正する。response を返す。"""
    prompt_template = CORRECTION_PROMPTS.get(lang, CORRECTION_PROMPTS["ja"])
    context_block = _build_context_block(ctx, lang) if ctx else ""
    prompt = prompt_template.format(context_block=context_block, raw_transcript=raw_transcript)
    return _generate_with_retry(
        client, model,
        contents=prompt,
        on_progress=on_progress,
        label="校正",
    )


def summarize(client, transcript_text, model, lang="ja", ctx=None,
              template_key="standard", custom_template="", on_progress=None):
    """文字起こしテキストから議事録要約を生成する。response を返す。"""
    return _generate_with_retry(
        client, model,
        contents=get_summary_prompt(lang, ctx, template_key, custom_template).format(transcript=transcript_text),
        on_progress=on_progress,
        label="議事録生成",
    )


# ───────── メインパイプライン ─────────

def run_pipeline(
    file_path: str,
    api_key: str,
    model: str = "gemini-2.5-flash",
    lang: str = "ja",
    ctx: MeetingContext | None = None,
    reference_files: list[str] | None = None,
    template_key: str = "standard",
    custom_template: str = "",
    output_dir: str = ".",
    output_prefix: str | None = None,
    on_progress=None,
):
    """文字起こし→要約の全工程を実行し、ファイルに保存する。

    Args:
        lang: 出力言語コード ("ja", "en", "zh", "ms")
        ctx: 会議メタ情報・キーワード・指示等
        reference_files: 参考資料ファイルパスのリスト (PDF等)
        template_key: 要約テンプレートキー ("standard", "action_focused", "executive", "detailed", "oneonone", "custom")
        custom_template: カスタムテンプレートテキスト（template_key="custom"時）

    Returns:
        (transcript_text, summary_text, transcript_path, summary_path, usage_stats)
    """
    client = genai.Client(api_key=api_key)
    fp = Path(file_path)
    usage = UsageStats()
    lang_name = SUPPORTED_LANGUAGES.get(lang, lang)
    if ctx is None:
        ctx = MeetingContext()

    # ─── 参考資料のテキスト抽出 ───
    if reference_files:
        if on_progress:
            on_progress("step", f"[前処理] 参考資料を読み込み中 ({len(reference_files)}件)...")
        for ref_path in reference_files:
            try:
                ref_uploaded = upload_and_wait(client, ref_path, on_progress=None)
                resp = _generate_with_retry(
                    client, model,
                    contents=[
                        types.Part.from_uri(file_uri=ref_uploaded.uri, mime_type=ref_uploaded.mime_type),
                        "この文書の主要な内容・用語・固有名詞を箇条書きで要約してください。",
                    ],
                    label="資料読み込み",
                )
                ctx.reference_texts.append(resp.text)
                if resp.usage_metadata:
                    usage.add(f"資料読み込み ({Path(ref_path).name})", resp.usage_metadata)
                try:
                    client.files.delete(name=ref_uploaded.name)
                except Exception:
                    pass
            except Exception as e:
                if on_progress:
                    on_progress("step", f"  ⚠️ 資料読み込みエラー: {Path(ref_path).name}: {e}")

    # ─── 動画→音声抽出 ───
    audio_tmp = _extract_audio(str(fp), on_progress)
    audio_file = audio_tmp or str(fp)

    # ─── 音声前処理（ノイズ除去・音量正規化）───
    normalized_tmp = _normalize_audio(audio_file, on_progress)
    if normalized_tmp:
        if audio_tmp:
            try:
                os.unlink(audio_tmp)
            except Exception:
                pass
        audio_file = normalized_tmp
        audio_tmp = normalized_tmp  # クリーンアップ用に追跡

    # ─── 2パス判定: 参考資料・辞書がある場合は2パス ───
    use_two_pass = bool(ctx.reference_texts or ctx.glossary)

    # ─── 音声分割 ───
    chunks = _split_audio(audio_file, on_progress=on_progress)

    # ─── Pass 1: 文字起こし ───
    if chunks:
        total_chunks = len(chunks)
        all_transcripts = []

        for idx, chunk_path in enumerate(chunks, 1):
            chunk_label = f"チャンク {idx}/{total_chunks}"
            if on_progress:
                on_progress("step", f"[{idx}/{total_chunks}] アップロード中...")
            try:
                uploaded = upload_and_wait(client, chunk_path, on_progress)
            finally:
                try:
                    os.unlink(chunk_path)
                except Exception:
                    pass

            if on_progress:
                on_progress("step", f"[{idx}/{total_chunks}] 文字起こし中 ({lang_name})...")

            resp = transcribe(client, uploaded, model, lang, ctx, on_progress)
            all_transcripts.append(resp.text)
            if resp.usage_metadata:
                usage.add(f"文字起こし ({chunk_label})", resp.usage_metadata)
            try:
                client.files.delete(name=uploaded.name)
            except Exception:
                pass

        if audio_tmp:
            try:
                os.unlink(audio_tmp)
            except Exception:
                pass

        transcript = "\n\n".join(all_transcripts)
    else:
        if on_progress:
            on_progress("step", "[1/4] アップロード中...")
        try:
            uploaded = upload_and_wait(client, audio_file, on_progress)
        finally:
            if audio_tmp:
                try:
                    os.unlink(audio_tmp)
                except Exception:
                    pass

        if on_progress:
            on_progress("step", f"[2/4] 文字起こし中 ({model} / {lang_name})...")

        resp1 = transcribe(client, uploaded, model, lang, ctx, on_progress)
        transcript = resp1.text
        if resp1.usage_metadata:
            usage.add("文字起こし", resp1.usage_metadata)
        try:
            client.files.delete(name=uploaded.name)
        except Exception:
            pass

    # ─── Pass 2: 校正（参考資料・辞書がある場合）───
    if use_two_pass:
        if on_progress:
            on_progress("step", "[校正] 参考資料・用語辞書と照合して校正中...")
        resp_correct = correct_transcript(client, transcript, model, lang, ctx, on_progress)
        transcript = resp_correct.text
        if resp_correct.usage_metadata:
            usage.add("2パス校正", resp_correct.usage_metadata)

    # ─── 議事録生成 ───
    if on_progress:
        label = f"[議事録] 議事録生成中 ({lang_name})..." if chunks else f"[3/4] 議事録生成中 ({lang_name})..."
        on_progress("step", label)

    resp2 = summarize(client, transcript, model, lang, ctx, template_key, custom_template, on_progress)
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
    parser.add_argument("--date", default="", help="会議日付 (例: 2024-04-14)")
    parser.add_argument("--time", default="", help="会議時刻 (例: 10:00-12:00)")
    parser.add_argument("--topic", default="", help="会議テーマ・議題")
    parser.add_argument("--participants", default="", help="参加者名（カンマ区切り）")
    parser.add_argument("--keywords", default="", help="重要キーワード（カンマ区切り）")
    parser.add_argument("--glossary", default="", help="専門用語辞書 (形式: 略語=正式名, ...)")
    parser.add_argument("--instructions", default="", help="要約のカスタム指示")
    parser.add_argument("--references", nargs="*", default=[], help="参考資料ファイル (PDF等)")
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

    ctx = MeetingContext(
        date=args.date,
        time=args.time,
        topic=args.topic,
        participants=args.participants,
        keywords=args.keywords,
        glossary=args.glossary.replace(",", "\n") if args.glossary else "",
        custom_instructions=args.instructions,
    )

    print(f"出力言語: {SUPPORTED_LANGUAGES.get(args.lang, args.lang)}")
    if ctx.topic:
        print(f"テーマ: {ctx.topic}")

    transcript, summary, t_path, s_path, usage = run_pipeline(
        file_path=str(fp),
        api_key=api_key,
        model=args.model,
        lang=args.lang,
        ctx=ctx,
        reference_files=args.references or None,
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
