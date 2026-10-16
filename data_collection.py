"""Compatibility entry point for measured data collection with heuristic labels."""

from improved_data_collection import HeuristicDataCollector, collect_comprehensive_dataset

DataCollector = HeuristicDataCollector


if __name__ == '__main__':
    input('Verify the motor rig and configuration, then press ENTER to collect, or Ctrl+C to cancel: ')
    collect_comprehensive_dataset()
