import time
from typing import List, Dict, Optional
import threading
import queue
import sys
import os

# Add the Ammeters directory to the path for importing client
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'Ammeters'))
from client import request_current_from_ammeter


class SamplingConfig:
    """Configuration class for measurement sampling parameters."""

    def __init__(self, measurements_count: int, total_duration_seconds: float,
                 sampling_frequency_hz: float):
        """
        Initialize sampling configuration.

        Args:
            measurements_count: Number of measurements to collect
            total_duration_seconds: Total test duration in seconds
            sampling_frequency_hz: Sampling frequency in Hz
        """
        self.measurements_count = measurements_count
        self.total_duration_seconds = total_duration_seconds
        self.sampling_frequency_hz = sampling_frequency_hz

        # Calculate effective interval based on configuration
        # Priority: If measurements_count is specified, calculate interval from duration
        # Otherwise use sampling_frequency_hz
        if measurements_count > 1 and total_duration_seconds > 0:
            # Spread measurements evenly across the total duration
            self.interval = total_duration_seconds / (measurements_count - 1)
        elif sampling_frequency_hz > 0:
            self.interval = 1.0 / sampling_frequency_hz
        else:
            self.interval = 1.0  # Default 1 second interval

    @classmethod
    def from_config_dict(cls, config: Dict) -> 'SamplingConfig':
        """Create SamplingConfig from configuration dictionary."""
        sampling = config.get("testing", {}).get("sampling", {})
        return cls(
            measurements_count=sampling.get("measurements_count", 100),
            total_duration_seconds=sampling.get("total_duration_seconds", 60),
            sampling_frequency_hz=sampling.get("sampling_frequency_hz", 10)
        )


class DataCollector:
    """
    Collects measurements from ammeter devices with configurable sampling.

    Supports configurable:
    - Number of measurements
    - Total test duration
    - Sampling frequency

    Ensures precise timing using drift compensation.
    """

    def __init__(self, config: Dict):
        """
        Initialize the DataCollector.

        Args:
            config: Configuration dictionary containing sampling and ammeter settings
        """
        self.config = config
        self.measurement_queue = queue.Queue()
        self.sampling_config = SamplingConfig.from_config_dict(config)
        self._stop_event = threading.Event()

    def collect_measurements(self, ammeter_type: str, test_id: str) -> List[Dict]:
        """
        Collect measurements from the specified ammeter.

        Args:
            ammeter_type: Type of ammeter ('greenlee', 'entes', 'circutor')
            test_id: Unique identifier for this test run

        Returns:
            List of measurement dictionaries with timestamp, value, and metadata
        """
        measurements = []
        self._stop_event.clear()

        total_measurements = self.sampling_config.measurements_count
        interval = self.sampling_config.interval

        # Start the sampling worker thread
        sampling_thread = threading.Thread(
            target=self._sampling_worker,
            args=(ammeter_type, interval, total_measurements),
            daemon=True
        )
        sampling_thread.start()

        test_start_time = time.time()

        # Collect results from the queue
        for i in range(total_measurements):
            try:
                # Use timeout to prevent infinite blocking
                result = self.measurement_queue.get(timeout=interval * 2 + 5)
                measurements.append({
                    "timestamp": result["timestamp"],
                    "relative_time": result["timestamp"] - test_start_time,
                    "value": result["value"],
                    "measurement_index": i,
                    "test_id": test_id,
                    "ammeter_type": ammeter_type
                })
            except queue.Empty:
                # If timeout, stop collection
                self._stop_event.set()
                break

        sampling_thread.join(timeout=5.0)
        return measurements

    def _sampling_worker(self, ammeter_type: str, interval: float, total_measurements: int):
        """
        Worker thread that collects measurements with precise timing.

        Uses drift compensation to maintain accurate sampling intervals
        even when individual measurements take varying amounts of time.

        Args:
            ammeter_type: Type of ammeter to sample from
            interval: Time between measurements in seconds
            total_measurements: Total number of measurements to collect
        """
        ammeter_config = self.config["ammeters"].get(ammeter_type, {})

        # Record absolute start time for drift compensation
        absolute_start = time.perf_counter()

        for i in range(total_measurements):
            if self._stop_event.is_set():
                break

            # Calculate expected time for this measurement
            expected_time = absolute_start + (i * interval)

            # Get measurement with precise timestamp
            measurement_timestamp = time.time()
            measurement_value = self._get_measurement(ammeter_type, ammeter_config)

            # Put result in queue
            self.measurement_queue.put({
                "timestamp": measurement_timestamp,
                "value": measurement_value,
                "index": i
            })

            # Calculate drift-compensated sleep time
            current_time = time.perf_counter()
            next_expected_time = absolute_start + ((i + 1) * interval)
            sleep_duration = next_expected_time - current_time

            # Only sleep if we have time remaining and not the last measurement
            if sleep_duration > 0 and i < total_measurements - 1:
                time.sleep(sleep_duration)

    def _get_measurement(self, ammeter_type: str, config: Dict) -> Optional[float]:
        """
        Get a measurement from the specified ammeter.

        Args:
            ammeter_type: Type of ammeter
            config: Ammeter-specific configuration

        Returns:
            Measurement value as float, or None if measurement failed
        """
        port = config.get("port")
        command = config.get("command", "")

        if port is None:
            return None

        # Request measurement from ammeter server
        value = request_current_from_ammeter(
            port=port,
            command=command.encode('utf-8'),
            timeout=2.0
        )

        return value

    def stop(self):
        """Stop any ongoing measurement collection."""
        self._stop_event.set()