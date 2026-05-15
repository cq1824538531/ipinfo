"""
generate_daily.py

GitHub Actions 每日定时调用，完成以下工作：
1. 从 keywords.txt 读取第一行关键词
2. 调用 Groq API 生成一篇中文帮助文章
3. 写入 help/<slug>.html
4. 更新 sitemap.xml（追加新URL）
5. 更新 help.html（在"更多文章"区块追加链接）
6. 删除 keywords.txt 已使用的关键词行

运行环境：
- GROQ_API_KEY 从环境变量读取（GitHub Secrets）
- 依赖：pip install groq
"""

import os
import re
import sys
import time
import datetime

from groq import Groq

# ============================================================
# 初始化
# ============================================================
api_key = os.environ.get('GROQ_API_KEY', '')
if not api_key:
    print("❌ 未找到 GROQ_API_KEY 环境变量")
    sys.exit(1)

client = Groq(api_key=api_key,
              base_url="https://ai-proxy.chatwise.app/groq")

BASE_URL = "https://ipinfo.gamenewspaper.com"
KEYWORDS_FILE = "keywords.txt"
SITEMAP_FILE = "sitemap.xml"
HELP_INDEX_FILE = "help.html"
HELP_DIR = "help"

TODAY = datetime.date.today().isoformat()  # 例：2026-05-16

# ============================================================
# CSS（内联，与主站风格一致）
# ============================================================
BASE_CSS = """
:root{--bg:#f8f9fa;--card:#fff;--primary:#4f8ef7;--text:#1a1a2e;--text-secondary:#555;--text-muted:#888;--border:#e5e7eb;--radius:12px}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);line-height:1.7}
.page-wrapper{min-height:100vh;display:flex;flex-direction:column}
.top-nav{background:var(--card);border-bottom:1px solid var(--border);padding:0 24px}
.top-nav__inner{max-width:960px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;height:56px}
.top-nav__brand{font-weight:700;font-size:1.05rem;color:var(--text);text-decoration:none;display:flex;align-items:center;gap:6px}
.top-nav__links{list-style:none;display:flex;gap:24px}
.top-nav__links a{color:var(--text-secondary);text-decoration:none;font-size:.95rem}
.top-nav__links a.active,.top-nav__links a:hover{color:var(--primary)}
.main-content{flex:1;padding:32px 16px}
.container{max-width:780px;margin:0 auto}
.breadcrumb{font-size:13px;color:var(--text-muted);margin-bottom:20px;display:flex;align-items:center;gap:6px}
.breadcrumb a{color:var(--text-muted);text-decoration:none}.breadcrumb a:hover{color:var(--primary)}
.article-header{margin-bottom:32px}
.article-header h1{font-size:1.65rem;font-weight:800;line-height:1.35;margin-bottom:12px}
.article-meta{font-size:13px;color:var(--text-muted);display:flex;gap:16px;flex-wrap:wrap}
.article-body{background:var(--card);border-radius:var(--radius);padding:32px;border:1px solid var(--border)}
.article-body h2{font-size:1.15rem;font-weight:700;margin:28px 0 12px;color:var(--text);padding-bottom:6px;border-bottom:2px solid var(--primary);display:inline-block}
.article-body h2:first-child{margin-top:0}
.article-body p{margin-bottom:14px;color:var(--text-secondary);font-size:.97rem}
.article-body ul,.article-body ol{margin:10px 0 16px 20px;color:var(--text-secondary);font-size:.97rem}
.article-body li{margin-bottom:6px}
.article-body strong{color:var(--text)}
.article-body code{background:#f1f3f5;border-radius:4px;padding:1px 6px;font-size:.9em;color:#c0392b;font-family:monospace}
.back-link{margin-top:28px;display:inline-flex;align-items:center;gap:6px;color:var(--primary);text-decoration:none;font-size:.93rem}
.back-link:hover{text-decoration:underline}
footer{background:var(--card);border-top:1px solid var(--border);padding:28px 24px;margin-top:40px}
.footer__inner{max-width:960px;margin:0 auto}
.footer__bottom{font-size:12px;color:var(--text-muted);text-align:center;margin-top:16px}
.footer__bottom a{color:var(--text-muted)}
@media(max-width:600px){.article-body{padding:20px}.article-header h1{font-size:1.3rem}}
"""

# ============================================================
# 1. 读取并消耗第一个关键词
# ============================================================
def pop_keyword():
    if not os.path.exists(KEYWORDS_FILE):
        print("❌ keywords.txt 不存在")
        sys.exit(0)

    with open(KEYWORDS_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 过滤空行，找第一个有效关键词
    valid = [(i, l.strip()) for i, l in enumerate(lines) if l.strip()]
    if not valid:
        print("✅ keywords.txt 已全部用完，今日跳过生成")
        sys.exit(0)

    idx, keyword = valid[0]

    # 删除该行
    lines.pop(idx)
    with open(KEYWORDS_FILE, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"📌 今日关键词：{keyword}（剩余 {len(valid)-1} 个）")
    return keyword


# ============================================================
# 2. slug 兜底（AI生成失败时用日期）
# ============================================================
def fallback_slug() -> str:
    return f"article-{TODAY.replace('-', '')}"


# ============================================================
# 3. AI 生成文章
# ============================================================
def generate_article(keyword: str) -> dict:
    prompt = f"""请围绕关键词「{keyword}」写一篇中文帮助中心文章。

要求：
1. 文章标题直接包含关键词「{keyword}」
2. 全文关键词密度3%-5%，自然融入，不堆砌
3. 全文中文，面向普通用户，语言通俗易懂
4. 字数700～1000字
5. 包含4～5个章节，每个章节用##标记：

## 章节标题
段落内容

6. 可适当使用列表（- 开头）
7. 只输出以下JSON，不输出任何其他内容：

{{
  "title": "文章标题（包含关键词，20字以内）",
  "slug": "english-url-slug（3-5个英文单词，连字符分隔，体现文章主题，例如：how-to-check-ip-location）",
  "article": "## 第一章节\\n内容\\n\\n## 第二章节\\n内容"
}}
"""
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="qwen/qwen3-32b",
                messages=[
                    {"role": "system", "content": "你是SEO内容专家。只输出JSON，不输出任何解释或代码块标记。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.65,
                max_tokens=2500,
            )
            raw = response.choices[0].message.content.strip()
            # 去掉 <think>...</think>
            raw = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL).strip()
            # 去掉可能的markdown代码块
            raw = re.sub(r'```[a-z]*\n?', '', raw).strip('`').strip()

            # 提取字段
            def extract(text, field):
                pattern = rf'"{field}":\s*"([\s\S]*?)"(?=\s*[,}}])'
                m = re.search(pattern, text)
                if m:
                    return m.group(1).replace('\\"', '"').replace('\\n', '\n').replace('\\\\', '\\').strip()
                return None

            title = extract(raw, 'title')
            slug = extract(raw, 'slug')
            article = extract(raw, 'article')

            # slug清洗：只保留字母数字和连字符，转小写
            if slug:
                slug = re.sub(r'[^a-z0-9-]', '', slug.lower().replace(' ', '-'))
                slug = re.sub(r'-+', '-', slug).strip('-')

            if title and article:
                return {'title': title, 'slug': slug or fallback_slug(), 'article': article}

            # 降级：尝试json解析
            import json
            m = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                data = json.loads(m.group())
                raw_slug = data.get('slug', '')
                raw_slug = re.sub(r'[^a-z0-9-]', '', raw_slug.lower().replace(' ', '-'))
                raw_slug = re.sub(r'-+', '-', raw_slug).strip('-')
                return {'title': data['title'], 'slug': raw_slug or fallback_slug(), 'article': data['article']}

        except Exception as e:
            print(f"  ⚠️ 第{attempt+1}次重试... {e}")
            time.sleep(10)

    raise RuntimeError("AI生成失败，已重试3次")


# ============================================================
# 4. Markdown 转 HTML
# ============================================================
def md_to_html(text: str) -> str:
    lines = text.split('\n')
    parts = []
    pending = []

    def flush():
        if pending:
            content = ' '.join(l.strip() for l in pending if l.strip())
            if content:
                parts.append(f'<p>{content}</p>')
            pending.clear()

    for line in lines:
        s = line.strip()
        if not s:
            flush()
        elif s.startswith('## '):
            flush()
            parts.append(f'<h2>{s[3:].strip()}</h2>')
        elif s.startswith('- ') or s.startswith('* '):
            flush()
            parts.append(f'<ul><li>{s[2:].strip()}</li></ul>')
        else:
            pending.append(s)
    flush()

    result = '\n'.join(parts)
    result = re.sub(r'</ul>\n<ul>', '\n', result)
    result = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', result)
    result = re.sub(r'`([^`]+)`', r'<code>\1</code>', result)
    return result


# ============================================================
# 5. 构建完整 HTML 页面
# ============================================================
def build_html(slug: str, title: str, article_md: str) -> str:
    body_html = md_to_html(article_md)
    plain = re.sub(r'<[^>]+>', '', body_html).replace('\n', ' ')
    meta_desc = plain[:150].strip()

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | 帮助中心 - IP归属地查询工具</title>
  <meta name="description" content="{meta_desc}">
  <link rel="canonical" href="{BASE_URL}/help/{slug}.html">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{title}">
  <meta property="og:url" content="{BASE_URL}/help/{slug}.html">
  <meta property="og:site_name" content="IP归属地查询工具">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "{title}",
    "datePublished": "{TODAY}",
    "dateModified": "{TODAY}",
    "publisher": {{
      "@type": "Organization",
      "name": "IP归属地查询工具",
      "url": "{BASE_URL}"
    }}
  }}
  </script>
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      {{"@type":"ListItem","position":1,"name":"首页","item":"{BASE_URL}/"}},
      {{"@type":"ListItem","position":2,"name":"帮助中心","item":"{BASE_URL}/help.html"}},
      {{"@type":"ListItem","position":3,"name":"{title}","item":"{BASE_URL}/help/{slug}.html"}}
    ]
  }}
  </script>
  <style>{BASE_CSS}</style>
</head>
<body>
<div class="page-wrapper">

  <nav class="top-nav" aria-label="主导航">
    <div class="top-nav__inner">
      <a class="top-nav__brand" href="../index.html">
        <span>🌍</span> IP归属地查询
      </a>
      <ul class="top-nav__links" role="list">
        <li><a href="../index.html">首页</a></li>
        <li><a href="../help.html" class="active" aria-current="page">帮助中心</a></li>
        <li><a href="../about.html">关于</a></li>
        <li><a href="../contact.html">联系我们</a></li>
      </ul>
    </div>
  </nav>

  <main class="main-content" id="main-content">
    <div class="container">

      <nav class="breadcrumb" aria-label="面包屑导航">
        <a href="../index.html">首页</a>
        <span aria-hidden="true">›</span>
        <a href="../help.html">帮助中心</a>
        <span aria-hidden="true">›</span>
        <span>{title}</span>
      </nav>

      <div class="article-header">
        <h1>{title}</h1>
        <div class="article-meta">
          <span>📅 {TODAY}</span>
          <span>📂 IP知识</span>
        </div>
      </div>

      <div class="article-body">
        {body_html}
      </div>

      <a href="../help.html" class="back-link">← 返回帮助中心</a>

    </div>
  </main>

  <footer>
    <div class="footer__inner">
      <div class="footer__bottom">
        <span>© 2026 IP归属地查询工具 · 数据来源：<a href="https://ipinfo.io" target="_blank" rel="noopener noreferrer">IPinfo.io</a></span>
      </div>
    </div>
  </footer>

</div>
</body>
</html>"""


# ============================================================
# 6. 更新 sitemap.xml
# ============================================================
def update_sitemap(slug: str):
    new_entry = f"""
  <url>
    <loc>{BASE_URL}/help/{slug}.html</loc>
    <lastmod>{TODAY}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>"""

    with open(SITEMAP_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # 插入到 </urlset> 之前
    content = content.replace('</urlset>', f'{new_entry}\n\n</urlset>')

    with open(SITEMAP_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  ✅ sitemap.xml 已更新")


# ============================================================
# 7. 更新 help.html（在标记位追加链接）
# ============================================================
def update_help_index(slug: str, title: str):
    new_link = f'          <a class="article-item" href="help/{slug}.html" role="listitem"><span class="article-item__title">{title}</span><span class="article-item__meta">{TODAY}</span><span class="article-item__arrow" aria-hidden="true">›</span></a>'

    marker = '<!-- DAILY_ARTICLES_END -->'

    with open(HELP_INDEX_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    if marker not in content:
        print(f"  ⚠️ help.html 中未找到标记 {marker}，跳过更新")
        return

    content = content.replace(marker, f'{new_link}\n        {marker}')

    with open(HELP_INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  ✅ help.html 已追加链接")


# ============================================================
# 主程序
# ============================================================
if __name__ == '__main__':
    print(f"🚀 开始生成 {TODAY} 的文章")

    keyword = pop_keyword()

    os.makedirs(HELP_DIR, exist_ok=True)

    print("⏳ AI 生成文章中...")
    result = generate_article(keyword)
    title = result['title']
    slug = result['slug']
    print(f"✅ 标题：{title}")
    print(f"✅ Slug：{slug}")

    # slug重复时加日期后缀
    out_path = os.path.join(HELP_DIR, f"{slug}.html")
    if os.path.exists(out_path):
        slug = f"{slug}-{TODAY.replace('-', '')}"
        out_path = os.path.join(HELP_DIR, f"{slug}.html")

    html = build_html(slug, title, result['article'])
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"💾 已写入：{out_path}")

    update_sitemap(slug)
    update_help_index(slug, title)

    print(f"\n✨ 完成！文章：{BASE_URL}/help/{slug}.html")
