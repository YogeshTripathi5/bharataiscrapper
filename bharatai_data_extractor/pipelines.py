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

    def process_item(self, item, spider):
        filename = re.sub(r'\W+', '_', item['url'])[:100] + ".md"
        path = os.path.join("markdown_output", filename)

        with open(path, "w", encoding="utf-8") as f:
            f.write(f"# {item['title']}\n\n")
            f.write(f"**Source:** {item['url']}\n\n")

            if item["meta_desc"]:
                f.write(f"**Summary:** {item['meta_desc']}\n\n")

            f.write("## Headings\n")
            for h in item["headings"]:
                f.write(f"- {h.strip()}\n")

            f.write("\n## Content\n")
            for p in item["paragraphs"]:
                text = p.strip()
                if len(text) > 40:
                    f.write(text + "\n\n")

            if item["tables"]:
                f.write("\n## Tables\n")
                for row in item["tables"]:
                    f.write(row + "\n")

            if item["media_links"]:
                f.write("\n## Media & Downloads\n")
                for m in item["media_links"]:
                    f.write(f"- Context: {m['context']}\n")
                    f.write(f"  Link: {m['url']}\n\n")

        return item
