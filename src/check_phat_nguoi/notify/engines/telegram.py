from __future__ import annotations

import asyncio
from asyncio import TimeoutError
from logging import getLogger
from typing import Final, override

from aiohttp import ClientError, ClientSession, ClientTimeout

from check_phat_nguoi.config import TelegramNotificationEngineConfig
from check_phat_nguoi.config.config_reader import config
from check_phat_nguoi.config.models.notifications.base_engine import (
    BaseNotificationEngineConfig,
)
from check_phat_nguoi.constants import SEND_MESSAGE_API_URL_TELEGRAM as API_URL

from ..markdown_message import MarkdownMessageDetail
from .base import BaseNotificationEngine

logger = getLogger(__name__)


class TelegramNotificationEngine(BaseNotificationEngine):
    timeout: Final[int] = config.request_timeout

    def __init__(self) -> None:
        self._session: ClientSession = ClientSession(
            timeout=ClientTimeout(self.timeout),
        )
        logger.debug(f"Created notify engine session: {type(self).__name__}")

    @override
    async def __aexit__(self, exc_type, exc_value, exc_traceback) -> None:
        await self._session.close()
        logger.debug(f"Closed notify engine session: {type(self).__name__}")

    async def _send_message(
        self,
        telegram: TelegramNotificationEngineConfig,
        message: str,
        *,
        plate: str,
    ) -> None:
        logger.info(f"Plate {plate}: Sending to Telegram Chat ID: {telegram.chat_id}")
        url: str = API_URL.format(bot_token=telegram.bot_token)
        payload: dict[str, str] = {
            "chat_id": telegram.chat_id,
            "text": message,
            "parse_mode": "Markdown",
        }
        try:
            async with self._session.post(
                url,
                json=payload,
            ) as response:
                response.raise_for_status()
            logger.info(
                f"Plate {plate}: Successfully sent to Telegram Chat ID: {telegram.chat_id}"
            )
        except TimeoutError as e:
            logger.error(
                f"Plate {plate}: Timeout ({self.timeout}s) sending to Telegram Chat ID: {telegram.chat_id}. {e}"
            )
        except ClientError as e:
            logger.error(
                f"Plate {plate}: Fail to sent to Telegram Chat ID: {telegram.chat_id}. {e}"
            )
        except Exception as e:
            logger.error(
                f"Plate {plate}: Fail to sent to Telegram Chat ID (internally): {telegram.chat_id}. {e}"
            )

    async def send(
        self,
        notification_config: BaseNotificationEngineConfig,
        plates_messages: tuple[MarkdownMessageDetail, ...],
    ) -> None:
        if not isinstance(notification_config, TelegramNotificationEngineConfig):
            return
        await asyncio.gather(
            *(
                self._send_message(
                    telegram=notification_config, message=message, plate=messages.plate
                )
                for messages in plates_messages
                for message in messages.messages
            )
        )
