#!/usr/bin/env python3
"""
性の悩み相談サイト 記事自動生成スクリプト
Claude API を使ってSEO記事を自動生成し、HTMLファイルとして保存する
"""

import anthropic
import json
import re
import time
from datetime import datetime
from pathlib import Path

# ── 設定 ──────────────────────────────────────────
API_KEY     = "YOUR_ANTHROPIC_API_KEY"  # ← ここにAPIキーを入力
BASE_DIR    = Path(__file__).parent
ARTICLES_DIR = BASE_DIR / "articles"
INDEX_FILE  = BASE_DIR / "articles_index.json"

ARTICLES_DIR.mkdir(exist_ok=True)

# ── 記事トピック一覧 ───────────────────────────────
# カテゴリごとにSEOキーワードを設定
TOPICS = [
    # 夫婦・パートナー
    {"category": "couple",     "cat_label": "夫婦・パートナー関係", "keyword": "夫婦 セックスレス 解消", "title": "夫婦のセックスレスを解消する5つのステップ"},
    {"category": "couple",     "cat_label": "夫婦・パートナー関係", "keyword": "パートナー 性の悩み 話し合い", "title": "パートナーと性の悩みを上手に話し合う方法"},
    {"category": "couple",     "cat_label": "夫婦・パートナー関係", "keyword": "産後 レス 原因 対策", "title": "産後レスの原因と夫婦で乗り越えるためのヒント"},
    {"category": "couple",     "cat_label": "夫婦・パートナー関係", "keyword": "更年期 夫婦関係 性生活", "title": "更年期が夫婦の性生活に与える影響と対処法"},

    # 身体の悩み（男性）
    {"category": "male",       "cat_label": "身体の悩み（男性）", "keyword": "ED 改善 原因 40代", "title": "40代からのED：原因と自分でできる改善方法"},
    {"category": "male",       "cat_label": "身体の悩み（男性）", "keyword": "男性 性欲 低下 原因", "title": "男性の性欲低下の原因とホルモンとの関係"},
    {"category": "male",       "cat_label": "身体の悩み（男性）", "keyword": "早漏 改善 方法", "title": "早漏を改善するために知っておくべきこと"},

    # 身体の悩み（女性）
    {"category": "female",     "cat_label": "身体の悩み（女性）", "keyword": "女性 性交痛 原因 対策", "title": "性交痛の原因と対処法：婦人科で相談すべきこと"},
    {"category": "female",     "cat_label": "身体の悩み（女性）", "keyword": "女性 性欲 低下 更年期", "title": "女性の性欲低下：更年期・ホルモンバランスとの関係"},
    {"category": "female",     "cat_label": "身体の悩み（女性）", "keyword": "膣 乾燥 潤い 対策", "title": "膣の乾燥・潤い不足の原因と日常でできるケア"},

    # 心理・セルフケア
    {"category": "mental",     "cat_label": "心理・セルフケア", "keyword": "性 罪悪感 原因 克服", "title": "性に罪悪感を感じる原因と心理的な向き合い方"},
    {"category": "mental",     "cat_label": "心理・セルフケア", "keyword": "性的トラウマ 回復 方法", "title": "性的トラウマからの回復：焦らず進む5つのステップ"},
    {"category": "mental",     "cat_label": "心理・セルフケア", "keyword": "自己肯定感 性 関係", "title": "自己肯定感と性の悩みの深い関係"},

    # 性教育・知識
    {"category": "education",  "cat_label": "性教育・知識", "keyword": "避妊 方法 比較 確実", "title": "避妊方法の種類と確実性：自分に合った方法を選ぶ"},
    {"category": "education",  "cat_label": "性教育・知識", "keyword": "STI 性感染症 予防 検査", "title": "性感染症（STI）の予防と検査について正しく知る"},
]

# ── プロンプトテンプレート ──────────────────────────
def build_prompt(topic: dict) -> str:
    return f"""あなたは性と健康に関する専門的なウェブライターです。
以下の条件でSEO記事を作成してください。

【記事タイトル】
{topic['title']}

【メインキーワード】
{topic['keyword']}

【カテゴリ】
{topic['cat_label']}

【条件】
- 文字数: 1500〜2000文字
- 医学的に正確で、読者に寄り添ったやさしいトーン
- 専門用語には簡単な説明を付ける
- 見出しはH2（##）とH3（###）で構造化する
- 最後に「まとめ」セクションを入れる
- わいせつな表現は避け、健康・医療・心理の観点で書く
- 免責事項として「本記事は医療アドバイスではありません」を末尾に記載

【出力形式】
Markdown形式で出力してください。タイトルのH1は不要です（システムで付与します）。
"""

# ── Markdown → HTML 変換 ────────────────────────
def md_to_html(md_text: str) -> str:
    html = md_text

    # H2
    html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    # H3
    html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
    # 太字
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    # 箇条書き
    html = re.sub(r'^[-・] (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    html = re.sub(r'(<li>.*</li>\n?)+', lambda m: f'<ul>\n{m.group()}</ul>\n', html)
    # 段落
    paragraphs = []
    for para in html.split('\n\n'):
        para = para.strip()
        if not para:
            continue
        if para.startswith('<h') or para.startswith('<ul'):
            paragraphs.append(para)
        else:
            paragraphs.append(f'<p>{para}</p>')
    return '\n'.join(paragraphs)

# ── HTMLファイル生成 ─────────────────────────────
def save_article_html(topic: dict, content_md: str, slug: str):
    content_html = md_to_html(content_md)
    now_str = datetime.now().strftime('%Y年%m月%d日')

    cat_colors = {
        "couple":    "#667EEA",
        "male":      "#4299E1",
        "female":    "#ED64A6",
        "mental":    "#9F7AEA",
        "education": "#48BB78",
    }
    color = cat_colors.get(topic['category'], "#667EEA")

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{topic['title']} | TalkSpace</title>
  <meta name="description" content="{topic['keyword']}に関する解説記事。{topic['cat_label']}カテゴリ。">
  <style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family:'Hiragino Sans','Yu Gothic',sans-serif; background:#F0F4FF; color:#2D3748; line-height:1.8; }}
    nav {{ background:#fff; border-bottom:1px solid #E2E8F0; padding:0 40px; height:64px; display:flex; align-items:center; justify-content:space-between; position:sticky; top:0; z-index:100; }}
    .logo {{ font-size:20px; font-weight:700; color:#2D3748; text-decoration:none; }}
    .logo span {{ color:#7C8CF8; }}
    .back-link {{ color:#7C8CF8; text-decoration:none; font-size:14px; }}
    .back-link:hover {{ text-decoration:underline; }}
    .container {{ max-width:780px; margin:48px auto; padding:0 24px; }}
    .article-header {{ margin-bottom:40px; }}
    .cat-tag {{ display:inline-block; background:{color}1a; color:{color}; font-size:12px; font-weight:600; padding:4px 12px; border-radius:20px; margin-bottom:12px; }}
    h1 {{ font-size:30px; font-weight:700; color:#1A202C; line-height:1.4; margin-bottom:12px; }}
    .article-meta {{ font-size:13px; color:#718096; }}
    .article-body {{ background:#fff; border-radius:16px; padding:40px; box-shadow:0 2px 12px rgba(45,55,72,0.06); }}
    .article-body h2 {{ font-size:22px; font-weight:700; color:#2D3748; margin:36px 0 14px; padding-left:14px; border-left:4px solid {color}; }}
    .article-body h3 {{ font-size:17px; font-weight:700; color:#4A5568; margin:24px 0 10px; }}
    .article-body p {{ margin-bottom:16px; font-size:15px; }}
    .article-body ul {{ margin:12px 0 20px 24px; }}
    .article-body li {{ margin-bottom:8px; font-size:15px; }}
    .article-body strong {{ color:#2D3748; }}
    .disclaimer {{ background:#FFF5F5; border:1px solid #FED7D7; border-radius:8px; padding:16px 20px; margin-top:32px; font-size:13px; color:#C53030; }}
    footer {{ text-align:center; padding:48px; color:#A0AEC0; font-size:13px; margin-top:48px; }}
  </style>
</head>
<body>
  <nav>
    <a href="../index.html" class="logo">Talk<span>Space</span></a>
    <a href="../index.html" class="back-link">← トップに戻る</a>
  </nav>

  <div class="container">
    <div class="article-header">
      <span class="cat-tag">{topic['cat_label']}</span>
      <h1>{topic['title']}</h1>
      <div class="article-meta">公開日: {now_str} ｜ キーワード: {topic['keyword']}</div>
    </div>

    <div class="article-body">
      {content_html}
      <div class="disclaimer">
        ※ 本記事は医療アドバイスではありません。身体の症状や深刻な悩みは、医師・専門家にご相談ください。
      </div>
    </div>
  </div>

  <footer>© 2026 TalkSpace. All rights reserved.</footer>
</body>
</html>"""

    out_path = ARTICLES_DIR / f"{slug}.html"
    out_path.write_text(html, encoding='utf-8')
    return out_path

# ── インデックスJSON更新 ──────────────────────────
def update_index(entries: list):
    INDEX_FILE.write_text(
        json.dumps(entries, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )

# ── メイン処理 ───────────────────────────────────
def main():
    client = anthropic.Anthropic(api_key=API_KEY)

    # 既存インデックス読み込み
    if INDEX_FILE.exists():
        index = json.loads(INDEX_FILE.read_text(encoding='utf-8'))
    else:
        index = []

    existing_slugs = {e['slug'] for e in index}

    print()
    print('=' * 50)
    print('  TalkSpace 記事自動生成')
    print('=' * 50)
    print(f'  対象トピック数: {len(TOPICS)}')
    print(f'  生成済み: {len(existing_slugs)}件')
    print()

    generated = 0
    skipped   = 0

    for i, topic in enumerate(TOPICS, 1):
        # スラッグ生成（タイトルから英数字+ハイフン）
        slug = f"{topic['category']}-{i:03d}"

        if slug in existing_slugs:
            print(f'  [{i:02d}/{len(TOPICS)}] スキップ（生成済み）: {topic["title"][:30]}...')
            skipped += 1
            continue

        print(f'  [{i:02d}/{len(TOPICS)}] 生成中: {topic["title"][:40]}')

        try:
            response = client.messages.create(
                model="claude-haiku-4-5-20251001",  # コスト抑制のためHaiku使用
                max_tokens=3000,
                messages=[
                    {"role": "user", "content": build_prompt(topic)}
                ]
            )

            content_md = response.content[0].text
            out_path = save_article_html(topic, content_md, slug)

            # インデックスに追加
            index.append({
                "slug":      slug,
                "title":     topic['title'],
                "category":  topic['category'],
                "cat_label": topic['cat_label'],
                "keyword":   topic['keyword'],
                "file":      f"articles/{slug}.html",
                "created_at": datetime.now().isoformat(),
            })
            update_index(index)
            existing_slugs.add(slug)

            print(f'         → 保存: {out_path.name}')
            generated += 1

            # API制限対策（1秒待機）
            time.sleep(1)

        except Exception as e:
            print(f'         → エラー: {e}')

    print()
    print('=' * 50)
    print(f'  生成完了: {generated}件 / スキップ: {skipped}件')
    print(f'  インデックス: {INDEX_FILE.name}')
    print('=' * 50)
    print()

if __name__ == '__main__':
    main()
