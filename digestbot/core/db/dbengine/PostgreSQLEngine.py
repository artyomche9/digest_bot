import asyncpg

from digestbot.core.common import config, LoggerFactory
from digestbot.core.db.dbengine.utils.createdb import (
    create_database,
    check_exist_tables,
    create_tables,
)


class PostgreSQLEngine:
    def __init__(self):
        self.logger = LoggerFactory.create_logger("PostgreSQLEngine", config.LOG_LEVEL)
        self.engine: asyncpg.Connection

    async def connect_to_database(
        self,
        user: str,
        password: str,
        database_name: str,
        host: str = "localhost",
        port: int = None,
    ) -> bool:
        """
        Create connection to database

        :param user: user name
        :param password: password for username
        :param database_name: database name
        :param host: database server address
        :param port: port for database server
        :return: status execution: 0 - Fail, 1 - Success
        """
        self.logger.info(f"Try to connect to '{database_name}' database")
        try:
            self.engine = await asyncpg.create_pool(
                user=user,
                password=password,
                database=database_name,
                host=host,
                port=port,
            )
            status = 2
        except asyncpg.InvalidCatalogNameError:
            self.logger.info(
                f"Database '{database_name}' does not exist. It Will be created for user '{user}'"
            )
            status = await create_database(
                user=user,
                password=password,
                host=host,
                database_name=database_name,
                logger=self.logger,
                port=port,
            )
        except asyncpg.InvalidPasswordError:
            status = 0
            self.logger.error(f"Invalid password for user '{user}'")
        except asyncpg.UndefinedObjectError:
            status = 0
            self.logger.error(f"User '{user}' does not exist")

        if status == 1:
            status = await self.connect_to_database(
                user, password, database_name, host, port
            )

        if status == 2:
            async with self.engine.acquire() as connection:
                exist_tables = await check_exist_tables(connection)

            if not exist_tables:
                async with self.engine.acquire() as connection:
                    status = await create_tables(
                        connection=connection, logger=self.logger
                    )

        return status

    async def make_execute(self, request_string: str):
        """
        Execute request
        :param request_string: request string
        """
        async with self.engine.acquire() as connection:
            return await connection.execute(request_string)

    async def make_fetch_rows(self, request_string: str):
        """
        Fetch request
        :param request_string: request string
        """

        async with self.engine.acquire() as connection:
            return await connection.fetch(request_string)

    async def close(self):
        """
        Close all connection with database
        """
        await self.engine.close()