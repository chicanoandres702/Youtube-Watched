#!/usr/bin/env python3
# coding: utf-8

import argparse
import json
import random
import re
import string
import sys
import time
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

def watch_anonymously(video_url, proxy=None):
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    })
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}

    try:
        response = session.get(video_url, timeout=20)
        response.raise_for_status()
        webpage = response.text
    except requests.RequestException as e:
        print(f"Error: Failed to fetch the video page via proxy. Reason: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        player_response_match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?})\s*;', webpage)
        ytcfg_match = re.search(r'ytcfg\.set\s*\(\s*({.+?})\s*\)\s*;', webpage)
        
        if not player_response_match or not ytcfg_match:
            raise ValueError("Could not find critical page state variables (ytInitialPlayerResponse or ytcfg). The proxy may be blocked or showing a CAPTCHA.")

        player_response = json.loads(player_response_match.group(1))
        ytcfg = json.loads(ytcfg_match.group(1))
        
        tracking_params = {
            "base_url": try_get(player_response, lambda x: x['playbackTracking']['videostatsPlaybackUrl']['baseUrl'], str),
            "video_id": try_get(player_response, lambda x: x['videoDetails']['videoId'], str),
            "video_length_str": try_get(player_response, lambda x: x['videoDetails']['lengthSeconds'], str),
            "event_id": try_get(player_response, lambda x: x['responseContext']['serviceTrackingParams'][0]['params'][1]['value'], str),
            "client_version": ytcfg.get("INNERTUBE_CLIENT_VERSION"),
            "client_name": ytcfg.get("INNERTUBE_CLIENT_NAME"),
        }
        
        # *** CRITICAL BUG FIX IS HERE ***
        # Check if any of the essential values are missing before proceeding.
        if not all(tracking_params.values()):
            # Find which keys are missing for better error logging
            missing_keys = [key for key, value in tracking_params.items() if value is None]
            raise ValueError(f"Failed to extract critical tracking parameters: {', '.join(missing_keys)}. The proxy is likely blocked.")

        # If all checks pass, convert length to float
        tracking_params["video_length"] = float(tracking_params["video_length_str"])
            
    except (ValueError, json.JSONDecodeError) as e:
        print(f"Error: Could not parse page state. Reason: {e}", file=sys.stderr)
        sys.exit(1)
        
    cpn = ''.join(random.choice(string.ascii_letters + string.digits + '-_') for _ in range(16))
    session_start_time = time.time()
    
    static_ping_params = {
        'ns': 'yt', 'el': 'detailpage', 'docid': tracking_params['video_id'], 'ver': '2',
        'c': tracking_params['client_name'], 'cver': tracking_params['client_version'],
        'cpn': cpn, 'ei': tracking_params['event_id'], 'fs': '0', 'hl': 'en',
        'len': str(tracking_params['video_length']), 'vis': '1', 'state': 'playing', 'fmt': '247',
    }

    ping_interval_seconds = 15
    num_pings = min(4, int(tracking_params['video_length'] // ping_interval_seconds))
    time.sleep(ping_interval_seconds * num_pings)
    
    final_cmt = tracking_params['video_length']
    relative_time_ms = int((time.time() - session_start_time) * 1000)
    final_ping_params = {
        **static_ping_params,
        'cmt': f"{final_cmt:.3f}", 'rt': f"{(relative_time_ms / 1000):.3f}",
        'lact': str(relative_time_ms), 'state': 'ended'
    }
    final_ping_url = update_url_query(tracking_params['base_url'], final_ping_params)

    try:
        session.get(final_ping_url, timeout=20)
    except requests.RequestException as e:
        print(f"Warning: The final ping failed to send: {e}", file=sys.stderr)
        
    # If we reach here, the script was successful. Exit with code 0.
    # The manager script will see this as a SUCCESS.
    sys.exit(0)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('video_url')
    parser.add_argument('--proxy')
    args = parser.parse_args()
    watch_anonymously(args.video_url, args.proxy)