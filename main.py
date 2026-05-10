#!/usr/bin/env python3
"""
wfbInstaller - Garmin Watchface Installer
Cross-platform console application for installing watchfaces on Garmin devices.
"""

import argparse
import sys
import io

# Set UTF-8 encoding for console on Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

from app_installer import AppInstaller
from logger import ConsoleLogger


def print_usage():
    """Print usage information"""
    print("""
╔════════════════════════════════════════════════════════════╗
║            wfbInstaller - Garmin Watchface Installer       ║
╚════════════════════════════════════════════════════════════╝

Usage:
  wfbinstaller                    - Interactive mode
  wfbinstaller <file.zip>         - Install from zip file
  wfbinstaller <file.prg>         - Install from prg file
  wfbinstaller <file.set>         - Install from settings file
  wfbinstaller <url>              - Download and install from URL
  wfbinstaller -d, --debug        - Enable debug logging

Examples:
  wfbinstaller mystyle.zip
  wfbinstaller mystyle.prg
  wfbinstaller https://garmin.watchfacebuilder.com/watchface/12345/
  wfbinstaller --debug mystyle.zip

Supported file types:
  .zip  - Watchface packages
  .prg  - Compiled watchface
  .set  - Watchface settings

Requirements:
  - libmtp (Windows/Linux)
  - libusb (Linux)
  - Python 3.7+

Installation:
  Linux:
    sudo apt-get install libmtp9 libusb-1.0-0
    pip install -r requirements.txt

  Windows:
    pip install -r requirements.txt
    (libmtp is included in python-libmtp)
""")


def main():
    parser = argparse.ArgumentParser(
        prog='wfbinstaller',
        description='Garmin Watchface Installer',
        add_help=False
    )

    parser.add_argument('input', nargs='?', default=None, help='File path or URL')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug logging')

    # Handle help manually
    if len(sys.argv) > 1 and sys.argv[1] in ('-h', '--help'):
        print_usage()
        sys.exit(0)

    args = parser.parse_args()

    logger = ConsoleLogger(debug_mode=args.debug)
    installer = AppInstaller(logger)

    try:
        # Check for Garmin device first
        installer.select_device()

        # Get input
        user_input = args.input

        if not user_input:
            logger.info("Type or drag URL, zip file, or .prg/.set file and press Enter:")
            user_input = input().strip()

        # Show usage if no input
        if not user_input:
            print_usage()
            return 0

        # Install
        result = installer.install(user_input)

        print()
        if result.success:
            logger.info(f"✓ {result.message}")
        else:
            logger.error(result.message)

        print()
        logger.info("Press Enter to exit...")
        input()

        return 0 if result.success else 1

    except KeyboardInterrupt:
        print("\n")
        logger.info("Installation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        if args.debug:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
