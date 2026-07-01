"""
Telegram Bot: Gram & Game Shop
Python (aiogram 3.x) versiyasi — asl PHP koddan to'liq o'girilgan
Developer: @ZcCoder (asl), Python'ga moslashtirildi
"""

import asyncio
import json
import logging
import os
import random
from pathlib import Path

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

# ====================== SOZLAMALAR ======================
API_TOKEN = "8631595682:AAHogiKNsaUELs7D9_fs1CeodixU217BNRE"  # Bot tokeningiz
ADMIN_ID = 8565856542  # O'zingizning Telegram ID raqamingiz
CARD_NUMBER = "9860246602105347"  # Karta raqamingiz
GRAM_PRICE = 20340  # 1 ta gram narxi (so'm)
BOT_USERNAME = "@StarsPay_HUMOBot"  # Referal havola uchun bot username (@ siz)

DB_PATH = Path("db.json")

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)


# ====================== FSM HOLATLARI ======================
class UserStates(StatesGroup):
    get_gram = State()        # gram miqdorini kutish
    send_receipt = State()    # chek (rasm) kutish


class AdminStates(StatesGroup):
    add_balance_id = State()
    add_balance_amount = State()
    sub_balance_id = State()
    sub_balance_amount = State()
    broadcast = State()
    ban_id = State()
    unban_id = State()
    channel_add = State()


# ====================== DATABASE (JSON) ======================
def load_db() -> dict:
    if not DB_PATH.exists():
        db = {"users": {}, "status": "on", "channels": []}
        save_db(db)
        return db
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(db: dict) -> None:
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False)


def get_user(db: dict, user_id: int) -> dict:
    return db["users"].setdefault(
        str(user_id),
        {
            "balance": 0,
            "bot_id": random.randint(1000, 9999),
            "banned": False,
            "referals": 0,
        },
    )


# ====================== KLAVIATURALAR ======================
def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💎 Gram olish"), KeyboardButton(text="💰 Gram sotish")],
            [KeyboardButton(text="🎮 Pubg"), KeyboardButton(text="🔥 FreeFire")],
            [KeyboardButton(text="💳 Hisob to'ldirish"), KeyboardButton(text="👤 Profil")],
            [KeyboardButton(text="📜 Qoida"), KeyboardButton(text="🎁 Gift olish")],
        ],
        resize_keyboard=True,
    )


def admin_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="➕ Pul qo'shish")],
            [KeyboardButton(text="➖ Pul ayirish"), KeyboardButton(text="📢 Xabar tarqatish")],
            [KeyboardButton(text="📢 Kanal sozlamalari"), KeyboardButton(text="⚙️ Bot holati")],
            [KeyboardButton(text="🚫 Ban/Unban")],
        ],
        resize_keyboard=True,
    )


def receipt_kb(user_id: int, order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Qabul qilish", callback_data=f"accept_{user_id}_{order_id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{user_id}"),
            ]
        ]
    )


def profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔗 Referal silka", callback_data="get_ref")]]
    )


def pubg_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="60 UC - 13,000 so'm", callback_data="buy_pubg_13000_60")],
            [InlineKeyboardButton(text="120 UC - 25,000 so'm", callback_data="buy_pubg_25000_120")],
            [InlineKeyboardButton(text="325 UC - 59,000 so'm", callback_data="buy_pubg_59000_325")],
            [InlineKeyboardButton(text="600 UC - 120,000 so'm", callback_data="buy_pubg_120000_600")],
        ]
    )


def gift_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="15🐻 - 3500 s", callback_data="gift"),
                InlineKeyboardButton(text="15💝 - 3500 s", callback_data="gift"),
            ],
            [
                InlineKeyboardButton(text="50🚀 - 12500 s", callback_data="gift"),
                InlineKeyboardButton(text="50🏆 - 12500 s", callback_data="gift"),
            ],
            [
                InlineKeyboardButton(text="25🎁 - 5000 s", callback_data="gift"),
                InlineKeyboardButton(text="25🌹 - 5000 s", callback_data="gift"),
            ],
        ]
    )


def bot_status_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ ON", callback_data="status_on"),
                InlineKeyboardButton(text="❌ OFF", callback_data="status_off"),
            ]
        ]
    )


def ban_unban_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚫 Ban", callback_data="ban_user"),
                InlineKeyboardButton(text="✅ Unban", callback_data="unban_user"),
            ]
        ]
    )


# ====================== MIDDLEWARE: bot off / ban tekshiruvi ======================
@router.message.middleware()
async def check_bot_status(handler, event: Message, data: dict):
    db = load_db()
    user_id = event.from_user.id

    # Bot o'chirilgan bo'lsa (admindan boshqasiga)
    if db.get("status") == "off" and user_id != ADMIN_ID:
        await event.answer(
            "⛔ Bot vaqtinchalik to'xtatildi. Botda ta'mirlash ishlari olib borilmoqda, tez orada ishga tushadi."
        )
        return

    # Banlangan foydalanuvchi
    u = db["users"].get(str(user_id))
    if u and u.get("banned"):
        await event.answer("🚫 Siz botdan foydalanish huquqidan mahrum qilingansiz.")
        return

    return await handler(event, data)


# ====================== START / RO'YXATDAN O'TISH ======================
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    db = load_db()
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    is_new = str(user_id) not in db["users"]
    u = get_user(db, user_id)

    if is_new:
        # referal ID ni /start <ref_id> dan olish
        parts = message.text.split(" ")
        ref_id = parts[1] if len(parts) > 1 else None
        if ref_id and ref_id != str(user_id) and ref_id in db["users"]:
            db["users"][ref_id]["balance"] += 50
            db["users"][ref_id]["referals"] += 1
            try:
                await bot.send_message(int(ref_id), "Sizda yangi referal! +50 so'm qo'shildi.")
            except Exception:
                pass
        save_db(db)

    await state.clear()
    await message.answer(
        f"🤝 Salom hurmatli {user_name}\n"
        "Biz haqimizda.👇\n"
        "Bizning ushbu botimiz orqali Gram olasiz va sotasiz.\n"
        "Va har xil xizmatlar mavjud ✔️\n"
        "Ishonchli va tezkor 🚀",
        reply_markup=admin_menu() if user_id == ADMIN_ID else main_menu(),
    )


# ====================== GRAM OLISH ======================
@router.message(F.text == "💎 Gram olish")
async def get_gram_start(message: Message, state: FSMContext):
    await state.set_state(UserStates.get_gram)
    await message.answer(
        f"💎 Gram 1ta narxi: {GRAM_PRICE:,} so'm\n"
        f"💳 Karta: {CARD_NUMBER}\n\n"
        "Gram qancha olmoqchisiz? Miqdorini faqat son ko'rinishida kiriting ❗"
    )


@router.message(UserStates.get_gram, F.text.regexp(r"^\d+$"))
async def get_gram_amount(message: Message, state: FSMContext):
    amount = int(message.text)
    price = amount * GRAM_PRICE
    await state.update_data(tmp_amount=amount)
    await state.set_state(UserStates.send_receipt)
    await message.answer(
        f"Umumiy summa: {price:,} so'm.\nTo'lovni amalga oshirib, chek rasmini (photo) yuboring."
    )


@router.message(UserStates.get_gram)
async def get_gram_invalid(message: Message):
    await message.answer("❗ Iltimos, faqat son (raqam) kiriting.")


# ====================== CHEK QABUL QILISH ======================
@router.message(UserStates.send_receipt, F.photo)
async def receive_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    amount = data.get("tmp_amount", "?")
    photo_id = message.photo[-1].file_id
    order_id = random.randint(100000, 999999)

    await bot.send_photo(
        ADMIN_ID,
        photo=photo_id,
        caption=(
            "🔔 Yangi buyurtma!\n"
            f"👤 Foydalanuvchi: {message.from_user.first_name} ({message.from_user.id})\n"
            f"💎 Miqdor: {amount}\n"
            f"🆔 Buyurtma ID: {order_id}"
        ),
        reply_markup=receipt_kb(message.from_user.id, order_id),
    )

    await state.clear()
    await message.answer("Chek yuborildi. Admin tasdiqlashini kuting...")


@router.message(UserStates.send_receipt)
async def receive_receipt_invalid(message: Message):
    await message.answer("❗ Iltimos, chek rasmini (photo) yuboring.")


# ====================== ADMIN: QABUL / RAD ETISH ======================
@router.callback_query(F.data.startswith("accept_"))
async def accept_order(call: CallbackQuery):
    _, u_id, o_id = call.data.split("_")
    await bot.send_message(
        int(u_id),
        f"✅ Buyurtma qabul qilindi. 1-5 daqiqada bajariladi 🚀\nBuyurtma ID: {o_id}",
    )
    await bot.edit_message_caption(
        chat_id=call.message.chat.id, message_id=call.message.message_id, caption="Tasdiqlandi ✅"
    )
    await call.answer()


@router.callback_query(F.data.startswith("reject_"))
async def reject_order(call: CallbackQuery):
    _, u_id = call.data.split("_")
    await bot.send_message(int(u_id), "❌ Buyurtmangiz rad etildi. Admin bilan bog'laning.")
    await bot.edit_message_caption(
        chat_id=call.message.chat.id, message_id=call.message.message_id, caption="Rad etildi ❌"
    )
    await call.answer()


# ====================== GRAM SOTISH ======================
@router.message(F.text == "💰 Gram sotish")
async def sell_gram(message: Message):
    await message.answer("Gram sotmoqchi bo'lsangiz adminga murojaat qiling:\n👨🏻‍💻 Admin: @ZcCoder")


# ====================== PROFIL ======================
@router.message(F.text == "👤 Profil")
async def profile(message: Message):
    db = load_db()
    u = get_user(db, message.from_user.id)
    save_db(db)
    await message.answer(
        f"👤 Ismingiz: {message.from_user.first_name}\n"
        f"🆔 Telegram ID: {message.from_user.id}\n"
        f"🔢 Botdagi ID: {u['bot_id']}\n"
        f"💰 Hisobingiz: {u['balance']} so'm\n\n"
        "Do'stlarni taklif qilib pul ishlang!",
        reply_markup=profile_kb(),
    )


@router.callback_query(F.data == "get_ref")
async def get_ref(call: CallbackQuery):
    await bot.send_message(
        call.message.chat.id,
        f"Sizning referal havolangiz:\nhttps://t.me/{BOT_USERNAME}?start={call.message.chat.id}\n\n"
        "Har bir taklif uchun 50 so'm beriladi.",
    )
    await call.answer()


# ====================== PUBG ======================
@router.message(F.text == "🎮 Pubg")
async def pubg_menu(message: Message):
    await message.answer("PUBG UC paketlarini tanlang:", reply_markup=pubg_kb())


@router.callback_query(F.data.startswith("buy_pubg_"))
async def buy_pubg(call: CallbackQuery):
    _, _, price_str, uc = call.data.split("_")
    price = int(price_str)
    db = load_db()
    u = get_user(db, call.message.chat.id)

    if u["balance"] >= price:
        u["balance"] -= price
        save_db(db)
        await bot.send_message(
            ADMIN_ID,
            f"🎮 PUBG Buyurtma!\nUser: {call.message.chat.id}\nUC: {uc}\nID yuborilishini kuting...",
        )
        await bot.send_message(
            call.message.chat.id, f"✅ Buyurtma qabul qilindi. Hisobingizdan {price} so'm yechildi."
        )
        await call.answer()
    else:
        await call.answer("⚠️ Mablag' yetarli emas!", show_alert=True)


# ====================== FREEFIRE ======================
@router.message(F.text == "🔥 FreeFire")
async def freefire(message: Message):
    await message.answer("Tez orada qo'shiladi...")


# ====================== QOIDA ======================
@router.message(F.text == "📜 Qoida")
async def rules(message: Message):
    await message.answer(
        "⚠️ Qoida: Adminga soxta chek tashlanmasin. Aldov bo'lsa ban beriladi.\n\nCreator: @ZcCoder"
    )


# ====================== GIFT OLISH ======================
@router.message(F.text == "🎁 Gift olish")
async def gift_menu(message: Message):
    await message.answer("Gift paketlarini tanlang:", reply_markup=gift_kb())


@router.callback_query(F.data == "gift")
async def gift_callback(call: CallbackQuery):
    await bot.send_message(
        ADMIN_ID,
        f"🎁 Gift buyurtma!\nUser: {call.message.chat.id} ({call.from_user.full_name})\nAdmin bilan bog'lanish kerak.",
    )
    await call.answer("Buyurtmangiz adminga yuborildi!", show_alert=True)


# ====================== HISOB TO'LDIRISH ======================
@router.message(F.text == "💳 Hisob to'ldirish")
async def topup(message: Message):
    await message.answer(
        f"💳 Hisobni to'ldirish uchun quyidagi kartaga pul o'tkazing:\n{CARD_NUMBER}\n\n"
        "So'ngra chek rasmini admin @AHMEDOV_ZXZ ga yuboring."
    )


# ====================== ===== ADMIN PANEL ===== ======================
def admin_only(message: Message) -> bool:
    return message.from_user.id == ADMIN_ID


# --- Statistika ---
@router.message(F.text == "📊 Statistika", F.from_user.id == ADMIN_ID)
async def stats(message: Message):
    db = load_db()
    count = len(db["users"])
    await message.answer(f"📊 Bot foydalanuvchilari soni: {count} ta")


# --- Bot holati ---
@router.message(F.text == "⚙️ Bot holati", F.from_user.id == ADMIN_ID)
async def bot_status(message: Message):
    await message.answer("Bot holatini tanlang:", reply_markup=bot_status_kb())


@router.callback_query(F.data.startswith("status_"))
async def set_status(call: CallbackQuery):
    st = call.data.split("_")[1]
    db = load_db()
    db["status"] = st
    save_db(db)
    await bot.edit_message_text(
        chat_id=call.message.chat.id, message_id=call.message.message_id, text=f"Bot holati {st} ga o'zgartirildi."
    )
    await call.answer()


# --- Pul qo'shish ---
@router.message(F.text == "➕ Pul qo'shish", F.from_user.id == ADMIN_ID)
async def add_balance_start(message: Message, state: FSMContext):
    await state.set_state(AdminStates.add_balance_id)
    await message.answer("Foydalanuvchi Telegram ID raqamini yuboring:")


@router.message(AdminStates.add_balance_id, F.from_user.id == ADMIN_ID)
async def add_balance_get_id(message: Message, state: FSMContext):
    await state.update_data(target_id=message.text.strip())
    await state.set_state(AdminStates.add_balance_amount)
    await message.answer("Qancha so'm qo'shmoqchisiz? (faqat son kiriting)")


@router.message(AdminStates.add_balance_amount, F.from_user.id == ADMIN_ID)
async def add_balance_get_amount(message: Message, state: FSMContext):
    if not message.text.strip().lstrip("-").isdigit():
        await message.answer("❗ Faqat son kiriting.")
        return
    data = await state.get_data()
    target_id = data["target_id"]
    amount = int(message.text.strip())

    db = load_db()
    if target_id not in db["users"]:
        await message.answer("❌ Bunday foydalanuvchi topilmadi.")
        await state.clear()
        return

    db["users"][target_id]["balance"] += amount
    save_db(db)
    await state.clear()
    await message.answer(f"✅ {target_id} foydalanuvchisiga {amount} so'm qo'shildi.")
    try:
        await bot.send_message(int(target_id), f"💰 Hisobingizga {amount} so'm qo'shildi!")
    except Exception:
        pass


# --- Pul ayirish ---
@router.message(F.text == "➖ Pul ayirish", F.from_user.id == ADMIN_ID)
async def sub_balance_start(message: Message, state: FSMContext):
    await state.set_state(AdminStates.sub_balance_id)
    await message.answer("Foydalanuvchi Telegram ID raqamini yuboring:")


@router.message(AdminStates.sub_balance_id, F.from_user.id == ADMIN_ID)
async def sub_balance_get_id(message: Message, state: FSMContext):
    await state.update_data(target_id=message.text.strip())
    await state.set_state(AdminStates.sub_balance_amount)
    await message.answer("Qancha so'm ayirmoqchisiz? (faqat son kiriting)")


@router.message(AdminStates.sub_balance_amount, F.from_user.id == ADMIN_ID)
async def sub_balance_get_amount(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❗ Faqat son kiriting.")
        return
    data = await state.get_data()
    target_id = data["target_id"]
    amount = int(message.text.strip())

    db = load_db()
    if target_id not in db["users"]:
        await message.answer("❌ Bunday foydalanuvchi topilmadi.")
        await state.clear()
        return

    db["users"][target_id]["balance"] = max(0, db["users"][target_id]["balance"] - amount)
    save_db(db)
    await state.clear()
    await message.answer(f"✅ {target_id} foydalanuvchisidan {amount} so'm ayirildi.")
    try:
        await bot.send_message(int(target_id), f"⚠️ Hisobingizdan {amount} so'm ayirildi.")
    except Exception:
        pass


# --- Xabar tarqatish (broadcast) ---
@router.message(F.text == "📢 Xabar tarqatish", F.from_user.id == ADMIN_ID)
async def broadcast_start(message: Message, state: FSMContext):
    await state.set_state(AdminStates.broadcast)
    await message.answer("Tarqatmoqchi bo'lgan xabaringizni yuboring (matn, rasm va h.k.):")


@router.message(AdminStates.broadcast, F.from_user.id == ADMIN_ID)
async def broadcast_send(message: Message, state: FSMContext):
    db = load_db()
    success, failed = 0, 0
    await message.answer("⏳ Xabar tarqatilmoqda...")
    for uid in db["users"].keys():
        try:
            await message.copy_to(int(uid))
            success += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)  # flood limitiga tushmaslik uchun
    await state.clear()
    await message.answer(f"✅ Xabar tarqatildi!\n📨 Yuborildi: {success}\n❌ Yuborilmadi: {failed}")


# --- Ban / Unban ---
@router.message(F.text == "🚫 Ban/Unban", F.from_user.id == ADMIN_ID)
async def ban_unban_menu(message: Message):
    await message.answer("Amalni tanlang:", reply_markup=ban_unban_kb())


@router.callback_query(F.data == "ban_user")
async def ban_user_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.ban_id)
    await call.message.answer("Ban qilmoqchi bo'lgan foydalanuvchi ID sini yuboring:")
    await call.answer()


@router.message(AdminStates.ban_id, F.from_user.id == ADMIN_ID)
async def ban_user_finish(message: Message, state: FSMContext):
    target_id = message.text.strip()
    db = load_db()
    if target_id not in db["users"]:
        await message.answer("❌ Bunday foydalanuvchi topilmadi.")
    else:
        db["users"][target_id]["banned"] = True
        save_db(db)
        await message.answer(f"🚫 Foydalanuvchi {target_id} ban qilindi.")
        try:
            await bot.send_message(int(target_id), "🚫 Siz botdan foydalanish huquqidan mahrum qilindingiz.")
        except Exception:
            pass
    await state.clear()


@router.callback_query(F.data == "unban_user")
async def unban_user_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.unban_id)
    await call.message.answer("Unban qilmoqchi bo'lgan foydalanuvchi ID sini yuboring:")
    await call.answer()


@router.message(AdminStates.unban_id, F.from_user.id == ADMIN_ID)
async def unban_user_finish(message: Message, state: FSMContext):
    target_id = message.text.strip()
    db = load_db()
    if target_id not in db["users"]:
        await message.answer("❌ Bunday foydalanuvchi topilmadi.")
    else:
        db["users"][target_id]["banned"] = False
        save_db(db)
        await message.answer(f"✅ Foydalanuvchi {target_id} unban qilindi.")
        try:
            await bot.send_message(int(target_id), "✅ Sizning ban holatingiz olib tashlandi.")
        except Exception:
            pass
    await state.clear()


# --- Kanal sozlamalari (majburiy obuna) ---
@router.message(F.text == "📢 Kanal sozlamalari", F.from_user.id == ADMIN_ID)
async def channel_settings(message: Message, state: FSMContext):
    db = load_db()
    channels = db.get("channels", [])
    text = "📢 Joriy majburiy kanallar:\n" + ("\n".join(channels) if channels else "Yo'q")
    text += "\n\nYangi kanal qo'shish uchun @username yuboring:"
    await state.set_state(AdminStates.channel_add)
    await message.answer(text)


@router.message(AdminStates.channel_add, F.from_user.id == ADMIN_ID)
async def channel_add(message: Message, state: FSMContext):
    channel = message.text.strip()
    db = load_db()
    db.setdefault("channels", []).append(channel)
    save_db(db)
    await state.clear()
    await message.answer(f"✅ Kanal qo'shildi: {channel}")


# ====================== MAIN ======================
async def main():
    if not DB_PATH.exists():
        save_db({"users": {}, "status": "on", "channels": []})
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
