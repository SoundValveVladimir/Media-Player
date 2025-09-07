import logging
import sys

class PrintLogger:
    """Класс для перенаправления stdout и stderr в логгер."""
    def __init__(self, logger, log_level=logging.INFO):
        self.logger = logger
        self.log_level = log_level

    def write(self, message):
        # Убираем пустые строки
        if message.strip():
            self.logger.log(self.log_level, message.strip())

    def flush(self):
        # Нужен для совместимости с потоками
        pass

def setup_logging(log_file='application.log'):
    """
    Настраивает логирование для приложения.
    Перенаправляет stdout и stderr в лог-файл.
    """
    logging.basicConfig(
        filename=log_file,
        level=logging.DEBUG,  # Уровень логирования
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    logger = logging.getLogger()

    # Перенаправляем stdout и stderr
    sys.stdout = PrintLogger(logger, logging.INFO)
    sys.stderr = PrintLogger(logger, logging.ERROR)
