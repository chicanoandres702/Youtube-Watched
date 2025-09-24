# YouTube Watched

This project contains a set of tools for interacting with YouTube, including Python scripts for simulating views and a browser extension for exporting cookies.

## Features

*   **`view_count.py` / `view_count.exe`**: A script to simulate watching a YouTube video with authentication (cookies) and proxy support. It uses multithreading to simulate multiple views concurrently.
*   **`watch_anonymously.py` / `watch_anonymously.exe`**: A script to simulate watching a YouTube video anonymously, with proxy support. It also uses multithreading to simulate multiple views.
*   **Browser Extension**: A simple browser extension that adds an "Export Cookies" button to YouTube pages, allowing you to download your cookies as a `cookies.txt` file.

## Python Scripts

The Python scripts are provided as both `.py` files and as standalone `.exe` executables.

### Installation (for .py scripts)

To run the Python scripts directly, you need to install the required dependencies:

```bash
pip install -r requirements.txt
```

### Usage

The executables (`view_count.exe` and `watch_anonymously.exe`) can be run from the command line. They are located in the `dist` directory.

#### `view_count.exe`

This script simulates watching a YouTube video with authentication.

```bash
view_count.exe <video_url> --cookies <path_to_cookies.txt> [--proxy <proxy_url>] [--threads <num_threads>] [--views <num_views>]
```

*   `<video_url>`: The full URL of the YouTube video.
*   `--cookies`: Path to your `cookies.txt` file.
*   `--proxy` (optional): Proxy to use for the connection (e.g., `http://user:pass@host:port`).
*   `--threads` (optional): Number of threads to use (default: 15).
*   `--views` (optional): Number of views to perform (default: 100).

#### `watch_anonymously.exe`

This script simulates watching a YouTube video anonymously.

```bash
watch_anonymously.exe <video_url> [--proxy <proxy_url>] [--threads <num_threads>] [--views <num_views>]
```

*   `<video_url>`: The full URL of the YouTube video.
*   `--proxy` (optional): Proxy to use for the connection.
*   `--threads` (optional): Number of threads to use (default: 15).
*   `--views` (optional): Number of views to perform (default: 100).

## Browser Extension

The browser extension allows you to easily export your YouTube cookies.

### Installation

1.  Open your browser and navigate to the extensions page (e.g., `chrome://extensions` in Chrome).
2.  Enable "Developer mode".
3.  Click "Load unpacked" and select the `extension` directory from this project.

### Usage

Once installed, a new "Export Cookies" button will appear on YouTube pages. Click this button to download a `cookies.txt` file containing your YouTube cookies.

## Disclaimer

These tools are for educational purposes only. Using these tools to artificially inflate view counts may be against YouTube's terms of service. Use at your own risk.
