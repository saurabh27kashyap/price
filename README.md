Product Finder

File: multibrand.py
Current logic and pipeline used for finding the most accurate product URLs using Google Lens + client-side filtering.

🚀 What We Do NOW

This system runs a multi-pass search and applies 6 strict filtering layers to avoid wrong, irrelevant, or category URLs.

🔍 SEARCH STRATEGY
PASS 1: Pure Image Search

Send the image to Google Lens with NO text

Get ~20–30 visually similar products

Apply local filtering (see filtering layers)

PASS 2: Image + Query (only for missing sites)

Triggered only when a site remains “Not Found” after Pass 1.

Second API call includes:

image + "brand gender category color"


Example:

Image + “The Bear House Men Shirts brown”

🛡️ CLIENT-SIDE FILTERING (6 Protection Layers)
Layer 1: Site Identification

Check the domain → Is the link from:

Myntra

Slikk

Brand site

Layer 2: Brand Verification

Marketplaces: brand must appear in the title OR URL

Brand sites: skip this check

Example: thebearhouse.com → automatically The Bear House

Layer 3: URL Validation (STRICT)

Reject:

/collections/, /category/, /search?, ?page=

Bewakoof: reject short URLs like mens-blue-hoodies-16

Slikk: fixed — reject /products?filters=... (was accepting earlier)

Accept only:

Valid product URLs with product IDs

Layer 4: Title Similarity

Compute keyword overlap between your extracted title and found product title.

Thresholds:

Myntra: 5% (lenient, Lens accurate)

Slikk: 5%

Brand sites: 15% (stricter, avoids variants)

Layer 5: Color Matching

Extract primary colors (black, white, blue, brown, etc.)

Rules:

Colors match → +15% similarity bonus

Colors mismatch → –20% penalty

Prevents: matching “Black T-shirt” with “White T-shirt”.

Layer 6: Candidate Selection

Marketplaces: pick item with best visual rank (trust Lens)

Brand sites: use visual rank + title similarity combination

✅ Summary of Pipeline

PASS 1: Image-only

PASS 2: Image + brand/category/color query

Apply 6 protection layers

Select final candidate per site

Avoids category pages, wrong products, and irrelevant matches
