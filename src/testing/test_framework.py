import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from ..utils.config import load_config
from .data_collector import DataCollector
from .result_analyzer import ResultAnalyzer
from .visualizer import DataVisualizer
from .result_manager import ResultManager


class AmmeterTestFramework:
    def __init__(self, config_path: str = "config/test_config.yaml"):
        self.config = load_config(config_path)
        self.data_collector = DataCollector(self.config)
        self.result_analyzer = ResultAnalyzer(self.config)
        self.visualizer = DataVisualizer(self.config)
        self.result_manager = ResultManager(self.config)
        self.test_id = str(uuid.uuid4())
        
    def run_test(self, ammeter_type: str) -> Dict:
        """
        הרצת בדיקה מלאה על אמפרמטר ספציפי
        """
        # איסוף נתונים
        collection_result = self.data_collector.collect_measurements(
            ammeter_type=ammeter_type,
            test_id=self.test_id
        )

        measurements = collection_result.measurements

        # ניתוח התוצאות
        analysis_results = self.result_analyzer.analyze(measurements)

        # יצירת ויזואליזציה
        if self.config["analysis"]["visualization"]["enabled"]:
            self.visualizer.create_visualizations(
                measurements,
                test_id=self.test_id,
                ammeter_type=ammeter_type
            )

        # הכנת המטא-דאטה
        metadata = {
            "test_id": self.test_id,
            "timestamp": datetime.now().isoformat(),
            "ammeter_type": ammeter_type,
            "test_duration_sla": self.config["testing"]["sampling"]["total_duration_seconds"],
            "actual_duration": collection_result.elapsed_time,
            "sampling_frequency": self.config["testing"]["sampling"]["sampling_frequency_hz"],
            "measurements_expected": collection_result.expected_count,
            "measurements_collected": collection_result.actual_count
        }

        # שמירת התוצאות
        results = {
            "metadata": metadata,
            "success": collection_result.success,
            "collection_status": collection_result.to_dict(),
            "measurements": measurements,
            "analysis": analysis_results
        }

        self.result_manager.save(results)
        return results

    def get_result(self, test_id: str) -> Optional[Dict]:
        """
        אחזור תוצאות בדיקה לפי מזהה
        """
        return self.result_manager.load(test_id)

    def list_results(self, ammeter_type: Optional[str] = None) -> List[Dict]:
        """
        רשימת כל תוצאות הבדיקות
        """
        if ammeter_type:
            return self.result_manager.find_by_ammeter(ammeter_type)
        return self.result_manager.list_all()

    def compare_results(self, test_ids: List[str]) -> Dict:
        """
        השוואה בין מספר תוצאות בדיקה
        """
        return self.result_manager.compare(test_ids)

    def get_latest_result(self, ammeter_type: Optional[str] = None) -> Optional[Dict]:
        """
        אחזור התוצאה האחרונה
        """
        return self.result_manager.get_latest(ammeter_type)

    def get_results_statistics(self) -> Dict:
        """
        סטטיסטיקות על כל הבדיקות
        """
        return self.result_manager.get_statistics()