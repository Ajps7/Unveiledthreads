# Split from the original server.py monolith — code is verbatim.
# All modules share the single `api_router` from core; route registration
# order is preserved by the import order in server.py.
from core import *  # noqa: F401,F403

# ============ MESSAGING ============

@api_router.get("/conversations")
async def get_conversations(request: Request):
    user = await get_current_user(request)
    
    convos = await db.conversations.find({
        "$or": [{"participant_1": user["id"]}, {"participant_2": user["id"]}]
    }).sort("last_message_at", -1).to_list(50)
    
    result = []
    for c in convos:
        c["id"] = str(c["_id"])
        del c["_id"]
        # Get other participant info
        other_id = c["participant_2"] if c["participant_1"] == user["id"] else c["participant_1"]
        other_user = await db.users.find_one({"_id": ObjectId(other_id)}, {"_id": 0, "password_hash": 0})
        c["other_user"] = other_user
        # Get brand name if other is a brand
        brand = await db.brands.find_one({"user_id": other_id})
        c["other_brand_name"] = brand["brand_name"] if brand else None
        result.append(c)
    
    return result

@api_router.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str, request: Request):
    user = await get_current_user(request)
    
    convo = await db.conversations.find_one({"_id": safe_object_id(conversation_id)})
    if not convo:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if user["id"] not in [convo["participant_1"], convo["participant_2"]]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    messages = await db.messages.find({"conversation_id": conversation_id}).sort("created_at", 1).to_list(200)
    
    result = []
    for m in messages:
        m["id"] = str(m["_id"])
        del m["_id"]
        result.append(m)
    
    # Mark messages from other user as read
    other_id = convo["participant_2"] if convo["participant_1"] == user["id"] else convo["participant_1"]
    await db.messages.update_many(
        {"conversation_id": conversation_id, "sender_id": other_id, "read": False},
        {"$set": {"read": True}}
    )
    
    return result

@api_router.post("/messages/send")
async def send_message(msg: MessageSend, request: Request):
    user = await get_current_user(request)
    
    if user["id"] == msg.recipient_id:
        raise HTTPException(status_code=400, detail="Cannot message yourself")
    
    # Scan message for forbidden content
    warning = scan_message(msg.content)
    if warning:
        raise HTTPException(status_code=400, detail=warning)
    
    # Check recipient exists
    recipient = await db.users.find_one({"_id": safe_object_id(msg.recipient_id)})
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    # Find or create conversation
    convo = await db.conversations.find_one({
        "$or": [
            {"participant_1": user["id"], "participant_2": msg.recipient_id},
            {"participant_1": msg.recipient_id, "participant_2": user["id"]}
        ]
    })
    
    now = datetime.now(timezone.utc)
    
    if not convo:
        convo_result = await db.conversations.insert_one({
            "participant_1": user["id"],
            "participant_2": msg.recipient_id,
            "order_id": msg.order_id,
            "last_message": msg.content[:100],
            "last_message_at": now,
            "created_at": now
        })
        conversation_id = str(convo_result.inserted_id)
    else:
        conversation_id = str(convo["_id"])
        await db.conversations.update_one(
            {"_id": convo["_id"]},
            {"$set": {"last_message": msg.content[:100], "last_message_at": now}}
        )
    
    # Insert message
    msg_doc = {
        "conversation_id": conversation_id,
        "sender_id": user["id"],
        "sender_name": user["name"],
        "content": msg.content,
        "flagged": False,
        "read": False,
        "created_at": now
    }
    result = await db.messages.insert_one(msg_doc)
    
    # Notify recipient
    await create_notification(
        user_id=msg.recipient_id,
        brand_id=None,
        notification_type="new_message",
        title=f"New message from {user['name']}",
        message=msg.content[:100],
        metadata={"conversation_id": conversation_id}
    )
    
    msg_doc.pop("_id", None)
    msg_doc["id"] = str(result.inserted_id)
    return msg_doc

@api_router.get("/messages/unread-count")
async def get_unread_message_count(request: Request):
    user = await get_current_user(request)
    
    # Get all conversation IDs for this user
    convos = await db.conversations.find({
        "$or": [{"participant_1": user["id"]}, {"participant_2": user["id"]}]
    }, {"_id": 1}).to_list(100)
    
    convo_ids = [str(c["_id"]) for c in convos]
    if not convo_ids:
        return {"count": 0}
    
    count = await db.messages.count_documents({
        "conversation_id": {"$in": convo_ids},
        "sender_id": {"$ne": user["id"]},
        "read": False
    })
    return {"count": count}

