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

## Features
The integration defines a custom [DataUpdateCoordinator](https://developers.home-assistant.io/docs/integration_fetching_data/#coordinated-single-api-poll-for-data-for-all-entities) which pulls all the devices' information in the specified account every 60 seconds.
 This is done using both HTTPs requests and a TCP socket. Any follow-up interaction that is done with the devices/entities is done via the socket connection.
In some cases the socket connection may be lost, however the integration is able to automatically recover.

### Supported Entities
- **Switch**: Control supported Higoal switches.
- **Cover**: Open and close supported Higoal covers.

## Tested Models
- **4B**
- **2B**
- **2R**

## Notes
- This integration has been tested with the models listed above but may work with others.
- Use at your own risk, as this is an unofficial integration.
- Using the same credentials as in the app can result in interferences. Therefore, it is recommended to create an additional user and add it to your home and use its credentials instead.

## Repository
[GitHub - ha-higoal](https://github.com/Minitour/ha-higoal)

