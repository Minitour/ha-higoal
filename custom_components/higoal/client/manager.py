import abc
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

import requests
from requests.exceptions import ConnectionError, RequestException

from .mq import MessageBroker, Message, MessageHandler
from .api import Api
from .device import DeviceRepository

logger = logging.getLogger(__name__)


@dataclass
class OfflineDevice:
    device: 'Device'
    last_update: datetime


type UnknownDevice = object()


class EntityListener(abc.ABC):
    """Entity Listener - Used to receive messages from broker."""

    @abc.abstractmethod
    def on_entity_changed(self, entity: 'Entity'):
        """Called when an entity is changed."""
        pass

    @abc.abstractmethod
    def on_device_added(self, device: 'Device'):
        pass

    @abc.abstractmethod
    def on_device_removed(self, device: 'Device'):
        pass


class Manager(MessageHandler):
    def __init__(self,
                 domain: str = "server.higoal.net",
                 port: int = 8143,
                 version: str = "V3.21.1",
                 username: str = None,
                 password: str = None,
                 entity_listener: EntityListener = None,
                 session: requests.Session = None):
        self.domain = domain
        self.api = Api(domain=domain, port=port, version=version, username=username, password=password, session=session)
        self.mq = None
        self.device_repository = DeviceRepository(self)
        self.device_map = {}
        self.entity_listener = entity_listener
        self.offline_devices = {}

    def get_devices(self):
        self.api.sign_in()
        devices = self.device_repository.get_devices()
        full_set = {device.identifier: device for device in devices}

        new_devices = []
        deleted_devices = []
        for device in full_set.values():
            if device.identifier in self.device_map:
                continue
            self.device_map[device.identifier] = device
            new_devices.append(device)
            # assume newly discovered devices are offline by default
            self.offline_devices[device.identifier] = OfflineDevice(device=device, last_update=datetime.now())

        # check for deleted devices
        for device_id, device in self.device_map.items():
            if device is UnknownDevice:
                continue
            if device_id not in full_set:
                # device has been removed
                deleted_devices.append(device)

        for device in deleted_devices:
            del self.device_map[device.identifier]

        return new_devices, deleted_devices

    def refresh(self):
        if self.mq is not None:
            self.mq.stop()
            self.mq = None

        self.api.sign_in()

        sharing_mq = MessageBroker(api=self.api, host=self.domain, port=17670)
        sharing_mq.add_message_handler(self)
        sharing_mq.connect()
        self.mq = sharing_mq

        for device in list(self.device_map.values()):
            if device is UnknownDevice:
                continue
            self.send_command(device.status_command())

    def check_offline_devices(self):
        for offline_device in self.offline_devices.values():
            if not offline_device.last_update + timedelta(seconds=30) < datetime.now():
                continue
            offline_device.last_update = datetime.now()
            self.send_command(offline_device.device.status_command())

    def on_receive(self, message: Message):
        self.check_offline_devices()
        if not message.is_status:
            return

        device = self.device_map.get(message.device_identifier)

        if device is UnknownDevice:
            return

        if device is None:
            self.device_map[message.device_identifier] = UnknownDevice
            # Got update on a device which we don't have.
            # This could indicate a new device being added.
            try:
                new_devices, deleted_devices = self.get_devices()
                for device in new_devices:
                    self.entity_listener.on_device_added(device)
                for device in deleted_devices:
                    self.entity_listener.on_device_removed(device)

                if new_devices:
                    # try again
                    return self.on_receive(message)
            except (ConnectionError, RequestException) as e:
                logger.warning(
                    "Failed to fetch device list due to connection error: %s. "
                    "Will retry on next message.",
                    e
                )
                # Don't remove UnknownDevice marker so we can retry later
                return
            except Exception as e:
                logger.error("Unexpected error while fetching device list: %s", e, exc_info=True)
                return
            # do nothing
            return

        # remove checksum info
        data = list(message.data)
        data[2] = 0
        data[3] = 0
        data[4] = 0
        data[-1] = 0
        data[-2] = 0

        changed_entities = device.set_current_status_response(bytes(data))
        for entity in changed_entities:
            self.entity_listener.on_entity_changed(entity)

        # if one of the entities is offline
        if device.offline:
            self.offline_devices[device.identifier] = OfflineDevice(device=device, last_update=datetime.now())
        elif device.identifier in self.offline_devices:
            del self.offline_devices[device.identifier]

    def send_command(self, data: bytes):
        if not self.mq:
            return
        self.mq.send_message(Message(data))
