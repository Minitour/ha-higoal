import abc

import requests

from .mq import MessageBroker, Message, MessageHandler
from .api import Api
from .device import DeviceRepository


class EntityListener(abc.ABC):
    """Entity Listener - Used to receive messages from broker."""

    @abc.abstractmethod
    def on_entity_changed(self, entity: 'Entity'):
        """Called when an entity is changed."""
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

    def get_devices(self):
        self.api.sign_in()
        devices = self.device_repository.get_devices()
        self.device_map = {device.identifier: device for device in devices}

    def refresh(self):
        if self.mq is not None:
            self.mq.stop()
            self.mq = None

        self.api.sign_in()

        sharing_mq = MessageBroker(api=self.api, host=self.domain, port=17670)
        sharing_mq.add_message_handler(self)
        sharing_mq.connect()
        self.mq = sharing_mq

        for device in self.device_map.values():
            self.send_command(device.status_command())

    def on_receive(self, message: Message):
        if not message.is_status:
            return
        data = message.data
        a, b, c, d = data[9], data[10], data[11], data[12]
        device_byte_id = (a, b, c, d)
        device = self.device_map.get(device_byte_id)

        if device is None:
            # TODO: Got update on a device which we don't have. Consider updating the device map
            # This could indicate a new device being added.
            return

        # remove checksum info
        data = list(data)
        data[2] = 0
        data[3] = 0
        data[4] = 0
        data[-1] = 0
        data[-2] = 0

        changed_entities = device.set_current_status_response(bytes(data))
        for entity in changed_entities:
            self.entity_listener.on_entity_changed(entity)

    def send_command(self, data: bytes):
        self.mq.send_message(Message(data))
