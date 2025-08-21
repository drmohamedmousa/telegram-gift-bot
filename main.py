import os, io, math
from PIL import Image
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, filters

print("Starting bot…")  # You should see this in Railway logs

# ---- Utilities -------------------------------------------------------------
def rgb_to_hsv(r, g, b):
    r, g, b = [x/255.0 for x in (r, g, b)]
    mx, mn = max(r,g,b), min(r,g,b)
    df = mx - mn
    if df == 0:
        h = 0.0
    elif mx == r:
        h = (60 * ((g - b) / df) + 360) % 360
    elif mx == g:
        h = (60 * ((b - r) / df) + 120) % 360
    else:
        h = (60 * ((r - g) / df) + 240) % 360
    s = 0.0 if mx == 0 else df / mx
    v = mx
    return h, s, v

def dominant_rgb(pil_image):
    im = pil_image.convert("RGB").resize((64, 64))
    colors = im.getcolors(64*64)
    if not colors:
        return (127,127,127)
    colors.sort(reverse=True)
    return colors[0][1]

def hex_of(rgb):
    return "#{:02X}{:02X}{:02X}".format(*rgb)

def sort_strategy(items, mode, target=None):
    # We’ll keep it simple: rainbow by hue
    if mode == "rainbow":
        return sorted(items, key=lambda x: rgb_to_hsv(*x["rgb"])[0])
    return items

# ---- Bot Handlers ----------------------------------------------------------
async def start(update: Update, context: CallbackContext):
    context.user_data.setdefault("gifts", [])
    await update.message.reply_text(
        "Hello 👋 Send me photos of your gifts (one per message). "
        "When you’re ready, type /order to get a color-sorted list."
    )

async def photo_handler(update: Update, context: CallbackContext):
    caption = (update.message.caption or "").strip() or f"Gift #{len(context.user_data.get('gifts', []))+1}"
    photo = update.message.photo[-1]  # highest quality
    file = await photo.get_file()
    bio = io.BytesIO()
    await file.download_to_memory(bio)
    bio.seek(0)
    img = Image.open(bio)
    rgb = dominant_rgb(img)
    entry = {"label": caption, "rgb": rgb}
    context.user_data.setdefault("gifts", []).append(entry)
    await update.message.reply_text(f"Saved: {caption} — dominant color {hex_of(rgb)}")

async def order_cmd(update: Update, context: CallbackContext):
    gifts = context.user_data.get("gifts", [])
    if not gifts:
        await update.message.reply_text("No gifts yet — send me some photos first!")
        return
    ordered = sort_strategy(gifts, "rainbow")
    lines = []
    for i, g in enumerate(ordered, 1):
        lines.append(f"{i}. {g['label']} ({hex_of(g['rgb'])})")
    await update.message.reply_text("Suggested order:\n" + "\n".join(lines))

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("Set BOT_TOKEN env var")
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("order", order_cmd))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
