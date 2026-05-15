"""
generate_help_articles.py

一次性生成 15 篇帮助中心 HTML 文章，直接写到 help/ 目录。
运行前确保已安装：pip install groq
并在同目录放好 config.txt（内容为 Groq API Key）。

输出结构：
  help/
    faq-accuracy.html
    faq-private-ip.html
    faq-rate-limit.html
    faq-location-mismatch.html
    tutorial-basic.html
    tutorial-my-ip.html
    tutorial-map.html
    what-is-ip.html
    public-vs-private-ip.html
    what-is-isp.html
    vpn-and-ip.html
    dynamic-vs-static-ip.html
    trouble-query-failed.html
    trouble-invalid-ip.html
    trouble-slow-response.html
"""

import os
import re
import time
from groq import Groq

# ============================================================
# 读取 API Key
# ============================================================
with open('config.txt', 'r') as f:
    api_key = f.read().strip()

client = Groq(api_key=api_key,
              base_url="https://ai-proxy.chatwise.app/groq")

# ============================================================
# 15 篇文章定义
# 字段：slug, page_title（中文，用于页面<title>和h1）,
#        meta_desc_hint（给AI的内容提示）, date, category_cn, category_slug
# ============================================================
ARTICLES = [
    # ── FAQ ──
    {
        "slug": "faq-accuracy",
        "page_title": "IP归属地查询结果准确吗？",
        "topic": "IP归属地查询结果的准确性，精确到城市级，VPN/代理/移动漫游会导致偏差，以及IP定位的技术局限性",
        "date": "2026-05-13",
        "category_cn": "常见问题",
        "category_slug": "faq",
    },
    {
        "slug": "faq-private-ip",
        "page_title": "内网IP为什么查不到归属地？",
        "topic": "内网（私有）IP地址（如192.168.x.x、10.x.x.x、172.16.x.x）为什么无法查询归属地，私有地址的定义、用途及与公网IP的区别",
        "date": "2026-05-13",
        "category_cn": "常见问题",
        "category_slug": "faq",
    },
    {
        "slug": "faq-rate-limit",
        "page_title": "查询频率有限制吗？免费版够用吗？",
        "topic": "IP查询工具的频率限制，免费API每分钟45次限额，个人日常够用，批量需求建议升级付费套餐",
        "date": "2026-05-12",
        "category_cn": "常见问题",
        "category_slug": "faq",
    },
    {
        "slug": "faq-location-mismatch",
        "page_title": "为什么显示的城市和我实际位置不符？",
        "topic": "IP归属地显示城市与实际位置不符的原因：运营商按区域批量分配IP、动态IP、移动网络、企业专线、CDN等因素导致IP定位偏差",
        "date": "2026-05-12",
        "category_cn": "常见问题",
        "category_slug": "faq",
    },
    # ── 教程 ──
    {
        "slug": "tutorial-basic",
        "page_title": "如何查询任意IP地址的归属地？",
        "topic": "一步步教用户如何在IP归属地查询工具中输入任意IP地址并获取归属地信息，包括输入格式、查询步骤、结果解读",
        "date": "2026-05-11",
        "category_cn": "使用教程",
        "category_slug": "tutorial",
    },
    {
        "slug": "tutorial-my-ip",
        "page_title": "如何快速查询我的公网IP？",
        "topic": "如何一键获取自己当前的公网IP地址，工具会自动检测并显示，无需手动输入，以及公网IP的概念和用途",
        "date": "2026-05-11",
        "category_cn": "使用教程",
        "category_slug": "tutorial",
    },
    {
        "slug": "tutorial-map",
        "page_title": "如何在地图上查看IP地理位置？",
        "topic": "IP查询工具的地图功能使用教程，查询结果会在地图上标注IP地理位置，理解经纬度坐标与地图定位的关系",
        "date": "2026-05-10",
        "category_cn": "使用教程",
        "category_slug": "tutorial",
    },
    # ── 知识科普 ──
    {
        "slug": "what-is-ip",
        "page_title": "什么是IP地址？IPv4与IPv6有何区别？",
        "topic": "IP地址的基本概念、作用、格式，IPv4（32位，约43亿个）与IPv6（128位，几乎无限）的区别、现状及过渡",
        "date": "2026-05-05",
        "category_cn": "IP 知识科普",
        "category_slug": "knowledge",
    },
    {
        "slug": "public-vs-private-ip",
        "page_title": "公网IP和内网IP有什么区别？",
        "topic": "公网IP（可在互联网直接访问，由ISP分配）与内网IP（私有地址段，仅局域网内使用，通过NAT共享一个公网IP）的区别、应用场景、如何查看",
        "date": "2026-05-05",
        "category_cn": "IP 知识科普",
        "category_slug": "knowledge",
    },
    {
        "slug": "what-is-isp",
        "page_title": "什么是ISP？运营商如何分配IP地址？",
        "topic": "ISP（互联网服务提供商）的定义，中国三大运营商（电信、联通、移动），IP地址由IANA→区域注册机构→ISP→用户逐级分配的体系",
        "date": "2026-05-04",
        "category_cn": "IP 知识科普",
        "category_slug": "knowledge",
    },
    {
        "slug": "vpn-and-ip",
        "page_title": "VPN如何改变IP归属地显示？",
        "topic": "VPN的工作原理：流量经过VPN服务器中转，对外显示的IP变为VPN服务器的IP，导致归属地改变，以及VPN检测和常见用途",
        "date": "2026-05-07",
        "category_cn": "IP 知识科普",
        "category_slug": "knowledge",
    },
    {
        "slug": "dynamic-vs-static-ip",
        "page_title": "动态IP和静态IP有什么区别？",
        "topic": "动态IP（每次连接由ISP动态分配，会变化，家庭宽带常见）与静态IP（固定不变，企业/服务器常用）的区别、优缺点、对IP查询的影响",
        "date": "2026-05-06",
        "category_cn": "IP 知识科普",
        "category_slug": "knowledge",
    },
    # ── 问题排查 ──
    {
        "slug": "trouble-query-failed",
        "page_title":'查询失败，提示"网络请求失败"怎么办？',
        "topic": "查询IP时出现网络请求失败的原因排查：本地网络问题、浏览器插件拦截、API限额、防火墙，以及逐步排查和解决方法",
        "date": "2026-05-09",
        "category_cn": "问题排查",
        "category_slug": "trouble",
    },
    {
        "slug": "trouble-invalid-ip",
        "page_title": "输入IP地址后提示格式错误？",
        "topic": "IP地址格式错误的原因：IPv4需四段0-255数字、IPv6格式、常见误输入（多空格、字母混入、缺少段），以及正确格式示例",
        "date": "2026-05-08",
        "category_cn": "问题排查",
        "category_slug": "trouble",
    },
    {
        "slug": "trouble-slow-response",
        "page_title": "查询速度慢，响应超时如何处理？",
        "topic": "IP查询响应慢或超时的原因：网络延迟、API服务器负载、本地DNS、浏览器缓存，以及加速查询的实用建议",
        "date": "2026-05-07",
        "category_cn": "问题排查",
        "category_slug": "trouble",
    },
]

# ============================================================
# 用CSS变量让页面风格与主站一致（无需引入外部css也能独立预览）
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
.article-meta span{display:flex;align-items:center;gap:4px}
.article-body{background:var(--card);border-radius:var(--radius);padding:32px;border:1px solid var(--border)}
.article-body h2{font-size:1.15rem;font-weight:700;margin:28px 0 12px;color:var(--text);padding-bottom:6px;border-bottom:2px solid var(--primary);display:inline-block}
.article-body h2:first-child{margin-top:0}
.article-body p{margin-bottom:14px;color:var(--text-secondary);font-size:.97rem}
.article-body ul,.article-body ol{margin:10px 0 16px 20px;color:var(--text-secondary);font-size:.97rem}
.article-body li{margin-bottom:6px}
.article-body strong{color:var(--text)}
.article-body code{background:#f1f3f5;border-radius:4px;padding:1px 6px;font-size:.9em;color:#c0392b;font-family:monospace}
.tip-box{background:#eff6ff;border-left:4px solid var(--primary);border-radius:6px;padding:14px 16px;margin:18px 0;font-size:.93rem;color:#1e40af}
.warn-box{background:#fff7ed;border-left:4px solid #f97316;border-radius:6px;padding:14px 16px;margin:18px 0;font-size:.93rem;color:#9a3412}
.back-link{margin-top:28px;display:inline-flex;align-items:center;gap:6px;color:var(--primary);text-decoration:none;font-size:.93rem}
.back-link:hover{text-decoration:underline}
footer{background:var(--card);border-top:1px solid var(--border);padding:28px 24px;margin-top:40px}
.footer__inner{max-width:960px;margin:0 auto}
.footer__bottom{font-size:12px;color:var(--text-muted);text-align:center;margin-top:16px}
.footer__bottom a{color:var(--text-muted)}
@media(max-width:600px){.article-body{padding:20px}.article-header h1{font-size:1.3rem}}
"""

# ============================================================
# AI 生成文章正文（纯中文，带##标记）
# ============================================================
def generate_article_body(article: dict) -> str:
    prompt = f"""请为以下主题写一篇中文帮助中心文章。

主题：{article['topic']}
页面标题（H1）：{article['page_title']}

要求：
1. 全文中文，面向普通用户，语言通俗易懂
2. 字数 600～900 字
3. 必须包含 3～5 个章节，每个章节用 ## 开头标记，格式严格如下：

## 章节标题
段落内容

## 章节标题
段落内容

4. 可适当使用列表（- 开头）增强可读性
5. 内容准确，突出实用性
6. 只输出文章正文，不要输出任何JSON、代码块标记或解释

"""
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model="qwen/qwen3-32b",
                messages=[
                    {"role": "system", "content": "你是专业的技术写作专家，擅长写清晰易懂的帮助中心文章。只输出文章正文，不输出任何额外内容。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.65,
                max_tokens=2048,
            )
            text = response.choices[0].message.content.strip()
            # 去掉 <think>...</think>（某些模型会带）
            text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
            # 去掉可能混入的markdown代码块标记
            text = re.sub(r'```[a-z]*\n?', '', text).strip('`').strip()
            return text
        except Exception as e:
            print(f"  ⚠️ 第{attempt+1}次重试... {e}")
            time.sleep(10)
    raise RuntimeError(f"生成失败: {article['slug']}")


# ============================================================
# 把 ##Markdown 正文转为 HTML 段落
# ============================================================
def markdown_to_html(text: str) -> str:
    lines = text.split('\n')
    html_parts = []
    pending_para = []

    def flush_para():
        if pending_para:
            content = ' '.join(l.strip() for l in pending_para if l.strip())
            if content:
                html_parts.append(f'<p>{content}</p>')
            pending_para.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            flush_para()
            continue
        if stripped.startswith('## '):
            flush_para()
            heading = stripped[3:].strip()
            html_parts.append(f'<h2>{heading}</h2>')
        elif stripped.startswith('- ') or stripped.startswith('* '):
            flush_para()
            # 收集连续列表项
            item = stripped[2:].strip()
            # 简单处理：单个li包在ul里（连续多个会分开，后面合并）
            html_parts.append(f'<ul><li>{item}</li></ul>')
        else:
            pending_para.append(stripped)

    flush_para()

    # 合并相邻 <ul>
    result = '\n'.join(html_parts)
    result = re.sub(r'</ul>\n<ul>', '\n', result)
    # 处理 **粗体**
    result = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', result)
    # 处理 `代码`
    result = re.sub(r'`([^`]+)`', r'<code>\1</code>', result)

    return result


# ============================================================
# 构建完整 HTML 页面
# ============================================================
def build_html(article: dict, body_md: str) -> str:
    body_html = markdown_to_html(body_md)
    slug = article['slug']
    title = article['page_title']
    date = article['date']
    cat_cn = article['category_cn']

    # meta description：取正文前120字
    plain = re.sub(r'<[^>]+>', '', body_html).replace('\n', ' ')
    meta_desc = plain[:120].strip()

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | 帮助中心 - IP归属地查询工具</title>
  <meta name="description" content="{meta_desc}">
  <link rel="canonical" href="https://ipinfo.gamenewspaper.com/help/{slug}.html">
  <meta property="og:type" content="article">
  <meta property="og:title" content="{title}">
  <meta property="og:url" content="https://ipinfo.gamenewspaper.com/help/{slug}.html">
  <meta property="og:site_name" content="IP归属地查询工具">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "{title}",
    "datePublished": "{date}",
    "dateModified": "{date}",
    "publisher": {{
      "@type": "Organization",
      "name": "IP归属地查询工具",
      "url": "https://ipinfo.gamenewspaper.com"
    }}
  }}
  </script>
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    "itemListElement": [
      {{"@type":"ListItem","position":1,"name":"首页","item":"https://ipinfo.gamenewspaper.com/"}},
      {{"@type":"ListItem","position":2,"name":"帮助中心","item":"https://ipinfo.gamenewspaper.com/help.html"}},
      {{"@type":"ListItem","position":3,"name":"{title}","item":"https://ipinfo.gamenewspaper.com/help/{slug}.html"}}
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
        <span>{cat_cn}</span>
        <span aria-hidden="true">›</span>
        <span>{title}</span>
      </nav>

      <div class="article-header">
        <h1>{title}</h1>
        <div class="article-meta">
          <span>📅 {date}</span>
          <span>📂 {cat_cn}</span>
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
    return html


# ============================================================
# 主程序
# ============================================================
if __name__ == '__main__':
    out_dir = 'help'
    os.makedirs(out_dir, exist_ok=True)

    total = len(ARTICLES)
    success = 0

    for i, article in enumerate(ARTICLES, 1):
        slug = article['slug']
        out_path = os.path.join(out_dir, f"{slug}.html")

        print(f"\n[{i}/{total}] 生成：{article['page_title']}")

        # 已存在则跳过（方便断点续跑）
        if os.path.exists(out_path):
            print(f"  ⏭️  已存在，跳过：{out_path}")
            success += 1
            continue

        try:
            body_md = generate_article_body(article)
            print(f"  ✅ 正文生成完毕（{len(body_md)} 字符）")

            html_content = build_html(article, body_md)

            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            print(f"  💾 已写入：{out_path}")
            success += 1

            # 避免触发频率限制
            if i < total:
                time.sleep(3)

        except Exception as e:
            if "rate_limit" in str(e).lower():
                print(f"  ⏳ 频率限制，等待 30 秒后继续...")
                time.sleep(30)
                # 不计入 success，下次运行会重试（文件不存在）
            else:
                print(f"  ❌ 失败：{e}")

    print(f"\n✨ 完成！成功生成 {success}/{total} 篇")
    print(f"📁 文件位于：./{out_dir}/")
