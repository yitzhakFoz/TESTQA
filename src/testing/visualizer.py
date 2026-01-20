import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Dict
import os

class DataVisualizer:
    def __init__(self, config: Dict):
        self.config = config
        self.plot_types = config["analysis"]["visualization"]["plot_types"]
        
    def create_visualizations(self, measurements: List[Dict], test_id: str, ammeter_type: str):
        """
        יצירת ויזואליזציות שונות של הנתונים
        """
        values = [m["value"] for m in measurements]
        timestamps = [m["timestamp"] for m in measurements]
        
        # יצירת תיקיית התוצאות
        save_dir = f"{self.config['result_management']['save_path']}/plots/{test_id}"
        os.makedirs(save_dir, exist_ok=True)

        for plot_type in self.plot_types:
            plt.figure(figsize=(10, 6))
            
            if plot_type == "time_series":
                self._create_time_series(timestamps, values, ammeter_type)
            elif plot_type == "histogram":
                self._create_histogram(values, ammeter_type)
            elif plot_type == "box_plot":
                self._create_box_plot(values, ammeter_type)
            
            plt.savefig(f"{save_dir}/{plot_type}.png")
            plt.close()

    def _create_time_series(self, timestamps, values, ammeter_type):
        """
        יצירת גרף מדידות לאורך זמן
        """
        relative_times = [t - timestamps[0] for t in timestamps]
        plt.plot(relative_times, values, '-o', alpha=0.5)
        plt.title(f'Time Series Plot - {ammeter_type}')
        plt.xlabel('Time (seconds)')
        plt.ylabel('Current (A)')
        plt.grid(True)

    def _create_histogram(self, values, ammeter_type):
        """
        יצירת היסטוגרמה של המדידות
        """
        sns.histplot(values, kde=True)
        plt.title(f'Measurement Distribution - {ammeter_type}')
        plt.xlabel('Current (A)')
        plt.ylabel('Count')

    def _create_box_plot(self, values, ammeter_type):
        """
        יצירת תרשים קופסה של המדידות
        """
        plt.boxplot(values)
        plt.title(f'Box Plot - {ammeter_type}')
        plt.ylabel('Current (A)')
        plt.xticks([1], [ammeter_type]) 