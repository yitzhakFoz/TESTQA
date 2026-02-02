import time
from typing import List, Dict
import threading
import queue

from src.ammeters.ammeter_measurement_api import AmmeterMeasurementAPI


class DataCollector:
    def __init__(self, config: Dict, logger):
        self.config = config
        self.measurement_queue = queue.Queue()
        self.ammeter_measurement_api = AmmeterMeasurementAPI(logger)
        self.logger = logger


    def collect_measurements(self, ammeter_type: str, test_id: str) -> List[Dict]:
        """
        איסוף מדידות מהאמפרמטר
        """
        self.logger.info(f"Starting data collection for {ammeter_type}")

        measurements = []
        sampling_config = self.config["testing"]["sampling"]

        # חישוב מרווח הזמן בין דגימות
        interval = 1.0 / sampling_config["sampling_frequency_hz"]
        total_measurements = sampling_config["measurements_count"]

        # הפעלת תהליכון נפרד לדגימה
        sampling_thread = threading.Thread(
            target=self._sampling_worker,
            args=(ammeter_type, interval, total_measurements)
        )
        sampling_thread.start()

        # איסוף התוצאות
        for _ in range(total_measurements):
            # שינוי: שליפת זוג נתונים (ערך + זמן)
            val, actual_ts = self.measurement_queue.get()

            measurements.append({
                "timestamp": actual_ts,  # שימוש בזמן המקורי מה-Worker
                "value": val,
                "test_id": test_id
            })

        sampling_thread.join()

        return measurements

    def _sampling_worker(self, ammeter_type: str, interval: float, total_measurements: int):
        ammeter_config = self.config["ammeters"][ammeter_type]

        start = time.perf_counter()  # זמן תחילת הדגימה הכוללת

        for i in range(total_measurements):
            target_time = start + i * interval  # זמן יעד לדגימה מספר i

            now = time.perf_counter()
            sleep_time = target_time - now
            if sleep_time > 0:
                time.sleep(sleep_time)

            measurement = self._get_measurement(ammeter_type, ammeter_config)
            measure_ts = time.perf_counter()
            self.measurement_queue.put((measurement, measure_ts))  #tuple

    def _get_measurement(self, ammeter_type: str, config: Dict) -> float:
        """
        קבלת מדידה מהאמפרמטר הספציפי
        """
        # כאן צריך לממש את הקריאה לאמפרמטר הספציפי
        # using existing ammeter code
        return self.ammeter_measurement_api.fetch_measurement(ammeter_type, config)
