# Split from the original server.py monolith — code is verbatim.
# All modules share the single `api_router` from core; route registration
# order is preserved by the import order in server.py.
from core import *  # noqa: F401,F403

# ============ COMMUNITY FEED ============

class CommunityPostCreate(BaseModel):
    content: str
    brand_tag: Optional[str] = None
    image_url: Optional[str] = None

class CommentCreate(BaseModel):
    content: str

@api_router.post("/community/posts")
async def create_community_post(post: CommunityPostCreate, request: Request):
    user = await get_current_user(request)
    
    warning = scan_message(post.content)
    if warning:
        raise HTTPException(status_code=400, detail=warning)
    
    post_doc = {
        "user_id": user["id"],
        "user_name": user["name"],
        "user_role": user.get("role", "user"),
        "content": post.content,
        "brand_tag": post.brand_tag,
        "image_url": post.image_url,
        "likes": [],
        "comment_count": 0,
        "created_at": datetime.now(timezone.utc)
    }
    
    # If user is a brand, attach brand info
    brand = await db.brands.find_one({"user_id": user["id"]})
    if brand:
        post_doc["brand_name"] = brand["brand_name"]
        post_doc["brand_id"] = str(brand["_id"])
    
    result = await db.community_posts.insert_one(post_doc)
    post_doc.pop("_id", None)
    post_doc["id"] = str(result.inserted_id)
    return post_doc

@api_router.get("/community/posts")
async def get_community_posts(
    sort: str = "latest",
    brand_tag: Optional[str] = None,
    limit: int = 30,
    skip: int = 0
):
    query = {}
    if brand_tag:
        query["brand_tag"] = brand_tag
    
    sort_field = "created_at" if sort == "latest" else "created_at"
    sort_dir = -1
    
    if sort == "trending":
        # Sort by like count (approximated by likes array length)
        posts = await db.community_posts.find(query).sort("created_at", -1).limit(100).to_list(100)
        posts.sort(key=lambda p: len(p.get("likes", [])), reverse=True)
        posts = posts[skip:skip+limit]
    else:
        posts = await db.community_posts.find(query).sort(sort_field, sort_dir).skip(skip).limit(limit).to_list(limit)
    
    result = []
    for p in posts:
        p["id"] = str(p["_id"])
        del p["_id"]
        p["like_count"] = len(p.get("likes", []))
        result.append(p)
    
    return result

@api_router.post("/community/posts/{post_id}/like")
async def toggle_like_post(post_id: str, request: Request):
    user = await get_current_user(request)
    
    post = await db.community_posts.find_one({"_id": safe_object_id(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    likes = post.get("likes", [])
    if user["id"] in likes:
        await db.community_posts.update_one(
            {"_id": safe_object_id(post_id)},
            {"$pull": {"likes": user["id"]}}
        )
        return {"liked": False, "like_count": len(likes) - 1}
    else:
        await db.community_posts.update_one(
            {"_id": safe_object_id(post_id)},
            {"$push": {"likes": user["id"]}}
        )
        return {"liked": True, "like_count": len(likes) + 1}

@api_router.get("/community/posts/{post_id}/comments")
async def get_post_comments(post_id: str):
    comments = await db.community_comments.find({"post_id": post_id}).sort("created_at", 1).to_list(100)
    result = []
    for c in comments:
        c["id"] = str(c["_id"])
        del c["_id"]
        result.append(c)
    return result

@api_router.post("/community/posts/{post_id}/comments")
async def add_post_comment(post_id: str, comment: CommentCreate, request: Request):
    user = await get_current_user(request)
    
    warning = scan_message(comment.content)
    if warning:
        raise HTTPException(status_code=400, detail=warning)
    
    post = await db.community_posts.find_one({"_id": safe_object_id(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    comment_doc = {
        "post_id": post_id,
        "user_id": user["id"],
        "user_name": user["name"],
        "user_role": user.get("role", "user"),
        "content": comment.content,
        "created_at": datetime.now(timezone.utc)
    }
    
    brand = await db.brands.find_one({"user_id": user["id"]})
    if brand:
        comment_doc["brand_name"] = brand["brand_name"]
    
    result = await db.community_comments.insert_one(comment_doc)
    
    await db.community_posts.update_one(
        {"_id": safe_object_id(post_id)},
        {"$inc": {"comment_count": 1}}
    )
    
    comment_doc.pop("_id", None)
    comment_doc["id"] = str(result.inserted_id)
    return comment_doc

@api_router.delete("/community/posts/{post_id}")
async def delete_community_post(post_id: str, request: Request):
    user = await get_current_user(request)
    post = await db.community_posts.find_one({"_id": safe_object_id(post_id)})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post["user_id"] != user["id"] and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    await db.community_posts.delete_one({"_id": safe_object_id(post_id)})
    await db.community_comments.delete_many({"post_id": post_id})
    return {"message": "Post deleted"}

# ============ PRODUCT COMMENTS ============

@api_router.get("/products/{product_id}/comments")
async def get_product_comments(product_id: str):
    comments = await db.product_comments.find({"product_id": product_id}).sort("created_at", -1).to_list(50)
    result = []
    for c in comments:
        c["id"] = str(c["_id"])
        del c["_id"]
        result.append(c)
    return result

@api_router.post("/products/{product_id}/comments")
async def add_product_comment(product_id: str, comment: CommentCreate, request: Request):
    user = await get_current_user(request)
    
    warning = scan_message(comment.content)
    if warning:
        raise HTTPException(status_code=400, detail=warning)
    
    product = await db.products.find_one({"_id": safe_object_id(product_id)})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    comment_doc = {
        "product_id": product_id,
        "user_id": user["id"],
        "user_name": user["name"],
        "user_role": user.get("role", "user"),
        "content": comment.content,
        "likes": [],
        "created_at": datetime.now(timezone.utc)
    }
    
    brand = await db.brands.find_one({"user_id": user["id"]})
    if brand:
        comment_doc["brand_name"] = brand["brand_name"]
    
    result = await db.product_comments.insert_one(comment_doc)
    comment_doc.pop("_id", None)
    comment_doc["id"] = str(result.inserted_id)
    return comment_doc

@api_router.post("/products/{product_id}/comments/{comment_id}/like")
async def toggle_like_product_comment(product_id: str, comment_id: str, request: Request):
    user = await get_current_user(request)
    comment = await db.product_comments.find_one({"_id": safe_object_id(comment_id)})
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    
    likes = comment.get("likes", [])
    if user["id"] in likes:
        await db.product_comments.update_one({"_id": safe_object_id(comment_id)}, {"$pull": {"likes": user["id"]}})
        return {"liked": False}
    else:
        await db.product_comments.update_one({"_id": safe_object_id(comment_id)}, {"$push": {"likes": user["id"]}})
        return {"liked": True}

@api_router.delete("/products/{product_id}/comments/{comment_id}")
async def delete_product_comment(product_id: str, comment_id: str, request: Request):
    user = await get_current_user(request)
    comment = await db.product_comments.find_one({"_id": safe_object_id(comment_id)})
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment["user_id"] != user["id"] and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.product_comments.delete_one({"_id": safe_object_id(comment_id)})
    return {"message": "Comment deleted"}

