import socket
from typing import Dict
from typing import Optional
from logging import Logger



class AmmeterMeasurementAPI:
    def __init__(self, logger):
        self.logger = logger
    """
    שכבה אחידה לתקשורת עם האמפרמטרים.
    המחלקה יודעת לקבל קונפיגורציה ספציפית ולבצע מדידה מול המכשיר.
    """

    def fetch_measurement(self, ammeter_type: str, ammeters_config: Dict) -> Optional[float]:
        """
        מבצע מדידה מול האמפרמטר.
        :param ammeter_type: שם האמפרמטר (למשל 'greenlee').
        :param ammeters_config: מילון ההגדרות הספציפי (מכיל 'port' ו-'command').
        """
        # 1. חילוץ נתונים מתוך הקונפיגורציה
        port = ammeters_config["port"]
        command = ammeters_config["command"]
        #המרה לביטים
        command = command.encode('utf-8')
        # 2. ביצוע התקשורת (TCP Socket)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                s.connect(('localhost', port))
                s.sendall(command)
                data = s.recv(1024)

                if not data:
                    self.logger.warning(f"Empty response from {ammeter_type} (port={port})")
                    return None

                measurement_value  = float(data.decode("utf-8").strip())
                self.logger.debug(f"Received {measurement_value } from {ammeter_type} (port={port})")
                # המרה ממחרוזת למספר עשרוני
                return measurement_value


        except ConnectionRefusedError:
            self.logger.error(f"Connection refused: {ammeter_type} (port={port})")
            return None
        except ValueError as e:
            self.logger.error(f"Invalid data from {ammeter_type} (port={port}): {e}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error with {ammeter_type} (port={port}): {e}")
            return None