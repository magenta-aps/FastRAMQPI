# SPDX-FileCopyrightText: 2019-2020 Magenta ApS
#
# SPDX-License-Identifier: MPL-2.0
"""This module tests the migration to quorum queues."""
import asyncio

import pytest
from pydantic import AmqpDsn
from pydantic import parse_obj_as

from .common import random_string
from fastramqpi.ramqp import AMQPSystem
from fastramqpi.ramqp.config import AMQPConnectionSettings


@pytest.mark.integration_test
async def test_multilayer_exchange_publish() -> None:
    """Test that we can publish to different layers on the exchange."""
    url_raw = "amqp://guest:guest@localhost:5672"
    url = parse_obj_as(AmqpDsn, url_raw)

    mo_exchange = random_string()

    queue_prefix_1 = random_string()
    amqp_system_1 = AMQPSystem(
        settings=AMQPConnectionSettings(
            url=url,
            queue_prefix=queue_prefix_1,
            exchange=mo_exchange,
        ),
    )
    amqp_system_1_exchange = f"{mo_exchange}_{queue_prefix_1}"

    queue_prefix_2 = random_string()
    amqp_system_2 = AMQPSystem(
        settings=AMQPConnectionSettings(
            url=url,
            queue_prefix=queue_prefix_2,
            exchange=mo_exchange,
        ),
    )
    amqp_system_2_exchange = f"{mo_exchange}_{queue_prefix_2}"

    callback_1_event = asyncio.Event()

    async def callback_1() -> None:
        callback_1_event.set()

    callback_2_event = asyncio.Event()

    async def callback_2() -> None:
        callback_2_event.set()

    routing_key = "foo"

    amqp_system_1.router.register(routing_key)(callback_1)
    amqp_system_2.router.register(routing_key)(callback_2)

    async with amqp_system_1, amqp_system_2:
        # Publishing to the OS2mo exchange to trigger both callbacks
        callback_1_event.clear()
        callback_2_event.clear()
        await amqp_system_1.publish_message(routing_key, "")
        await callback_1_event.wait()
        await callback_2_event.wait()

        # Publishing to the amqp_system_1 exchange to trigger one callback
        callback_1_event.clear()
        callback_2_event.clear()
        await amqp_system_1.publish_message(
            routing_key, "", exchange=amqp_system_1_exchange
        )
        await callback_1_event.wait()
        assert callback_2_event.is_set() is False

        # Publishing to the amqp_system_2 exchange to trigger one callback
        callback_1_event.clear()
        callback_2_event.clear()
        await amqp_system_1.publish_message(
            routing_key, "", exchange=amqp_system_2_exchange
        )
        await asyncio.sleep(0)
        await callback_2_event.wait()
        assert callback_1_event.is_set() is False
