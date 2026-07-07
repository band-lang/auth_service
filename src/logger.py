import logging
import structlog
import sys
from typing import Any
from pathlib import Path


_configured = False


def setup_logger(name: str = "petushokgram") -> Any:
    global _configured

    if _configured is False:
        logger = logging.basicConfig(
            #Форматирование сообщений
            format="%(message)s",
            #Куда будут выводиться логи(консоль)
            stream=sys.stdout,
            #Уровень
            level=logging.DEBUG
        )

        Path("logs").mkdir(exist_ok=True)
        file_handler = logging.FileHandler("logs/app.log")

        #Добавили хендлер для написания логов в указанный файл
        file_handler = logging.FileHandler("logs/app.log")
        #Форматирование сообщений
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        #Получили логгер по его имени и добавили хендлер
        logging.getLogger(name).addHandler(file_handler)
        

        structlog.configure(
            processors=[
                #Добавляет в сообщение в логах его тип: info, debug и т.п.
                structlog.stdlib.add_log_level,

                #Добавляет в сообщение timestamp с временем в формате iso
                #2026-01-15T14:30:02.123456

                structlog.processors.TimeStamper(fmt="iso"),

                #Добавляет поля filename и lineno. В filename - в каком
                #Файле вызван logger, lineno - на какой строке.
                structlog.processors.CallsiteParameterAdder(
                    {
                        structlog.processors.CallsiteParameter.FILENAME,
                        structlog.processors.CallsiteParameter.LINENO
                    }
                ),
                #Форматирует сообщение - делает его цветным и читаемым.
                structlog.dev.ConsoleRenderer(),
            ],
            #Указываю structlog'у использовать стандартный логгер, а не
            #Аналог из structlog. Иначе structlog может начать писать логи в свой поток
            #И они могут не дойти до оригинального logger'а.
            wrapper_class=structlog.stdlib.BoundLogger,
            
            #Когда structlogger запрашивает logger (structlogger.get_logger(name))
            #Отдавай стандартный logger.Logger(name), а не structlog'овский аналог.
            logger_factory=structlog.stdlib.LoggerFactory(),

            #Кешировать логгер после его первого создания
            cache_logger_on_first_use=True
        )

        _configured = True

    return structlog.get_logger(name)


logger = setup_logger()