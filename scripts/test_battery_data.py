#!/usr/bin/env python3
"""
Test script to see what battery data GAM returns without updating RT.
"""
import csv
import subprocess
import sys
import logging
from pathlib import Path

def collect_battery_data(gam_path='gam'):
    """Run GAM telemetry command and return CSV data."""
    cmd = [gam_path, 'print', 'crostelemetry', 'fields', 'batterystatusreport,batteryinfo,serialnumber']
    
    logging.info(f"Running GAM command: {' '.join(cmd)}")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        logging.error(f"GAM command failed: {proc.stderr.strip()}")
        sys.exit(proc.returncode)
    
    # Parse CSV output
    reader = csv.DictReader(proc.stdout.splitlines())
    data = list(reader)
    logging.info(f"Retrieved battery data for {len(data)} devices")
    return data

def analyze_battery_data(data):
    """Analyze and print sample battery data."""
    print(f"\nTotal devices: {len(data)}")
    
    if data:
        print("\nAvailable CSV columns:")
        for col in sorted(data[0].keys()):
            print(f"  - {col}")
        
        print("\nSample data from first 3 devices:")
        for i, row in enumerate(data[:3]):
            serial = row.get('serialNumber', 'N/A')
            print(f"\nDevice {i+1} (Serial: {serial}):")
            
            # Battery status report fields
            for key, value in row.items():
                if 'battery' in key.lower() and value:
                    print(f"  {key}: {value}")
            
            # Calculate health if possible
            full_charge = row.get('batteryStatusReport.0.fullChargeCapacity')
            design_capacity = row.get('batteryInfo.0.designCapacity')
            if full_charge and design_capacity:
                try:
                    health_pct = round((float(full_charge) / float(design_capacity)) * 100, 1)
                    print(f"  Calculated Health: {health_pct}%")
                except:
                    print(f"  Calculated Health: Error calculating")

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    gam_path = '/Users/jmartin/bin/gam7/gam'
    data = collect_battery_data(gam_path)
    analyze_battery_data(data)

if __name__ == '__main__':
    main()
