# CSV product-import for brands. Split out of routes/products.py to keep the
# core CRUD file focused. All imports land as `status="draft"` so nothing
# reaches buyers without an explicit publish step.
from core import *  # noqa: F401,F403
from routes.products import CATEGORIES  # canonical list; keep drafts inside it

import csv
import io
import ipaddress
import re
import socket
from urllib.parse import urlparse

# ============ CSV IMPORT CONSTANTS ============
MAX_IMPORT_FILE_BYTES = 5 * 1024 * 1024        # 5 MB cap on the CSV itself
MAX_IMPORT_PRODUCTS = 200                       # per-file product cap
MAX_IMAGES_PER_PRODUCT = 10                     # matches ProductCreate.images cap
MAX_SIZES_PER_PRODUCT = 15                      # matches ProductCreate.sizes cap
MAX_IMAGE_FETCH_BYTES = 8 * 1024 * 1024         # match MAX_IMAGE_SIZE (8MB) for parity
IMAGE_FETCH_TIMEOUT = 20                        # seconds per remote image
# Only allow http(s) hosts. Rejects file://, javascript:, gopher:, etc.
ALLOWED_IMAGE_SCHEMES = {"http", "https"}
# SSRF defence: only allow the standard web ports. Rejects http://host:6379/…
# (Redis), :27017 (Mongo), :22 (SSH), etc. Empty port = default port for scheme.
ALLOWED_IMAGE_PORTS = {80, 443, None}
# Cloud-metadata endpoints — explicitly blocklisted on top of the generic
# link-local / private-IP guards. Belt-and-braces vs. is_link_local.
CLOUD_METADATA_HOSTS = {
    "169.254.169.254",              # AWS, GCP, Azure IMDS v1/v2
    "fd00:ec2::254",                # AWS IPv6 IMDS
    "metadata.google.internal",     # GCP alias
    "metadata",                     # k8s / IMDS alias
}


# ---- Column-name → canonical-field mapping ----
# Values are lowercased/stripped before lookup. Multiple aliases map to the
# same canonical field so Shopify/Etsy/WooCommerce/Squarespace/generic
# exports all Just Work without asking the seller to remap columns.
COLUMN_ALIASES: dict[str, str] = {
    # name / title
    "name": "name",
    "title": "name",
    "product name": "name",
    "product title": "name",
    # description
    "description": "description",
    "body": "description",
    "body (html)": "description",
    "body_html": "description",
    "product description": "description",
    # price
    "price": "price",
    "variant price": "price",
    "regular price": "price",
    # category
    "category": "category",
    "product type": "category",
    "type": "category",
    "product category": "category",
    # sizes
    "size": "size",
    "sizes": "size",
    "variant": "size",
    "option1 value": "size",  # Shopify convention when Option1 Name == "Size"
    # stock
    "stock": "stock",
    "inventory": "stock",
    "quantity": "stock",
    "variant inventory qty": "stock",
    "stock quantity": "stock",
    # images
    "image": "image",
    "images": "image",
    "image src": "image",
    "image url": "image",
    # grouping key (Shopify)
    "handle": "handle",
}

# Extra columns that carry additional images (e.g. Shopify Image Src on
# extra rows or bespoke CSVs with image_2, image_3…). Matched by prefix.
IMAGE_EXTRA_PREFIXES = ("image_", "image ", "images_", "additional image")


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_html_to_text(raw: str) -> str:
    """Very defensive HTML → plain-text: strip tags and collapse whitespace.
    Shopify's `Body (HTML)` column can contain <p>, <br>, <img> etc — we
    keep the readable text and drop everything else."""
    if not raw:
        return ""
    text = _TAG_RE.sub(" ", str(raw))
    # Turn common HTML entities into their characters, then normalise whitespace.
    text = html.unescape(text)
    return _WS_RE.sub(" ", text).strip()


def _canonicalise_header(h: str) -> Optional[str]:
    """Map a CSV header cell to a canonical field name, or None if unknown."""
    if not h:
        return None
    key = h.strip().lower()
    if key in COLUMN_ALIASES:
        return COLUMN_ALIASES[key]
    for pref in IMAGE_EXTRA_PREFIXES:
        if key.startswith(pref):
            return "image"
    return None


def _parse_price(raw) -> Optional[float]:
    """Handle "£12.50", "12,50", "$19.99", etc. Returns None if not parseable."""
    if raw is None:
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    s = str(raw).strip()
    if not s:
        return None
    # Drop currency symbols and spaces; convert comma decimal to dot.
    s = re.sub(r"[^\d.,-]", "", s)
    if s.count(",") and not s.count("."):
        s = s.replace(",", ".")
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def _parse_int(raw) -> Optional[int]:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _first_nonempty(*vals):
    for v in vals:
        if v is not None and str(v).strip() != "":
            return v
    return None


def _valid_external_image_url(url: str) -> bool:
    """Only accept http(s) URLs. Rejects file://, javascript:, and empties."""
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False
    return parsed.scheme in ALLOWED_IMAGE_SCHEMES and bool(parsed.netloc)


def _is_safe_public_url(url: str) -> bool:
    """SSRF gate: return True only if `url` (a) parses to an http(s) URL on a
    standard web port, (b) resolves to public/global IPs on every A/AAAA
    record, and (c) isn't a known cloud-metadata alias.

    Blocks: loopback (127.x, ::1), link-local (169.254.x — covers AWS/GCP/Azure
    IMDS), private (10.x, 172.16/12, 192.168.x, fc00::/7), reserved,
    multicast, unspecified, and any explicit non-80/443 port. Fails closed:
    if DNS resolution or parsing throws for any reason, we return False and
    the fetch is skipped.

    NOTE: this is the pre-flight destination check called before every
    outbound HTTP request in the CSV importer. To keep redirect-based SSRF
    off the table, the fetcher itself must NOT follow redirects."""
    if not _valid_external_image_url(url):
        return False
    try:
        parsed = urlparse(url.strip())
    except Exception:
        return False

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return False

    # Explicit blocklist first — cheaper than DNS resolution, and catches
    # attackers who bypass IP checks with metadata.google.internal etc.
    if hostname in CLOUD_METADATA_HOSTS:
        logger.warning(f"[SSRF] Blocked known metadata host: {hostname}")
        return False

    # Only standard web ports. parsed.port is None when the URL omits it
    # (uses the scheme default) — which we accept.
    if parsed.port is not None and parsed.port not in ALLOWED_IMAGE_PORTS:
        logger.warning(f"[SSRF] Blocked non-standard port: {parsed.port} on {hostname}")
        return False

    # Resolve every A/AAAA record. Any single non-public address = reject.
    # Using getaddrinfo (not gethostbyname) so we see IPv6 too.
    try:
        infos = socket.getaddrinfo(hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    except Exception as e:
        logger.warning(f"[SSRF] DNS resolution failed for {hostname}: {e}")
        return False

    if not infos:
        return False

    for _family, _type, _proto, _canon, sockaddr in infos:
        ip_str = sockaddr[0]
        # Strip IPv6 zone-id suffix if present (e.g. "fe80::1%eth0").
        if "%" in ip_str:
            ip_str = ip_str.split("%", 1)[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            logger.warning(f"[SSRF] Unparseable IP for {hostname}: {ip_str}")
            return False

        # Belt-and-braces: cloud metadata IPs, even if they somehow slipped
        # past hostname blocklist via CNAME.
        if str(ip) in CLOUD_METADATA_HOSTS:
            logger.warning(f"[SSRF] Blocked metadata IP {ip} for {hostname}")
            return False

        # The main filter. Note is_link_local covers 169.254.0.0/16 (AWS/GCP
        # IMDS), is_private covers 10/8, 172.16/12, 192.168/16, fc00::/7,
        # is_loopback covers 127/8 and ::1.
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            logger.warning(f"[SSRF] Blocked non-public IP {ip} for {hostname}")
            return False

    return True


def _guess_mime_from_bytes(data: bytes) -> Optional[str]:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and len(data) >= 12 and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _ext_for_mime(mime: str) -> str:
    return {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "image/webp": "webp",
    }.get(mime, "jpg")


async def _fetch_and_store_external_image(url: str, brand_id: str, user_id: str) -> Optional[str]:
    """Download an image from a CSV-supplied URL, verify it's a real image,
    and put it into our own object storage. Returns the local `/api/files/...`
    URL on success, or None on any failure (network, size, MIME, storage).

    We DO NOT keep the original external URL — the whole point of the import
    is to stop listings depending on the brand's Shopify/Etsy CDN.
    """
    if not _valid_external_image_url(url):
        return None
    # SSRF gate: resolve the hostname and refuse if any resolved IP is
    # private/loopback/link-local/etc. Runs BEFORE the network call.
    if not _is_safe_public_url(url):
        return None
    try:
        # allow_redirects=False is the key redirect-based-SSRF defence: a
        # public URL that 302's to 169.254.169.254 would otherwise bypass
        # the pre-check above. If a legitimate source uses redirects, the
        # brand can point us at the final CDN URL directly.
        resp = http_requests.get(
            url,
            timeout=IMAGE_FETCH_TIMEOUT,
            stream=True,
            allow_redirects=False,
        )
        if 300 <= resp.status_code < 400:
            logger.warning(f"[CSV-IMPORT] Refusing to follow redirect for {url} → {resp.headers.get('Location')}")
            return None
        resp.raise_for_status()
        # Stream so we can hard-cap the total downloaded bytes.
        chunks = []
        total = 0
        for chunk in resp.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            total += len(chunk)
            if total > MAX_IMAGE_FETCH_BYTES:
                logger.warning(f"[CSV-IMPORT] Image too large, skipping: {url}")
                return None
            chunks.append(chunk)
        data = b"".join(chunks)
    except Exception as e:
        logger.warning(f"[CSV-IMPORT] Fetch failed for {url}: {e}")
        return None

    mime = _guess_mime_from_bytes(data)
    if not mime:
        logger.warning(f"[CSV-IMPORT] Unknown format, skipping: {url}")
        return None
    if not verify_image_magic_bytes(data, mime):
        logger.warning(f"[CSV-IMPORT] Magic-byte check failed: {url}")
        return None

    file_id = str(uuid.uuid4())
    path = f"{APP_NAME}/imports/{brand_id}/{file_id}.{_ext_for_mime(mime)}"
    try:
        result = put_object(path, data, mime)
    except Exception as e:
        logger.error(f"[CSV-IMPORT] Storage put failed: {e}")
        return None

    # Register in the files collection so /api/files serves it and GDPR
    # user-data flows can find it.
    await db.files.insert_one({
        "file_id": file_id,
        "storage_path": result["path"],
        "original_filename": urlparse(url).path.rsplit("/", 1)[-1] or f"{file_id}.{_ext_for_mime(mime)}",
        "content_type": mime,
        "size": result.get("size", len(data)),
        "user_id": user_id,
        "source_url": url,
        "is_deleted": False,
        "created_at": datetime.now(timezone.utc),
    })
    return f"/api/files/{result['path']}"


def _group_rows(rows: List[dict]) -> List[dict]:
    """Group CSV rows into products.

    Shopify/Etsy exports emit one row PER VARIANT with the title repeated
    and most product fields blank on continuation rows. We group by Handle
    (Shopify) when present, otherwise by (name.lower()). Continuation rows
    contribute their variant size and any extra image URLs; product-level
    fields (description/price/category/stock) are taken from the first
    row that carries them.
    """
    groups: dict[str, dict] = {}
    order: list[str] = []
    last_key: Optional[str] = None

    for i, row in enumerate(rows):
        handle = str(row.get("handle") or "").strip().lower()
        name = str(row.get("name") or "").strip()
        key = handle or (name.lower() if name else last_key or f"__row{i}")

        # Continuation row (Shopify pattern): same handle, blank name — keep
        # the previous group. If no handle either, fall back to sticky last_key.
        if key not in groups:
            groups[key] = {
                "_row_number": i + 2,   # +2 = header row is 1, first data row is 2
                "name": name,
                "description": "",
                "price": None,
                "category": None,
                "stock": None,
                "shipping_cost": None,
                "sizes": [],
                "images": [],
            }
            order.append(key)

        g = groups[key]

        # Take the first non-empty description/price/category/stock we see.
        desc_raw = row.get("description")
        if desc_raw and not g["description"]:
            g["description"] = _strip_html_to_text(desc_raw)

        price = _parse_price(row.get("price"))
        if price is not None and g["price"] is None:
            g["price"] = price

        cat = row.get("category")
        if cat and not g["category"]:
            g["category"] = str(cat).strip().lower()

        stock = _parse_int(row.get("stock"))
        if stock is not None and g["stock"] is None:
            g["stock"] = stock

        # Prefer the first non-blank name across rows in the group.
        if name and not g["name"]:
            g["name"] = name

        # Sizes: collect every non-empty size cell across all rows in the group.
        size_val = row.get("size")
        if size_val:
            s = str(size_val).strip()
            if s and s.lower() not in ("default title",) and s not in g["sizes"]:
                if len(g["sizes"]) < MAX_SIZES_PER_PRODUCT:
                    g["sizes"].append(s)

        # Images: collect distinct URLs across all image columns and rows.
        for img in row.get("_images", []):
            if img and img not in g["images"]:
                if len(g["images"]) < MAX_IMAGES_PER_PRODUCT:
                    g["images"].append(img)

        last_key = key

    return [groups[k] for k in order]


def _extract_rows(csv_text: str) -> List[dict]:
    """Parse CSV text into a list of {canonical_field: value, _images: [urls]} dicts.

    Multiple image columns (Image Src, image_2, image_3, ...) are collapsed
    into a single `_images` list per row. Unknown columns are silently
    ignored — we don't want to fail an import because Shopify added a new
    "SEO Description" column."""
    reader = csv.reader(io.StringIO(csv_text))
    try:
        headers_raw = next(reader)
    except StopIteration:
        return []

    # Map each column index → canonical field name (or None to skip).
    # We preserve the LIST of image column indices because Shopify's
    # additional image columns share the same "image src" alias.
    canon = [_canonicalise_header(h) for h in headers_raw]

    out: List[dict] = []
    for row in reader:
        if not any(cell.strip() for cell in row if cell is not None):
            continue  # skip fully blank lines
        entry: dict = {"_images": []}
        for idx, val in enumerate(row):
            if idx >= len(canon):
                break
            field = canon[idx]
            if field is None:
                continue
            if field == "image":
                if val and val.strip():
                    entry["_images"].append(val.strip())
            else:
                # Take the first non-empty value per canonical field per row.
                if field not in entry and val is not None:
                    entry[field] = val
        out.append(entry)
    return out


def _sanitise_text(raw: Optional[str], max_len: int) -> str:
    if raw is None:
        return ""
    txt = _strip_html_to_text(str(raw))
    return txt[:max_len]


async def _build_product_doc(
    group: dict,
    brand: dict,
    user_id: str,
) -> Tuple[Optional[dict], Optional[str], List[str]]:
    """Turn a grouped row-set into a persisted product doc (as draft).

    Returns (product_doc_or_None, error_reason_or_None, warnings_list).
    A non-None error means the row was SKIPPED. Warnings are non-fatal
    (e.g. an image failed to fetch — product is still created as a draft
    with a `missing_images` flag).
    """
    warnings: List[str] = []

    # ---- Required fields ----
    name = _sanitise_text(group.get("name"), 120).strip()
    if len(name) < 2:
        return None, "missing or too-short product name", warnings

    price = group.get("price")
    if price is None or price <= 0:
        return None, "missing or invalid price", warnings
    if price > 10000:
        return None, "price above marketplace cap (£10,000)", warnings

    description = _sanitise_text(group.get("description"), 3000).strip()
    if len(description) < 10:
        # Pad short descriptions with a placeholder so validation passes;
        # the brand can edit before publishing. Better UX than skipping.
        description = (description + " — Imported listing; edit before publishing.").strip()
        if len(description) < 10:
            description = "Imported listing. Please add a full product description before publishing."
        warnings.append("description was short and has been padded — please edit before publishing")

    category = (_sanitise_text(group.get("category"), 50) or "accessories").strip().lower()
    # Coerce unknown categories to "accessories" so drafts don't fail
    # validation just because the source used a different taxonomy.
    if not any(c["id"] == category for c in CATEGORIES):
        warnings.append(f"unknown category '{category}' — defaulted to 'accessories'")
        category = "accessories"

    sizes = group.get("sizes") or []
    if not sizes:
        sizes = ["One Size"]
        warnings.append("no sizes in CSV — defaulted to 'One Size'")

    stock = group.get("stock")
    if stock is None or stock < 0:
        stock = 0

    # ---- Fetch images into our storage ----
    stored_images: List[str] = []
    for url in group.get("images") or []:
        if len(stored_images) >= MAX_IMAGES_PER_PRODUCT:
            break
        local = await _fetch_and_store_external_image(url, str(brand["_id"]), user_id)
        if local:
            stored_images.append(local)
        else:
            warnings.append(f"couldn't fetch image: {url}")

    if not stored_images:
        # No images survived — still create the draft so the brand can fix
        # it, but keep it un-publishable until they upload something.
        warnings.append("no images stored — brand must add at least one image before publishing")

    # Moderate any images we DID store. Drafts NEVER auto-publish so this
    # is informational only; the actual publish gate re-checks moderation.
    moderation: List[dict] = []
    if stored_images:
        moderation = await moderate_product_images(stored_images)

    now = datetime.now(timezone.utc)
    doc = {
        "brand_id": str(brand["_id"]),
        "brand_name": brand["brand_name"],
        "name": name,
        "description": description,
        "price": float(price),
        "category": category,
        "sizes": sizes[:MAX_SIZES_PER_PRODUCT],
        "images": stored_images,
        "stock": int(stock),
        "shipping_cost": 3.99,
        "colour": None,
        "material": None,
        "gender": "unisex",
        "condition": "new",
        "fit": None,
        "is_preorder": False,
        "preorder_ship_date": None,
        "preorder_limit": None,
        "story": None,
        "details": None,
        "materials": None,
        "fit_notes": None,
        "care": None,
        "images_moderation": moderation,
        # Never surface drafts publicly — even if moderation says 'passed'.
        "moderation_status": (
            "needs_review" if any(m["status"] == "unverified" for m in moderation) else
            "flagged" if any(m["status"] == "flagged" for m in moderation) else
            "passed"
        ),
        "status": "draft",
        "import_source": "csv",
        "import_warnings": warnings,
        "missing_images": len(stored_images) == 0,
        "created_at": now,
    }
    return doc, None, warnings


# ============ ROUTES ============

@api_router.post("/products/import/csv")
@limiter.limit("5/minute")
async def import_products_csv(request: Request, file: UploadFile = File(...)):
    """Bulk-import a brand's catalogue from a CSV. Products land as
    reviewable drafts so nothing reaches buyers without an explicit
    publish step and passing moderation."""
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")

    # Size + content-type gate on the CSV itself.
    if file.content_type and file.content_type not in (
        "text/csv", "application/csv", "application/vnd.ms-excel",
        "text/plain", "application/octet-stream",
    ):
        raise HTTPException(status_code=400, detail="Please upload a CSV file (.csv).")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="CSV file is empty.")
    if len(raw) > MAX_IMPORT_FILE_BYTES:
        raise HTTPException(status_code=400, detail=f"CSV must be under {MAX_IMPORT_FILE_BYTES // (1024*1024)}MB.")

    # Decode: prefer UTF-8, fall back to Latin-1 so a Shopify export saved
    # from Excel doesn't 500 the endpoint.
    try:
        csv_text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        csv_text = raw.decode("latin-1", errors="replace")

    rows = _extract_rows(csv_text)
    if not rows:
        raise HTTPException(status_code=400, detail="No product rows found in CSV. Check the header row.")

    groups = _group_rows(rows)
    if len(groups) > MAX_IMPORT_PRODUCTS:
        raise HTTPException(
            status_code=400,
            detail=f"CSV contains {len(groups)} products — the per-file cap is {MAX_IMPORT_PRODUCTS}. Split it into smaller files.",
        )

    created = 0
    errors: List[dict] = []
    warnings_all: List[dict] = []
    created_ids: List[str] = []

    for g in groups:
        doc, err, warns = await _build_product_doc(g, brand, user["id"])
        if err:
            errors.append({"row": g.get("_row_number"), "name": g.get("name") or "(unknown)", "reason": err})
            continue
        result = await db.products.insert_one(doc)
        pid = str(result.inserted_id)
        created_ids.append(pid)
        created += 1
        if warns:
            warnings_all.append({"product_id": pid, "name": doc["name"], "warnings": warns})

    logger.info(
        f"[CSV-IMPORT] brand={brand['_id']} created={created} skipped={len(errors)} "
        f"warnings={sum(len(w['warnings']) for w in warnings_all)}"
    )

    return {
        "created": created,
        "skipped": len(errors),
        "errors": errors,
        "warnings": warnings_all,
        "created_ids": created_ids,
    }


@api_router.get("/products/my/drafts")
async def list_my_drafts(request: Request):
    """Return the current brand's draft products (imported but not yet published)."""
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")

    drafts = await db.products.find({
        "brand_id": str(brand["_id"]),
        "status": "draft",
    }).sort("created_at", -1).limit(500).to_list(500)

    for d in drafts:
        d["id"] = str(d["_id"])
        del d["_id"]
    return drafts


def _draft_publish_blocker(product: dict) -> Optional[str]:
    """Return a human-readable reason this draft can't be published yet,
    or None if it's good to go. Mirrors the validation applied at create
    time so a hand-edited draft can't sneak past."""
    if not product.get("images"):
        return "add at least one image before publishing"
    if product.get("missing_images"):
        return "some images from the CSV couldn't be imported — replace them before publishing"
    mod = product.get("moderation_status")
    if mod == "flagged":
        return "one or more images were flagged by moderation — replace them before publishing"
    if mod == "needs_review":
        return "images are pending admin review — please wait for moderation to finish"
    if not product.get("name") or len(product["name"].strip()) < 2:
        return "product name is missing"
    desc = product.get("description") or ""
    if len(desc.strip()) < 10:
        return "description is too short (min 10 characters)"
    if not product.get("price") or product["price"] <= 0:
        return "price must be greater than £0"
    if not product.get("sizes"):
        return "add at least one size before publishing"
    if not product.get("category"):
        return "category is missing"
    return None


@api_router.post("/products/{product_id}/publish")
async def publish_draft(product_id: str, request: Request):
    """Flip a draft into a live listing. Enforces the same validation and
    moderation gates as the create endpoint."""
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")

    product = await db.products.find_one({"_id": safe_object_id(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product.get("brand_id") != str(brand["_id"]):
        raise HTTPException(status_code=403, detail="Not authorised to publish this product")
    if product.get("status") != "draft":
        raise HTTPException(status_code=400, detail="Only drafts can be published")

    blocker = _draft_publish_blocker(product)
    if blocker:
        raise HTTPException(status_code=422, detail=blocker)

    await db.products.update_one(
        {"_id": safe_object_id(product_id)},
        {"$set": {"status": "published", "published_at": datetime.now(timezone.utc)}},
    )
    return {"id": product_id, "status": "published"}


@api_router.post("/products/drafts/publish-all")
async def publish_all_valid_drafts(request: Request):
    """Publish every valid draft in one go. Drafts with any blocker
    (missing images, flagged moderation, etc.) are left as drafts and
    returned in the `skipped` list so the brand can fix them."""
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")

    drafts = await db.products.find({
        "brand_id": str(brand["_id"]),
        "status": "draft",
    }).to_list(500)

    published_ids: List[str] = []
    skipped: List[dict] = []
    for d in drafts:
        blocker = _draft_publish_blocker(d)
        if blocker:
            skipped.append({"product_id": str(d["_id"]), "name": d.get("name"), "reason": blocker})
            continue
        await db.products.update_one(
            {"_id": d["_id"]},
            {"$set": {"status": "published", "published_at": datetime.now(timezone.utc)}},
        )
        published_ids.append(str(d["_id"]))

    return {"published": len(published_ids), "skipped": len(skipped), "skipped_details": skipped, "published_ids": published_ids}


class BulkDeleteDrafts(BaseModel):
    ids: List[str] = Field(min_length=1, max_length=200)


@api_router.post("/products/drafts/delete-many")
async def bulk_delete_drafts(payload: BulkDeleteDrafts, request: Request):
    """Delete a batch of the brand's own drafts. Safety: we hard-scope
    to (brand_id, status='draft') so a compromised token can't wipe
    published listings via this endpoint even if it forges IDs."""
    user = await require_brand(request)
    brand = await db.brands.find_one({"user_id": user["id"]})
    if not brand:
        raise HTTPException(status_code=404, detail="Brand profile not found")

    # Sanitise + coerce. Any single malformed ObjectId in the batch fails
    # the whole request with a 400 — mixing valid + invalid IDs almost
    # always signals a client bug or a tampered request, and swallowing
    # bad IDs silently would make that impossible to debug.
    valid_object_ids = []
    for pid in payload.ids:
        try:
            valid_object_ids.append(ObjectId(pid))
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid product ID in batch: {pid!r}")
    if not valid_object_ids:
        raise HTTPException(status_code=400, detail="No valid draft IDs supplied")

    result = await db.products.delete_many({
        "_id": {"$in": valid_object_ids},
        "brand_id": str(brand["_id"]),
        "status": "draft",
    })
    return {"deleted": result.deleted_count}
