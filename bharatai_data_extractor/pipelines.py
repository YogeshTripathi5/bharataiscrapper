# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import os
import re

# useful for handling different item types with a single interface
class MarkdownPipeline:

    def open_spider(self, spider):
        os.makedirs("markdown_output", exist_ok=True)
        self.domain_files = {}  # Track open files by domain
        self.domain_page_counts = {}  # Track number of pages per domain

    def close_spider(self, spider):
        # Close all open file handles
        for f in self.domain_files.values():
            f.close()
        
        # Print summary
        spider.logger.info("=" * 80)
        spider.logger.info("SCRAPING SUMMARY")
        spider.logger.info("=" * 80)
        for domain, count in self.domain_page_counts.items():
            spider.logger.info(f"  {domain}: {count} pages scraped")
        spider.logger.info("=" * 80)

    def process_item(self, item, spider):
        domain = item['domain']
        
        # Create/get the file for this domain
        if domain not in self.domain_files:
            # Create a safe filename from domain
            safe_domain = re.sub(r'\W+', '_', domain)
            filename = f"{safe_domain}.md"
            path = os.path.join("markdown_output", filename)
            
            # Open file in append mode
            self.domain_files[domain] = open(path, "a", encoding="utf-8")
            self.domain_page_counts[domain] = 0
            
            # Write domain header (only once per domain)
            f = self.domain_files[domain]
            f.write(f"# Domain: {domain}\n\n")
            f.write(f"This file contains all scraped pages from the domain: **{domain}**\n\n")
            f.write("---\n\n")
        
        # Increment page count for this domain
        self.domain_page_counts[domain] += 1
        
        # Append page data to the domain file
        f = self.domain_files[domain]
        
        f.write(f"## Page {self.domain_page_counts[domain]}: {item['title']}\n\n")
        f.write(f"**URL:** {item['url']}\n\n")

        if item["meta_desc"]:
            f.write(f"**Summary:** {item['meta_desc']}\n\n")

        if item["headings"]:
            f.write("### Headings\n")
            for h in item["headings"]:
                if h and h.strip():
                    f.write(f"- {h.strip()}\n")
            f.write("\n")

        f.write("### Content\n")
        for p in item["paragraphs"]:
            text = p.strip()
            if len(text) > 40:
                f.write(text + "\n\n")

        if item["tables"]:
            f.write("### Tables\n")
            for row in item["tables"]:
                f.write(row + "\n")
            f.write("\n")

        if item["media_links"]:
            f.write("### Media & Downloads\n")
            for m in item["media_links"]:
                f.write(f"- **Context:** {m['context']}\n")
                f.write(f"  **Link:** {m['url']}\n\n")

        f.write("\n---\n\n")  # Separator between pages
        f.flush()  # Ensure data is written to disk

        return item
