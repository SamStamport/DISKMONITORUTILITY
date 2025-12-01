import psutil
import time
from collections import defaultdict

def monitor_disk_activity(duration=120, interval=1):
    """Monitor disk activity and summarize top users."""
    print(f"Monitoring disk activity for {duration} seconds...\n")
    
    process_io = defaultdict(lambda: {'read': 0, 'write': 0})
    
    start_time = time.time()
    samples = 0
    
    while time.time() - start_time < duration:
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                io = proc.io_counters()
                pid = proc.info['pid']
                name = proc.info['name']
                
                # Store cumulative IO
                process_io[name]['read'] += io.read_bytes
                process_io[name]['write'] += io.write_bytes
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        samples += 1
        time.sleep(interval)
    
    # Calculate totals and sort
    process_totals = []
    for name, io in process_io.items():
        total = io['read'] + io['write']
        process_totals.append({
            'name': name,
            'read_mb': io['read'] / (1024 * 1024),
            'write_mb': io['write'] / (1024 * 1024),
            'total_mb': total / (1024 * 1024)
        })
    
    process_totals.sort(key=lambda x: x['total_mb'], reverse=True)
    
    # Display results
    print(f"\n{'Process':<30} {'Read (MB)':<15} {'Write (MB)':<15} {'Total (MB)':<15}")
    print("=" * 75)
    
    for proc in process_totals[:15]:  # Top 15
        print(f"{proc['name']:<30} {proc['read_mb']:<15.2f} {proc['write_mb']:<15.2f} {proc['total_mb']:<15.2f}")
    
    print(f"\nMonitored for {duration} seconds ({samples} samples)")

if __name__ == "__main__":
    # Install psutil first: pip install psutil
    monitor_disk_activity(duration=120, interval=1)