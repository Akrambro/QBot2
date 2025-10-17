import os
import sys
import time
import signal
import subprocess
import uvicorn
from server import app

def kill_port_processes(port=8000):
    """Kill any processes using the specified port (Windows & Unix compatible)"""
    try:
        print(f"🔍 Checking for processes using port {port}...")
        current_pid = os.getpid()
        
        if os.name == 'nt':  # Windows
            try:
                # Use netstat to find processes using the port
                result = subprocess.run(
                    ["netstat", "-ano"], 
                    capture_output=True, 
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                )
                
                if result.returncode == 0:
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if f":{port}" in line and "LISTENING" in line:
                            # Extract PID (last column)
                            parts = line.strip().split()
                            if parts:
                                try:
                                    pid = int(parts[-1])
                                    if pid != current_pid and pid != 0:
                                        # Kill the process using taskkill
                                        kill_result = subprocess.run(
                                            ["taskkill", "/PID", str(pid), "/F"],
                                            capture_output=True,
                                            text=True,
                                            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
                                        )
                                        if kill_result.returncode == 0:
                                            print(f"✅ Killed process {pid} using port {port}")
                                        else:
                                            print(f"⚠️ Failed to kill process {pid}: {kill_result.stderr}")
                                except (ValueError, IndexError):
                                    continue
            except Exception as e:
                print(f"⚠️ Windows port cleanup error: {e}")
        
        else:  # Unix/Linux/Mac
            try:
                # Use lsof for Unix systems
                result = subprocess.run(["lsof", "-ti", f":{port}"], capture_output=True, text=True)
                if result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid and pid.isdigit():
                            pid_int = int(pid)
                            if pid_int != current_pid:
                                try:
                                    os.kill(pid_int, signal.SIGTERM)
                                    time.sleep(0.5)
                                    os.kill(pid_int, signal.SIGKILL)
                                    print(f"✅ Killed process {pid} using port {port}")
                                except ProcessLookupError:
                                    pass  # Process already dead
                                except Exception as e:
                                    print(f"⚠️ Failed to kill process {pid}: {e}")
            except FileNotFoundError:
                # Try fuser as fallback
                try:
                    subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True, stderr=subprocess.DEVNULL)
                except FileNotFoundError:
                    print("⚠️ Neither lsof nor fuser available on this system")
        
        # Wait for cleanup
        time.sleep(1)
        print(f"🧹 Port {port} cleanup completed")
        
    except Exception as e:
        print(f"⚠️ Port cleanup warning: {e}")

def start_server():
    """Start the server with automatic port cleanup"""
    port = 8000
    
    try:
        # Clean up port before starting
        kill_port_processes(port)
        
        print(f"🚀 Starting server on port {port}...")
        uvicorn.run(app, host="0.0.0.0", port=port)
        
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {port} is still in use. Try running: lsof -ti:{port} | xargs kill -9")
            sys.exit(1)
        else:
            print(f"💥 Server error: {e}")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    start_server()
