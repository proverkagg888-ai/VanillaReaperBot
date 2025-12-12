
import asyncio
import logging
import os
import random
try:
	from dotenv import load_dotenv
	load_dotenv()
	DOTENV_LOADED = True
except Exception:
	DOTENV_LOADED = False
from datetime import datetime, timedelta
from typing import Dict, Set, Optional

from telegram import (Update, ChatPermissions, ChatMember, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (
	Application,
	CommandHandler,
	ContextTypes,
	MessageHandler,
	ChatMemberHandler,
	CallbackQueryHandler,
	filters,
)

# --- Logging ---
logging.basicConfig(
	format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
	level=logging.INFO,
)
logger = logging.getLogger(__name__)

# --- Config / In-memory storage ---
OWNER_ID = 1871352653

# runtime data containers
admins: Dict[int, Set[int]] = {}  # chat_id -> set(admin user_ids)
warns: Dict[int, Dict[int, int]] = {}  # chat_id -> {user_id: warns_count}
mutes: Dict[int, Dict[int, float]] = {}  # chat_id -> {user_id: mute_end_timestamp}
banned: Dict[int, Set[int]] = {}  # chat_id -> set(banned_ids)
recent_activity: Dict[int, Set[int]] = {}  # chat_id -> set(user_ids recently active)
victim_of_day: Dict[int, Optional[int]] = {}  # chat_id -> user_id
last_message_time: Dict[int, float] = {}  # chat_id -> timestamp

# --- Phrase banks (unique phrases) ---
GREETINGS = [
	"О, свежая плоть, здравствуй.",
	"Великий случай: новый человек вошёл.",
	"Здравствуй, смертный. Не задерживайся.",
	"О да, ещё один для нашего веселья.",
	"Приветствую. Надеюсь, ты не наивен.",
	"Вход принят. Держи свою душу при себе.",
	"О, пришёл наблюдатель. Присаживайся к костру.",
	"Хэй, новый; мы тебя уже отметили в списке.",
	"Здравствуй — входящий на деградацию удовольствия.",
	"Привет! Не обещаем доброты, только сарказм.",
]

FAREWELLS = [
	"Ушёл? Надеюсь, с миром — или без.",
	"Прощай, и пусть судьба будет крива.",
	"Пока. Надеюсь, ты был полезен для насмешек.",
	"Уход — это тоже действие. Прощай.",
	"До свидания. Мы и не заметили разницы.",
	"Покинул чат — хорошо, площади для ступеней меньше.",
	"Исчезновение принято. Возвращайся, если осмелишься.",
	"Пока-пока. Неси свою вину аккуратно.",
	"Прощай, герой собственной драмы.",
	"Удачи. Нам нужны жертвы, а не свидетели.",
]

ROASTS = [
	"Ты как бесплатный Wi-Fi — никто не доверяет, но все пользуются.",
	"Твой интеллект вызывает вопросы у поисковых систем.",
	"Если бы сарказм был валютой, ты бы всё равно был беден.",
	"Ты доказательство того, что эволюция иногда ошибается.",
	"Ты — как реклама: навязчив, но бесполезен.",
	"Твоя гордость вредит окружающим, особенно тебе.",
	"Ты выглядишь как чей-то плохой жизненный выбор.",
	"Твои шутки — это напоминание о климатическом кризисе.",
	"У тебя редкий талант — портить воздух словом.",
	"Если бы глупость была болезнью, тебя бы пожалели.",
	"Твоя самооценка явно переоценена.",
	"Ты похож на captcha: никто не хочет тратить на тебя время.",
	"Твой вклад в разговоры — как спам в почте.",
	"Ты приносишь радость... окружающим, когда уходишь.",
	"Твоя харизма — будто выключатель: всегда выключена.",
	"Ты как устаревший мем — уже не смешно.",
	"Если бы невнимательность была искусством, ты бы был Моне.",
	"Ты как баг, но без возможности фикса.",
	"Твоя значимость напоминает пустой инбокс.",
	"Ты — консольная ошибка в GUI мире.",
	"Твои сообщения — тонкая попытка привлечь внимание.",
	"Ты вкладываешь в дискуссию ровно столько, сколько ноль в десятке.",
	"Твоя логика — как древний браузер: не поддерживается.",
	"Ты — живое доказательство, что автозаполнение ошибается.",
	"Твои аргументы настолько тонки, что их не видно.",
	"С тобой рядом даже тишина кажется умнее.",
	"Ты смешнее, когда молчишь — чаще так и делай.",
	"Ты — как спойлер: портит все впечатления.",
	"Твоя репутация стабильна: низкая и заслуженная.",
	"Ты уникален — как ошибка 404 в реальной жизни.",
	"Если бы сарказм был лекарством, тебя бы спасли.",
	"Ты редко улыбаешься — и это взаимно.",
	"Твоя победа — это мираж, но зато пышный.",
	"Ты редкий случай: человек, опережающий тупость времени.",
	"Твоя перспектива ограничена, но зато уверенная.",
	"Твоя значимость легко помещается в файл подкачки.",
	"Твоя вера в себя — словно плохой Wi-Fi: нестабильна.",
	"В твоём логове мыши — мыши умнее.",
	"Ты как уведомление: нужен редко, раздражаешь часто.",
	"Твоя серьезность вызывает смех у стен.",
	"Ты как старая шутка — знаешь, что смешно, только не сейчас.",
	"Ты — куст в саду жизни: никто не обращает внимания.",
	"Твои мечты популярны лишь у сна.",
	"Твоя гордость — это прыщик на лбу успеха.",
	"Твои достижения — локальное исключение правил.",
	"Ты — проект без README: непонятен и нерабоч.",
	"Твоя аргументация — короткий цикл бедствий.",
	"Ты — как устаревшая ветка: никто не мерджит.",
	"Твои намерения благие, но реализация — катастрофа.",
]

VANILLA = [
	"Жизнь — как ванильный крем: сладкая корка, пустота внутри.",
	"Сарказм — это приправка, ваниль — основа. Ешь осторожно.",
	"Ваниль — это философия компромисса между скукой и уютом.",
	"Быть ванилью — значит быть спокойной катастрофой.",
	"Иногда лучшая месть — это забыть и сделать саркастично.",
	"Ваниль учит терпению: ждать, пока кто-то ошибётся.",
	"Философия ванили — принять посредственность с улыбкой.",
	"Ваниль — это когда мир мягкий, но душа остра.",
	"Иногда смысл — в маленьких горьких каплях к кофе.",
	"Ванильная грусть — это искусство улыбаться в темноте.",
	"Сарказм — кислота, ваниль — платформа.",
	"Ваниль — это когда ты понимаешь мир, но не хочешь вмешиваться.",
	"Философия: меньше ожиданий — меньше разочарований.",
	"Ванильная мудрость: не спорь с глупостью, она тебя поглотит.",
	"Имей план, но умей наслаждаться его провалом.",
	"Лучше быть практичным, чем правым и одиозным.",
	"Ваниль — это сангвиник, замаскированный под циника.",
	"Счастье — это маленькая ложка мороженого в конце дня.",
	"Будь ванилью: стабильно, но иногда пронзительно.",
	"Настоящая смелость — признать свою скуку и жить с ней.",
]

AGGRO = [
	"Эй, вы тут молчите — скучно же до ужаса.",
	"Жизнь коротка, а вы сидите и ворчите. Разбудите меня.",
	"Если вы здесь ещё молчите — кто-то явно спит.",
	"Прокричи что-нибудь ценное или хотя бы забавно.",
	"Молчание съедает хорошие шутки. Давайте их кормить.",
	"Вы что, в музее? Оживите воздух.",
	"Пустота в чате более громкая, чем вы думаете.",
	"Разговор — как еда; вы явно на диете.",
	"Эй, шум! Кто-нибудь заставь этот чат жить.",
	"Не дайте скуке победить — расскажите худший анекдот.",
	"Если бы молчание было спортом, вы бы выиграли медаль.",
	"Где ваши слова? Они опаздывают.",
	"Разбудите обсуждение или я начну его за вас.",
	"Здесь напряг тишины — пора её разорвать.",
	"Один крик может изменить всё. Попробуйте.",
	"Пишите, пока я ещё запомнил, кто вы.",
	"Мы не зомби — включайтесь в живую дискуссию.",
	"Если вы молчите, значит будете списаны как скучные.",
	"Мне нравятся шумные люди. Тихие — на полке.",
	"Шумите. Я люблю вылавливать жертв молчания.",
]

# --- Helpers ---
def ensure_chat_structs(chat_id: int):
	admins.setdefault(chat_id, set())
	warns.setdefault(chat_id, {})
	mutes.setdefault(chat_id, {})
	banned.setdefault(chat_id, set())
	recent_activity.setdefault(chat_id, set())
	victim_of_day.setdefault(chat_id, None)
	last_message_time.setdefault(chat_id, datetime.utcnow().timestamp())

def is_owner(user_id: int) -> bool:
	return user_id == OWNER_ID

def is_admin(user_id: int, chat_id: int) -> bool:
	ensure_chat_structs(chat_id)
	return user_id in admins.get(chat_id, set()) or is_owner(user_id)

async def try_restrict(chat_id: int, user_id: int, until: Optional[datetime], bot):
	try:
		# check bot privileges
		bot_me = await bot.get_me()
		try:
			bot_member = await bot.get_chat_member(chat_id, bot_me.id)
			can_restrict = getattr(bot_member, "can_restrict_members", False) or bot_member.status == ChatMember.CREATOR
		except Exception:
			can_restrict = False
		if not can_restrict:
			logger.warning("Bot lacks restrict rights in chat %s", chat_id)
			return False
		perms = ChatPermissions(can_send_messages=False)
		await bot.restrict_chat_member(chat_id, user_id, permissions=perms, until_date=until)
		logger.info("Restricted %s in %s until %s", user_id, chat_id, until)
		return True
	except Exception as e:
		logger.warning("Failed to restrict %s in %s: %s", user_id, chat_id, e)
		return False

async def try_unrestrict(chat_id: int, user_id: int, bot):
	try:
		# check bot privileges
		bot_me = await bot.get_me()
		try:
			bot_member = await bot.get_chat_member(chat_id, bot_me.id)
			can_restrict = getattr(bot_member, "can_restrict_members", False) or bot_member.status == ChatMember.CREATOR
		except Exception:
			can_restrict = False
		if not can_restrict:
			logger.warning("Bot lacks restrict rights in chat %s for unrestrict", chat_id)
			return False
		perms = ChatPermissions(
			can_send_messages=True,
			can_send_media_messages=True,
			can_send_polls=True,
			can_send_other_messages=True,
			can_add_web_page_previews=True,
		)
		await bot.restrict_chat_member(chat_id, user_id, permissions=perms)
		logger.info("Unrestricted %s in %s", user_id, chat_id)
		return True
	except Exception as e:
		logger.warning("Failed to unrestrict %s in %s: %s", user_id, chat_id, e)
		return False

# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
	await update.message.reply_text("VanillaReaperBot at your service. Use /help for commands.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
	text = (
		"Доступные команды:\n"
		"/roast (reply) — пошутить\n"
		"/vanilla — ванильная фраза\n"
		"/duel (reply или id1 id2) — дуэль\n"
		"/roulette — рулетка\n"
		"/profile (reply) — профиль пользователя\n"
		"/warn /mute /kick /ban — модерация (для админов)\n"
	)
	keyboard = [
		[InlineKeyboardButton("Роast", callback_data="roast"), InlineKeyboardButton("Vanilla", callback_data="vanilla")],
		[InlineKeyboardButton("Рулетка", callback_data="roulette"), InlineKeyboardButton("Профиль", callback_data="profile")],
		[InlineKeyboardButton("Инфо о боте", callback_data="botinfo")],
	]
	await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
	user = update.effective_user
	chat = update.effective_chat
	if not is_owner(user.id):
		return await update.message.reply_text("Только владелец может выдавать админов.")
	if not context.args and not update.message.reply_to_message:
		return await update.message.reply_text("Укажи пользователя через reply или @username.")
	if update.message.reply_to_message:
		target = update.message.reply_to_message.from_user
	else:
		try:
			username = context.args[0]
			member = await context.bot.get_chat_member(chat.id, username)
			target = member.user
		except Exception:
			return await update.message.reply_text("Не удалось найти пользователя.")
	ensure_chat_structs(chat.id)
	admins[chat.id].add(target.id)
	await update.message.reply_text(f"{target.mention_html()} теперь админ.", parse_mode="HTML")

async def removeadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
	user = update.effective_user
	chat = update.effective_chat
	if not is_owner(user.id):
		return await update.message.reply_text("Только владелец может снимать админов.")
	if update.message.reply_to_message:
		target = update.message.reply_to_message.from_user
	elif context.args:
		try:
			username = context.args[0]
			member = await context.bot.get_chat_member(chat.id, username)
			target = member.user
		except Exception:
			return await update.message.reply_text("Не удалось найти пользователя.")
	else:
		return await update.message.reply_text("Укажи пользователя через reply или @username.")
	ensure_chat_structs(chat.id)
	admins[chat.id].discard(target.id)
	await update.message.reply_text(f"{target.mention_html()} больше не админ.", parse_mode="HTML")

async def setowner(update: Update, context: ContextTypes.DEFAULT_TYPE):
	global OWNER_ID
	user = update.effective_user
	if not is_owner(user.id):
		return await update.message.reply_text("Только владелец может передать владение.")
	if update.message.reply_to_message:
		target = update.message.reply_to_message.from_user
	elif context.args:
		try:
			username = context.args[0]
			member = await context.bot.get_chat_member(update.effective_chat.id, username)
			target = member.user
		except Exception:
			return await update.message.reply_text("Не удалось найти пользователя.")
	else:
		return await update.message.reply_text("Укажи пользователя через reply или @username.")
	OWNER_ID = target.id
	await update.message.reply_text(f"Владельцем теперь {target.mention_html()}", parse_mode="HTML")

async def schedule_unmute(application: Application, chat_id: int, user_id: int, seconds: int):
	await asyncio.sleep(seconds)
	ensure_chat_structs(chat_id)
	if user_id in mutes.get(chat_id, {}) and mutes[chat_id][user_id] <= datetime.utcnow().timestamp():
		mutes[chat_id].pop(user_id, None)
		try:
			await try_unrestrict(chat_id, user_id, application.bot)
		except Exception:
			logger.exception("Scheduled unmute failed for %s in %s", user_id, chat_id)


async def admins_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
	chat = update.effective_chat
	ensure_chat_structs(chat.id)
	owner_text = f"Владелец: <a href=\"tg://user?id={OWNER_ID}\">{OWNER_ID}</a>"
	admin_texts = []
	for a in admins.get(chat.id, set()):
		admin_texts.append(f"<a href=\"tg://user?id={a}\">{a}</a>")
	text = owner_text + "\nАдмины: " + (", ".join(admin_texts) if admin_texts else "нет")
	await update.message.reply_text(text, parse_mode="HTML")

async def warn_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
	chat = update.effective_chat
	user = update.effective_user
	ensure_chat_structs(chat.id)
	if not is_admin(user.id, chat.id):
		return await update.message.reply_text("Только админы могут выдавать варны.")
	if not update.message.reply_to_message:
		return await update.message.reply_text("Используй /warn в reply на сообщение пользователя.")
	target = update.message.reply_to_message.from_user
	if is_owner(target.id):
		return await update.message.reply_text("Нельзя предупреждать владельца.")
	warns[chat.id].setdefault(target.id, 0)
	warns[chat.id][target.id] += 1
	count = warns[chat.id][target.id]
	await update.message.reply_text(f"{target.mention_html()} получил предупреждение {count}/3.", parse_mode="HTML")
	if count >= 3:
		banned.setdefault(chat.id, set()).add(target.id)
		try:
			await context.bot.ban_chat_member(chat.id, target.id)
		except Exception:
			logger.exception("Не удалось забанить при 3 варнах.")
		await update.message.reply_text(f"{target.mention_html()} забанен после 3 предупреждений.", parse_mode="HTML")

async def warns_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
	chat = update.effective_chat
	ensure_chat_structs(chat.id)
	if update.message.reply_to_message:
		target = update.message.reply_to_message.from_user
	elif context.args:
		try:
			uid = int(context.args[0])
			target = await context.bot.get_chat_member(chat.id, uid)
			target = target.user
		except Exception:
			return await update.message.reply_text("Не удалось найти пользователя.")
	else:
		target = update.effective_user
	count = warns[chat.id].get(target.id, 0)
	await update.message.reply_text(f"У {target.mention_html()} предупреждений: {count}", parse_mode="HTML")

async def mute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
	chat = update.effective_chat
	user = update.effective_user
	if not is_admin(user.id, chat.id):
		return await update.message.reply_text("Только админы могут мутить.")
	if not update.message.reply_to_message:
		return await update.message.reply_text("Используй /mute в reply на сообщение пользователя.")
	try:
		seconds = int(context.args[0]) if context.args else 60
	except Exception:
		seconds = 60
	target = update.message.reply_to_message.from_user
	if is_owner(target.id):
		return await update.message.reply_text("Нельзя мутить владельца.")
	until = datetime.utcnow() + timedelta(seconds=seconds)
	ok = await try_restrict(chat.id, target.id, until, context.bot)
	if not ok:
		return await update.message.reply_text("У меня нет прав ограничивать пользователей. Сделайте бота админом с правом 'Ban users' / 'Restrict members'.")
	mutes.setdefault(chat.id, {})[target.id] = until.timestamp()

	# schedule unmute via asyncio task
	async def unmute_later(chat_id: int, user_id: int, delay: int, bot):
		await asyncio.sleep(delay)
		ensure_chat_structs(chat_id)
		if user_id in mutes.get(chat_id, {}) and mutes[chat_id][user_id] <= datetime.utcnow().timestamp():
			mutes[chat_id].pop(user_id, None)
			await try_unrestrict(chat_id, user_id, bot)

	asyncio.create_task(unmute_later(chat.id, target.id, seconds, context.bot))
	await update.message.reply_text(f"{target.mention_html()} замучен на {seconds} секунд.", parse_mode="HTML")

async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
	chat = update.effective_chat
	user = update.effective_user
	if not is_admin(user.id, chat.id):
		return await update.message.reply_text("Только админы могут снимать мюты.")
	if not update.message.reply_to_message and not context.args:
		return await update.message.reply_text("Укажи пользователя через reply или ID.")
	if update.message.reply_to_message:
		target = update.message.reply_to_message.from_user
	else:
		try:
			uid = int(context.args[0])
			target = await context.bot.get_chat_member(chat.id, uid)
			target = target.user
		except Exception:
			return await update.message.reply_text("Не удалось найти пользователя.")
	mutes.get(chat.id, {}).pop(target.id, None)
	await try_unrestrict(chat.id, target.id, context.bot)
	await update.message.reply_text(f"{target.mention_html()} размучен.", parse_mode="HTML")

async def kick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
	chat = update.effective_chat
	user = update.effective_user
	if not is_admin(user.id, chat.id):
		return await update.message.reply_text("Только админы могут кикать.")
	if not update.message.reply_to_message:
		return await update.message.reply_text("Используй /kick в reply на сообщение.")
	target = update.message.reply_to_message.from_user
	if is_owner(target.id):
		return await update.message.reply_text("Нельзя кикнуть владельца.")
	# check bot privileges
	bot_me = await context.bot.get_me()
	try:
		bot_member = await context.bot.get_chat_member(chat.id, bot_me.id)
		can_restrict = getattr(bot_member, "can_restrict_members", False) or bot_member.status == ChatMember.CREATOR
	except Exception:
		can_restrict = False
	if not can_restrict:
		return await update.message.reply_text("У меня нет прав кикать/банить пользователей. Сделайте бота админом с правом 'Ban users'.")
	try:
		await context.bot.ban_chat_member(chat.id, target.id)
		await context.bot.unban_chat_member(chat.id, target.id)
		await update.message.reply_text(f"{target.mention_html()} кикнут.", parse_mode="HTML")
	except Exception:
		logger.exception("kick failed")
		await update.message.reply_text("Не удалось кикнуть пользователя.")

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
	chat = update.effective_chat
	user = update.effective_user
	if not is_admin(user.id, chat.id):
		return await update.message.reply_text("Только админы могут банить.")
	if not update.message.reply_to_message:
		return await update.message.reply_text("Используй /ban в reply на сообщение.")
	target = update.message.reply_to_message.from_user
	if is_owner(target.id):
		return await update.message.reply_text("Нельзя банить владельца.")
	# check bot privileges
	bot_me = await context.bot.get_me()
	try:
		bot_member = await context.bot.get_chat_member(chat.id, bot_me.id)
		can_restrict = getattr(bot_member, "can_restrict_members", False) or bot_member.status == ChatMember.CREATOR
	except Exception:
		can_restrict = False
	if not can_restrict:
		return await update.message.reply_text("У меня нет прав банить пользователей. Сделайте бота админом с правом 'Ban users'.")
	try:
		await context.bot.ban_chat_member(chat.id, target.id)
		banned.setdefault(chat.id, set()).add(target.id)
		await update.message.reply_text(f"{target.mention_html()} забанен.", parse_mode="HTML")
	except Exception:
		logger.exception("ban failed")
		await update.message.reply_text("Не удалось забанить пользователя.")

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
	chat = update.effective_chat
	user = update.effective_user
	if not is_admin(user.id, chat.id):
		return await update.message.reply_text("Только админы могут разбанить.")
	if not context.args:
		return await update.message.reply_text("Укажи ID пользователя: /unban <user_id>")
	# check bot privileges
	bot_me = await context.bot.get_me()
	try:
		bot_member = await context.bot.get_chat_member(chat.id, bot_me.id)
		can_restrict = getattr(bot_member, "can_restrict_members", False) or bot_member.status == ChatMember.CREATOR
	except Exception:
		can_restrict = False
	if not can_restrict:
		return await update.message.reply_text("У меня нет прав разбанивать пользователей. Сделайте бота админом с правом 'Ban users'.")
	try:
		uid = int(context.args[0])
		await context.bot.unban_chat_member(chat.id, uid)
		banned.get(chat.id, set()).discard(uid)
		await update.message.reply_text(f"Пользователь {uid} разбанен.")
	except Exception:
		logger.exception("unban failed")
		await update.message.reply_text("Не удалось разбанить пользователя.")

async def roast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
	if update.message.reply_to_message:
		target = update.message.reply_to_message.from_user
	else:
		target = update.effective_user
	text = random.choice(ROASTS)
	await update.message.reply_text(f"{target.mention_html()} — {text}", parse_mode="HTML")


async def botinfo_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
	chat = update.effective_chat
	bot_me = await context.bot.get_me()
	info_lines = [f"Бот: @{bot_me.username} (id={bot_me.id})"]
	try:
		member = await context.bot.get_chat_member(chat.id, bot_me.id)
		info_lines.append(f"Статус бота в чате: {member.status}")
		flags = []
		if getattr(member, 'can_restrict_members', False):
			flags.append('can_restrict_members')
		if getattr(member, 'can_delete_messages', False):
			flags.append('can_delete_messages')
		if getattr(member, 'can_promote_members', False):
			flags.append('can_promote_members')
		if flags:
			info_lines.append('Права: ' + ', '.join(flags))
	except Exception:
		info_lines.append('Не удалось получить статус бота в этом чате.')
	await update.message.reply_text('\n'.join(info_lines))

async def vanilla_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
	text = random.choice(VANILLA)
	await update.message.reply_text(text)

async def duel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
	chat = update.effective_chat
	if len(context.args) >= 2:
		# try parse two IDs
		try:
			a = int(context.args[0])
			b = int(context.args[1])
		except Exception:
			return await update.message.reply_text("Укажи два ID через пробел или используй reply+command.")
		a_user = await context.bot.get_chat_member(chat.id, a)
		b_user = await context.bot.get_chat_member(chat.id, b)
		names = (a_user.user, b_user.user)
	elif update.message.reply_to_message:
		names = (update.effective_user, update.message.reply_to_message.from_user)
	else:
		return await update.message.reply_text("Используй /duel в reply или укажи два ID.")
	winner = random.choice(names)
	await update.message.reply_text(f"Дуэль! Победитель: {winner.mention_html()}", parse_mode="HTML")

async def roulette_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
	chat = update.effective_chat
	user = update.effective_user
	ensure_chat_structs(chat.id)
	# target from reply or user
	target = update.message.reply_to_message.from_user if update.message.reply_to_message else user
	roll = random.choice(["nothing", "short_mute", "long_mute", "roast", "honor", "victim"])
	if roll == "nothing":
		await update.message.reply_text("Колесо крутится... Ничего не получилось. Удача не для тебя.")
	elif roll == "short_mute":
		seconds = 30
		until = datetime.utcnow() + timedelta(seconds=seconds)
		await try_restrict(chat.id, target.id, until, context.bot)
		mutes.setdefault(chat.id, {})[target.id] = until.timestamp()
		# schedule unmute via asyncio
		async def _u():
			await asyncio.sleep(seconds)
			await try_unrestrict(chat.id, target.id, context.bot)

		asyncio.create_task(_u())
		await update.message.reply_text(f"Колесо выбрало мут на {seconds} секунд для {target.mention_html()}.", parse_mode="HTML")
	elif roll == "long_mute":
		seconds = 300
		until = datetime.utcnow() + timedelta(seconds=seconds)
		await try_restrict(chat.id, target.id, until, context.bot)
		mutes.setdefault(chat.id, {})[target.id] = until.timestamp()
		# schedule unmute via asyncio
		async def _u2():
			await asyncio.sleep(seconds)
			await try_unrestrict(chat.id, target.id, context.bot)

		asyncio.create_task(_u2())
		await update.message.reply_text(f"О, длинный мут: {seconds} секунд для {target.mention_html()}.", parse_mode="HTML")
	elif roll == "roast":
		await update.message.reply_text(f"Рулетка выдала ростер: {random.choice(ROASTS)}")
	elif roll == "honor":
		await update.message.reply_text(f"Честь дана {target.mention_html()} — минутой молчания.", parse_mode="HTML")
	elif roll == "victim":
		# set victim of day
		victim_of_day[chat.id] = target.id
		await update.message.reply_text(f"Жертва дня: {target.mention_html()}.", parse_mode="HTML")

async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
	await update.message.reply_text("Провожу саркастический обыск... Нашёл только тонкие оправдания и плохой вкус.")

async def profile_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
	chat = update.effective_chat
	if update.message.reply_to_message:
		target = update.message.reply_to_message.from_user
	else:
		target = update.effective_user
	ensure_chat_structs(chat.id)
	w = warns.get(chat.id, {}).get(target.id, 0)
	mute_until = mutes.get(chat.id, {}).get(target.id)
	victim = victim_of_day.get(chat.id)
	text = f"Профиль {target.mention_html()}:\nПредупреждения: {w}\n"
	if mute_until:
		remaining = int(mute_until - datetime.utcnow().timestamp())
		text += f"Мут ещё: {remaining} сек\n"
	else:
		text += "Мут: нет\n"
	text += f"Жертва дня: {('Да' if victim == target.id else 'Нет')}"
	await update.message.reply_text(text, parse_mode="HTML")


async def commands_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
	# handle inline button presses safely
	query = update.callback_query
	if not query:
		return
	await query.answer()
	data = query.data
	chat = query.message.chat
	bot = context.bot
	user = query.from_user

	if data == 'roast':
		if query.message.reply_to_message:
			target = query.message.reply_to_message.from_user
		else:
			target = user
		await bot.send_message(chat.id, f"{target.mention_html()} — {random.choice(ROASTS)}", parse_mode="HTML")
	elif data == 'vanilla':
		await bot.send_message(chat.id, random.choice(VANILLA))
	elif data == 'roulette':
		if query.message.reply_to_message:
			target = query.message.reply_to_message.from_user
		else:
			target = user
		roll = random.choice(["nothing", "short_mute", "long_mute", "roast", "honor", "victim"]) 
		if roll == "nothing":
			await bot.send_message(chat.id, "Колесо крутится... Ничего не получилось. Удача не для тебя.")
		elif roll == "short_mute":
			seconds = 30
			until = datetime.utcnow() + timedelta(seconds=seconds)
			ok = await try_restrict(chat.id, target.id, until, bot)
			if not ok:
				await bot.send_message(chat.id, "У меня нет прав мутить пользователя. Сделайте бота админом.")
			else:
				mutes.setdefault(chat.id, {})[target.id] = until.timestamp()
				asyncio.create_task(schedule_unmute(context.application, chat.id, target.id, seconds))
				await bot.send_message(chat.id, f"Колесо выбрало мут на {seconds} секунд для {target.mention_html()}.", parse_mode="HTML")
		elif roll == "long_mute":
			seconds = 300
			until = datetime.utcnow() + timedelta(seconds=seconds)
			ok = await try_restrict(chat.id, target.id, until, bot)
			if not ok:
				await bot.send_message(chat.id, "У меня нет прав мутить пользователя. Сделайте бота админом.")
			else:
				mutes.setdefault(chat.id, {})[target.id] = until.timestamp()
				asyncio.create_task(schedule_unmute(context.application, chat.id, target.id, seconds))
				await bot.send_message(chat.id, f"О, длинный мут: {seconds} секунд для {target.mention_html()}.", parse_mode="HTML")
		elif roll == "roast":
			await bot.send_message(chat.id, f"Рулетка выдала ростер: {random.choice(ROASTS)}")
		elif roll == "honor":
			await bot.send_message(chat.id, f"Честь дана {target.mention_html()} — минутой молчания.", parse_mode="HTML")
		elif roll == "victim":
			victim_of_day[chat.id] = target.id
			await bot.send_message(chat.id, f"Жертва дня: {target.mention_html()}.", parse_mode="HTML")
	elif data == 'duel':
		await bot.send_message(chat.id, 'Используйте /duel в reply на сообщение или укажите 2 ID: /duel <id1> <id2>')
	elif data == 'profile':
		await bot.send_message(chat.id, 'Используйте /profile в reply на сообщение пользователя, чтобы увидеть профиль.')
	elif data == 'botinfo':
		try:
			await botinfo_cmd(query.message, context)
		except Exception:
			logger.exception('botinfo via callback failed')


async def sacrifice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
	chat = update.effective_chat
	user = update.effective_user
	if not is_admin(user.id, chat.id):
		return await update.message.reply_text("Только админы могут выбирать жертву дня.")
	ensure_chat_structs(chat.id)
	pool = list(recent_activity.get(chat.id, set()))
	if not pool:
		return await update.message.reply_text("Нет активных пользователей для выбора.")
	victim = random.choice(pool)
	victim_of_day[chat.id] = victim
	await update.message.reply_text(f"Жертва дня: <a href=\"tg://user?id={victim}\">{victim}</a>", parse_mode="HTML")

# --- Message and chat handlers ---
async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
	msg = update.message
	if not msg:
		return
	# ignore bots
	if msg.from_user and msg.from_user.is_bot:
		return
	chat_id = update.effective_chat.id
	ensure_chat_structs(chat_id)
	uid = msg.from_user.id
	# track activity and last message
	recent_activity[chat_id].add(uid)
	last_message_time[chat_id] = datetime.utcnow().timestamp()

	# auto replies: only on mention, reply-to-bot, or in private chat
	text = (msg.text or msg.caption or "")
	is_private = update.effective_chat.type == 'private'
	bot_username = globals().get('BOT_USERNAME')
	mentioned = False
	if msg.entities:
		for ent in msg.entities:
			if ent.type in ('mention', 'text_mention'):
				ent_text = text[ent.offset: ent.offset + ent.length]
				if bot_username and bot_username.lower() in ent_text.lower():
					mentioned = True
					break
	if is_private or mentioned or (msg.reply_to_message and msg.reply_to_message.from_user and msg.reply_to_message.from_user.id == (await context.bot.get_me()).id):
		await msg.reply_text(random.choice(VANILLA + AGGRO))

async def check_silence_job(context: ContextTypes.DEFAULT_TYPE):
	now_ts = datetime.utcnow().timestamp()
	for chat_id, last_ts in list(last_message_time.items()):
		if now_ts - last_ts > 300:
			try:
				await context.bot.send_message(chat_id, random.choice(AGGRO))
				last_message_time[chat_id] = now_ts
			except Exception:
				logger.exception("Не удалось отправить агро-фразу в %s", chat_id)


async def silence_daemon(app: Application):
	# background loop to send aggro-phrases to silent chats
	while True:
		try:
			now_ts = datetime.utcnow().timestamp()
			for chat_id, last_ts in list(last_message_time.items()):
				if now_ts - last_ts > 300:
					try:
						await app.bot.send_message(chat_id, random.choice(AGGRO))
						last_message_time[chat_id] = now_ts
					except Exception:
						logger.exception("Не удалось отправить агро-фразу в %s", chat_id)
		except Exception:
			logger.exception("Ошибка в silence_daemon")
		await asyncio.sleep(60)


async def welcome_goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE):
	# ChatMemberHandler handler: greet new members and say goodbye to left
	result = update.chat_member
	status = result.new_chat_member.status
	chat_id = update.effective_chat.id
	user = result.new_chat_member.user
	if status == ChatMember.MEMBER:
		await context.bot.send_message(chat_id, random.choice(GREETINGS))
	elif status == ChatMember.LEFT:
		await context.bot.send_message(chat_id, random.choice(FAREWELLS))

# --- Startup and main ---
def main():
	if DOTENV_LOADED:
		logger.info("Loaded .env via python-dotenv")
	else:
		logger.info("python-dotenv not installed or .env not found; skipping .env load")
	token = os.getenv("BOT_TOKEN")
	if not token:
		logger.error("BOT_TOKEN env var is not set")
		return
	async def start_backgrounds(application: Application):
			# start background daemons after app initialization
			asyncio.create_task(silence_daemon(application))
			# register visible commands for users
			try:
				commands = [
					BotCommand("start", "Запуск бота"),
					BotCommand("help", "Список команд"),
					BotCommand("roast", "Пошутить (reply)") ,
					BotCommand("vanilla", "Ванильная философия"),
					BotCommand("duel", "Дуэль (reply или 2 ID)"),
					BotCommand("roulette", "Рулетка"),
					BotCommand("profile", "Профиль (reply)") ,
					BotCommand("search", "Саркастический обыск"),
				]
				await application.bot.set_my_commands(commands)
			except Exception:
				logger.exception("Не удалось установить команды бота")
			# cache bot username for mention detection
			try:
				me = await application.bot.get_me()
				globals()['BOT_USERNAME'] = me.username
			except Exception:
				globals()['BOT_USERNAME'] = None

	app = Application.builder().token(token).post_init(start_backgrounds).build()

	# command handlers
	app.add_handler(CommandHandler("start", start))
	app.add_handler(CommandHandler(["help", "commands"], help_cmd))
	app.add_handler(CommandHandler("addadmin", addadmin))
	app.add_handler(CommandHandler("removeadmin", removeadmin))
	app.add_handler(CommandHandler("setowner", setowner))
	app.add_handler(CommandHandler("admins", admins_list))
	app.add_handler(CommandHandler("warn", warn_cmd))
	app.add_handler(CommandHandler("warns", warns_cmd))
	app.add_handler(CommandHandler("mute", mute_cmd))
	app.add_handler(CommandHandler("unmute", unmute_cmd))
	app.add_handler(CommandHandler("kick", kick_cmd))
	app.add_handler(CommandHandler("ban", ban_cmd))
	app.add_handler(CommandHandler("unban", unban_cmd))
	app.add_handler(CommandHandler("roast", roast_cmd))
	app.add_handler(CommandHandler("vanilla", vanilla_cmd))
	app.add_handler(CommandHandler("duel", duel_cmd))
	app.add_handler(CommandHandler("roulette", roulette_cmd))
	app.add_handler(CommandHandler("search", search_cmd))
	app.add_handler(CommandHandler("profile", profile_cmd))
	app.add_handler(CommandHandler("sacrifice", sacrifice_cmd))

	# message handler
	app.add_handler(MessageHandler(filters.ALL & (~filters.COMMAND), on_message))
	# callback handler for inline buttons
	app.add_handler(CallbackQueryHandler(commands_button_handler))

	# global error handler
	async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
		logger.exception("Unhandled exception: %s", context.error)
		try:
			# notify owner if possible
			bot = context.application.bot
			await bot.send_message(OWNER_ID, f"Ошибка в боте: {context.error}")
		except Exception:
			logger.exception("Не удалось уведомить владельца об ошибке")

	app.add_error_handler(global_error_handler)

	# chat member updates
	app.add_handler(ChatMemberHandler(welcome_goodbye, ChatMemberHandler.CHAT_MEMBER))

	# Note: JobQueue may be unavailable in some installs, use asyncio daemon instead

	logger.info("Starting VanillaReaperBot...")
	app.run_polling()


if __name__ == "__main__":
	main()

