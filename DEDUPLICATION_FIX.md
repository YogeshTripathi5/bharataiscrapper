# Scraper Deduplication Fix - Summary

## Problem Identified

The scraped output file `www_edfirst_in.md` showed massive repetition of content. For example:
- "Advancing Education through" appeared **32 times**
- The same page content was duplicated across multiple "pages"

## Root Causes

### Issue 1: URL Fragment Duplication
The scraper was treating URLs with different fragments as separate pages:
```
https://www.edfirst.in/          ← Page 1
https://www.edfirst.in/#contact  ← Page 2 (SAME PAGE!)
https://www.edfirst.in/#careers  ← Page 3 (SAME PAGE!)
https://www.edfirst.in/#support  ← Page 4 (SAME PAGE!)
```

**Why this happened:**
- Fragment identifiers (`#contact`, `#careers`, etc.) are anchor links on a single-page application
- The spider was checking `if response.url in self.visited_urls`
- URLs with different fragments were considered unique, even though they serve the same HTML content

### Issue 2: Overly Broad CSS Selectors
The original paragraph extraction code was:
```python
item["paragraphs"] = response.css("p::text, li::text, span::text, div::text").getall()
```

**Problems:**
- **Too broad:** Extracted text from `<p>`, `<li>`, `<span>`, and `<div>` elements indiscriminately
- **Navigation repetition:** Captured all text from headers, navigation menus, footers, sidebars
- **No deduplication:** Elements appearing on every section of the page were captured multiple times
- **Short snippets:** Included button text, labels, and UI elements

**Example of what was captured:**
- Navigation links: "About", "Contact", "Careers" → repeated on every page
- Footer text: "© 2024 EdFirst" → repeated on every page
- Button labels: "Learn More", "Apply Now" → captured from multiple buttons

## Solutions Implemented

### Fix 1: URL Normalization with Fragment Removal

**Code changes (lines 98-106):**
```python
# 🔗 Normalize URL by removing fragment (#anchor) to avoid duplicate scraping
parsed_url = urlparse(response.url)
normalized_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
if parsed_url.query:
    normalized_url += f"?{parsed_url.query}"

if normalized_url in self.visited_urls:
    self.logger.info(f"⏭️ Skipping duplicate (fragment): {response.url}")
    return
self.visited_urls.add(normalized_url)
```

**What this does:**
- Removes fragment identifiers (`#...`) from URLs before checking if visited
- `https://www.edfirst.in/#contact` → normalized to → `https://www.edfirst.in/`
- Now only scrapes the page **once**, regardless of anchor links
- Still logs all visited URLs (with fragments) for transparency

### Fix 2: Intelligent Content Extraction

**Code changes (lines 131-151):**
```python
# 📝 Extract paragraphs more intelligently
main_content = response.css("main, article, .content, #content")
if main_content:
    # Prioritize main content area
    paragraphs = main_content.css("p::text").getall()
else:
    # Fallback to all paragraphs
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
```

**Improvements:**
1. **Focused extraction:** Tries to extract from `<main>`, `<article>`, `.content` containers first
2. **Text-only approach:** Removed `li::text, span::text, div::text` selectors
3. **Length filter:** Ignores text snippets shorter than 20 characters (buttons, labels, etc.)
4. **Deduplication:** Removes duplicate paragraphs while maintaining original order
5. **Trimming:** Strips whitespace for clean comparison

### Fix 3: Heading Deduplication

**Code changes (lines 129-139):**
```python
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
```

**What this does:**
- Removes duplicate headings (e.g., "Contact Us" in navigation AND footer)
- Preserves first occurrence order
- Cleans up whitespace

## Expected Impact

### Before Fix:
```
Page 1: Full content (500 lines)
Page 2: Same content + all nav/footer (550 lines) ← DUPLICATE
Page 3: Same content + all nav/footer (550 lines) ← DUPLICATE
Page 4: Same content + all nav/footer (550 lines) ← DUPLICATE
Total: ~2,150 lines with massive repetition
```

### After Fix:
```
Page 1: Clean, deduplicated content (200-300 lines)
Total: ~200-300 lines with no repetition
```

**Reduction:** ~85-90% reduction in redundant content

## Benefits

1. **Cleaner data:** No more repetitive navigation/footer text
2. **Smaller files:** More efficient storage and processing
3. **Better quality:** Focus on actual content, not UI elements
4. **Accurate scraping:** One page = one scrape (fragments handled correctly)
5. **Easier analysis:** LLMs and other tools can process the data more effectively

## Testing Recommendations

To verify the fix:
1. Delete the existing `markdown_output/www_edfirst_in.md` file
2. Run the scraper again: `scrapy crawl knowledge`
3. Check the new output file:
   - Should have only ONE entry for `www.edfirst.in`
   - "Advancing Education through" should appear ~1-2 times (in actual content)
   - No massive repetition from navigation/footer

## Files Modified

1. **bharatai_data_extractor/spiders/knowledge_spider.py**
   - Added URL normalization logic
   - Improved paragraph extraction with deduplication
   - Added heading deduplication
   - Enhanced logging for skipped duplicates
