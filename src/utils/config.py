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
    if sampling['measurements_count'] <= 0:
        raise ValueError("measurements_count must be positive")
    if sampling['sampling_frequency_hz'] <= 0:
        raise ValueError("sampling_frequency_hz must be positive")
    
    return True 