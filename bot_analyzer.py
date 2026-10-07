import asyncio
import os
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from telethon import TelegramClient, events, types
from telethon.sessions import StringSession


API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION_B64 = os.environ["SESSION_B64"]
BOT_TOKEN = os.environ["BOT_TOKEN"]

user_client = TelegramClient(StringSession(SESSION_B64), API_ID, API_HASH)
bot = TelegramClient("bot_analyzer_session", API_ID, API_HASH)


@bot.on(events.NewMessage(pattern=r"t\.me/([a-zA-Z0-9_]+)"))
async def handler(event):
    link = event.pattern_match.group(1)
    await event.reply("Собираю статистику... 15-20 секунд.")
    try:
        entity = await user_client.get_entity(link)
        title = entity.title

        participants = await user_client.get_participants(entity, limit=0)
        count = participants.total

        if isinstance(entity, types.Channel) and entity.megagroup:
            group_type = "супергруппа"
        elif isinstance(entity, types.Channel):
            group_type = "канал"
        else:
            group_type = "группа"

        admins = []
        bots = []
        async for user in user_client.iter_participants(
            entity, filter=types.ChannelParticipantsAdmins
        ):
            name = user.username or user.first_name
            if user.bot:
                bots.append(name)
            else:
                admins.append(name)
        admins_str = ", ".join(admins[:5]) if admins else "не видно"
        bots_str = ", ".join(bots[:5]) if bots else "нет"

        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(hours=24)
        count_hour = 0
        count_day = 0
        async for message in user_client.iter_messages(entity, limit=1000):
            msg_date = message.date
            if msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=timezone.utc)
            if msg_date > day_ago:
                count_day += 1
                if msg_date > hour_ago:
                    count_hour += 1
            else:
                break

        views_list = []
        async for message in user_client.iter_messages(entity, limit=20):
            if message.views:
                views_list.append(message.views)

        if views_list:
            avg_views = int(sum(views_list) / len(views_list))
            max_views = max(views_list)
            views_str = f"Среднее: {avg_views}, Максимум: {max_views}"
        else:
            views_str = "недоступно (группа)"

        text = (
            f"Статистика по @{link}:\n\n"
            f"Название: {title}\n"
            f"Участников: {count}\n"
            f"Тип: {group_type}\n"
            f"Админы: {admins_str}\n"
            f"Боты-админы: {bots_str}\n"
            f"Активность: {count_hour} сообщений/час, {count_day} сообщений/24ч\n"
            f"Просмотры: {views_str}\n"
        )

        await event.reply(text)
    except Exception as e:
        await event.reply(f"Ошибка: {e}")


async def main():
    await user_client.start()
    await bot.start(bot_token=BOT_TOKEN)
    print("Бот-аналитик запущен.")
    await bot.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())
