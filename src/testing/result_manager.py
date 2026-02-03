import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class TestResultMetadata:
    """Metadata for a test result."""
    test_id: str
    timestamp: str
    ammeter_type: str
    test_duration_sla: float
    actual_duration: float
    sampling_frequency: float
    measurements_expected: int
    measurements_collected: int
    success: bool

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> 'TestResultMetadata':
        return cls(
            test_id=data.get("test_id", ""),
            timestamp=data.get("timestamp", ""),
            ammeter_type=data.get("ammeter_type", ""),
            test_duration_sla=data.get("test_duration_sla", 0),
            actual_duration=data.get("actual_duration", 0),
            sampling_frequency=data.get("sampling_frequency", 0),
            measurements_expected=data.get("measurements_expected", 0),
            measurements_collected=data.get("measurements_collected", 0),
            success=data.get("success", False)
        )


class ResultManager:
    """
    Manages test result archiving, retrieval, and comparison.

    Features:
    - Unique identification for each test run
    - Metadata storage with index for quick lookups
    - Easy retrieval by test_id, date range, ammeter_type, or success status
    - Comparison of historical results
    """

    INDEX_FILENAME = "results_index.json"

    def __init__(self, config: Dict):
        """
        Initialize the ResultManager.

        Args:
            config: Configuration dictionary with result_management settings
        """
        self.config = config
        self.save_path = Path(config["result_management"]["save_path"])
        self.save_path.mkdir(parents=True, exist_ok=True)
        self._index = self._load_index()

    def _get_index_path(self) -> Path:
        """Get the path to the index file."""
        return self.save_path / self.INDEX_FILENAME

    def _load_index(self) -> Dict[str, Dict]:
        """Load or create the results index."""
        index_path = self._get_index_path()
        if index_path.exists():
            with open(index_path, 'r') as f:
                return json.load(f)
        return {}

    def _save_index(self) -> None:
        """Save the results index to disk."""
        index_path = self._get_index_path()
        with open(index_path, 'w') as f:
            json.dump(self._index, f, indent=2)

    def _generate_filename(self, test_id: str, timestamp: str) -> str:
        """Generate a unique filename for a test result."""
        date_part = timestamp[:10].replace("-", "")
        return f"{date_part}_{test_id}.json"

    def save(self, results: Dict) -> str:
        """
        Save test results to disk and update the index.

        Args:
            results: Complete test results dictionary

        Returns:
            Path to the saved file
        """
        metadata = results.get("metadata", {})
        test_id = metadata.get("test_id", "")
        timestamp = metadata.get("timestamp", datetime.now().isoformat())

        filename = self._generate_filename(test_id, timestamp)
        filepath = self.save_path / filename

        with open(filepath, 'w') as f:
            json.dump(results, f, indent=4)

        self._index[test_id] = {
            "filename": filename,
            "timestamp": timestamp,
            "ammeter_type": metadata.get("ammeter_type", ""),
            "success": results.get("success", False),
            "actual_duration": metadata.get("actual_duration", 0),
            "measurements_collected": metadata.get("measurements_collected", 0)
        }
        self._save_index()

        return str(filepath)

    def load(self, test_id: str) -> Optional[Dict]:
        """
        Load a test result by its ID.

        Args:
            test_id: Unique test identifier

        Returns:
            Test results dictionary or None if not found
        """
        if test_id not in self._index:
            return None

        filename = self._index[test_id]["filename"]
        filepath = self.save_path / filename

        if not filepath.exists():
            return None

        with open(filepath, 'r') as f:
            return json.load(f)

    def list_all(self) -> List[Dict]:
        """
        List all test results metadata.

        Returns:
            List of index entries sorted by timestamp (newest first)
        """
        results = [
            {"test_id": test_id, **data}
            for test_id, data in self._index.items()
        ]
        return sorted(results, key=lambda x: x["timestamp"], reverse=True)

    def find_by_ammeter(self, ammeter_type: str) -> List[Dict]:
        """
        Find all test results for a specific ammeter type.

        Args:
            ammeter_type: Type of ammeter to filter by

        Returns:
            List of matching index entries
        """
        return [
            {"test_id": test_id, **data}
            for test_id, data in self._index.items()
            if data.get("ammeter_type") == ammeter_type
        ]

    def find_by_date_range(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Find test results within a date range.

        Args:
            start_date: Start date in ISO format (YYYY-MM-DD)
            end_date: End date in ISO format (YYYY-MM-DD)

        Returns:
            List of matching index entries
        """
        results = []
        for test_id, data in self._index.items():
            timestamp = data.get("timestamp", "")[:10]
            if start_date <= timestamp <= end_date:
                results.append({"test_id": test_id, **data})
        return sorted(results, key=lambda x: x["timestamp"], reverse=True)

    def find_by_success(self, success: bool) -> List[Dict]:
        """
        Find test results by success status.

        Args:
            success: True for successful tests, False for failed

        Returns:
            List of matching index entries
        """
        return [
            {"test_id": test_id, **data}
            for test_id, data in self._index.items()
            if data.get("success") == success
        ]

    def get_latest(self, ammeter_type: Optional[str] = None) -> Optional[Dict]:
        """
        Get the most recent test result.

        Args:
            ammeter_type: Optional filter by ammeter type

        Returns:
            Most recent test result or None
        """
        if ammeter_type:
            results = self.find_by_ammeter(ammeter_type)
        else:
            results = self.list_all()

        if not results:
            return None

        return self.load(results[0]["test_id"])

    def compare(self, test_ids: List[str]) -> Dict:
        """
        Compare multiple test results.

        Args:
            test_ids: List of test IDs to compare

        Returns:
            Comparison dictionary with analysis results side by side
        """
        comparison = {
            "tests": [],
            "analysis_comparison": {},
            "summary": {}
        }

        analyses = {}
        for test_id in test_ids:
            result = self.load(test_id)
            if result:
                comparison["tests"].append({
                    "test_id": test_id,
                    "metadata": result.get("metadata", {}),
                    "success": result.get("success", False)
                })
                analyses[test_id] = result.get("analysis", {})

        if not analyses:
            return comparison

        all_metrics = set()
        for analysis in analyses.values():
            all_metrics.update(analysis.keys())

        for metric in all_metrics:
            comparison["analysis_comparison"][metric] = {
                test_id: analysis.get(metric)
                for test_id, analysis in analyses.items()
            }

        numeric_metrics = ["mean", "median", "std_dev", "min", "max"]
        for metric in numeric_metrics:
            if metric in comparison["analysis_comparison"]:
                values = [
                    v for v in comparison["analysis_comparison"][metric].values()
                    if v is not None and isinstance(v, (int, float))
                ]
                if values:
                    comparison["summary"][metric] = {
                        "min": min(values),
                        "max": max(values),
                        "spread": max(values) - min(values)
                    }

        return comparison

    def delete(self, test_id: str) -> bool:
        """
        Delete a test result.

        Args:
            test_id: Test ID to delete

        Returns:
            True if deleted, False if not found
        """
        if test_id not in self._index:
            return False

        filename = self._index[test_id]["filename"]
        filepath = self.save_path / filename

        if filepath.exists():
            filepath.unlink()

        del self._index[test_id]
        self._save_index()
        return True

    def get_statistics(self) -> Dict:
        """
        Get overall statistics about stored results.

        Returns:
            Statistics dictionary
        """
        total = len(self._index)
        if total == 0:
            return {"total_tests": 0}

        successful = sum(1 for d in self._index.values() if d.get("success"))
        by_ammeter = {}
        for data in self._index.values():
            ammeter = data.get("ammeter_type", "unknown")
            by_ammeter[ammeter] = by_ammeter.get(ammeter, 0) + 1

        return {
            "total_tests": total,
            "successful_tests": successful,
            "failed_tests": total - successful,
            "success_rate": successful / total if total > 0 else 0,
            "by_ammeter_type": by_ammeter
        }
