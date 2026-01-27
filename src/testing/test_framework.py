import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from ..utils.config import load_config
from .data_collector import DataCollector
from .result_analyzer import ResultAnalyzer
from .visualizer import DataVisualizer

class AmmeterTestFramework:
    def __init__(self, config_path: str = "config/test_config.yaml"):
        self.config = load_config(config_path)
        self.data_collector = DataCollector(self.config)
        self.result_analyzer = ResultAnalyzer(self.config)
        self.visualizer = DataVisualizer(self.config)
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

        self._save_results(results)
        return results

    def _save_results(self, results: Dict) -> None:
        """
        שמירת תוצאות הבדיקה
        """
        import json
        import os
        
        save_path = self.config["result_management"]["save_path"]
        filename = f"{save_path}/{results['metadata']['test_id']}.json"
        
        os.makedirs(save_path, exist_ok=True)
        with open(filename, 'w') as f:
            json.dump(results, f, indent=4) 