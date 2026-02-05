import scrapy
from scrapy.http import TextResponse
from bharatai_data_extractor.items import PageItem
from urllib.parse import urlparse
import os
from datetime import datetime

class KnowledgeSpider(scrapy.Spider):
    name = "knowledge"
    visited_urls = set()
    visited_urls_file = "visited_urls.txt"
    
    # Allow all domains - don't restrict to start domain
    allowed_domains = []  # Empty list = no domain restrictions

    # 🚫 Never crawl these (internet explosion sources)
    BLOCKED_DOMAINS = [
        "facebook", "twitter", "instagram", "linkedin",
        "pinterest", "amazon", "flipkart", "netflix",
        "spotify", "news", "blogspot", "wordpress"
    ]

    # 🧠 Indicates knowledge pages
    KNOWLEDGE_KEYWORDS = [
        "education", "policy", "scheme", "program",
        "student", "curriculum", "training", "ministry",
        "university", "school", "institute"
    ]

    # 🌍 Domains likely to contain real docs
    TRUST_DOMAIN_HINTS = [
        ".gov.in",      # Central & State Government
        ".nic.in",      # National Informatics Centre hosted sites
        ".ac.in",       # Indian academic institutions
        ".edu.in",      # Educational institutions (less common now)
        ".org.in",      # Govt-affiliated orgs / councils
        ".res.in",      # Research institutions
        ".ernet.in",    # Education & research network
        ".aiims.edu",   # AIIMS and medical institutes
        ".gov",      # Central & State Government
        ".nic",      # National Informatics Centre hosted sites
        ".ac",       # Indian academic institutions
    ]



    handle_httpstatus_list = [403]

    def spider_opened(self, spider):
        """Initialize the visited URLs file when spider starts"""
        with open(self.visited_urls_file, 'w', encoding='utf-8') as f:
            f.write(f"# Visited URLs - Scraping started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("# " + "="*70 + "\n\n")
        self.logger.info(f"📝 Visited URLs will be logged to: {self.visited_urls_file}")

    def log_visited_url(self, url):
        """Append a visited URL to the file"""
        with open(self.visited_urls_file, 'a', encoding='utf-8') as f:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] {url}\n")

    def start_requests(self):
        yield scrapy.Request(
            "https://www.edfirst.in/",
            meta={"playwright": True}
        )

    def is_blocked(self, url):
        return any(b in url.lower() for b in self.BLOCKED_DOMAINS)

    def is_trusted_domain(self, url):
        return any(hint in url.lower() for hint in self.TRUST_DOMAIN_HINTS)

    def is_relevant_page(self, response):
        if not isinstance(response, TextResponse):
            return False

        text = " ".join(
            response.css("p::text, h1::text, h2::text").getall()
        ).lower()
        return any(word in text for word in self.KNOWLEDGE_KEYWORDS)

    def parse(self, response):
        # 🛡️ HANDLE BLOCKS / 403 ERRORS
        if response.status == 403:
            if response.meta.get("playwright"):
                self.logger.warning(f"⚠️ Playwright blocked on {response.url}. Retrying with standard Scrapy Request...")
                yield scrapy.Request(
                    response.url,
                    callback=self.parse,
                    meta={"playwright": False}, # Disable Playwright for retry
                    dont_filter=True
                )
            else:
                self.logger.error(f"❌ blocked (403) even with standard request: {response.url}. Skipping.")
            return

        # 🔗 Normalize URL by removing fragment (#anchor) to avoid duplicate scraping
        parsed_url = urlparse(response.url)
        normalized_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
        if parsed_url.query:
            normalized_url += f"?{parsed_url.query}"
        
        if normalized_url in self.visited_urls:
            self.logger.info(f"⏭️ Skipping duplicate (fragment): {response.url}")
            return
        self.visited_urls.add(normalized_url)
        
        # 📝 Log the visited URL to file
        self.log_visited_url(response.url)

        # 📄 Check if it's text (HTML) content
        if not isinstance(response, TextResponse):
            return

        # 🚫 Skip junk pages but allow trusted domains
        if not self.is_relevant_page(response) and not self.is_trusted_domain(response.url):
            return

        # Extract domain from URL
        domain = parsed_url.netloc  # e.g., 'education.gov.in' or 'nta.ac.in'
        
        item = PageItem()
        item["url"] = response.url
        item["domain"] = domain
        item["title"] = response.css("title::text").get()
        item["meta_desc"] = response.css("meta[name='description']::attr(content)").get()

        # Extract headings and remove duplicates
        headings = response.css("h1::text, h2::text, h3::text, h4::text").getall()
        headings = [h.strip() for h in headings if h.strip()]
        # Remove duplicates while preserving order
        seen_headings = set()
        unique_headings = []
        for h in headings:
            if h not in seen_headings:
                seen_headings.add(h)
                unique_headings.append(h)
        item["headings"] = unique_headings
        
        # 📝 Extract paragraphs more intelligently - focus on main content, avoid nav/footer repetition
        # Try to get content from main content areas first
        main_content = response.css("main, article, .content, #content")
        if main_content:
            # Extract from main content area
            paragraphs = main_content.css("p::text").getall()
        else:
            # Fallback to all paragraphs, but avoid navigation
            paragraphs = response.css("p::text").getall()
        
        # Filter out empty or very short text (likely UI elements)
        paragraphs = [p.strip() for p in paragraphs if p.strip() and len(p.strip()) > 20]
        # Remove duplicates while preserving order
        seen = set()
        unique_paragraphs = []
        for p in paragraphs:
            if p not in seen:
                seen.add(p)
                unique_paragraphs.append(p)
        
        item["paragraphs"] = unique_paragraphs

        # 📊 TABLES
        tables = []
        for row in response.css("table tr"):
            cols = row.css("td::text, th::text").getall()
            if cols:
                tables.append(" | ".join([c.strip() for c in cols]))
        item["tables"] = tables

        # 🎥 MEDIA LINKS WITH CONTEXT
        media = []
        for a in response.css("a"):
            href = a.attrib.get("href", "")
            context = " ".join(a.xpath("ancestor::p//text()").getall()).strip()

            if any(x in href.lower() for x in [
                ".pdf", ".jpg", ".png", ".jpeg",
                ".mp4", ".webm",
                "youtube.com", "youtu.be"
            ]):
                media.append({
                    "url": response.urljoin(href),
                    "context": context
                })

        item["media_links"] = media
        yield item

        # 🔁 FOLLOW LINKS INTELLIGENTLY
        for link in response.css("a::attr(href)").getall():
            full_url = response.urljoin(link)

            if (
                full_url.startswith("http")
                and full_url not in self.visited_urls
                and not self.is_blocked(full_url)
            ):
                yield scrapy.Request(
                    full_url,
                    callback=self.parse,
                    meta={"playwright": True}, # Default to Playwright
                    dont_filter=True
                )