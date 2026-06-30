import html

import structlog
from aiogram import Dispatcher, F, types
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import InaccessibleMessage
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.crud.transaction import get_user_transactions
from app.database.models import TransactionType, User
from app.handlers.subscription.autopay import handle_confirm_unlink, handle_saved_cards_list, handle_unlink_card
from app.keyboards.inline import (
    get_back_keyboard,
    get_balance_keyboard,
    get_pagination_keyboard,
    get_payment_methods_keyboard,
)
from app.localization.texts import get_texts
from app.states import BalanceStates
from app.utils.decorators import error_handler


logger = structlog.get_logger(__name__)

TRANSACTIONS_PER_PAGE = 10

CREDIT_TRANSACTION_TYPES: frozenset[str] = frozenset(
    {
        TransactionType.DEPOSIT.value,
        TransactionType.REFERRAL_REWARD.value,
        TransactionType.REFUND.value,
        TransactionType.POLL_REWARD.value,
    }
)


async def route_payment_by_method(
    message: types.Message, db_user: User, amount_kopeks: int, state: FSMContext, payment_method: str
) -> bool:
    """
    Роутер платежей по методу оплаты.

    Args:
        message: Сообщение для ответа
        db_user: Пользователь БД
        amount_kopeks: Сумма в копейках
        state: FSM состояние
        payment_method: Метод оплаты (yookassa, stars, cryptobot и т.д.)

    Returns:
        True если платеж обработан, False если метод неизвестен
    """
    if payment_method == 'stars':
        from .stars import process_stars_payment_amount

        await process_stars_payment_amount(message, db_user, amount_kopeks, state)
        return True

    # Все остальные методы требуют сессию БД
    from app.database.database import AsyncSessionLocal

    if payment_method == 'yookassa':
        from .yookassa import process_yookassa_payment_amount

        async with AsyncSessionLocal() as db:
            await process_yookassa_payment_amount(message, db_user, db, amount_kopeks, state)
        return True

    if payment_method == 'yookassa_sbp':
        from .yookassa import process_yookassa_sbp_payment_amount

        async with AsyncSessionLocal() as db:
            await process_yookassa_sbp_payment_amount(message, db_user, db, amount_kopeks, state)
        return True

    if payment_method == 'mulenpay':
        from .mulenpay import process_mulenpay_payment_amount

        async with AsyncSessionLocal() as db:
            await process_mulenpay_payment_amount(message, db_user, db, amount_kopeks, state)
        return True

    if payment_method == 'platega':
        from .platega import process_platega_payment_amount

        async with AsyncSessionLocal() as db:
            await process_platega_payment_amount(message, db_user, db, amount_kopeks, state)
        return True

    if payment_method == 'wata':
        from .wata import process_wata_payment_amount

        async with AsyncSessionLocal() as db:
            await process_wata_payment_amount(message, db_user, db, amount_kopeks, state)
        return True

    if payment_method == 'pal24':
        from .pal24 import process_pal24_payment_amount

        async with AsyncSessionLocal() as db:
            await process_pal24_payment_amount(message, db_user, db, amount_kopeks, state)
        return True

    if payment_method == 'cryptobot':
        from .cryptobot import process_cryptobot_payment_amount

        async with AsyncSessionLocal() as db:
            await process_cryptobot_payment_amount(message, db_user, db, amount_kopeks, state)
        return True

    if payment_method == 'heleket':
        from .heleket import process_heleket_payment_amount

        async with AsyncSessionLocal() as db:
            await process_heleket_payment_amount(message, db_user, db, amount_kopeks, state)
        return True

    if payment_method == 'cloudpayments':
        from .cloudpayments import process_cloudpayments_payment_amount

        async with AsyncSessionLocal() as db:
            await process_cloudpayments_payment_amount(message, db_user, db, amount_kopeks, state)
        return True

    if payment_method in ('freekassa', 'freekassa_sbp', 'freekassa_card'):
        from .freekassa import process_freekassa_payment_amount

        async with AsyncSessionLocal() as db:
            await process_freekassa_payment_amount(
                message, db_user, db, amount_kopeks, state, payment_method=payment_method
            )
        return True

    if payment_method in ('kassa_ai', 'kassa_ai_sbp', 'kassa_ai_card', 'kassa_ai_sberpay'):
        from .kassa_ai import process_kassa_ai_payment_amount

        async with AsyncSessionLocal() as db:
            await process_kassa_ai_payment_amount(
                message, db_user, db, amount_kopeks, state, payment_method=payment_method
            )
        return True

    if payment_method == 'severpay':
        from .severpay import process_severpay_payment_amount

        async with AsyncSessionLocal() as db:
            await process_severpay_payment_amount(message, db_user, db, amount_kopeks, state)
        return True

    if payment_method == 'paypear':
        from .paypear import process_paypear_payment_amount

        async with AsyncSessionLocal() as db:
            await process_paypear_payment_amount(message, db_user, db, amount_kopeks, state)
        return True

    if payment_method == 'rollypay':
        from .rollypay import process_rollypay_payment_amount

        async with AsyncSessionLocal() as db:
            await process_rollypay_payment_amount(message, db_user, db, amount_kopeks, state)
        return True

    if payment_method in ('overpay', 'overpay_fps', 'overpay_card', 'overpay_int'):
        from .overpay import process_overpay_payment_amount

        async with AsyncSessionLocal() as db:
            await process_overpay_payment_amount(message, db_user, db, amount_kopeks, state)
        return True

    if payment_method in ('aurapay', 'aurapay_sbp', 'aurapay_card'):
        from .aurapay import process_aurapay_payment_amount

        async with AsyncSessionLocal() as db:
            await process_aurapay_payment_amount(message, db_user, db, amount_kopeks, state)
        return True

    if payment_method in ('etoplatezhi', 'etoplatezhi_sbp', 'etoplatezhi_card'):
        from .etoplatezhi import process_etoplatezhi_payment_amount

        async with AsyncSessionLocal() as db:
            await process_etoplatezhi_payment_amount(message, db_user, db, amount_kopeks, state)
        return True

    if payment_method in ('antilopay', 'antilopay_sbp', 'antilopay_card', 'antilopay_sberpay'):
        from .antilopay import process_antilopay_payment_amount

        async with AsyncSessionLocal() as db:
            await process_antilopay_payment_amount(message, db_user, db, amount_kopeks, state)
        return True

    if payment_method in ('jupiter', 'jupiter_sbp'):
        from .jupiter import process_jupiter_payment_amount

        async with AsyncSessionLocal() as db:
            await process_jupiter_payment_amount(message, db_user, db, amount_kopeks, state)
        return True

    if payment_method in ('donut', 'donut_card', 'donut_sbp', 'donut_sbp_qr'):
        from .donut import process_donut_payment_amount

        async with AsyncSessionLocal() as db:
            await process_donut_payment_amount(message, db_user, db, amount_kopeks, state)
        return True

    if payment_method in ('lava', 'lava_card', 'lava_sbp'):
        from .lava import process_lava_payment_amount

        async with AsyncSessionLocal() as db:
            await process_lava_payment_amount(message, db_user, db, amount_kopeks, state)
        return True

    if payment_method == 'riopay':
        from .riopay import process_riopay_payment_amount

        async with AsyncSessionLocal() as db:
            await process_riopay_payment_amount(message, db_user, db, amount_kopeks, state)
        return True

    return False


@error_handler
async def show_balance_menu(callback: types.CallbackQuery, db_user: User, db: AsyncSession):
    # Проверяем, доступно ли сообщение
    if isinstance(callback.message, InaccessibleMessage):
        await callback.answer()
        return

    texts = get_texts(db_user.language)

    balance_text = texts.BALANCE_INFO.format(balance=texts.format_price(db_user.balance_kopeks))

    reply_markup = get_balance_keyboard(db_user.language)

    try:
        if callback.message and callback.message.text:
            await callback.message.edit_text(balance_text, reply_markup=reply_markup)
        elif callback.message and callback.message.caption:
            await callback.message.edit_caption(balance_text, reply_markup=reply_markup)
        else:
            await callback.message.answer(balance_text, reply_markup=reply_markup)
    except TelegramBadRequest as error:
        logger.warning('Failed to edit balance message, sending a new one instead', error=error)
        await callback.message.answer(balance_text, reply_markup=reply_markup)
    await callback.answer()


@error_handler
async def show_balance_history(callback: types.CallbackQuery, db_user: User, db: AsyncSession, page: int = 1):
    texts = get_texts(db_user.language)

    offset = (page - 1) * TRANSACTIONS_PER_PAGE

    raw_transactions = await get_user_transactions(db, db_user.id, limit=TRANSACTIONS_PER_PAGE * 3, offset=offset)

    seen_transactions = set()
    unique_transactions = []

    for transaction in raw_transactions:
        rounded_time = transaction.created_at.replace(second=0, microsecond=0)
        transaction_key = (transaction.amount_kopeks, transaction.description, rounded_time)

        if transaction_key not in seen_transactions:
            seen_transactions.add(transaction_key)
            unique_transactions.append(transaction)

            if len(unique_transactions) >= TRANSACTIONS_PER_PAGE:
                break

    all_transactions = await get_user_transactions(db, db_user.id, limit=1000)
    seen_all = set()
    total_unique = 0

    for transaction in all_transactions:
        rounded_time = transaction.created_at.replace(second=0, microsecond=0)
        transaction_key = (transaction.amount_kopeks, transaction.description, rounded_time)
        if transaction_key not in seen_all:
            seen_all.add(transaction_key)
            total_unique += 1

    if not unique_transactions:
        await callback.message.edit_text('📊 История операций пуста', reply_markup=get_back_keyboard(db_user.language))
        await callback.answer()
        return

    text = '📊 <b>История операций</b>\n\n'

    for transaction in unique_transactions:
        is_credit = transaction.type in CREDIT_TRANSACTION_TYPES
        emoji = '💰' if is_credit else '💸'
        amount_text = (
            f'+{texts.format_price(transaction.amount_kopeks)}'
            if is_credit
            else f'-{texts.format_price(abs(transaction.amount_kopeks))}'
        )

        text += f'{emoji} {amount_text}\n'
        text += f'📝 {html.escape(transaction.description or "")}\n'
        text += f'📅 {transaction.created_at.strftime("%d.%m.%Y %H:%M")}\n\n'

    keyboard = []
    total_pages = (total_unique + TRANSACTIONS_PER_PAGE - 1) // TRANSACTIONS_PER_PAGE

    if total_pages > 1:
        pagination_row = get_pagination_keyboard(page, total_pages, 'balance_history', db_user.language)
        keyboard.extend(pagination_row)

    keyboard.append([types.InlineKeyboardButton(text=texts.BACK, callback_data='menu_balance')])

    await callback.message.edit_text(
        text, reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode='HTML'
    )
    await callback.answer()


@error_handler
async def handle_balance_history_pagination(callback: types.CallbackQuery, db_user: User, db: AsyncSession):
    page = int(callback.data.split('_')[-1])
    await show_balance_history(callback, db_user, db, page)


@error_handler
async def show_payment_methods(callback: types.CallbackQuery, db_user: User, db: AsyncSession, state: FSMContext):
    from app.config import settings
    from app.utils.payment_utils import get_payment_methods_text

    texts = get_texts(db_user.language)

    # Проверка ограничения на пополнение
    if getattr(db_user, 'restriction_topup', False):
        reason = html.escape(getattr(db_user, 'restriction_reason', None) or 'Действие ограничено администратором')
        support_url = settings.get_support_contact_url()
        keyboard = []
        if support_url:
            keyboard.append([types.InlineKeyboardButton(text='🆘 Обжаловать', url=support_url)])
        keyboard.append([types.InlineKeyboardButton(text=texts.BACK, callback_data='menu_balance')])

        await callback.message.edit_text(
            f'🚫 <b>Пополнение ограничено</b>\n\n{reason}\n\n'
            'Если вы считаете это ошибкой, вы можете обжаловать решение.',
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=keyboard),
        )
        await callback.answer()
        return

    payment_text = get_payment_methods_text(db_user.language)

    # Проверяем сохранённую корзину для автоподстановки суммы пополнения
    amount_kopeks = 0
    try:
        from app.services.user_cart_service import user_cart_service

        cart_data = await user_cart_service.get_user_cart(db_user.id)
        if cart_data and cart_data.get('saved_cart'):
            missing = cart_data.get('missing_amount', 0)
            if missing > 0:
                amount_kopeks = missing
    except Exception:
        pass

    full_text = payment_text

    keyboard = get_payment_methods_keyboard(amount_kopeks, db_user.language)

    # Если сообщение недоступно, отправляем новое
    if isinstance(callback.message, InaccessibleMessage):
        await callback.message.answer(full_text, reply_markup=keyboard, parse_mode='HTML')
        await callback.answer()
        return

    try:
        await callback.message.edit_text(full_text, reply_markup=keyboard, parse_mode='HTML')
    except TelegramBadRequest:
        try:
            await callback.message.edit_caption(full_text, reply_markup=keyboard, parse_mode='HTML')
        except TelegramBadRequest:
            try:
                await callback.message.delete()
            except TelegramBadRequest:
                pass
            await callback.message.answer(full_text, reply_markup=keyboard, parse_mode='HTML')

    await callback.answer()


@error_handler
async def handle_payment_methods_unavailable(callback: types.CallbackQuery, db_user: User):
    texts = get_texts(db_user.language)

    await callback.answer(
        texts.t(
            'PAYMENT_METHODS_UNAVAILABLE_ALERT',
            '⚠️ В данный момент автоматические способы оплаты временно недоступны. Для пополнения баланса обратитесь в техподдержку.',
        ),
        show_alert=True,
    )


@error_handler
async def handle_successful_topup_with_cart(user_id: int, amount_kopeks: int, bot, db: AsyncSession):
    from aiogram.fsm.storage.base import StorageKey

    from app.bot import dp
    from app.database.crud.user import get_user_by_id

    user = await get_user_by_id(db, user_id)
    if not user:
        return

    # Email-only users don't have telegram_id - skip Telegram notification
    if not user.telegram_id:
        logger.info('Skipping cart notification for email-only user', user_id=user_id)
        return

    storage = dp.storage
    key = StorageKey(bot_id=bot.id, chat_id=user.telegram_id, user_id=user.telegram_id)

    try:
        state_data = await storage.get_data(key)
        current_state = await storage.get_state(key)

        if current_state == 'SubscriptionStates:cart_saved_for_topup' and state_data.get('saved_cart'):
            texts = get_texts(user.language)
            total_price = state_data.get('total_price', 0)

            keyboard = types.InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        types.InlineKeyboardButton(
                            text='🛒 Вернуться к оформлению подписки', callback_data='return_to_saved_cart'
                        )
                    ],
                    [types.InlineKeyboardButton(text='💰 Мой баланс', callback_data='menu_balance')],
                    [types.InlineKeyboardButton(text='🏠 Главное меню', callback_data='back_to_menu')],
                ]
            )

            if 0 < total_price <= user.balance_kopeks:
                balance_hint = 'Средств на балансе достаточно для оформления.'
            else:
                missing = max(total_price - user.balance_kopeks, 0)
                # Без округления, иначе при не хватке <50 копеек покажется «0 ₽».
                balance_hint = f'Не хватает: {texts.format_price(missing, round_kopeks=False)}'

            success_text = (
                f'✅ Баланс пополнен на {texts.format_price(amount_kopeks)}!\n\n'
                f'💰 Текущий баланс: {texts.format_price(user.balance_kopeks)}\n\n'
                f'🛒 У вас есть сохранённая корзина на {texts.format_price(total_price)}\n'
                f'{balance_hint}\n\n'
                f'Хотите продолжить оформление?'
            )

            await bot.send_message(
                chat_id=user.telegram_id, text=success_text, reply_markup=keyboard, parse_mode='HTML'
            )

    except Exception as e:
        logger.error('Ошибка обработки успешного пополнения с корзиной', error=e)


@error_handler
async def request_support_topup(
    callback: types.CallbackQuery, db_user: User, state: FSMContext, db: AsyncSession
):
    texts = get_texts(db_user.language)

    if not settings.is_support_topup_enabled():
        await callback.answer(
            texts.t(
                'SUPPORT_TOPUP_DISABLED',
                'Пополнение через поддержку отключено. Попробуйте другой способ оплаты.',
            ),
            show_alert=True,
        )
        return

    # Контекст покупки подписки: корзина сохранена, сумма известна → не спрашиваем
    cart = None
    try:
        from app.services.user_cart_service import user_cart_service

        cart = await user_cart_service.get_user_cart(db_user.id)
    except Exception as e:
        logger.error('Не удалось получить корзину для оплаты через поддержку', error=e)

    if cart and cart.get('missing_amount') and cart.get('return_to_cart'):
        import json

        missing_amount = int(cart['missing_amount'])
        await state.clear()
        await _create_support_payment_request(
            bot=callback.bot,
            db=db,
            db_user=db_user,
            amount_kopeks=missing_amount,
            request_type='subscription',
            payload=json.dumps({'return_to_cart': True}),
            item_title='подписка',
        )
        await callback.message.edit_text(
            texts.t(
                'SUPPORT_SUB_REQUEST_CREATED',
                '✅ <b>Заявка на оплату подписки создана</b>\n\n'
                'Сумма: <b>{amount} ₽</b>\n\n'
                'Поддержка свяжется с вами. После подтверждения оплаты вы сможете '
                'завершить покупку подписки.',
            ).format(amount=f'{missing_amount / 100:.0f}'),
            reply_markup=get_back_keyboard(db_user.language, callback_data='back_to_menu'),
            parse_mode='HTML',
        )
        await callback.answer()
        return

    # Иначе — обычное пополнение баланса: спрашиваем сумму
    await state.set_state(BalanceStates.waiting_for_support_request)
    await callback.message.edit_text(
        texts.t(
            'SUPPORT_TOPUP_ENTER_AMOUNT',
            '🛠️ <b>Пополнение через поддержку</b>\n\n'
            'Введите сумму пополнения в рублях (например: <code>500</code>).\n\n'
            'После отправки будет создана заявка — поддержка свяжется с вами '
            'и подтвердит зачисление.',
        ),
        reply_markup=get_back_keyboard(db_user.language, callback_data='balance_topup'),
        parse_mode='HTML',
    )
    await callback.answer()


@error_handler
async def process_support_topup_amount(
    message: types.Message, db_user: User, state: FSMContext, db: AsyncSession
):
    """Принимает сумму, создаёт тикет + заявку и уведомляет админов с кнопками."""
    texts = get_texts(db_user.language)

    if not message.text:
        await message.answer(texts.INVALID_AMOUNT, reply_markup=get_back_keyboard(db_user.language))
        return

    try:
        amount_rubles = float(message.text.strip().replace(',', '.'))
    except ValueError:
        await message.answer(
            texts.INVALID_AMOUNT,
            reply_markup=get_back_keyboard(db_user.language, callback_data='balance_topup'),
        )
        return

    if amount_rubles < 1:
        await message.answer(
            texts.t('SUPPORT_TOPUP_MIN_AMOUNT', 'Минимальная сумма пополнения: 1 ₽'),
            reply_markup=get_back_keyboard(db_user.language, callback_data='balance_topup'),
        )
        return

    amount_kopeks = int(round(amount_rubles * 100))
    await state.clear()

    await _create_support_payment_request(
        bot=message.bot,
        db=db,
        db_user=db_user,
        amount_kopeks=amount_kopeks,
        request_type='balance',
        payload=None,
    )

    await message.answer(
        texts.t(
            'SUPPORT_TOPUP_REQUEST_CREATED',
            '✅ <b>Заявка создана</b>\n\n'
            'Сумма: <b>{amount} ₽</b>\n\n'
            'Поддержка скоро свяжется с вами для оплаты. После подтверждения '
            'баланс будет пополнен автоматически.',
        ).format(amount=f'{amount_kopeks / 100:.0f}'),
        reply_markup=get_back_keyboard(db_user.language, callback_data='back_to_menu'),
        parse_mode='HTML',
    )


async def _create_support_payment_request(
    *,
    bot,
    db: AsyncSession,
    db_user: User,
    amount_kopeks: int,
    request_type: str,
    payload: str | None,
    item_title: str | None = None,
) -> None:
    """Создаёт тикет + заявку SupportPaymentRequest и шлёт админам кнопки."""
    from app.database.crud.support_payment import create_support_payment_request
    from app.database.crud.ticket import TicketCRUD
    from app.services.admin_notification_service import AdminNotificationService, NotificationCategory

    amount_display = f'{amount_kopeks / 100:.0f} ₽'
    username = f'@{db_user.username}' if db_user.username else '—'
    full_name = (db_user.full_name if getattr(db_user, 'full_name', None) else None) or 'Пользователь'

    if request_type == 'subscription':
        kind_ru = f'Покупка подписки: {item_title or "подписка"}'
        ticket_title = f'Оплата через поддержку — подписка ({amount_display})'
    else:
        kind_ru = 'Пополнение баланса'
        ticket_title = f'Оплата через поддержку — баланс ({amount_display})'

    ticket_text = (
        f'🛠️ Заявка на оплату через поддержку\n\n'
        f'Тип: {kind_ru}\n'
        f'Сумма: {amount_display}\n\n'
        f'Пользователь подтвердит оплату в этом тикете.'
    )

    ticket = None
    try:
        ticket = await TicketCRUD.create_ticket(
            db,
            user_id=db_user.id,
            title=ticket_title,
            message_text=ticket_text,
            priority='high',
        )
    except Exception as e:
        logger.error('Не удалось создать тикет для заявки на оплату', error=e)

    request = await create_support_payment_request(
        db,
        user_id=db_user.id,
        amount_kopeks=amount_kopeks,
        request_type=request_type,
        ticket_id=ticket.id if ticket else None,
        payload=payload,
    )

    ticket_line = f'🎫 Тикет: #{ticket.id}\n' if ticket else ''
    admin_text = (
        f'🛠️ <b>ЗАЯВКА НА ОПЛАТУ ЧЕРЕЗ ПОДДЕРЖКУ</b>\n\n'
        f'👤 <b>Пользователь:</b> {full_name}\n'
        f'🆔 <b>Telegram ID:</b> <code>{db_user.telegram_id}</code>\n'
        f'📱 <b>Username:</b> {username}\n'
        f'{ticket_line}'
        f'📦 <b>Тип:</b> {kind_ru}\n'
        f'💰 <b>Сумма:</b> {amount_display}\n'
        f'🧾 <b>Заявка:</b> #{request.id}\n\n'
        f'Ответьте пользователю в тикете и нажмите кнопку после оплаты:'
    )

    keyboard_rows = []
    if ticket:
        keyboard_rows.append(
            [
                types.InlineKeyboardButton(
                    text='💬 Ответить', callback_data=f'admin_reply_ticket_{ticket.id}'
                )
            ]
        )
    keyboard_rows.append(
        [
            types.InlineKeyboardButton(
                text='✅ Подтвердить', callback_data=f'sup_pay_ok:{request.id}'
            ),
            types.InlineKeyboardButton(
                text='❌ Отклонить', callback_data=f'sup_pay_no:{request.id}'
            ),
        ]
    )
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

    try:
        admin_service = AdminNotificationService(bot)
        await admin_service.send_admin_notification(
            admin_text, reply_markup=keyboard, category=NotificationCategory.TICKETS
        )
    except Exception as e:
        logger.error('Не удалось отправить заявку на оплату админам', error=e)


@error_handler
async def confirm_support_payment(callback: types.CallbackQuery, db: AsyncSession):
    """Админ подтверждает заявку: зачисляет баланс или активирует подписку."""
    from app.database.crud.support_payment import (
        get_support_payment_request,
        set_support_payment_status,
    )
    from app.database.crud.user import add_user_balance, get_user_by_id

    if not settings.is_admin(callback.from_user.id):
        await callback.answer('Недостаточно прав', show_alert=True)
        return

    try:
        request_id = int(callback.data.split(':', 1)[1])
    except (IndexError, ValueError):
        await callback.answer('Некорректная заявка', show_alert=True)
        return

    request = await get_support_payment_request(db, request_id)
    if not request:
        await callback.answer('Заявка не найдена', show_alert=True)
        return
    if request.status != 'pending':
        await callback.answer(f'Заявка уже обработана ({request.status})', show_alert=True)
        return

    user = await get_user_by_id(db, request.user_id)
    if not user:
        await callback.answer('Пользователь не найден', show_alert=True)
        return

    amount_display = f'{request.amount_kopeks / 100:.0f} ₽'

    # И для баланса, и для подписки деньги зачисляются на баланс.
    # Для подписки пользователь затем завершает покупку из сохранённой корзины.
    if request.amount_kopeks > 0:
        ok = await add_user_balance(
            db,
            user,
            request.amount_kopeks,
            description='Оплата через поддержку',
            bot=callback.bot,
        )
        if not ok:
            await callback.answer('Ошибка зачисления баланса', show_alert=True)
            return

    user_kb = None
    if request.request_type == 'subscription':
        user_text = (
            f'✅ <b>Оплата подтверждена</b>\n\n'
            f'Баланс пополнен на <b>{amount_display}</b>.\n'
            f'Нажмите кнопку ниже, чтобы завершить покупку подписки.'
        )
        user_kb = types.InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    types.InlineKeyboardButton(
                        text='✅ Завершить покупку', callback_data='return_to_saved_cart'
                    )
                ]
            ]
        )
    else:
        user_text = (
            f'✅ <b>Баланс пополнен</b>\n\n'
            f'Сумма: <b>{amount_display}</b>\n'
            f'Спасибо за оплату!'
        )

    await set_support_payment_status(db, request, 'approved', processed_by=callback.from_user.id)

    # Закрываем связанный тикет
    if request.ticket_id:
        try:
            from app.database.crud.ticket import TicketCRUD

            await TicketCRUD.close_ticket(db, request.ticket_id)
        except Exception as e:
            logger.error('Не удалось закрыть тикет после подтверждения заявки', error=e)

    if user.telegram_id:
        try:
            await callback.bot.send_message(
                user.telegram_id, user_text, parse_mode='HTML', reply_markup=user_kb
            )
        except Exception as e:
            logger.error('Не удалось уведомить пользователя о подтверждении', error=e)

    try:
        await callback.message.edit_text(
            callback.message.html_text + f'\n\n✅ <b>Подтверждено</b> ({amount_display})',
            parse_mode='HTML',
        )
    except Exception:
        pass
    await callback.answer('Заявка подтверждена')


@error_handler
async def reject_support_payment(callback: types.CallbackQuery, db: AsyncSession):
    """Админ отклоняет заявку на оплату."""
    from app.database.crud.support_payment import (
        get_support_payment_request,
        set_support_payment_status,
    )
    from app.database.crud.user import get_user_by_id

    if not settings.is_admin(callback.from_user.id):
        await callback.answer('Недостаточно прав', show_alert=True)
        return

    try:
        request_id = int(callback.data.split(':', 1)[1])
    except (IndexError, ValueError):
        await callback.answer('Некорректная заявка', show_alert=True)
        return

    request = await get_support_payment_request(db, request_id)
    if not request:
        await callback.answer('Заявка не найдена', show_alert=True)
        return
    if request.status != 'pending':
        await callback.answer(f'Заявка уже обработана ({request.status})', show_alert=True)
        return

    await set_support_payment_status(db, request, 'rejected', processed_by=callback.from_user.id)

    # Закрываем связанный тикет
    if request.ticket_id:
        try:
            from app.database.crud.ticket import TicketCRUD

            await TicketCRUD.close_ticket(db, request.ticket_id)
        except Exception as e:
            logger.error('Не удалось закрыть тикет после отклонения заявки', error=e)

    user = await get_user_by_id(db, request.user_id)
    if user and user.telegram_id:
        try:
            await callback.bot.send_message(
                user.telegram_id,
                '❌ <b>Заявка на оплату отклонена</b>\n\n'
                'Свяжитесь с поддержкой для уточнения деталей.',
                parse_mode='HTML',
            )
        except Exception as e:
            logger.error('Не удалось уведомить пользователя об отклонении', error=e)

    try:
        await callback.message.edit_text(
            callback.message.html_text + '\n\n❌ <b>Отклонено</b>',
            parse_mode='HTML',
        )
    except Exception:
        pass
    await callback.answer('Заявка отклонена')


@error_handler
async def process_topup_amount(message: types.Message, db_user: User, state: FSMContext):
    texts = get_texts(db_user.language)

    try:
        if not message.text:
            if message.successful_payment:
                logger.info(
                    'Получено сообщение об успешном платеже без текста, обработчик суммы пополнения завершает работу'
                )
                await state.clear()
                return

            await message.answer(texts.INVALID_AMOUNT, reply_markup=get_back_keyboard(db_user.language))
            return

        amount_text = message.text.strip()
        if not amount_text:
            await message.answer(texts.INVALID_AMOUNT, reply_markup=get_back_keyboard(db_user.language))
            return

        amount_rubles = float(amount_text.replace(',', '.'))

        if amount_rubles < 1:
            await message.answer(
                'Минимальная сумма пополнения: 1 ₽',
                reply_markup=get_back_keyboard(db_user.language, callback_data='balance_topup'),
            )
            return

        if amount_rubles > 50000:
            await message.answer(
                'Максимальная сумма пополнения: 50,000 ₽',
                reply_markup=get_back_keyboard(db_user.language, callback_data='balance_topup'),
            )
            return

        amount_kopeks = int(amount_rubles * 100)
        data = await state.get_data()
        payment_method = data.get('payment_method', 'stars')

        if payment_method in ['yookassa', 'yookassa_sbp']:
            if amount_kopeks < settings.YOOKASSA_MIN_AMOUNT_KOPEKS:
                min_rubles = settings.YOOKASSA_MIN_AMOUNT_KOPEKS / 100
                await message.answer(
                    f'❌ Минимальная сумма для оплаты через YooKassa: {min_rubles:.0f} ₽',
                    reply_markup=get_back_keyboard(db_user.language, callback_data='balance_topup'),
                )
                return

            if amount_kopeks > settings.YOOKASSA_MAX_AMOUNT_KOPEKS:
                max_rubles = settings.YOOKASSA_MAX_AMOUNT_KOPEKS / 100
                await message.answer(
                    f'❌ Максимальная сумма для оплаты через YooKassa: {max_rubles:,.0f} ₽'.replace(',', ' '),
                    reply_markup=get_back_keyboard(db_user.language, callback_data='balance_topup'),
                )
                return

        if not await route_payment_by_method(message, db_user, amount_kopeks, state, payment_method):
            await message.answer('Неизвестный способ оплаты')

    except ValueError:
        await message.answer(texts.INVALID_AMOUNT, reply_markup=get_back_keyboard(db_user.language))


@error_handler
async def handle_sbp_payment(callback: types.CallbackQuery, db: AsyncSession):
    try:
        local_payment_id = int(callback.data.split('_')[-1])

        from app.database.crud.yookassa import get_yookassa_payment_by_local_id

        payment = await get_yookassa_payment_by_local_id(db, local_payment_id)

        if not payment:
            await callback.answer('❌ Платеж не найден', show_alert=True)
            return

        import json

        metadata = json.loads(payment.metadata_json) if payment.metadata_json else {}
        confirmation_token = metadata.get('confirmation_token')

        if not confirmation_token:
            await callback.answer('❌ Токен подтверждения не найден', show_alert=True)
            return

        await callback.message.answer(
            f'Для оплаты через СБП откройте приложение вашего банка и подтвердите платеж.\\n\\n'
            f'Если у вас не открылось банковское приложение автоматически, вы можете:\\n'
            f'1. Скопировать этот токен: <code>{confirmation_token}</code>\\n'
            f'2. Открыть приложение вашего банка\\n'
            f'3. Найти функцию оплаты по токену\\n'
            f'4. Вставить токен и подтвердить платеж',
            parse_mode='HTML',
        )

        await callback.answer('Информация об оплате отправлена', show_alert=True)

    except Exception as e:
        logger.error('Ошибка обработки embedded платежа СБП', error=e)
        await callback.answer('❌ Ошибка обработки платежа', show_alert=True)


@error_handler
async def handle_topup_amount_callback(
    callback: types.CallbackQuery,
    db_user: User,
    state: FSMContext,
):
    try:
        _, method, amount_str = callback.data.split('|', 2)
        amount_kopeks = int(amount_str)
    except ValueError:
        await callback.answer('❌ Некорректный запрос', show_alert=True)
        return

    if amount_kopeks <= 0:
        await callback.answer('❌ Некорректная сумма', show_alert=True)
        return

    try:
        # Особые случаи, требующие специальной логики
        if method.startswith('platega_m'):
            from app.database.database import AsyncSessionLocal

            from .platega import process_platega_payment_amount

            platega_method_code = int(method[len('platega_m') :])
            await state.update_data(payment_method='platega', platega_method=platega_method_code)
            await state.set_state(BalanceStates.waiting_for_amount)
            async with AsyncSessionLocal() as db:
                await process_platega_payment_amount(callback.message, db_user, db, amount_kopeks, state)
        elif method == 'platega':
            from app.database.database import AsyncSessionLocal

            from .platega import process_platega_payment_amount, start_platega_payment

            data = await state.get_data()
            method_code = int(data.get('platega_method', 0)) if data else 0

            if method_code > 0:
                await state.set_state(BalanceStates.waiting_for_amount)
                async with AsyncSessionLocal() as db:
                    await process_platega_payment_amount(callback.message, db_user, db, amount_kopeks, state)
            else:
                await state.update_data(platega_pending_amount=amount_kopeks)
                await start_platega_payment(callback, db_user, state)
        elif method == 'tribute':
            from .tribute import start_tribute_payment

            await start_tribute_payment(callback, db_user)
            return
        # Стандартные методы через роутер
        else:
            await state.update_data(payment_method=method)
            await state.set_state(BalanceStates.waiting_for_amount)
            if not await route_payment_by_method(callback.message, db_user, amount_kopeks, state, method):
                await callback.answer('❌ Неизвестный способ оплаты', show_alert=True)
                return

        await callback.answer()

    except Exception as error:
        logger.error('Ошибка быстрого пополнения', error=error)
        await callback.answer('❌ Ошибка обработки запроса', show_alert=True)


def register_balance_handlers(dp: Dispatcher):
    dp.callback_query.register(show_balance_menu, F.data == 'menu_balance')

    dp.callback_query.register(show_balance_history, F.data == 'balance_history')

    dp.callback_query.register(handle_balance_history_pagination, F.data.startswith('balance_history_page_'))

    dp.callback_query.register(show_payment_methods, F.data == 'balance_topup')

    from .stars import start_stars_payment

    dp.callback_query.register(start_stars_payment, F.data == 'topup_stars')

    from .yookassa import start_yookassa_payment

    dp.callback_query.register(start_yookassa_payment, F.data == 'topup_yookassa')

    from .yookassa import start_yookassa_sbp_payment

    dp.callback_query.register(start_yookassa_sbp_payment, F.data == 'topup_yookassa_sbp')

    from .mulenpay import start_mulenpay_payment

    dp.callback_query.register(start_mulenpay_payment, F.data == 'topup_mulenpay')

    from .wata import start_wata_payment

    dp.callback_query.register(start_wata_payment, F.data == 'topup_wata')

    from .pal24 import start_pal24_payment

    dp.callback_query.register(start_pal24_payment, F.data == 'topup_pal24')
    from .pal24 import handle_pal24_method_selection

    dp.callback_query.register(
        handle_pal24_method_selection,
        F.data.startswith('pal24_method_'),
    )

    from .platega import handle_platega_method_selection, start_platega_direct_method, start_platega_payment

    dp.callback_query.register(start_platega_payment, F.data == 'topup_platega')
    dp.callback_query.register(
        handle_platega_method_selection,
        F.data.startswith('platega_method_'),
    )
    dp.callback_query.register(
        start_platega_direct_method,
        F.data.regexp(r'^topup_platega_m\d+$'),
    )

    from .yookassa import check_yookassa_payment_status

    dp.callback_query.register(check_yookassa_payment_status, F.data.startswith('check_yookassa_'))

    from .tribute import start_tribute_payment

    dp.callback_query.register(start_tribute_payment, F.data == 'topup_tribute')

    dp.callback_query.register(request_support_topup, F.data == 'topup_support')
    dp.message.register(process_support_topup_amount, BalanceStates.waiting_for_support_request)
    dp.callback_query.register(confirm_support_payment, F.data.startswith('sup_pay_ok:'))
    dp.callback_query.register(reject_support_payment, F.data.startswith('sup_pay_no:'))

    from .yookassa import check_yookassa_payment_status

    dp.callback_query.register(check_yookassa_payment_status, F.data.startswith('check_yookassa_'))

    dp.message.register(process_topup_amount, BalanceStates.waiting_for_amount)

    from .cryptobot import start_cryptobot_payment

    dp.callback_query.register(start_cryptobot_payment, F.data == 'topup_cryptobot')

    from .cryptobot import check_cryptobot_payment_status

    dp.callback_query.register(check_cryptobot_payment_status, F.data.startswith('check_cryptobot_'))

    from .heleket import check_heleket_payment_status, start_heleket_payment

    dp.callback_query.register(start_heleket_payment, F.data == 'topup_heleket')
    dp.callback_query.register(check_heleket_payment_status, F.data.startswith('check_heleket_'))

    from .cloudpayments import start_cloudpayments_payment

    dp.callback_query.register(start_cloudpayments_payment, F.data == 'topup_cloudpayments')

    from .freekassa import (
        start_freekassa_card_topup,
        start_freekassa_sbp_topup,
        start_freekassa_topup,
    )

    dp.callback_query.register(start_freekassa_topup, F.data == 'topup_freekassa')
    dp.callback_query.register(start_freekassa_sbp_topup, F.data == 'topup_freekassa_sbp')
    dp.callback_query.register(start_freekassa_card_topup, F.data == 'topup_freekassa_card')

    from .kassa_ai import (
        start_kassa_ai_card_topup,
        start_kassa_ai_sberpay_topup,
        start_kassa_ai_sbp_topup,
        start_kassa_ai_topup,
    )

    dp.callback_query.register(start_kassa_ai_topup, F.data == 'topup_kassa_ai')
    dp.callback_query.register(start_kassa_ai_sbp_topup, F.data == 'topup_kassa_ai_sbp')
    dp.callback_query.register(start_kassa_ai_card_topup, F.data == 'topup_kassa_ai_card')
    dp.callback_query.register(start_kassa_ai_sberpay_topup, F.data == 'topup_kassa_ai_sberpay')

    from .riopay import start_riopay_topup

    dp.callback_query.register(start_riopay_topup, F.data == 'topup_riopay')

    from .severpay import start_severpay_topup

    dp.callback_query.register(start_severpay_topup, F.data == 'topup_severpay')

    from .paypear import start_paypear_topup

    dp.callback_query.register(start_paypear_topup, F.data == 'topup_paypear')

    from .rollypay import start_rollypay_topup

    dp.callback_query.register(start_rollypay_topup, F.data == 'topup_rollypay')

    from .overpay import (
        start_overpay_card_topup,
        start_overpay_fps_topup,
        start_overpay_int_topup,
        start_overpay_topup,
    )

    dp.callback_query.register(start_overpay_topup, F.data == 'topup_overpay')
    dp.callback_query.register(start_overpay_fps_topup, F.data == 'topup_overpay_fps')
    dp.callback_query.register(start_overpay_card_topup, F.data == 'topup_overpay_card')
    dp.callback_query.register(start_overpay_int_topup, F.data == 'topup_overpay_int')

    from .aurapay import start_aurapay_card_topup, start_aurapay_sbp_topup, start_aurapay_topup

    dp.callback_query.register(start_aurapay_topup, F.data == 'topup_aurapay')
    dp.callback_query.register(start_aurapay_sbp_topup, F.data == 'topup_aurapay_sbp')
    dp.callback_query.register(start_aurapay_card_topup, F.data == 'topup_aurapay_card')

    from .etoplatezhi import start_etoplatezhi_card_topup, start_etoplatezhi_sbp_topup, start_etoplatezhi_topup

    dp.callback_query.register(start_etoplatezhi_topup, F.data == 'topup_etoplatezhi')
    dp.callback_query.register(start_etoplatezhi_sbp_topup, F.data == 'topup_etoplatezhi_sbp')
    dp.callback_query.register(start_etoplatezhi_card_topup, F.data == 'topup_etoplatezhi_card')

    from .antilopay import (
        start_antilopay_card_topup,
        start_antilopay_sberpay_topup,
        start_antilopay_sbp_topup,
        start_antilopay_topup,
    )

    dp.callback_query.register(start_antilopay_topup, F.data == 'topup_antilopay')
    dp.callback_query.register(start_antilopay_sbp_topup, F.data == 'topup_antilopay_sbp')
    dp.callback_query.register(start_antilopay_card_topup, F.data == 'topup_antilopay_card')
    dp.callback_query.register(start_antilopay_sberpay_topup, F.data == 'topup_antilopay_sberpay')

    from .jupiter import start_jupiter_sbp_topup, start_jupiter_topup

    dp.callback_query.register(start_jupiter_topup, F.data == 'topup_jupiter')
    dp.callback_query.register(start_jupiter_sbp_topup, F.data == 'topup_jupiter_sbp')

    from .donut import (
        start_donut_card_topup,
        start_donut_sbp_qr_topup,
        start_donut_sbp_topup,
        start_donut_topup,
    )

    dp.callback_query.register(start_donut_topup, F.data == 'topup_donut')
    dp.callback_query.register(start_donut_card_topup, F.data == 'topup_donut_card')
    dp.callback_query.register(start_donut_sbp_topup, F.data == 'topup_donut_sbp')
    dp.callback_query.register(start_donut_sbp_qr_topup, F.data == 'topup_donut_sbp_qr')

    from .lava import start_lava_card_topup, start_lava_sbp_topup, start_lava_topup

    dp.callback_query.register(start_lava_topup, F.data == 'topup_lava')
    dp.callback_query.register(start_lava_card_topup, F.data == 'topup_lava_card')
    dp.callback_query.register(start_lava_sbp_topup, F.data == 'topup_lava_sbp')

    from .mulenpay import check_mulenpay_payment_status

    dp.callback_query.register(check_mulenpay_payment_status, F.data.startswith('check_mulenpay_'))

    from .wata import check_wata_payment_status

    dp.callback_query.register(check_wata_payment_status, F.data.startswith('check_wata_'))

    from .pal24 import check_pal24_payment_status

    dp.callback_query.register(check_pal24_payment_status, F.data.startswith('check_pal24_'))

    from .platega import check_platega_payment_status

    dp.callback_query.register(check_platega_payment_status, F.data.startswith('check_platega_'))

    dp.callback_query.register(handle_payment_methods_unavailable, F.data == 'payment_methods_unavailable')

    dp.callback_query.register(handle_topup_amount_callback, F.data.startswith('topup_amount|'))

    dp.callback_query.register(handle_saved_cards_list, F.data == 'saved_cards_list')
    dp.callback_query.register(handle_unlink_card, F.data.startswith('unlink_card_'))
    dp.callback_query.register(handle_confirm_unlink, F.data.startswith('confirm_unlink_'))
