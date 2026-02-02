import yaml
from typing import Dict


def load_config(config_path: str) -> Dict:
    """
    טעינת קובץ הקונפיגורציה
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)


        validate_required_sections(config)
        resolve_sampling_config(config)
        return config

def validate_required_sections(config: Dict) -> None:
    """
      וידוא תקינות הקונפיגורציה
      """
    required_sections = ['testing', 'ammeters', 'analysis', 'result_management']

    # בדיקת קיום כל החלקים הנדרשים
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required section: {section}")


def resolve_sampling_config(config: Dict) -> bool:

    sampling = config['testing']['sampling']

    measurements_count = sampling.get('measurements_count')
    sampling_frequency_hz = sampling.get('sampling_frequency_hz')
    total_duration_seconds = sampling.get('total_duration_seconds')

    # מוודא שיש 3 שהם לא ריקים
    provided_fields_count = sum(
        value is not None
        for value in (
            measurements_count,
            sampling_frequency_hz,
            total_duration_seconds,
        )
    )
    if provided_fields_count < 2:
        raise ValueError(
            "Sampling config must provide at least 2 of: "
            "measurements_count, sampling_frequency_hz, total_duration_seconds"
        )

    if measurements_count is not None:
        if not isinstance(measurements_count, int) or measurements_count <= 0:
            raise ValueError("measurements_count must be a positive integer")

    if sampling_frequency_hz is not None:
        if not isinstance(sampling_frequency_hz, (int, float)) or sampling_frequency_hz <= 0:
            raise ValueError("sampling_frequency_hz must be a positive number")
        sampling_frequency_hz = float(sampling_frequency_hz)

    if total_duration_seconds is not None:
        if not isinstance(total_duration_seconds, (int, float)) or total_duration_seconds <= 0:
            raise ValueError("total_duration_seconds must be a positive number")
        total_duration_seconds = float(total_duration_seconds)


    tolerance = 1e-3

    # 2 מתוך 3 -> מחשבים את החסר
    if provided_fields_count == 2:
        if measurements_count is None:
            expected_count = total_duration_seconds * sampling_frequency_hz
            rounded_count = int(round(expected_count))
            if abs(expected_count - rounded_count) > tolerance:
                raise ValueError("Duration * Frequency must result in an integer measurements_count")
            measurements_count = rounded_count

        elif sampling_frequency_hz is None:
            sampling_frequency_hz = measurements_count / total_duration_seconds

        else:  # total_duration_seconds is None
            total_duration_seconds = measurements_count / sampling_frequency_hz

    # יש 3 -> בודקים שאין סתירה
    else:
        expected_count = total_duration_seconds * sampling_frequency_hz
        if abs(expected_count - measurements_count) > tolerance:
            raise ValueError(
                f"Sampling config conflict: total_duration_seconds({total_duration_seconds}) * "
                f"sampling_frequency_hz({sampling_frequency_hz}) = {expected_count}, "
                f"but measurements_count = {measurements_count}"
            )

    # בסוף: כותבים חזרה לקונפיג (כדי שכל המערכת תקבל 3 ערכים מלאים)
    sampling["measurements_count"] = int(measurements_count)
    sampling["sampling_frequency_hz"] = float(sampling_frequency_hz)
    sampling["total_duration_seconds"] = float(total_duration_seconds)

    return True
