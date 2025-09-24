#!/usr/bin/env python3
# coding: utf-8

import argparse
import json
import random
import re
import string
import sys
import time
from http.cookiejar import MozillaCookieJar
from urllib.parse import urlencode, urlparse, parse_qs as url_parse_qs, urlunparse

import requests

# --- Helper Functions (same as before) ---
def try_get(src, getter, expected_type=None):
    if not isinstance(src, (dict, list)): return None
    if not isinstance(getter, (list, tuple)): getter = [getter]
    for get in getter:
        try: src = get(src)
        except (AttributeError, KeyError, TypeError, IndexError): return None
    if expected_type and not isinstance(src, expected_type): return None
    return src

def update_url_query(url, params):
    url_parts = list(urlparse(url))
    query = dict(url_parse_qs(url_parts[4]))
    query.update(params)
    url_parts[4] = urlencode(query, doseq=True)
    return urlunparse(url_parts)
# ---

def watch_fast_with_cookies_and_proxy(video_url, cookie_file, proxy=None):
    print(f"Starting FAST, authenticated watch simulation for: {video_url}")
    if proxy:
        print(f"Using proxy: {proxy}")
        
    script_start_time = time.time()

    # 1. Initialize Session with Headers, Cookies, and Optional Proxy
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    })
    
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}

    try:
        cookie_jar = MozillaCookieJar(cookie_file)
        cookie_jar.load()
        session.cookies.update(cookie_jar)
    except Exception as e:
        print(f"Error: Could not load cookies from '{cookie_file}'. {e}", file=sys.stderr)
        sys.exit(1)

    # ... The rest of the script logic is identical to the previous version ...
    # 2. Fetch the video page to get all initial state data
    print("Step 1: Fetching video page and initial state...")
    try:
        response = session.get(video_url, timeout=20) # Increased timeout for proxies
        response.raise_for_status()
        webpage = response.text
    except requests.exceptions.ProxyError as e:
        print(f"Error: Proxy connection failed. Please check your proxy URL and credentials. Details: {e}", file=sys.stderr)
        sys.exit(1)
    except requests.RequestException as e:
        print(f"Error: Failed to fetch the video page. {e}", file=sys.stderr)
        sys.exit(1)

    # 3. Meticulously Extract All Necessary Tracking Parameters
    print("Step 2: Deep parsing of page state for tracking parameters...")
    try:
        player_response_match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?})\s*;', webpage)
        ytcfg_match = re.search(r'ytcfg\.set\s*\(\s*({.+?})\s*\)\s*;', webpage)
        
        if not player_response_match or not ytcfg_match:
            raise ValueError("Could not find critical page state variables (ytInitialPlayerResponse or ytcfg).")

        player_response = json.loads(player_response_match.group(1))
        ytcfg = json.loads(ytcfg_match.group(1))
        
        tracking_params = {
            "base_url": try_get(player_response, lambda x: x['playbackTracking']['videostatsPlaybackUrl']['baseUrl'], str),
            "video_id": try_get(player_response, lambda x: x['videoDetails']['videoId'], str),
            "video_length": float(try_get(player_response, lambda x: x['videoDetails']['lengthSeconds'], str)),
            "event_id": try_get(player_response, lambda x: x['responseContext']['serviceTrackingParams'][0]['params'][1]['value'], str),
            "client_version": ytcfg.get("INNERTUBE_CLIENT_VERSION"),
            "client_name": ytcfg.get("INNERTUBE_CLIENT_NAME"),
        }
        
        if not all(tracking_params.values()):
            raise ValueError(f"Failed to extract one or more critical tracking parameters: {tracking_params}")
            
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Error: Failed to parse page state. The page might be an error page. Details: {e}", file=sys.stderr)
        sys.exit(1)
        
    # 4. Prepare for the simulated session
    print("Step 3: Preparing simulated viewing session...")
    cpn = ''.join(random.choice(string.ascii_letters + string.digits + '-_') for _ in range(16))
    
    static_ping_params = {
        'ns': 'yt', 'el': 'detailpage', 'docid': tracking_params['video_id'], 'ver': '2',
        'c': tracking_params['client_name'], 'cver': tracking_params['client_version'],
        'cpn': cpn, 'ei': tracking_params['event_id'], 'fs': '0', 'hl': 'en',
        'len': str(tracking_params['video_length']), 'vis': '1', 'state': 'playing', 'fmt': '247',
    }

    # 5. Simulate Playback by Sending All Pings in a Rapid Burst
    print("Step 4: Calculating virtual timestamps and sending all pings in a burst...")
    ping_interval_seconds = 15
    num_pings = min(4, int(tracking_params['video_length'] // ping_interval_seconds))
    all_pings = []
    for i in range(1, num_pings + 1):
        simulated_watch_time = i * ping_interval_seconds
        virtual_real_time_ms = int(simulated_watch_time * 1000)
        dynamic_ping_params = {
            'cmt': f"{simulated_watch_time:.3f}", 'rt': f"{virtual_real_time_ms / 1000:.3f}", 'lact': str(virtual_real_time_ms),
        }
        all_pings.append({**static_ping_params, **dynamic_ping_params})

    final_cmt = tracking_params['video_length']
    virtual_real_time_ms = int(final_cmt * 1000)
    final_ping_params = {
        **static_ping_params,
        'cmt': f"{final_cmt:.3f}", 'rt': f"{virtual_real_time_ms / 1000:.3f}",
        'lact': str(virtual_real_time_ms), 'state': 'ended'
    }
    all_pings.append(final_ping_params)

    for i, ping_data in enumerate(all_pings):
        ping_url = update_url_query(tracking_params['base_url'], ping_data)
        print(f"   - Sending Ping {i+1}/{len(all_pings)} (State: {ping_data['state']}, Time: {ping_data['cmt']}s)...")
        try:
            session.get(ping_url, timeout=20)
        except requests.RequestException as e:
            print(f"   - Warning: A ping failed to send: {e}", file=sys.stderr)

    script_end_time = time.time()
    total_duration = script_end_time - script_start_time
    
    print(f"\n✅ Success! Authenticated simulation complete in {total_duration:.2f} seconds.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="A FAST, authenticated script to simulate watching a YouTube video, with proxy support.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('video_url', help='The full URL of the YouTube video to watch.')
    parser.add_argument('--cookies', required=True, metavar='FILE', help='Path to your cookies file (cookies.txt).')
    parser.add_argument('--proxy', metavar='URL', help='Proxy to use for the connection (e.g., http://user:pass@host:port or socks5://host:port).')
    
    args = parser.parse_args()
    watch_fast_with_cookies_and_proxy(args.video_url, args.cookies, args.proxy)