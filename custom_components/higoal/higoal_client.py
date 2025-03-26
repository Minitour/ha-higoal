import logging
import random
import socket
from dataclasses import dataclass, field

import aiohttp

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class ChecksumHandler:
    # renamed from byteA
    secret_byte_a = 0

    # renamed from byteB
    secret_byte_b = 0

    @staticmethod
    def convert_to_unsigned(value):
        return value & 0xFF

    @staticmethod
    def compute_checksum(data, start_index, end_index, secret_byte):
        length = len(data) - 1
        if start_index < 0 or start_index >= length or end_index > length or end_index <= start_index:
            return 0
        unsigned_byte = ChecksumHandler.convert_to_unsigned(secret_byte)
        checksum = 0
        while start_index <= end_index:
            checksum ^= ChecksumHandler.convert_to_unsigned(data[start_index])
            for _ in range(8):
                bit = checksum & 1
                checksum >>= 1
                if bit != 0:
                    checksum ^= unsigned_byte
            start_index += 1
        return checksum

    @staticmethod
    def get_checksum(data, start_index, end_index):
        return [
            ChecksumHandler.compute_checksum(data, start_index, end_index, 28),
            ChecksumHandler.compute_checksum(data, start_index, end_index, 122)
        ]


class CharacterMapper:
    CHARACTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    A = CHARACTERS[0]
    B = CHARACTERS[1]
    C = CHARACTERS[2]
    D = CHARACTERS[3]
    E = CHARACTERS[4]
    F = CHARACTERS[5]
    G = CHARACTERS[6]
    H = CHARACTERS[7]
    I = CHARACTERS[8]
    J = CHARACTERS[9]
    K = CHARACTERS[10]
    L = CHARACTERS[11]
    M = CHARACTERS[12]
    N = CHARACTERS[13]
    O = CHARACTERS[14]
    P = CHARACTERS[15]
    Q = CHARACTERS[16]
    R = CHARACTERS[17]
    S = CHARACTERS[18]
    T = CHARACTERS[19]
    U = CHARACTERS[20]
    V = CHARACTERS[21]
    W = CHARACTERS[22]
    X = CHARACTERS[23]
    Y = CHARACTERS[24]
    Z = CHARACTERS[25]
    NUM_0 = CHARACTERS[26]
    NUM_1 = CHARACTERS[27]
    NUM_2 = CHARACTERS[28]
    NUM_3 = CHARACTERS[29]
    NUM_4 = CHARACTERS[30]
    NUM_5 = CHARACTERS[31]
    NUM_6 = CHARACTERS[32]
    NUM_7 = CHARACTERS[33]
    NUM_8 = CHARACTERS[34]
    NUM_9 = CHARACTERS[35]

    @staticmethod
    def parse_custom_encoded_string(input_str: str) -> int:
        try:
            return int(
                input_str
                .replace(CharacterMapper.D, CharacterMapper.NUM_0)
                .replace(CharacterMapper.X, CharacterMapper.NUM_0)
                .replace(CharacterMapper.O, CharacterMapper.NUM_0)
                .replace(CharacterMapper.I, CharacterMapper.NUM_1)
                .replace(CharacterMapper.J, CharacterMapper.NUM_1)
                .replace(CharacterMapper.L, CharacterMapper.NUM_1)
                .replace(CharacterMapper.N, CharacterMapper.NUM_2)
                .replace(CharacterMapper.S, CharacterMapper.NUM_2)
                .replace(CharacterMapper.Z, CharacterMapper.NUM_2)
                .replace(CharacterMapper.E, CharacterMapper.NUM_3)
                .replace(CharacterMapper.W, CharacterMapper.NUM_3)
                .replace(CharacterMapper.M, CharacterMapper.NUM_3)
                .replace(CharacterMapper.A, CharacterMapper.NUM_4)
                .replace(CharacterMapper.G, CharacterMapper.NUM_4)
                .replace(CharacterMapper.H, CharacterMapper.NUM_4)
                .replace(CharacterMapper.F, CharacterMapper.NUM_5)
                .replace(CharacterMapper.K, CharacterMapper.NUM_5)
                .replace(CharacterMapper.C, CharacterMapper.NUM_6)
                .replace(CharacterMapper.U, CharacterMapper.NUM_6)
                .replace(CharacterMapper.Y, CharacterMapper.NUM_7)
                .replace(CharacterMapper.V, CharacterMapper.NUM_7)
                .replace(CharacterMapper.T, CharacterMapper.NUM_7)
                .replace(CharacterMapper.B, CharacterMapper.NUM_8)
                .replace(CharacterMapper.Q, CharacterMapper.NUM_9)
                .replace(CharacterMapper.R, CharacterMapper.NUM_9)
                .replace(CharacterMapper.P, CharacterMapper.NUM_9)
            )
        except Exception:
            return -1

    @staticmethod
    def generate_random_number_in_range(i6, i7):
        """Generate a random number between i6 and i7, inclusive."""
        return random.randint(i6, i7)


def encode_token(token):
    # Create a byte array of 16 elements
    byte_arr = bytearray(16)

    # Iterate through the token in steps of 2 characters
    for i in range(0, 32, 2):
        # Convert each 2-character substring to a byte
        byte_arr[i // 2] = int(token[i:i + 2], 16)

    return bytes(byte_arr)


def generate_auth_command(token: str) -> bytes:
    """
    This function builds a byte array which embeds the token of the user. It is used as the first command that is sent
    when a socket session is established.
    """
    base_byte_array = [170, 90, 1, 1, 1, 2, 240, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                       0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
    token_byte_array = encode_token(token)
    home_id_byte_array = [0, 0, 0, 0]  # This also gets the job done
    base_byte_array[9] = token_byte_array[2]
    base_byte_array[10] = token_byte_array[7]
    base_byte_array[11] = home_id_byte_array[1]
    base_byte_array[12] = token_byte_array[12]
    base_byte_array[13] = token_byte_array[8]
    base_byte_array[14] = home_id_byte_array[0]
    base_byte_array[15] = token_byte_array[6]
    base_byte_array[16] = token_byte_array[3]
    base_byte_array[17] = home_id_byte_array[3]
    base_byte_array[18] = token_byte_array[14]
    base_byte_array[19] = token_byte_array[9]
    base_byte_array[20] = token_byte_array[15]
    base_byte_array[21] = home_id_byte_array[2]
    base_byte_array[22] = token_byte_array[11]
    base_byte_array[23] = token_byte_array[5]
    base_byte_array[24] = token_byte_array[13]
    base_byte_array[25] = token_byte_array[0]
    base_byte_array[26] = token_byte_array[4]
    base_byte_array[27] = token_byte_array[10]
    base_byte_array[28] = token_byte_array[1]
    command = bytearray(base_byte_array)
    checksum = bytes(ChecksumHandler.get_checksum(command, 2, 20))
    return bytes(command)[:-2] + checksum


def generate_command(
        device_id: str,
        device_type: int,
        read_only: bool = True,
        entity: int = None,
        entity_type: int = None,
        action: int = None
) -> bytes:
    """
    This function builds a byte array to control the device. It can be used to either perform actions on the device
    or get the state of the device.
    """
    numeric_device_id = CharacterMapper.parse_custom_encoded_string(device_id)

    # Check for valid device ID and type
    if numeric_device_id <= 0 or device_type <= 0:
        return b''

    # Convert device ID to little-endian bytes
    device_id_bytes = numeric_device_id.to_bytes(4, byteorder='little')

    # Create the command array
    command = bytearray([
        0xAA,  # Start byte 1
        0x5A,  # Start byte 2
        0x01,  # Command parameters
        0x01,
        0x01,
        0x02,
        0x01,
        0x01 if read_only else 0x02,
        0x00,  # Padding

        # Device ID bytes (little-endian)
        device_id_bytes[0],
        device_id_bytes[1],
        device_id_bytes[2],
        device_id_bytes[3],

        0x00,  # Reserved/padding

        # Device type byte
        device_type & 0xFF,

        # Remaining padding bytes
        *([0x00] * 33)
    ])
    if not read_only:
        command[18 + entity] = action
        if entity_type == 3:
            command[18 + entity + 16] = 255

    checksum = bytes(ChecksumHandler.get_checksum(command, 2, 20))
    return bytes(command)[:-2] + checksum


models = {
    1: "8B",
    8: "8B",
    16: "8B",
    24: "8B",
    2: "6B",
    9: "6B",
    17: "6B",
    25: "6B",
    3: "PT",
    13: "PT",
    18: "PT",
    26: "PT",
    4: "2B",
    11: "2B",
    19: "2B",
    27: "2B",
    5: "4B",
    10: "4B",
    20: "4B",
    28: "4B",
    6: "2R",
    15: "2R",
    21: "2R",
    29: "2R",
    7: "SOCKET",
    14: "SOCKET",
    23: "SOCKET",
    30: "SOCKET",
    12: "IR",
    22: "IR",
    31: "PIMA",
    160: "C4"
}


@dataclass
class Entity:
    """
    Entity corresponds to a button/switch.
    """
    id: int
    name: str
    type: int
    device: 'Device' = field(repr=False)
    response: bytes = field(repr=False, default=None)

    def _get_on_action(self) -> int:
        action = 255
        if self.type == 3 and self.name == '':
            action = 240
        return action

    def _get_off_action(self) -> int:
        if self.type == 3:
            return 0
        return 240

    def turn_on(self):
        """
        Turn on the switch
        """
        action = self._get_on_action()
        cmd = generate_command(
            device_id=self.device.id,
            device_type=self.device.type,
            read_only=False,
            entity=self.id,
            entity_type=self.type,
            action=action
        )
        self.response = self.device.api.send_command(cmd)

    def turn_off(self):
        """
        Turn off the switch
        """
        if self.type == 3:
            # for type 3 the turn-off command is the same as the turn-on command.
            self.turn_on()
            return
        action = self._get_off_action()
        cmd = generate_command(
            device_id=self.device.id,
            device_type=self.device.type,
            read_only=False,
            entity=self.id,
            entity_type=self.type,
            action=action
        )
        self.response = self.device.api.send_command(cmd)

    def status_command(self):
        return self.device.status_command()

    def is_turned_on(self, use_cache: bool = True) -> bool:
        """
        Check if the switch is turned on or not.
        """
        response = self._current_response(use_cache=use_cache)
        return response[18 + self.id] == 255

    def is_online(self, use_cache: bool = True):
        """
        Check if the switch is online.
        """
        response = list(self._current_response(use_cache=use_cache))
        return response[18 + self.id] != 0

    def percentage(self, use_cache: bool = True) -> float | None:
        """
        Get percentage of blinds 1.0 means fully closed while 0.0 means fully open.
        """
        if self.type != 3:
            return None
        status = list(self._current_response(use_cache=use_cache))
        value = max(min(status[-10], 100), 0)
        return value / 100

    def _current_response(self, use_cache: bool = True) -> bytes:
        if use_cache and self.response:
            return self.response

        return self.device.api.send_command(
            self.status_command()
        )

    def get_related_entity(self) -> 'Entity' | None:
        if self.type != 3:
            return None
        if self.name == '':
            return None
        index = 0
        for index, button in enumerate(self.device.buttons):
            if button == self:
                break
        if index + 1 >= len(self.device.buttons):
            return None
        button = self.device.buttons[index + 1]
        if button.type != 3:
            return None
        return button


@dataclass
class Device:
    """
    A device (or sometimes host) refers to a physical switch
    """
    id: str
    type: int
    name: str
    room_id: str
    home_id: str
    ssid: str
    mac: str
    version: str
    buttons: list[Entity]
    api: 'HigoalApiClient' = field(repr=False)

    @property
    def model_name(self):
        return models.get(self.type) or 'UNKNOWN'

    @classmethod
    def init_from(cls, device: dict, api: 'HigoalApiClient') -> 'Device':
        """
        Create an instance of device from dictionary object and api client.
        """
        button_names = device.get('buttonName').split(';')
        button_types = device.get('buttonType').split(',')
        buttons = []
        device = Device(
            id=device.get('id'),
            type=device.get('type'),
            name=device.get('name'),
            room_id=device.get('roomId'),
            home_id=device.get('homeId'),
            ssid=device.get('ssid'),
            mac=device.get('mac'),
            version=device.get('version'),
            buttons=buttons,
            api=api
        )
        for i, (button_name, button_type) in enumerate(zip(button_names, button_types)):
            button_type = int(button_type)
            if button_type == 0:
                continue
            buttons.append(
                Entity(
                    id=i,
                    name=button_name,
                    type=button_type,
                    device=device
                )
            )

        return device

    def status_command(self) -> bytes:
        """
        Generates the status command.
        """
        return generate_command(
            device_id=self.id,
            device_type=self.type,
            read_only=True
        )

    def button(self, name: str) -> Entity | None:
        """
        Get button by name.
        """
        for button in self.buttons:
            if button.name == name:
                return button

    def set_current_status_response(self, response: bytes) -> None:
        for button in self.buttons:
            button.response = response


class HigoalApiClient:

    def __init__(
            self,
            domain: str = 'server.higoal.net',
            port: int = 8143,
            version: str = 'V3.21.1',
            username: str = None,
            password: str = None,
            session: aiohttp.ClientSession = None,
    ):
        self._session = session
        self.remote_socket = None
        self._username = username
        self._password = password
        self._version = version
        self._domain = domain
        self._port = port
        self._url = f'https://{domain}:{port}'
        self._user_id = None
        self._token = None
        self._home_ids = None
        self._auth_command = None

    def _init_socket(self):
        self.remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.remote_socket.connect((self._domain, 17670))
        self.remote_socket.sendall(self._auth_command)
        self.remote_socket.recv(4096)

    @property
    def is_signed_in(self):
        return self._user_id and self._token and self._home_ids

    async def sign_in(self):
        """
        Perform log-in with the provided credentials.
        """
        if self.is_signed_in:
            return

        payload = f"password={self._password}&username={self._username}&ver={self._version}"
        headers = {'content-type': "application/x-www-form-urlencoded; charset=utf-8"}
        response = await self._session.request("POST", f'{self._url}/login', data=payload, headers=headers)
        body = await response.json()
        self._user_id = body.get('repData', {}).get('uid')
        self._token = body.get('repData', {}).get('token')
        self._home_ids = [home.get('id') for home in body.get('repData', {}).get('homeList', [])]

        if self._token is None:
            raise Exception('Log-in failed')

        self._auth_command = generate_auth_command(self._token)

    async def get_devices(self) -> list[Device]:
        """
        Get devices (hosts) assigned to the account.
        """
        if not self.is_signed_in:
            await self.sign_in()

        devices = []
        for home in self._home_ids:
            payload = f"homeId={home}&token={self._token}&uid={self._user_id}"
            headers = {'content-type': "application/x-www-form-urlencoded; charset=utf-8"}
            response = await self._session.request("POST", f'{self._url}/get_host_list', data=payload, headers=headers)
            body = await response.json()
            devices.extend(body.get('repData', []))
        devices = [Device.init_from(device, self) for device in devices]
        status_commands = [device.status_command() for device in devices]
        responses = [self.send_command(command) for command in status_commands]

        if responses:
            for device, response in zip(devices, responses):
                device.set_current_status_response(response)

        return devices

    def send_command(self, command: bytes, max_attempts=3) -> bytes | None:
        """
        Opens a socket, sends the command, waits for a response, and then closes the socket.
        """
        if not self.remote_socket:
            self._init_socket()

        if max_attempts == 0:
            return None
        logger.debug(f'Sending command: {list(command)}')
        try:
            self.remote_socket.sendall(command)
            response = self.remote_socket.recv(4096)
            logger.debug(f'Got Response: {list(response)}')
        except (socket.gaierror, socket.timeout, ConnectionRefusedError, socket.error):
            self._init_socket()
            return self.send_command(command, max_attempts - 1)

        return response
