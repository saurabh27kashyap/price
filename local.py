import requests
import csv
import sys
import io
import time
import re
from urllib.parse import urlparse

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# === CONFIGURATION ===
API_KEY = "90fe9a9b51538cd2fb2a4ac882dec6471108bbbbe46114f41acdd018df4e74a7"

# Coverage threshold - trigger second pass if below this
COVERAGE_THRESHOLD = 0.50  # 50%

# Primary sites - Always search these
PRIMARY_SITES = ["myntra", "slikk"]

# Target shopping sites - Primary 2 + Brand sites
SHOPPING_SITES = {
    # Primary marketplaces
    "myntra": ["myntra.com"],
    "slikk": ["slikk.club"],
    
    # Brand sites
    "bewakoof": ["bewakoof.com"],
    "sassafras": ["sassafras.in"],
    "indian_garage_co": ["tigc.in"],
    "bearhouse": ["thebearhouse.com", "bearhouseindia.com", "thebearhouse.in"],
    "bearcompany": ["bearcompany.in", "thebearcompany.com"],
    "mydesignation": ["mydesignation.com"],
    "beeglee": ["beeglee.in"],
    "color_capital": ["colorcapital.in"],
    "chapter_2": ["chapter2drip.com"],
    "qissa": ["shopqissa.com"],
    "mywishbag": ["mywishbag.com"],
    "campus_sutra": ["campussutra.com"],
    "haute_sauce": ["buyhautesauce.com"],
    "silisoul": ["silisoul.com"],
    "guns_and_sons": ["gunsnsons.com"],
    
    # Sassafras sub-brands mapped to main brand site
    "mascln_sassafras": ["sassafras.in"],
    "shae_by_sassafras": ["sassafras.in"],
    "pink_paprika_by_sassafras": ["sassafras.in"],
}

def get_brand_site(brand_name):
    """
    Get the brand's own website (if exists)
    Returns: brand_site_key or None
    
    ROBUST: Handles all Sassafras sub-brands (Shae, MASCLN, Pink Paprika)
    and maps them to sassafras.in
    """
    # Convert brand name to lowercase for matching
    # Remove ALL spaces, hyphens, and underscores for consistent matching
    brand_lower = brand_name.lower().replace(" ", "").replace("-", "").replace("_", "")
    
    # Enhanced brand mapping with more variations
    brand_mapping = {
        # Bewakoof
        "bewakoof": "bewakoof",
        
        # Sassafras and sub-brands - ALL map to "sassafras"
        "sassafras": "sassafras",
        # MASCLN variants
        "masclnsassafras": "sassafras",
        "mascln": "sassafras",
        "masclnbysassafras": "sassafras",
        "masclnSASSAFRAS": "sassafras",
        # Shae variants
        "shaebysassafras": "sassafras",
        "shae": "sassafras",
        "shaeSASSAFRAS": "sassafras",
        "shaesassafras": "sassafras",
        # Pink Paprika variants
        "pinkpaprikabysassafras": "sassafras",
        "pinkpaprika": "sassafras",
        "pinkpaprikaSASSAFRAS": "sassafras",
        "pinkpaprikasassafras": "sassafras",
        
        # The Indian Garage Co
        "indiangarageco": "indian_garage_co",
        "indiangaragecompany": "indian_garage_co",
        "theindiangaragecompany": "indian_garage_co",
        "theindiangaragecom": "indian_garage_co",
        "theindiangarageco": "indian_garage_co",
        "theindiangarage": "indian_garage_co",
        "tigc": "indian_garage_co",
        
        # Bear House
        "bearhouse": "bearhouse",
        "thebearhouse": "bearhouse",
        "bearhouseindia": "bearhouse",
        "thebearhouseindia": "bearhouse",
        
        # Bear Company
        "bearcompany": "bearcompany",
        "thebearcompany": "bearcompany",
        "bear": "bearcompany",
        "bearco": "bearcompany",
        
        # MyDesignation
        "mydesignation": "mydesignation",
        "designation": "mydesignation",
        
        # BEEGLEE
        "beeglee": "beeglee",
        
        # Color Capital
        "colorcapital": "color_capital",
        
        # Chapter 2
        "chapter2": "chapter_2",
        "chaptertwo": "chapter_2",
        
        # QISSA
        "qissa": "qissa",
        
        # MYWISHBAG
        "mywishbag": "mywishbag",
        
        # Campus Sutra
        "campussutra": "campus_sutra",
        
        # Haute Sauce
        "hautesauce": "haute_sauce",
        
        # SILISOUL
        "silisoul": "silisoul",
        
        # Guns & Sons
        "gunsandsons": "guns_and_sons",
        "gunssons": "guns_and_sons",
        "gunsnsons": "guns_and_sons",
    }
    
    # Get brand's own site if it exists in our database
    brand_site = brand_mapping.get(brand_lower)
    if brand_site and brand_site in SHOPPING_SITES:
        return brand_site
    
    # FALLBACK: Check if brand contains sassafras-related keywords
    # This ensures ALL Sassafras sub-brands map to sassafras.in
    sassafras_keywords = ['sassafras', 'mascln', 'shae', 'paprika']
    if any(keyword in brand_lower for keyword in sassafras_keywords):
        if "sassafras" in SHOPPING_SITES:
            return "sassafras"
    
    return None

def extract_domain(url):
    """Extract clean domain from URL"""
    try:
        parsed = urlparse(url.lower())
        domain = parsed.netloc.replace('www.', '')
        return domain
    except:
        return ""

def identify_site(url):
    """Identify which shopping site the URL belongs to"""
    domain = extract_domain(url)
    url_lower = url.lower()
    
    for site_key, site_patterns in SHOPPING_SITES.items():
        for pattern in site_patterns:
            if pattern in domain or pattern in url_lower:
                return site_key
    return None

def extract_price_from_match(match_data):
    """
    Extract price from match data - handles all possible price formats from SerpAPI
    Returns only numeric values without currency symbols
    """
    price_info = match_data.get("price", {})
    
    # Case 1: Price is a dictionary with 'value' and/or 'extracted_value'
    if isinstance(price_info, dict):
        # Try 'value' first (formatted string like "₹660*")
        price_value = price_info.get("value", "")
        if price_value and price_value not in ["N/A", "", "null"]:
            # Clean the price value
            cleaned = re.sub(r'[₹Rs.,\s*INR]', '', price_value, flags=re.IGNORECASE)
            if cleaned and cleaned.replace('.', '').isdigit():
                return cleaned
        
        # Try 'extracted_value' (usually numeric)
        extracted = price_info.get("extracted_value", "")
        if extracted and str(extracted) not in ["N/A", "", "null"]:
            return str(extracted)
    
    # Case 2: Price is a string
    elif isinstance(price_info, str):
        if price_info and price_info not in ["N/A", "", "null"]:
            cleaned = re.sub(r'[₹Rs.,\s*INR]', '', price_info, flags=re.IGNORECASE)
            if cleaned and cleaned.replace('.', '').isdigit():
                return cleaned
    
    return "Price not displayed in listing"

def extract_colors_from_title(title):
    """Extract color keywords from title"""
    colors = [
        'black', 'white', 'blue', 'red', 'green', 'yellow', 'pink', 'purple', 
        'orange', 'brown', 'grey', 'gray', 'beige', 'navy', 'olive', 'maroon',
        'silver', 'gold', 'cream', 'khaki', 'tan', 'teal', 'burgundy', 'mint',
        'lavender', 'coral', 'peach', 'mustard', 'charcoal', 'rose'
    ]
    
    title_lower = title.lower()
    found_colors = [c for c in colors if c in title_lower]
    return found_colors

def check_brand_relaxed_match(match, target_brand, site_key):
    """
    RELAXED brand verification with site-specific rules
    - Brand's own site: Accept all (site presence = brand verified)
    - Marketplaces: Require brand in title OR URL
    Returns True if brand match is acceptable
    """
    title = match.get("title", "").lower()
    link = match.get("link", "").lower()
    source = match.get("source", "").lower()
    
    # If product is on brand's own website, skip brand verification
    if site_key and site_key not in ['myntra', 'slikk']:
        return True
    
    # For marketplaces, check brand presence
    target_lower = target_brand.lower()
    
    # Generate brand variations to check
    brand_keywords = target_lower.replace("-", " ").replace("_", " ").split()
    
    brand_variations = [
        target_lower.replace(" ", ""),
        target_lower.replace(" ", "-"),
        target_lower.replace(" ", "_"),
        target_lower,
    ]
    
    if len(brand_keywords) > 1:
        combined = "".join(brand_keywords)
        brand_variations.append(combined)
        
        if brand_keywords[0] in ["the"]:
            without_the = " ".join(brand_keywords[1:])
            brand_variations.append(without_the)
            brand_variations.append(without_the.replace(" ", ""))
    
    # Special brand-specific variations
    if "bear" in target_lower:
        brand_variations.extend([
            "bear", "bearhouse", "bear house", "thebearhouse", "the bear house",
            "bearcompany", "bear company", "thebearcompany", "the bear company",
        ])
    
    if "bewakoof" in target_lower:
        brand_variations.extend(["bewakoof", "bwkf"])
    
    if "indian" in target_lower and "garage" in target_lower:
        brand_variations.extend(["indiangarage", "indian garage", "tigc"])
    
    if "sassafras" in target_lower or "mascln" in target_lower or "shae" in target_lower or "pink paprika" in target_lower:
        brand_variations.extend([
            "sassafras", "mascln", "shae", "pink paprika"
        ])
    
    if "mydesignation" in target_lower:
        brand_variations.extend(["mydesignation", "my designation", "designation"])
    
    if "beeglee" in target_lower:
        brand_variations.extend(["beeglee", "bee glee"])
    
    if "chapter" in target_lower:
        brand_variations.extend(["chapter2", "chapter 2", "chapter two"])
    
    if "campus" in target_lower:
        brand_variations.extend(["campussutra", "campus sutra"])
    
    if "guns" in target_lower or "sons" in target_lower:
        brand_variations.extend(["guns", "sons", "gunsnsons", "guns & sons"])
    
    # Check if ANY brand variation exists in title, link, or source
    combined_text = f"{title} {link} {source}"
    
    for variation in brand_variations:
        if variation and len(variation) > 2 and variation in combined_text:
            return True
    
    return False

def is_valid_product_url(url):
    """
    STRICT URL validation - reject category/collection/search pages
    Returns True for actual product pages only
    """
    url_lower = url.lower()
    
    # Invalid patterns - these indicate non-product pages
    invalid_patterns = [
        '/collections/', '/collection/', '/category/', '/categories/',
        '/search', '?search=', '/s?', '/find/',
        '/brand/', '/brands/', '/sale/', '/deals/',
        '/all-products', '/shop?',
        '/filter', '/sort=',
        '?page=', '&page=',  # Pagination
        '/men/', '/women/', '/kids/', '/unisex/',
        '/clothing/', '/accessories/', '/footwear/'
    ]
    
    # Check for invalid patterns
    for pattern in invalid_patterns:
        if pattern in url_lower:
            return False
    
    # Site-specific validations
    if 'bewakoof.com' in url_lower:
        return '/p/' in url_lower or '/product/' in url_lower or '/buy' in url_lower
    elif 'myntra.com' in url_lower:
        return '/buy' in url_lower or '/p/' in url_lower
    elif 'slikk.club' in url_lower:
        return True  # Accept all Slikk URLs after invalid pattern check
    elif 'mydesignation.com' in url_lower:
        return '/products/' in url_lower
    elif 'sassafras.in' in url_lower:
        return '/products/' in url_lower
    elif 'bearhouse' in url_lower or 'bearcompany' in url_lower or 'thebearhouse' in url_lower:
        return '/products/' in url_lower or '/product/' in url_lower
    elif 'tigc.in' in url_lower:
        return '/products/' in url_lower
    elif 'beeglee.in' in url_lower:
        return '/products/' in url_lower or '/product/' in url_lower
    elif 'colorcapital.in' in url_lower:
        return '/products/' in url_lower or '/product/' in url_lower
    elif 'chapter2drip.com' in url_lower:
        return '/products/' in url_lower or '/product/' in url_lower
    elif 'shopqissa.com' in url_lower:
        return '/products/' in url_lower or '/product/' in url_lower
    elif 'mywishbag.com' in url_lower:
        return '/products/' in url_lower or '/product/' in url_lower
    elif 'campussutra.com' in url_lower:
        return '/products/' in url_lower or '/product/' in url_lower
    elif 'buyhautesauce.com' in url_lower:
        return '/products/' in url_lower or '/product/' in url_lower
    elif 'silisoul.com' in url_lower:
        return '/products/' in url_lower or '/product/' in url_lower
    elif 'gunsnsons.com' in url_lower:
        return '/products/' in url_lower or '/product/' in url_lower
    
    # Generic validation: Accept URLs with 3+ meaningful path segments
    path_segments = [s for s in url_lower.split('/') if s and not s.startswith('?')]
    return len(path_segments) >= 3

def search_image_on_serpapi(image_url):
    """
    Search for visually similar products using SerpAPI Google Lens
    PURE IMAGE SEARCH - No text query
    FRESH DATA - No cache
    """
    params = {
        "engine": "google_lens",
        "url": image_url,
        "api_key": API_KEY,
        "country": "in",
        "hl": "en",
        "no_cache": "true"
    }
    
    try:
        response = requests.get("https://serpapi.com/search", params=params, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"  ❌ API Error: {str(e)}")
        return None

def search_image_with_query_on_serpapi(image_url, brand_query):
    """
    Search with Image + Brand Query ONLY
    Let Google return ALL brand products, we filter locally
    FRESH DATA - No cache
    INCREASED TIMEOUT - 60 seconds to avoid timeouts
    """
    params = {
        "engine": "google_lens",
        "url": image_url,
        "q": brand_query,
        "api_key": API_KEY,
        "country": "in",
        "hl": "en",
        "no_cache": "true"
    }
    
    try:
        response = requests.get("https://serpapi.com/search", params=params, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"  ❌ API Error: {str(e)}")
        return None

def calculate_title_similarity(original_title, found_title):
    """
    Calculate similarity between original and found product titles
    Returns a score between 0-100
    Includes color matching bonus/penalty
    """
    if not original_title or not found_title:
        return 0
    
    # Normalize titles
    orig_lower = original_title.lower()
    found_lower = found_title.lower()
    
    # Extract keywords (ignore common words)
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'with', 'for', 'on', 'in', 'at', 'to', 'buy', 'shop', 'online'}
    
    orig_keywords = set(re.findall(r'\b\w+\b', orig_lower)) - stop_words
    found_keywords = set(re.findall(r'\b\w+\b', found_lower)) - stop_words
    
    if not orig_keywords:
        return 0
    
    # Calculate keyword overlap
    common_keywords = orig_keywords & found_keywords
    overlap_score = (len(common_keywords) / len(orig_keywords)) * 100
    
    # Extract and compare colors
    orig_colors = extract_colors_from_title(orig_lower)
    found_colors = extract_colors_from_title(found_lower)
    
    # Color match bonus/penalty
    color_bonus = 0
    if orig_colors:
        if any(c in found_colors for c in orig_colors):
            color_bonus = 15  # Bonus for matching color
        elif found_colors:
            color_bonus = -20  # Penalty for wrong color
    
    final_score = min(100, max(0, overlap_score + color_bonus))
    return final_score

def extract_product_info(visual_matches, target_brand, allowed_sites, original_product, pass_type="first"):
    """
    Extract product URLs with ROBUST LOCAL FILTERING
    NEW APPROACH: Get all results from Google, filter locally with strict criteria
    
    Local Filtering:
    - Visual Rank: Top 15 only (reject low ranks)
    - Category: Keyword match (mandatory)
    - Gender: Flexible (Men/Unisex, Women/Unisex ok)
    - Price: ±30% validation (if available)
    - Title: 10-20% similarity (less important now)
    - Brand: Relaxed verification
    """
    results = {}
    for site_key in allowed_sites:
        results[site_key] = {
            "url": "Not Found",
            "price": "Product not available on site",
        }
    
    if not visual_matches:
        return results, 0, 0
    
    brand_matches = 0
    rejected = 0
    rejected_similarity = 0
    rejected_rank = 0
    rejected_category = 0
    rejected_price = 0
    
    # Extract original product attributes for filtering
    original_title = original_product.get('product_title', '')
    original_gender = original_product.get('gender', '').lower()
    original_category = original_product.get('category', '').lower()
    original_price = float(original_product.get('min_price_rupees', 0)) if original_product.get('min_price_rupees') else 0
    
    # Process each match and collect candidates
    candidates = {site_key: [] for site_key in allowed_sites}
    
    for idx, match in enumerate(visual_matches, 1):
        link = match.get("link", "")
        match_title = match.get("title", "").lower()
        
        if not link:
            continue
        
        # === FILTER 1: Visual Rank (Top 15 only) ===
        if idx > 15:
            rejected_rank += 1
            continue
        
        site_key = identify_site(link)
        if not site_key or site_key not in allowed_sites:
            continue
        
        # === FILTER 2: Brand Verification ===
        if not check_brand_relaxed_match(match, target_brand, site_key):
            rejected += 1
            continue
        
        # === FILTER 3: URL Validation ===
        if not is_valid_product_url(link):
            continue
        
        # === FILTER 4: Category Match (MANDATORY) ===
        category_keywords = {
            'shirts': ['shirt'],
            't-shirts': ['tshirt', 't-shirt', 'tee'],
            'jeans': ['jean'],
            'trousers': ['trouser', 'pant'],
            'kurtas': ['kurta', 'kurti'],
            'dresses': ['dress'],
            'tops': ['top', 'bodysuit', 'corset', 'cami', 'tank', 'crop'],
            'jackets': ['jacket', 'blazer'],
            'sweatshirts': ['sweatshirt', 'sweater', 'hoodie'],
            'skirts': ['skirt'],
        }
        
        category_match = False
        if original_category:
            for cat_key, cat_keywords in category_keywords.items():
                if cat_key in original_category:
                    if any(kw in match_title for kw in cat_keywords):
                        category_match = True
                        break
            
            # If category specified but no match, reject
            if not category_match and original_category not in ['other sets', 'onesies', 'glasses', 'caps']:
                rejected_category += 1
                continue
        
        # === FILTER 5: Price Validation (±30% tolerance) ===
        price_str = extract_price_from_match(match)
        price_valid = True
        
        if original_price > 0 and price_str not in ["Price not displayed in listing", "Product not available on site", "Check site for price"]:
            try:
                found_price = float(price_str)
                price_diff = abs(found_price - original_price) / original_price
                
                # Reject if price difference > 30%
                if price_diff > 0.30:
                    rejected_price += 1
                    price_valid = False
                    continue
            except:
                pass  # If price parsing fails, accept the match
        
        # === FILTER 6: Title Similarity (Now less important) ===
        similarity_score = calculate_title_similarity(original_title, match_title)
        
        # Lower thresholds since we have stricter rank/category/price filters
        is_marketplace = site_key in ['myntra', 'slikk']
        
        if is_marketplace:
            similarity_threshold = 3  # Very low for marketplaces
        else:
            similarity_threshold = 10  # Low for brand sites
        
        if similarity_score < similarity_threshold:
            rejected_similarity += 1
            continue
        
        # === PASSED ALL FILTERS - Add to candidates ===
        candidates[site_key].append({
            "url": link,
            "price": price_str,
            "visual_rank": idx,
            "similarity": similarity_score,
            "title": match_title
        })
    
    # Select BEST candidate for each site
    # NEW LOGIC: Prioritize lower rank (more visually similar)
    for site_key in allowed_sites:
        if candidates[site_key]:
            # Simply pick the lowest visual rank (most visually similar)
            # Since we already filtered by category, price, etc., rank is most important
            best_match = min(candidates[site_key], key=lambda x: x['visual_rank'])
            
            results[site_key] = {
                "url": best_match["url"],
                "price": best_match["price"]
            }
            
            brand_matches += 1
            
            # Display result with filtering stats
            site_display = site_key.upper().replace("_", " ")
            rank = best_match["visual_rank"]
            similarity = best_match["similarity"]
            price_display = f"₹{best_match['price']}" if best_match["price"] not in ["Price not displayed in listing", "Product not available on site", "Check site for price"] else "Check site"
            pass_indicator = "🔄" if pass_type == "second" else "✓"
            print(f"      {pass_indicator} {site_display}: Rank #{rank} | Match {similarity:.0f}% | Price: {price_display}")
    
    # Debug info for rejections
    if pass_type == "second":
        total_rejected = rejected + rejected_rank + rejected_category + rejected_price + rejected_similarity
        if total_rejected > 0:
            print(f"      Filtered: {total_rejected} (rank>{rejected_rank}, cat={rejected_category}, price={rejected_price}, sim={rejected_similarity})")
    
    return results, brand_matches, rejected

def process_single_product(product, product_idx, total_products):
    """
    Process a single product with 2-pass search strategy
    Returns: dict with site_results
    """
    print(f"\n[{product_idx}/{total_products}] {product['product_title'][:60]}... ({product['brand']})")
    
    if not product['image']:
        print("  ⚠ No image URL - Skipping")
        return {'product': product, 'site_results': {}, 'brand_site': None}
    
    # Determine which sites to search for this product
    brand_site = get_brand_site(product['brand'])
    allowed_sites = PRIMARY_SITES.copy()
    if brand_site:
        allowed_sites.append(brand_site)
    
    print(f"  🔍 Searching: {', '.join([s.upper() for s in allowed_sites])}")
    
    # === PASS 1: Pure image search ===
    search_results = search_image_on_serpapi(product['image'])
    
    if not search_results:
        print("  ⚠ No API results")
        return {'product': product, 'site_results': {}, 'brand_site': brand_site}
    
    visual_matches = search_results.get("visual_matches", [])
    
    site_results, brand_matches, rejected = extract_product_info(
        visual_matches, 
        product['brand'], 
        allowed_sites, 
        product,  # Pass full product dict for local filtering
        pass_type="first"
    )
    
    sites_found = sum(1 for site_data in site_results.values() if site_data["url"] != "Not Found")
    print(f"  💾 Pass 1: Found on {sites_found}/{len(allowed_sites)} site(s)")
    
    # === PASS 2: Image + Brand Query ONLY (local filtering) ===
    sites_missing = [s for s in allowed_sites if site_results.get(s, {}).get('url') == "Not Found"]
    
    if sites_missing:
        print(f"  🔄 Pass 2: Brand-only query (local filtering enabled)")
        
        # NEW APPROACH: Use ONLY brand in query
        # Let Google return ALL brand products, we filter locally
        # For sassafras sub-brands, use just "SASSAFRAS"
        brand_for_query = product['brand']
        if any(x in product['brand'].lower() for x in ['mascln', 'shae', 'pink paprika']):
            brand_for_query = "SASSAFRAS"
        
        print(f"  Query: {brand_for_query} (filtering: {product['category']}, {product['gender']}, price ±30%)")
        
        search_results = search_image_with_query_on_serpapi(product['image'], brand_for_query)
        
        if search_results:
            visual_matches = search_results.get("visual_matches", [])
            print(f"  → Got {len(visual_matches)} results from Google, filtering locally...")
            
            site_results_pass2, _, _ = extract_product_info(
                visual_matches,
                product['brand'],
                sites_missing,
                product,  # Pass full product dict for local filtering
                pass_type="second"
            )
            
            # Update results
            for site_key in sites_missing:
                if site_results_pass2.get(site_key, {}).get('url') != "Not Found":
                    site_results[site_key] = site_results_pass2[site_key]
    
    sites_found_final = sum(1 for site_data in site_results.values() if site_data["url"] != "Not Found")
    print(f"  ✅ Total: Found on {sites_found_final}/{len(allowed_sites)} site(s)")
    
    return {'product': product, 'site_results': site_results, 'brand_site': brand_site}

def process_products(input_csv, output_csv):
    """
    MULTI-BRAND PROCESSING with GENERIC OUTPUT SCHEMA
    - Handles multiple brands in a single CSV
    - Outputs generic columns: brand_price, brand_url (instead of brand-specific names)
    - Maintains myntra and slikk columns as-is
    """
    # Read input CSV
    products = []
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            products.append({
                'style_id': row.get('style_id', ''),
                'brand': row.get('brand', ''),
                'product_title': row.get('product_title', ''),
                'gender': row.get('gender', ''),
                'category': row.get('category', ''),
                'min_price_rupees': row.get('min_price_rupees', ''),
                'image': row.get('first_image_url', '')
            })
    
    # Get unique brands
    unique_brands = list(set(p['brand'] for p in products))
    
    print(f"\n{'='*80}")
    print(f"🔍 MULTI-BRAND PRODUCT SEARCH v6.0 - LOCAL FILTERING")
    print(f"{'='*80}")
    print(f"Input: {input_csv} → Output: {output_csv}")
    print(f"✅ NEW: Brand-only queries + Local filtering")
    print(f"✅ Filters: Rank≤15, Category match, Price±30%")
    print(f"✅ Timeout: 60s (avoid API timeouts)")
    print(f"✅ Generic output schema: brand_price, brand_url")
    print(f"{'='*80}")
    print(f"\n📦 Processing {len(products)} products from {len(unique_brands)} brand(s):")
    for brand in sorted(unique_brands):
        count = sum(1 for p in products if p['brand'] == brand)
        print(f"   • {brand}: {count} product(s)")
    print()
    
    # Fixed output schema with generic brand columns
    fieldnames = [
        'style_id', 'brand', 'product_title', 'gender', 'category',
        'klydo_price', 'myntra_price', 'slikk_price', 'brand_price',
        'klydo_url', 'myntra_url', 'slikk_url', 'brand_url'
    ]
    
    all_results = []
    
    print(f"{'='*80}")
    print("PROCESSING PRODUCTS")
    print(f"{'='*80}")
    
    # Process each product individually
    for idx, product in enumerate(products, 1):
        result = process_single_product(product, idx, len(products))
        all_results.append(result)
        
        # Rate limiting between products
        if idx < len(products):
            time.sleep(1)
    
    # WRITE RESULTS
    print(f"\n{'='*80}")
    print("WRITING RESULTS")
    print(f"{'='*80}\n")
    
    with open(output_csv, 'w', encoding='utf-8', newline='') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        
        for result_entry in all_results:
            product = result_entry['product']
            site_results = result_entry['site_results']
            brand_site = result_entry['brand_site']
            
            # Extract prices and URLs
            myntra_data = site_results.get('myntra', {"url": "Not Found", "price": "Product not available on site"})
            slikk_data = site_results.get('slikk', {"url": "Not Found", "price": "Product not available on site"})
            
            # Get brand site data (if exists)
            if brand_site:
                brand_data = site_results.get(brand_site, {"url": "Not Found", "price": "Product not available on site"})
            else:
                brand_data = {"url": "Not Found", "price": "Product not available on site"}
            
            row_data = {
                'style_id': product['style_id'],
                'brand': product['brand'],
                'product_title': product['product_title'],
                'gender': product['gender'],
                'category': product['category'],
                'klydo_price': product['min_price_rupees'],
                'myntra_price': myntra_data['price'],
                'slikk_price': slikk_data['price'],
                'brand_price': brand_data['price'],
                'klydo_url': f"https://klydo.in/product/{product['style_id']}",
                'myntra_url': myntra_data['url'],
                'slikk_url': slikk_data['url'],
                'brand_url': brand_data['url']
            }
            
            writer.writerow(row_data)
    
    # Final coverage report
    print(f"\n✅ Processed {len(products)} products")
    print(f"\n{'='*80}")
    print("COVERAGE SUMMARY")
    print(f"{'='*80}")
    
    myntra_count = sum(1 for r in all_results if r['site_results'].get('myntra', {}).get('url') != "Not Found")
    slikk_count = sum(1 for r in all_results if r['site_results'].get('slikk', {}).get('url') != "Not Found")
    
    # Count brand site coverage (each product may have different brand site)
    brand_count = 0
    for r in all_results:
        brand_site = r['brand_site']
        if brand_site and r['site_results'].get(brand_site, {}).get('url') != "Not Found":
            brand_count += 1
    
    myntra_pct = (myntra_count / len(products) * 100) if products else 0
    slikk_pct = (slikk_count / len(products) * 100) if products else 0
    brand_pct = (brand_count / len(products) * 100) if products else 0
    
    myntra_status = "✅" if myntra_pct >= 50 else "⚠️"
    slikk_status = "✅" if slikk_pct >= 50 else "⚠️"
    brand_status = "✅" if brand_pct >= 50 else "⚠️"
    
    print(f"{myntra_status} MYNTRA: {myntra_count}/{len(products)} ({myntra_pct:.0f}%)")
    print(f"{slikk_status} SLIKK: {slikk_count}/{len(products)} ({slikk_pct:.0f}%)")
    print(f"{brand_status} BRAND SITES: {brand_count}/{len(products)} ({brand_pct:.0f}%)")
    
    print(f"\n✅ Output saved: {output_csv}")
    print("📄 Schema: style_id, brand, ..., myntra_price, slikk_price, brand_price, myntra_url, slikk_url, brand_url")

# === MAIN EXECUTION ===
if __name__ == "__main__":
    INPUT_FILE = "sample.csv"
    OUTPUT_FILE = "many.csv"
    
    process_products(INPUT_FILE, OUTPUT_FILE)
    
    print("\n✅ ALL DONE!")
    print(f"📄 Check: {OUTPUT_FILE}")
