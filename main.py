import asyncio
from collections import Counter
import os
from datetime import datetime
import re

from telethon import TelegramClient, events
from telethon import types

# ============================================
# НАСТРОЙКА ДЛЯ RAILWAY
# ============================================
api_id = os.environ.get('API_ID')
api_hash = os.environ.get('API_HASH')
phone = os.environ.get('PHONE')

if not all([api_id, api_hash, phone]):
    raise ValueError("❌ Не заданы переменные окружения!")

client = TelegramClient('session', int(api_id), api_hash)

# Хранилище активных задач парсинга
active_tasks = {}

# ============================================
# ФУНКЦИИ ПАРСИНГА
# ============================================

async def parse_chat_members(chat_link, user_id):
    """Парсинг участников чата"""
    try:
        await client.send_message(user_id, f"🔍 Начинаю парсинг участников чата:\n{chat_link}")
        
        # Получаем участников
        participants = await client.get_participants(chat_link, aggressive=True)
        
        users_data = []
        for user in participants:
            if user.bot or user.deleted:
                continue
            
            user_info = {
                'id': user.id,
                'username': f"@{user.username}" if user.username else 'Нет',
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'phone': user.phone if user.phone else 'Скрыт',
            }
            users_data.append(user_info)
        
        # Формируем результат
        result_text = f"✅ Парсинг завершен!\n\n"
        result_text += f"👥 Найдено участников: {len(users_data)}\n"
        result_text += f"📱 С username: {sum(1 for u in users_data if u['username'] != 'Нет')}\n"
        result_text += f"☎️ С телефоном: {sum(1 for u in users_data if u['phone'] != 'Скрыт')}\n\n"
        
        # Сохраняем в файл
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f'members_{timestamp}.txt'
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"Участники чата: {chat_link}\n")
            f.write(f"Дата: {datetime.now()}\n")
            f.write("=" * 60 + "\n\n")
            
            for user in users_data:
                f.write(f"ID: {user['id']}\n")
                f.write(f"Username: {user['username']}\n")
                f.write(f"Имя: {user['first_name']} {user['last_name']}\n")
                f.write(f"Телефон: {user['phone']}\n")
                f.write("-" * 40 + "\n")
        
        result_text += f"💾 Данные сохранены в: {filename}\n\n"
        result_text += "📋 Первые 10 участников:\n"
        
        for i, user in enumerate(users_data[:10], 1):
            result_text += f"{i}. {user['first_name']} {user['last_name']} ({user['username']}) - ID: {user['id']}\n"
        
        if len(users_data) > 10:
            result_text += f"\n... и ещё {len(users_data) - 10} участников"
        
        # Отправляем результат
        await client.send_message(user_id, result_text)
        
        # Отправляем файл
        await client.send_file(user_id, filename, caption="📄 Полный список участников")
        
    except Exception as e:
        await client.send_message(user_id, f"❌ Ошибка при парсинге участников:\n{str(e)}")


async def parse_chat_comments(chat_link, start_id, end_id, user_id):
    """Парсинг комментариев к постам"""
    try:
        await client.send_message(
            user_id, 
            f"🔍 Начинаю парсинг комментариев\n"
            f"📍 Чат: {chat_link}\n"
            f"📝 Посты: {start_id} - {end_id}"
        )
        
        commentators = []
        commentators_id = []
        total_comments = 0
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        comments_file = f'comments_{timestamp}.txt'
        
        # Открываем файл для записи
        with open(comments_file, 'w', encoding='utf-8') as f:
            f.write(f"Комментарии из чата: {chat_link}\n")
            f.write(f"Дата: {datetime.now()}\n")
            f.write("=" * 60 + "\n\n")
        
        # Парсим посты
        for post_id in range(start_id, end_id + 1):
            try:
                async for message in client.iter_messages(chat_link, reply_to=post_id, reverse=True):
                    sender = message.sender
                    sender_id = message.from_id.user_id if message.from_id else None
                    
                    if isinstance(sender, types.User):
                        sender_name = sender.first_name if sender.first_name else "Unknown User"
                    elif sender is not None:
                        sender_name = getattr(sender, 'title', 'Unknown Channel/Group')
                    else:
                        sender_name = 'Unknown Sender'
                    
                    commentators.append(sender_name)
                    commentators_id.append(str(sender_id))
                    total_comments += 1
                    
                    # Записываем комментарий
                    with open(comments_file, 'a', encoding='utf-8') as f:
                        f.write(f"Пост ID: {post_id}\n")
                        f.write(f"Дата: {message.date}\n")
                        f.write(f"Автор: {sender_name} (ID: {sender_id})\n")
                        f.write(f"Текст: {message.text}\n")
                        f.write("-" * 40 + "\n")
                
                # Прогресс каждые 50 постов
                if post_id % 50 == 0:
                    await client.send_message(user_id, f"⏳ Обработано постов: {post_id}/{end_id}")
                    
            except Exception as e:
                continue
        
        # Статистика
        counter = Counter(commentators)
        counter_ids = Counter(commentators_id)
        
        # Сохраняем статистику
        stats_file = f'stats_{timestamp}.txt'
        with open(stats_file, 'w', encoding='utf-8') as f:
            f.write("СТАТИСТИКА ПО КОММЕНТАТОРАМ\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Всего комментариев: {total_comments}\n")
            f.write(f"Уникальных комментаторов: {len(counter)}\n\n")
            f.write("ТОП-20 АКТИВНЫХ:\n")
            f.write("-" * 60 + "\n")
            
            for idx, (name, count) in enumerate(counter.most_common(20), 1):
                f.write(f"{idx}. {name} – {count} комментариев\n")
        
        # Формируем ответ
        result = f"✅ Парсинг комментариев завершен!\n\n"
        result += f"💬 Всего комментариев: {total_comments}\n"
        result += f"👥 Уникальных комментаторов: {len(counter)}\n\n"
        result += "🏆 ТОП-5 АКТИВНЫХ:\n"
        
        for idx, (name, count) in enumerate(counter.most_common(5), 1):
            result += f"{idx}. {name} – {count}\n"
        
        await client.send_message(user_id, result)
        
        # Отправляем файлы
        await client.send_file(user_id, comments_file, caption="📄 Все комментарии")
        await client.send_file(user_id, stats_file, caption="📊 Статистика")
        
    except Exception as e:
        await client.send_message(user_id, f"❌ Ошибка при парсинге комментариев:\n{str(e)}")


# ============================================
# ОБРАБОТЧИКИ КОМАНД
# ============================================

@client.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    """Приветствие"""
    help_text = """
🤖 **Telegram Парсер Бот**

Я могу парсить:
1️⃣ Участников чатов и групп
2️⃣ Комментарии к постам в каналах

**Команды:**

📋 `/members` - парсинг участников
Отправьте: `/members https://t.me/chat_name`

💬 `/comments` - парсинг комментариев
Отправьте: `/comments https://t.me/channel 1 100`
(где 1 - начальный ID поста, 100 - конечный)

❓ `/help` - показать справку

**Примеры:**
`/members https://t.me/mychat`
`/comments https://t.me/channel 1 50`

Просто отправьте команду с параметрами!
    """
    await event.respond(help_text)


@client.on(events.NewMessage(pattern='/help'))
async def help_handler(event):
    """Справка"""
    await start_handler(event)


@client.on(events.NewMessage(pattern=r'/members (.+)'))
async def members_handler(event):
    """Парсинг участников"""
    chat_link = event.pattern_match.group(1).strip()
    user_id = event.sender_id
    
    await event.respond(f"✅ Принято! Начинаю парсинг участников...\n{chat_link}")
    
    # Запускаем парсинг в фоне
    asyncio.create_task(parse_chat_members(chat_link, user_id))


@client.on(events.NewMessage(pattern=r'/comments (.+)'))
async def comments_handler(event):
    """Парсинг комментариев"""
    try:
        params = event.pattern_match.group(1).strip().split()
        
        if len(params) < 3:
            await event.respond(
                "❌ Неверный формат!\n\n"
                "Используйте:\n"
                "`/comments https://t.me/channel 1 100`\n\n"
                "где 1 - начальный ID, 100 - конечный ID"
            )
            return
        
        chat_link = params[0]
        start_id = int(params[1])
        end_id = int(params[2])
        user_id = event.sender_id
        
        await event.respond(
            f"✅ Принято! Начинаю парсинг комментариев...\n"
            f"Чат: {chat_link}\n"
            f"Посты: {start_id} - {end_id}"
        )
        
        # Запускаем парсинг в фоне
        asyncio.create_task(parse_chat_comments(chat_link, start_id, end_id, user_id))
        
    except Exception as e:
        await event.respond(f"❌ Ошибка: {str(e)}")


# ============================================
# ЗАПУСК БОТА
# ============================================

async def main():
    """Запуск бота"""
    print("🚀 Запуск Telegram парсер-бота...")
    
    await client.start(phone=phone)
    
    me = await client.get_me()
    print(f"✅ Бот запущен!")
    print(f"📱 Аккаунт: {me.first_name} (@{me.username})")
    print(f"🆔 ID: {me.id}")
    print("=" * 60)
    print("💬 Напишите боту /start чтобы начать")
    print("🔄 Бот работает в режиме ожидания команд...")
    print("=" * 60)
    
    # Держим бота активным
    await client.run_until_disconnected()


if __name__ == '__main__':
    client.loop.run_until_complete(main())
