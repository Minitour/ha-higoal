# Higoal Home Assistant Integration

![GitHub Release](https://img.shields.io/github/v/release/Minitour/ha-higoal?style=flat-square)
![GitHub Stars](https://img.shields.io/github/stars/Minitour/ha-higoal?style=flat-square)
![GitHub Issues](https://img.shields.io/github/issues/Minitour/ha-higoal?style=flat-square)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Unofficial integration, use at your own risk!

## Installation

1. Ensure that [HACS](https://hacs.xyz/) is installed.
2. Add this repository as a custom repository.
3. Search for and install the "Higoal" integration.
4. Restart Home Assistant.
5. Configure the `Higoal` integration.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Minitour&repository=ha-higoal&category=Integration)

## Configuration

1. `Username` - Your Higoal account username.
2. `Password` - Your Higoal account password.

It is recommended that you create a dedicated username and password for HomeAssistant to use instead of your main
account's username and password. The reason for this is that the backend only allows for one active connection per user.

## Features

The integration uses a mix of both HTTP and TCP Socket based requests to interact with the backend to control the devices.
The structure of the integration is highly influenced by the Tuya integration. HTTP requests are used to log in and 
retrieve the list of devices, while the TCP socket is used to monitor any changes and send commands to the devices.

### Supported Entities

- **Switch**: Control supported Higoal switches.
- **Light**: Control dimmer-based lights.
- **Cover**: Open and close supported Higoal covers.

## Tested Models

- **4B**
- **2B**
- **2R**

## Notes

- This integration has been tested with the models listed above but may work with others.
- Use at your own risk, as this is an unofficial integration.
- Using the same credentials as in the app can result in interferences. Therefore, it is recommended to create an
  additional user and add it to your home and use its credentials instead.

## Repository

[GitHub - ha-higoal](https://github.com/Minitour/ha-higoal)

