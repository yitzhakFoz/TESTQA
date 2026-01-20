import logging
import os
from datetime import datetime

class TestLogger:
    def __init__(self, test_id: str):
        self.test_id = test_id
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """
        הגדרת הלוגר עם פורמט מותאם וכתיבה לקובץ
        """
        # יצירת תיקיית הלוגים
        log_dir = "results/logs"
        os.makedirs(log_dir, exist_ok=True)

        # הגדרת שם הקובץ עם תאריך ומזהה הבדיקה
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = f"{log_dir}/{timestamp}_{self.test_id}.log"

        # הגדרת הלוגר
        logger = logging.getLogger(f"test_{self.test_id}")
        logger.setLevel(logging.DEBUG)

        # הגדרת פורמט
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # הוספת handler לקובץ
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # הוספת handler למסוף
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        return logger

    def info(self, message: str):
        self.logger.info(message)

    def error(self, message: str):
        self.logger.error(message)

    def debug(self, message: str):
        self.logger.debug(message)

    def warning(self, message: str):
        self.logger.warning(message) 