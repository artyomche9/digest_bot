import sys
import slack
import asyncio
import digestbot.core.ui_processor.ReqParser as ReqParser
import digestbot.core.ui_processor.common
from digestbot.core.slack_api.Slacker import Slacker
from digestbot.core import PostgreSQLEngine
from digestbot.core.db.dbrequest.message import (
    upsert_messages,
    get_messages_without_links,
    update_message_links,
)
from digestbot.core.common import config, LoggerFactory
from datetime import datetime, timedelta
import signal
import time

_logger = LoggerFactory.create_logger(__name__, config.LOG_LEVEL)
slacker: Slacker
db_engine: PostgreSQLEngine


async def crawl_messages() -> None:
    while True:
        # get messages and insert them into database
        ch_info = await slacker.get_channels_list()
        for ch_id, ch_name in ch_info:
            _logger.info(f"Channel: {ch_name}")

            day_ago = datetime.now() - timedelta(days=1)
            messages = await slacker.get_channel_messages(ch_id, day_ago)
            if messages:
                await upsert_messages(db_engine=db_engine, messages=messages)
            _logger.info(str(messages))

        # update messages without permalinks
        req_status, empty_links_messages = await get_messages_without_links(
            db_engine=db_engine
        )
        if req_status and empty_links_messages:
            messages = await slacker.update_permalinks(messages=empty_links_messages)
            await update_message_links(db_engine=db_engine, messages=messages)
            _logger.debug(f"Updated permalinks for {len(messages)} messages.")

        # wait for next time
        await asyncio.sleep(config.CRAWL_INTERVAL)


@slack.RTMClient.run_on(event="message")
async def handle_message(**payload) -> None:
    """Preprocess messages"""
    global slacker

    if "data" not in payload:
        return None

    data = payload["data"]
    channel = data.get("channel", "")
    is_im = await slacker.is_direct_channel(channel) or False
    if config.PM_ONLY and not is_im:
        return None

    message = digestbot.core.ui_processor.common.UserRequest(
        text=data.get("text", ""),
        user=data.get("user", "") or data.get("username", ""),
        channel=channel,
        ts=data.get("ts", ""),
        is_im=is_im,
    )

    await ReqParser.process_message(
        message=message, bot_name=config.BOT_NAME, api=slacker, db_engine=db_engine
    )


if __name__ == "__main__":
    slacker = Slacker(
        user_token=config.SLACK_USER_TOKEN, bot_token=config.SLACK_BOT_TOKEN
    )

    loop = asyncio.get_event_loop()

    # connect to database
    db_engine = PostgreSQLEngine()
    connection_future = lambda: db_engine.connect_to_database(
        user=config.DB_USER,
        password=config.DB_PASS,
        database_name=config.DB_NAME,
        host=config.DB_HOST,
        port=config.DB_PORT,
    )

    connected = False
    for i in range(5):
        status = connection_future()
        loop.run_until_complete(status)
        if status != 0:
            connected = True
            break
        _logger.warning(f"Could not connect to database, attempt #{i}. Retrying...")
        time.sleep(3)

    if not connected:
        _logger.error("Could not connect to database. Exiting...")
        sys.exit(1)

    # Instantiate crawler timer with corresponding function
    crawler_task = loop.create_task(crawl_messages())

    # start Real-Time Listener and crawler
    overall_tasks = asyncio.gather(slacker.start_listening(), crawler_task)
    try:
        signal.signal(
            signal.SIGTERM, lambda *args: exec("raise KeyboardInterrupt")
        )  # correct exit handler
        loop.run_until_complete(overall_tasks)
    except KeyboardInterrupt:
        # TODO: graceful shutdown doesn't work, need to fix
        _logger.info("Received exit signal, exiting...")
        db_engine.close()
        sys.exit(0)
