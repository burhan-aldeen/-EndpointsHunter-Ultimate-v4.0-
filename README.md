Here is a clean, professional, and human-written README.md in English, tailored for your version 5.0 update.

***

# EndpointsHunter Ultimate v5.0

EndpointsHunter Ultimate is a high-performance reconnaissance tool designed for security researchers and bug bounty hunters. It automates the discovery of web endpoints by aggregating data from multiple passive sources and performing intelligent active probing.

## Key Features

* **Multi-Source Harvesting:** Collects data from over 12 reliable sources including Wayback Machine, AlienVault OTX, VirusTotal, URLScan, and GitHub.
* **Subdomain List Mode:** Ability to process a large list of subdomains and perform wordlist-based fuzzing across all of them simultaneously.
* **Smart Wildcard Detection:** Advanced logic to identify and filter out false-positive 200 OK responses by analyzing content length baselines.
* **Full Parameter Extraction:** Automatically extracts and organizes URL parameters to help identify potential injection points like XSS, SQLi, and SSRF.
* **Live Verification:** Checks endpoints in real-time to confirm their status codes, page titles, and response sizes.

## Installation

This tool requires Python 3.x. You will need to install the following dependencies:

```bash
pip install requests colorama urllib3
```

## How to Use

Simply run the script and follow the interactive menu:

```bash
python EndpointsHunter.py
```

### Modes of Operation
1. **Single Domain Scan:** Best for deep-diving into a specific target. It combines passive data harvesting with live status checking.
2. **Subdomain List Mode:** Designed for scale. Provide a text file containing subdomains, and the tool will fuzz each one for common paths and sensitive files.

## Configuration

To get the most out of this tool, it is highly recommended to add your own API keys in the configuration section of the script. This includes:
* VirusTotal API Keys
* GitHub Personal Access Token
* URLScan API Key

## Output Files

The tool generates two main files upon completion:
* `found_endpoints.txt`: A human-readable report categorized by source, including a raw list ready for further automation.
* `endpoints_detailed.json`: A structured data file containing status codes, response lengths, and page titles for every live endpoint found.

## Disclaimer

This tool is intended for legal security auditing and educational purposes only. Always obtain explicit permission before testing any infrastructure that you do not own.

**Developed by: @Burhan_ALDeen**

***

### A quick safety note:
Before you upload this to GitHub, please **remove the API keys and GitHub Token** you included in the script above. If you push that code to a public repository, other people can use your tokens to access your accounts or hit your API limits. Use empty strings instead: `""`.
