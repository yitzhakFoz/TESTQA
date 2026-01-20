import time
from typing import List, Dict
import threading
import queue

class DataCollector:
    def __init__(self, config: Dict):
        self.config = config
        self.measurement_queue = queue.Queue()
        
    def collect_measurements(self, ammeter_type: str, test_id: str) -> List[Dict]:
        """
        איסוף מדידות מהאמפרמטר
        """
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
            measurement = self.measurement_queue.get()
            measurements.append({
                "timestamp": time.time(),
                "value": measurement,
                "test_id": test_id
            })
            
        sampling_thread.join()
        return measurements
        
    def _sampling_worker(self, ammeter_type: str, interval: float, total_measurements: int):
        """
        עובד שאוסף את המדידות בתהליכון נפרד
        """
        ammeter_config = self.config["ammeters"][ammeter_type]
        
        for _ in range(total_measurements):
            start_time = time.time()
            
            # קבלת מדידה מהאמפרמטר
            # כאן צריך להשתמש בקוד הקיים של האמפרמטרים
            measurement = self._get_measurement(ammeter_type, ammeter_config)
            
            self.measurement_queue.put(measurement)
            
            # המתנה עד לדגימה הבאה
            elapsed = time.time() - start_time
            if elapsed < interval:
                time.sleep(interval - elapsed)
                
    def _get_measurement(self, ammeter_type: str, config: Dict) -> float:
        """
        קבלת מדידה מהאמפרמטר הספציפי
        """
        # כאן צריך לממש את הקריאה לאמפרמטר הספציפי
        # using existing ammeter code
        pass 