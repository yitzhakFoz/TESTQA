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
    """
    Configuration class for measurement sampling parameters.

    The three parameters have distinct roles:
    - sampling_frequency_hz: Defines the sampling rate (how often to take measurements)
    - measurements_count: Defines how many measurements are needed for test completion
    - total_duration_seconds: SLA - maximum allowed time for test (timeout)
    """

    def __init__(self, measurements_count: int, total_duration_seconds: float,
                 sampling_frequency_hz: float):
        """
        Initialize sampling configuration.

        Args:
            measurements_count: Number of measurements to collect (completion criteria)
            total_duration_seconds: Maximum allowed time for test - SLA (timeout)
            sampling_frequency_hz: Sampling frequency in Hz (defines interval)

        Raises:
            ValueError: If configuration is invalid or test is impossible
        """
        self._validate_parameters(measurements_count, total_duration_seconds, sampling_frequency_hz)

        self.measurements_count = measurements_count
        self.total_duration_seconds = total_duration_seconds
        self.sampling_frequency_hz = sampling_frequency_hz

        # Interval is determined solely by frequency
        self.interval = 1.0 / sampling_frequency_hz

        # Calculate theoretical minimum time needed
        self.minimum_time_required = (measurements_count - 1) * self.interval

    def _validate_parameters(self, measurements_count: int, total_duration_seconds: float,
                            sampling_frequency_hz: float) -> None:
        """Validate that all parameters are valid and test is achievable."""
        if measurements_count <= 0:
            raise ValueError("measurements_count must be positive")
        if total_duration_seconds <= 0:
            raise ValueError("total_duration_seconds must be positive")
        if sampling_frequency_hz <= 0:
            raise ValueError("sampling_frequency_hz must be positive")

        # Check if test is theoretically possible
        interval = 1.0 / sampling_frequency_hz
        minimum_time = (measurements_count - 1) * interval
        if minimum_time > total_duration_seconds:
            raise ValueError(
                f"Impossible configuration: need minimum {minimum_time:.2f}s "
                f"to collect {measurements_count} measurements at {sampling_frequency_hz}Hz, "
                f"but SLA is only {total_duration_seconds}s"
            )

    @classmethod
    def from_config_dict(cls, config: Dict) -> 'SamplingConfig':
        """Create SamplingConfig from configuration dictionary."""
        sampling = config.get("testing", {}).get("sampling", {})
        return cls(
            measurements_count=sampling.get("measurements_count", 100),
            total_duration_seconds=sampling.get("total_duration_seconds", 60),
            sampling_frequency_hz=sampling.get("sampling_frequency_hz", 10)
        )


class CollectionResult:
    """Result of a measurement collection run."""

    def __init__(self, measurements: List[Dict], success: bool,
                 elapsed_time: float, expected_count: int, reason: str = ""):
        self.measurements = measurements
        self.success = success
        self.elapsed_time = elapsed_time
        self.expected_count = expected_count
        self.actual_count = len(measurements)
        self.reason = reason

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "elapsed_time": self.elapsed_time,
            "expected_count": self.expected_count,
            "actual_count": self.actual_count,
            "reason": self.reason
        }


class DataCollector:
    """
    Collects measurements from ammeter devices with configurable sampling.

    Configuration:
    - sampling_frequency_hz: Defines sampling rate (interval = 1/frequency)
    - measurements_count: Number of measurements needed for completion
    - total_duration_seconds: SLA - maximum time allowed (timeout)

    Success criteria:
    - Collected all required measurements within the SLA time limit

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
        self._sla_exceeded = threading.Event()

    def collect_measurements(self, ammeter_type: str, test_id: str) -> CollectionResult:
        """
        Collect measurements from the specified ammeter with SLA enforcement.

        Args:
            ammeter_type: Type of ammeter ('greenlee', 'entes', 'circutor')
            test_id: Unique identifier for this test run

        Returns:
            CollectionResult with measurements, success status, and timing info
        """
        measurements = []
        self._stop_event.clear()
        self._sla_exceeded.clear()

        # Clear any stale items from the queue
        while not self.measurement_queue.empty():
            try:
                self.measurement_queue.get_nowait()
            except queue.Empty:
                break

        total_measurements = self.sampling_config.measurements_count
        interval = self.sampling_config.interval
        sla_timeout = self.sampling_config.total_duration_seconds

        # Start the sampling worker thread
        sampling_thread = threading.Thread(
            target=self._sampling_worker,
            args=(ammeter_type, interval, total_measurements),
            daemon=True
        )

        test_start_time = time.perf_counter()
        sampling_thread.start()

        # Collect results from the queue with SLA monitoring
        for i in range(total_measurements):
            # Calculate remaining time until SLA timeout
            elapsed = time.perf_counter() - test_start_time
            remaining_time = sla_timeout - elapsed

            if remaining_time <= 0:
                # SLA exceeded - stop collection
                self._stop_event.set()
                self._sla_exceeded.set()
                break

            try:
                # Wait for measurement with timeout based on remaining SLA time
                queue_timeout = min(interval * 2 + 1, remaining_time)
                result = self.measurement_queue.get(timeout=queue_timeout)

                measurements.append({
                    "timestamp": result["timestamp"],
                    "relative_time": result["relative_time"],
                    "value": result["value"],
                    "measurement_index": i,
                    "test_id": test_id,
                    "ammeter_type": ammeter_type
                })
            except queue.Empty:
                # Check if it's due to SLA or other issue
                elapsed = time.perf_counter() - test_start_time
                if elapsed >= sla_timeout:
                    self._stop_event.set()
                    self._sla_exceeded.set()
                break

        # Final timing
        elapsed_time = time.perf_counter() - test_start_time

        # Wait for worker thread to finish
        sampling_thread.join(timeout=2.0)

        # Determine success/failure
        success = len(measurements) >= total_measurements and elapsed_time <= sla_timeout

        if success:
            reason = "Completed successfully"
        elif self._sla_exceeded.is_set():
            reason = f"SLA exceeded: collected {len(measurements)}/{total_measurements} in {elapsed_time:.2f}s (limit: {sla_timeout}s)"
        else:
            reason = f"Collection incomplete: {len(measurements)}/{total_measurements} measurements"

        return CollectionResult(
            measurements=measurements,
            success=success,
            elapsed_time=elapsed_time,
            expected_count=total_measurements,
            reason=reason
        )

    def _sampling_worker(self, ammeter_type: str, interval: float, total_measurements: int):
        """
        Worker thread that collects measurements with precise timing.

        Uses drift compensation to maintain accurate sampling intervals
        even when individual measurements take varying amounts of time.
        Respects SLA timeout - stops if SLA is exceeded.

        Args:
            ammeter_type: Type of ammeter to sample from
            interval: Time between measurements in seconds
            total_measurements: Total number of measurements to collect
        """
        ammeter_config = self.config["ammeters"].get(ammeter_type, {})
        sla_timeout = self.sampling_config.total_duration_seconds

        # Record absolute start time for drift compensation
        absolute_start = time.perf_counter()

        for i in range(total_measurements):
            # Check stop conditions
            if self._stop_event.is_set():
                break

            # Check SLA before taking measurement
            elapsed = time.perf_counter() - absolute_start
            if elapsed > sla_timeout:
                self._sla_exceeded.set()
                break

            # Calculate expected time for this measurement
            expected_time = absolute_start + (i * interval)

            # Get measurement with precise timestamp
            measurement_timestamp = time.time()
            measurement_perf_time = time.perf_counter()
            measurement_value = self._get_measurement(ammeter_type, ammeter_config)

            # Calculate relative time from test start
            relative_time = measurement_perf_time - absolute_start

            # Put result in queue
            self.measurement_queue.put({
                "timestamp": measurement_timestamp,
                "relative_time": relative_time,
                "value": measurement_value,
                "index": i
            })

            # Calculate drift-compensated sleep time
            current_time = time.perf_counter()
            next_expected_time = absolute_start + ((i + 1) * interval)
            sleep_duration = next_expected_time - current_time

            # Only sleep if we have time remaining and not the last measurement
            if sleep_duration > 0 and i < total_measurements - 1:
                # Use interruptible sleep to respond quickly to stop events
                self._stop_event.wait(timeout=sleep_duration)

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