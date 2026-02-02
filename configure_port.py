#!/usr/bin/env python3
"""
Port configuration utility for Study Tracker

Usage:
    python configure_port.py [port]
    python configure_port.py --interactive

If no port is provided, shows current port and available options.
"""

import os
import sys
import argparse
from config import ConfigLoader, AppConfig


def check_port_available(port: int) -> tuple:
    """Check if a port is available for binding"""
    import socket

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex(("127.0.0.1", port))
        return result == 0, "Port is in use"
    except:
        return True, "Port is available"


def list_common_ports() -> dict:
    """Check availability of common development ports"""
    common_ports = {
        5000: "Flask default",
        8000: "Django alternative",
        3000: "Node.js common",
        8080: "HTTP alternative",
        9000: "Development range",
        5001: "Flask alternative",
        8081: "Secure HTTP alternative",
    }

    results = {}
    for port, description in common_ports.items():
        available, message = check_port_available(port)
        results[port] = {
            "available": available,
            "message": message,
            "description": description,
        }

    return results


def suggest_alternative_port(current_port: int) -> int:
    """Suggest an alternative port"""
    # Common ports in order of preference
    preferred_ports = [5000, 5001, 8000, 8080, 3000, 9000, 8081]

    for port in preferred_ports:
        if port != current_port and check_port_available(port)[0]:
            return port

    # If all preferred ports are taken, find any available port
    for port in range(5000, 5100):
        if check_port_available(port)[0]:
            return port

    return -1  # No available port found


def update_env_file(port: int) -> bool:
    """Update .env file with new port"""
    env_file = ".env"

    try:
        # Read existing .env file
        lines = []
        if os.path.exists(env_file):
            with open(env_file, "r") as f:
                lines = f.readlines()

        # Update or add FLASK_PORT line
        port_line = f"FLASK_PORT={port}\n"
        port_updated = False

        with open(env_file, "w") as f:
            for line in lines:
                if line.startswith("FLASK_PORT="):
                    f.write(port_line)
                    port_updated = True
                elif line.strip() and not line.startswith("#"):
                    f.write(line)

            if not port_updated:
                f.write(port_line)

        print(f"✅ Port updated to {port}")
        return True

    except Exception as e:
        print(f"❌ Error updating .env file: {e}")
        return False


def interactive_mode():
    """Interactive port configuration"""
    print("🚀 Study Tracker Port Configuration")
    print("=" * 50)

    # Check current configuration
    config = ConfigLoader.load_from_env()
    current_port = config.port

    print(f"📍 Current port: {current_port}")

    # Check if current port is available
    available, message = check_port_available(current_port)
    status = "✅ Available" if available else "❌ " + message
    print(f"📊 Status: {status}")

    print("\n📋 Common ports availability:")
    common_ports = list_common_ports()

    for port, info in sorted(common_ports.items()):
        symbol = "✅" if info["available"] else "❌"
        print(
            f"  {symbol} Port {port:<4} ({info['description']:<20}) - {info['message']}"
        )

    if not available:
        suggested = suggest_alternative_port(current_port)
        if suggested > 0:
            print(f"\n💡 Suggested alternative: {suggested}")
        else:
            print(f"\n⚠️  No common ports available (5000-5100 range)")

    print("\n" + "=" * 50)

    # Ask user for new port
    while True:
        try:
            user_input = input(
                f"🎯 Enter new port (or press Enter to keep {current_port}): "
            ).strip()

            if not user_input:
                print(f"📍 Keeping current port {current_port}")
                return current_port

            new_port = int(user_input)

            if new_port < 1024 or new_port > 65535:
                print("❌ Port must be between 1024 and 65535")
                continue

            if check_port_available(new_port)[0]:
                if update_env_file(new_port):
                    print(f"🎉 Port changed to {new_port}! Restart the application.")
                    return new_port
                else:
                    print("❌ Failed to update .env file")
            else:
                available, message = check_port_available(new_port)
                print(f"❌ Port {new_port}: {message}")

        except ValueError:
            print("❌ Please enter a valid port number")
        except KeyboardInterrupt:
            print("\n👋 Port configuration cancelled")
            return current_port


def command_line_mode(port: str = None):
    """Command line port configuration"""
    if port is None:
        print("❌ Please provide a port number")
        print("Usage: python configure_port.py [port|--interactive]")
        sys.exit(1)

    try:
        new_port = int(port)

        if new_port < 1024 or new_port > 65535:
            print("❌ Port must be between 1024 and 65535")
            sys.exit(1)

        available, message = check_port_available(new_port)

        if not available:
            print(f"❌ Port {new_port}: {message}")
            suggested = suggest_alternative_port(new_port)
            if suggested > 0:
                print(f"💡 Suggested alternative: {suggested}")
            sys.exit(1)

        if update_env_file(new_port):
            print(f"🎉 Port changed to {new_port}!")
            print("🔄 Restart the application to use the new port.")
        else:
            print("❌ Failed to update .env file")
            sys.exit(1)

    except ValueError:
        print("❌ Invalid port number")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Configure Study Tracker server port",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("port", nargs="?", help="Set port number (1024-65535)")

    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Interactive port configuration",
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help="Check current port and common alternatives",
    )

    args = parser.parse_args()

    if args.check:
        config = ConfigLoader.load_from_env()
        current_port = config.port

        print("🚀 Study Tracker Port Check")
        print("=" * 40)
        print(f"📍 Current configuration: Port {current_port}")

        available, message = check_port_available(current_port)
        status = "✅ Available" if available else "❌ " + message
        print(f"📊 Status: {status}")

        print("\n📋 Common ports:")
        common_ports = list_common_ports()

        for port, info in sorted(common_ports.items()):
            symbol = "✅" if info["available"] else "❌"
            print(
                f"  {symbol} Port {port:<4} ({info['description']:<20}) - {info['message']}"
            )

        print("\n" + "=" * 40)

        if not available:
            suggested = suggest_alternative_port(current_port)
            if suggested > 0:
                print(f"💡 To change port: python configure_port.py {suggested}")
                print(
                    f"💡 Or use interactive mode: python configure_port.py --interactive"
                )

    elif args.interactive:
        interactive_mode()
    elif args.port:
        command_line_mode(args.port)
    else:
        config = ConfigLoader.load_from_env()
        print(f"🚀 Study Tracker Port Configuration")
        print("=" * 40)
        print(f"📍 Current port: {config.port}")
        print(
            f"📊 Status: {'Available' if check_port_available(config.port)[0] else 'In Use'}"
        )
        print("\n💡 Usage:")
        print("  python configure_port.py 5001     # Set port to 5001")
        print("  python configure_port.py -i         # Interactive mode")
        print("  python configure_port.py --check     # Check port status")


if __name__ == "__main__":
    main()
