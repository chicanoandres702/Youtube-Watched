#!/usr/bin/env python3
# coding: utf-8

import argparse
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue

import requests

# --- Configuration ---
# UPDATED: The new USA-specific plain-text proxy source
PROXY_LIST_URL = "https://pastebin.com/raw/cGv2f1FN"
PROXY_CHECK_URL = "https://httpbin.org/ip"
REQUEST_TIMEOUT = 15

# --- Shared resources for real-time logging ---
checked_count = 0
valid_count = 0
total_proxies = 0
simulations_completed = 0
simulations_succeeded = 0
simulations_failed = 0
lock = threading.Lock()

# --- Script Components ---

def fetch_proxies():
    """
    Fetches a list of proxies from the plain-text proxyscrape source.
    """
    print(f"[INFO] Fetching proxy list from {PROXY_LIST_URL}...")
    try:
        response = requests.get(PROXY_LIST_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        # This source returns plain text, ip:port per line
        proxies = response.text.strip().splitlines()
        print(f"[INFO] Fetched {len(proxies)} proxies.")
        return proxies
    except requests.RequestException as e:
        print(f"[ERROR] Could not fetch proxy list: {e}", file=sys.stderr)
        return []

def print_progress():
    """Prints the progress of the proxy checking phase on a single line."""
    progress_message = (
        f"\r[PHASE 1] Checking proxies: {checked_count}/{total_proxies} "
        f"| Valid found: {valid_count}"
    )
    sys.stdout.write(progress_message)
    sys.stdout.flush()

def print_phase2_progress(total_simulations):
    """Prints the progress of the simulation phase on a single line."""
    progress_message = (
        f"\r[PHASE 2] Running simulations: {simulations_completed}/{total_simulations} "
        f"| Success: {simulations_succeeded} | Failed: {simulations_failed}"
    )
    sys.stdout.write(progress_message)
    sys.stdout.flush()

def check_proxy(proxy, valid_proxies_queue):
    """
    Checks if a single proxy (ip:port) is valid and updates counters.
    """
    global checked_count, valid_count
    
    is_valid = False
    proxy_url = f"http://{proxy}"
    try:
        proxies_dict = {"http": proxy_url, "https": proxy_url}
        response = requests.get(
            PROXY_CHECK_URL, proxies=proxies_dict, timeout=REQUEST_TIMEOUT, stream=True)
        if 200 <= response.status_code < 400:
            valid_proxies_queue.put(proxy) # Put the original ip:port string in the queue
            is_valid = True
    except requests.RequestException:
        pass

    with lock:
        checked_count += 1
        if is_valid:
            valid_count += 1
        print_progress()

def run_view_simulation(proxy, video_url):
    """Executes 'watch_anonymously.py' with the given proxy (ip:port)."""
    proxy_url_for_subprocess = f"http://{proxy}"
    command = [sys.executable, "watch_anonymously.py", video_url, "--proxy", proxy_url_for_subprocess]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, encoding='utf-8')
        if result.returncode == 0:
            return f"✅ SUCCESS with proxy {proxy}"
        else:
            error_message = result.stderr.strip().split('\n')[-1]
            return f"❌ FAILED with proxy {proxy}. Reason: {error_message}"
    except FileNotFoundError:
        return "[FATAL ERROR] 'watch_anonymously.py' not found in the same directory."
    except Exception as e:
        return f"[FATAL ERROR] An unexpected error occurred for {proxy}: {e}"

def main():
    global total_proxies, simulations_completed, simulations_succeeded, simulations_failed
    
    parser = argparse.ArgumentParser(
        description="A manager script to fetch, validate, and use proxies to run anonymous view simulations.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="Requires 'watch_anonymously.py'. SOCKS support is not needed for this proxy source."
    )
    parser.add_argument('video_url', help='The full URL of the YouTube video.')
    parser.add_argument('--threads', type=int, default=10, help='Number of concurrent threads to use (default: 10).')
    args = parser.parse__args()

    # Phase 1
    proxies_to_check = fetch_proxies()
    if not proxies_to_check:
        return

    total_proxies = len(proxies_to_check)
    print(f"\n[PHASE 1] Starting validation for {total_proxies} proxies with {args.threads} threads...")
    
    valid_proxies_queue = Queue()
    print_progress()
    
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        list(executor.map(lambda p: check_proxy(p, valid_proxies_queue), proxies_to_check))

    print("\n")
    valid_proxies = list(valid_proxies_queue.queue)
    print(f"[PHASE 1 COMPLETE] Found {len(valid_proxies)} valid proxies.")

    if not valid_proxies:
        print("[INFO] No working proxies found. Exiting.")
        return

    # Phase 2
    print(f"\n[PHASE 2] Starting view simulations for {len(valid_proxies)} valid proxies with {args.threads} threads...")
    
    total_simulations = len(valid_proxies)
    print_phase2_progress(total_simulations)

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = {executor.submit(run_view_simulation, proxy, args.video_url): proxy for proxy in valid_proxies}
        for future in as_completed(futures):
            result_message = future.result()

            with lock:
                simulations_completed += 1
                if "✅ SUCCESS" in result_message:
                    simulations_succeeded += 1
                else:
                    simulations_failed += 1
                
                # Erase the progress line, print the result, then print the updated progress
                sys.stdout.write(f"\r{' ' * 80}\r")
                print(result_message)
                print_phase2_progress(total_simulations)

            if "[FATAL ERROR]" in result_message:
                print("\n[CRITICAL] A fatal error occurred, stopping all operations.", file=sys.stderr)
                executor.shutdown(wait=False, cancel_futures=True)
                return

    print("\n[ALL TASKS COMPLETE] Manager script has finished.")

if __name__ == '__main__':
    main()