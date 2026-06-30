"""CRUD для заявок на оплату через поддержку (SupportPaymentRequest)."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import SupportPaymentRequest


async def create_support_payment_request(
    db: AsyncSession,
    user_id: int,
    amount_kopeks: int,
    request_type: str = 'balance',
    ticket_id: int | None = None,
    payload: str | None = None,
) -> SupportPaymentRequest:
    request = SupportPaymentRequest(
        user_id=user_id,
        amount_kopeks=amount_kopeks,
        request_type=request_type,
        ticket_id=ticket_id,
        payload=payload,
        status='pending',
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)
    return request


async def get_support_payment_request(
    db: AsyncSession,
    request_id: int,
) -> SupportPaymentRequest | None:
    result = await db.execute(
        select(SupportPaymentRequest).where(SupportPaymentRequest.id == request_id)
    )
    return result.scalar_one_or_none()


async def set_support_payment_status(
    db: AsyncSession,
    request: SupportPaymentRequest,
    status: str,
    processed_by: int | None = None,
) -> SupportPaymentRequest:
    request.status = status
    request.processed_at = datetime.now(UTC)
    request.processed_by = processed_by
    await db.commit()
    await db.refresh(request)
    return request
