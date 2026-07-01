"""Middleware to ignore non-private chat messages.

When the bot is added as admin to a group or supergroup (including forums
with topics), it should silently drop all incoming messages and callback
queries from those chats. Only private (DM) interactions are processed.

Not registered on chat_member — channel_member.py needs ChatMemberUpdated
events from groups/channels to track required channel subscriptions.
Not registered on pre_checkout_query — no chat context, always private.
"""

from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.config import settings


logger = structlog.get_logger(__name__)


def _admin_group_chat_ids() -> set[int]:
    """ID групп-чатов уведомлений (где живут топики покупок/тикетов/бекапов).

    События из них НЕ глушим — там админ нажимает кнопки заявок на оплату,
    отвечает в тикетах и т.п.
    """
    ids: set[int] = set()
    for attr in (
        'ADMIN_NOTIFICATIONS_CHAT_ID',
        'ADMIN_REPORTS_CHAT_ID',
        'BACKUP_SEND_CHAT_ID',
        'LOG_ROTATION_CHAT_ID',
    ):
        val = getattr(settings, attr, None)
        if val in (None, ''):
            continue
        try:
            ids.add(int(val))
        except (TypeError, ValueError):
            continue
    return ids


class ChatTypeFilterMiddleware(BaseMiddleware):
    """Drop messages and callback queries from non-private chats.

    Исключение — настроенные админ-чаты уведомлений (там обрабатываются
    кнопки заявок на оплату и ответы админов в тикетах).
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        chat = None
        if isinstance(event, Message):
            chat = event.chat
        elif isinstance(event, CallbackQuery) and event.message:
            chat = event.message.chat

        if chat is not None and chat.type != ChatType.PRIVATE:
            if chat.id not in _admin_group_chat_ids():
                logger.debug(
                    'Dropping non-private chat event',
                    chat_id=chat.id,
                    chat_type=chat.type,
                )
                return None

        return await handler(event, data)
