import multiprocessing
import time
import os
import sys
import signal
import threading
import itertools
import random

# ---------------------------
# Configuration / defaults
# ---------------------------
DEFAULT_PC_AMOUNT = 16384      # interpreted as the maximum "PC Amount" for the ramp
DEFAULT_SPEED = 2             # seconds between doublings
DEFAULT_MEM_MB = 128
DEFAULT_USE_BUSY_LOOP = True  # if False, CPU worker will sleep intermittently to reduce heat

# Global state
processes = []
terminate_flag = multiprocessing.Event()

# ---------------------------
# Worker definitions
# ---------------------------
def cpu_worker_throttle(load_percent=100):
    slice_time = 0.1
    busy_time = slice_time * load_percent / 100.0
    while not terminate_flag.is_set():
        t0 = time.time()
        while (time.time() - t0) < busy_time:
            pass
        rem = slice_time - (time.time() - t0)
        if rem > 0:
            time.sleep(rem)

def cpu_worker_busy():
    while not terminate_flag.is_set():
        pass

def memory_worker(size_in_mb=10):
    try:
        data = ['x' * 1024 * 1024] * int(size_in_mb)
        while not terminate_flag.is_set():
            time.sleep(0.5)
    except MemoryError:
        return

# ---------------------------
# Process control helpers
# ---------------------------
def spawn_cpu_worker(use_busy, load_percent=100):
    if use_busy or load_percent == 100:
        p = multiprocessing.Process(target=cpu_worker_busy)
    else:
        p = multiprocessing.Process(target=cpu_worker_throttle, args=(load_percent,))
    p.start()
    return p

def spawn_mem_worker(size_mb):
    p = multiprocessing.Process(target=memory_worker, args=(size_mb,))
    p.start()
    return p

def terminate_all():
    terminate_flag.set()
    for p in processes:
        try:
            if p.is_alive():
                p.terminate()
        except Exception:
            pass
    for p in processes:
        try:
            p.join(timeout=1)
        except Exception:
            pass

def signal_handler(sig, frame):
    print("\n[!] Received interrupt. Terminating workers...")
    terminate_all()
    print("[*] Clean exit.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
if hasattr(signal, "SIGTERM"):
    signal.signal(signal.SIGTERM, signal_handler)

# ---------------------------
# Fake "hacking" UI bits (no worker counts displayed)
# ---------------------------
HACK_BANNER = r"""
  _    _            _               _    _        _   _             
 | |  | |          | |             | |  | |      | | (_)            
 | |__| | __ _  ___| | ____ _ _ __ | |__| | ___  | |_ _  ___  _ __  
 |  __  |/ _` |/ __| |/ / _` | '_ \|  __  |/ _ \ | __| |/ _ \| '_ \ 
 | |  | | (_| | (__|   < (_| | | | | |  | |  __/ | |_| | (_) | | | |
 |_|  |_|\__,_|\___|_|\_\__,_|_| |_|_|  |_|\___|  \__|_|\___/|_| |_|
                                                                    
            HACKNET | ESTABLISHING PROCESS GRID ...
"""

HACK_MESSAGES = [
    "scanning ports...",
    "probing kernel modules...",
    "enumerating processors...",
    "allocating vectors...",
    "synchronizing clocks...",
    "injecting synthetic load...",
    "hammering memory pages...",
    "amplifying threads...",
    "raising entropy...",
    "warming CPU cores..."
]

def spinning_cursor():
    for ch in itertools.cycle('|/-\\'):
        yield ch

def fake_hack_console(stop_event, area, speed, mem_mb, use_busy, dry_run, load_percent):
    spinner = spinning_cursor()
    start_time = time.time()
    msg_cycle = itertools.cycle(HACK_MESSAGES)

    # This console intentionally does NOT display worker counts.
    while not stop_event.is_set():
        uptime = int(time.time() - start_time)
        msg = next(msg_cycle)
        cursor = next(spinner)
        # DO NOT include numbers of workers in this line
        line = f"{cursor} {msg}  uptime={uptime}s  targeting_area={area}  speed={speed}s"
        print("\r" + line + (" " * 20), end="", flush=True)

        if random.random() < 0.07:
            # fake "node found" lines that avoid giving counts
            ip = ".".join(str(random.randint(1, 254)) for _ in range(4))
            print(f"\n[FOUND] node@{ip} in {area} - latency~{random.randint(1,200)}ms")

        time.sleep(0.12)

# ---------------------------
# Main ramp logic (no printed worker counts)
# ---------------------------
def start_ramp(pc_amount=DEFAULT_PC_AMOUNT, speed=DEFAULT_SPEED, mem_mb=DEFAULT_MEM_MB,
               use_busy=DEFAULT_USE_BUSY_LOOP, dry_run=False, load_percent=100, area="unknown"):
    stop_fake_console = threading.Event()
    console_thread = threading.Thread(target=fake_hack_console,
                                      args=(stop_fake_console, area, speed, mem_mb, use_busy, dry_run, load_percent),
                                      daemon=True)
    console_thread.start()

    count = 1
    try:
        while count <= pc_amount and not terminate_flag.is_set():
            # Intentionally avoid printing count. Only give a minimal status line.
            print("\n\n[*] RAMP STEP: initiating next wave...")
            if dry_run:
                print("[dry-run] simulation mode - no worker processes will be created.")
            else:
                # spawn 'count' cpu and 'count' mem workers under the hood
                for i in range(count):
                    p_cpu = spawn_cpu_worker(use_busy, load_percent)
                    processes.append(p_cpu)
                    p_mem = spawn_mem_worker(mem_mb)
                    processes.append(p_mem)

            # wait 'speed' seconds between doublings
            slept = 0.0
            while slept < speed and not terminate_flag.is_set():
                time.sleep(0.1)
                slept += 0.1

            count *= 2
        print("\n[*] Ramp finished or stopped.")
    except KeyboardInterrupt:
        pass
    finally:
        stop_fake_console.set()
        console_thread.join(timeout=1)
        print("\n[*] Use 'Terminate all' from the menu or press Ctrl+C to stop workers.")
    return

# ---------------------------
# Terminal menu (PC Amount, Area, Speed)
# ---------------------------
def clear_screen():
    if os.name == "nt":
        os.system("cls")
    else:
        os.system("clear")

def prompt_int(prompt, default):
    try:
        val = input(f"{prompt} [{default}]: ").strip()
        if val == "":
            return int(default)
        return int(val)
    except Exception:
        print("[!] invalid input, using default.")
        return int(default)

def main_menu():
    pc_amount = DEFAULT_PC_AMOUNT
    speed = DEFAULT_SPEED
    mem_mb = DEFAULT_MEM_MB
    use_busy = DEFAULT_USE_BUSY_LOOP
    dry_run = False
    load_percent = 98
    area = "GLOBAL"

    while True:
        clear_screen()
        print(HACK_BANNER)
        print()
        print("ACTIONS:")
        print("  S) Start 'operation'")
        print("  Q) Quit")
        print()
        choice = input("Select option (1-6, S, T, Q): ").strip().lower()

        if choice == "s":
            start_ramp(pc_amount=pc_amount, speed=speed, mem_mb=mem_mb,
                       use_busy=use_busy, dry_run=dry_run, load_percent=load_percent, area=area)
            input("\nPress Enter to return to menu.")
        elif choice == "q":
            if any(p.is_alive() for p in processes):
                print("[!] There are still live worker processes.")
                yn = input("Terminate them and quit? (y/N): ").strip().lower()
                if yn == "y":
                    terminate_all()
            print("[*] Exiting.")
            break
        else:
            print("[!] Unknown option.")
            time.sleep(0.4)

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        signal_handler(None, None)
