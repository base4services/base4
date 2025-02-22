import os
import redis
import asyncio
import logging

# BOT_TOKEN = os.getenv('TELEGRAM_INFO_BOT_API_TOKEN')
# BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

REDIS_HOST = os.getenv('DB_REDIS_HOST', 'localhost')
REDIS_PORT = os.getenv('DB_REDIS_PORT', 6379)

TELEGRAM_ERRORS_REDIS_CHANNEL_TIMEOUT = os.getenv('TELEGRAM_ERRORS_REDIS_CHANNEL_TIMEOUT', 60)

class Observer:

    def __init__(self,channel, logger_name, timeout=TELEGRAM_ERRORS_REDIS_CHANNEL_TIMEOUT, redis_decode_responses=True):
        self.channel = channel
        self.timeout = timeout
        self.log = logging.getLogger(logger_name)
        self.redis_client = redis.Redis(REDIS_HOST, REDIS_PORT, decode_responses=redis_decode_responses)

    async def handle_message(self, msg: str):
        raise NameError("NOT IMPLEMENTED")


    async def run(self):
        self.log.info(f'Starting {self.channel} observer')
        print(f'Starting {self.channel} observer logger={self.log}')

        while True:
            self.log.info('waiting for task')
            message = self.redis_client.brpop([self.channel], self.timeout)
            if not message:
                continue

            try:
                await self.handle_message(message[1])
                ...
            except Exception as e:
                self.log.error(f'Message handling error: {e}')
                self.log.error(f'Message with error: {message}')


async def main():
    observer = Observer()
    await observer.run()

if __name__ == "__main__":
    asyncio.run(main())
