import yaml
from typing import Dict

def load_config(config_path: str) -> Dict:
    """
    טעינת קובץ הקונפיגורציה
    """
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def validate_config(config: Dict) -> bool:
    """
    וידוא תקינות הקונפיגורציה
    """
    required_sections = ['testing', 'ammeters', 'analysis', 'result_management']
    
    # בדיקת קיום כל החלקים הנדרשים
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required section: {section}")
    
    # בדיקת הגדרות הדגימה
    sampling = config['testing']['sampling']
    if sampling.get('measurements_count', 0) <= 0:
        raise ValueError("measurements_count must be positive")
    if sampling.get('sampling_frequency_hz', 0) <= 0:
        raise ValueError("sampling_frequency_hz must be positive")
    if sampling.get('total_duration_seconds', 0) <= 0:
        raise ValueError("total_duration_seconds must be positive")

    # בדיקה שהקונפיגורציה אפשרית - הזמן המינימלי לא חורג מה-SLA
    measurements_count = sampling['measurements_count']
    sampling_frequency_hz = sampling['sampling_frequency_hz']
    total_duration_seconds = sampling['total_duration_seconds']

    interval = 1.0 / sampling_frequency_hz
    minimum_time = (measurements_count - 1) * interval
    if minimum_time > total_duration_seconds:
        raise ValueError(
            f"Impossible configuration: need minimum {minimum_time:.2f}s "
            f"to collect {measurements_count} measurements at {sampling_frequency_hz}Hz, "
            f"but SLA is only {total_duration_seconds}s"
        )

    return True