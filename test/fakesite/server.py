import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

DATA_DIR = Path(__file__).parent
PER_PAGE = 5


def render_card(a):
    result_html = ""
    if a.get("result"):
        result_html = (
            f'<div><span class="font14 font-red">Résultat '
            f'<span class="fontRadikalBold">{a["result"]}</span></span></div>'
        )
    image_html = ""
    if a.get("image"):
        image_html = (
            f'<div class="col-md-3 imageArticle noPaddingRight">'
            f'<a href="{a["url"]}"><img class="owl-lazy" loading="lazy" src="{a["image"]}"></a></div>'
        )
    date_html = ""
    if a.get("date"):
        date_html = (
            f'<span><a href="{a["url"]}" style="text-decoration: none" class="font12 colorBlueDark">'
            f'<i class="fa-regular fa-clock marginRight5 font12 colorBlueDark" aria-hidden="true"></i>Publié le '
            f'{a["date"]}</a></span>'
        )
    return f"""
    <div class="col-md-12 articleResume">
      <div class="row">
        <div class="col-md-12 traitSep"></div>
        <div class="col-md-9 contenuArticle">
            <a href="/rubrique/fake/section"><div class="labelRge  marginRight10">Test</div></a>
            {date_html}
            <div class="clear"></div>
            <a href="{a["url"]}">
                <h3 class="titreArticle" data-clamp="2">{a["title"]}</h3>
                {result_html}
                <h4 class="resumeArticle">{a.get("excerpt", "")}</h4>
            </a>
        </div>
        {image_html}
      </div>
    </div>"""


def render_banner():
    # decoy "à ne pas manquer" block — regression check: scraper must never pick this up
    return """
    <div class="bgGris containerWide noPrint">
      <div class="container"><div class="row">
        <div class="blocNePasManquer col-md-12">
          <div class="titreBlocGris">à ne pas manquer</div>
          <div class="carouselMobile owl-carousel owl-theme">
            <a href="/article/decoy-should-be-ignored/999999" class="linkNePasManquer">
              <div class="nePasManquer noPadding">
                <div class="nePasManquerImage"></div>
                <div class="nePasManquerContent"><div class="nePasManquerRedac">
                  <h5 class="nePasManquerTitre">DECOY — should never be scraped or notified</h5>
                </div></div>
              </div>
            </a>
          </div>
        </div>
      </div></div>
    </div>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path.startswith("/rubrique/blocked"):
            # mimics a Cloudflare challenge page, for testing the block-detection path
            html = (
                "<!DOCTYPE html><html><head><title>Just a moment...</title>"
                "<meta http-equiv='content-security-policy' "
                "content=\"script-src 'nonce-x' https://challenges.cloudflare.com\">"
                "</head><body>Checking your browser...</body></html>"
            )
            self._send_html(html)
            return

        if parsed.path.startswith("/rubrique/fake"):
            # /rubrique/fake -> articles.json (single-site tests)
            # /rubrique/fake-a, /rubrique/fake-b -> articles_a.json, articles_b.json (dual-rubrique tests)
            slug = parsed.path.rsplit("/", 1)[-1]
            suffix = slug[len("fake") :].replace("-", "_")  # "", "_a", "_b", ...
            data_file = DATA_DIR / f"articles{suffix}.json"
            qs = parse_qs(parsed.query)
            page_num = int(qs.get("page", ["1"])[0])
            articles = json.loads(data_file.read_text(encoding="utf-8"))
            start = (page_num - 1) * PER_PAGE
            page_articles = articles[start : start + PER_PAGE]

            cards_html = render_banner() + "".join(render_card(a) for a in page_articles)
            html = (
                "<!DOCTYPE html><html><head><meta charset='utf-8'>"
                "<title>Fake rubrique</title></head><body>"
                f"<div class='listeArticles'>{cards_html}</div></body></html>"
            )
            self._send_html(html)
            return

        if parsed.path.startswith("/article/"):
            html = f"<!DOCTYPE html><html><body><h1>Fake article page</h1><p>{parsed.path}</p></body></html>"
            self._send_html(html)
            return

        self.send_response(404)
        self.end_headers()

    def _send_html(self, html: str):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8791
    print(f"serving fake rubrique on http://localhost:{port}/rubrique/fake")
    HTTPServer(("localhost", port), Handler).serve_forever()
