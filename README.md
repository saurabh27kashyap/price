# 🛍️ Product Finder — Search Pipeline Documentation
**File:** `multibrand.py`  
A multi-pass product search pipeline using Google Lens + strict client-side filtering to return the most accurate product URLs.

---

## 🔍 Current Search Strategy

### **PASS 1 — Pure Image Search**
- Send the image to **Google Lens with *no text***.  
- Collect **20–30 visually similar product candidates**.  
- Apply all filtering layers (see below).

---

### **PASS 2 — Image + Query (Only for Missing Sites)**
If a required site is still **“Not Found”** after Pass 1:

- Make a second Lens request with:  
- **Example:**  
`Image + "The Bear House Men Shirts brown"`

This increases match accuracy for sites that pure visual search misses.

---

## 🛡️ Client-Side Filtering (6 Layers)

### **1. Site Identification**
Detect the domain and classify link as:
- Myntra  
- Slikk  
- Brand website  

---

### **2. Brand Verification**
- **Marketplaces:** brand must appear in the **title OR URL**  
- **Brand sites:** skip verification  
- e.g. `thebearhouse.com` auto-maps to **The Bear House**

---

### **3. Strict URL Validation**
Reject URLs containing:
- `/collections/`
- `/category/`
- `/search?`
- `?page=`

Special rules:
- **Bewakoof:** reject category-like URLs (e.g., `mens-blue-hoodies-16`)  
- **Slikk:** reject `/products?filters=...` (previous issue now fixed)

Only **valid product URLs with product IDs** are accepted.

---

### **4. Title Similarity Matching**
Compute keyword overlap between your extracted title vs. product title.

**Thresholds:**
- **Myntra:** 5% (Lens is accurate here)  
- **Slikk:** 5%  
- **Brand sites:** 15% (stricter to avoid same-product variants)

---

### **5. Color Matching**
Extract primary color tokens (black, white, blue, brown, etc.)

Scoring:
- **Color match:** +15% similarity  
- **Color mismatch:** –20% similarity  

Prevents wrong-color item matches (e.g., black vs. white).

---

### **6. Final Candidate Selection**
- **Marketplaces:** choose the product with the best **visual rank** from Lens  
- **Brand sites:** use a mix of **visual rank + title similarity**

---

## ✅ Pipeline Summary
1. Perform image-only search  
2. Re-run with image + metadata if needed  
3. Apply all 6 filtering layers  
4. Select the most accurate final product URL  
5. Avoid category pages, irrelevant products, duplicates, and mismatches  

---

