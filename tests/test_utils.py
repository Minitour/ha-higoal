"""Tests for command generation, checksum, and character mapper."""

from client.utils import (
    generate_command,
    generate_auth_command,
    verify_response,
    encode_token,
    ChecksumHandler,
    CharacterMapper,
)


class TestCharacterMapper:
    def test_known_mapping(self):
        assert CharacterMapper.parse_custom_encoded_string("A") == 4
        assert CharacterMapper.parse_custom_encoded_string("Q") == 9

    def test_numeric_passthrough(self):
        assert CharacterMapper.parse_custom_encoded_string("0") == 0
        assert CharacterMapper.parse_custom_encoded_string("9") == 9

    def test_multi_character_string(self):
        result = CharacterMapper.parse_custom_encoded_string("AA")
        assert result == 44

    def test_invalid_string_returns_minus_one(self):
        assert CharacterMapper.parse_custom_encoded_string("") == -1


class TestGenerateCommand:
    def test_command_length_is_48(self):
        cmd = generate_command(device_id="ABCD1234", device_type=5)
        assert len(cmd) == 48

    def test_read_only_flag(self):
        cmd_ro = generate_command(device_id="ABCD1234", device_type=5, read_only=True)
        cmd_rw = generate_command(device_id="ABCD1234", device_type=5, read_only=False, entity=0, entity_type=1, action=255)

        assert cmd_ro[7] == 0x01  # read-only
        assert cmd_rw[7] == 0x02  # read-write

    def test_start_bytes(self):
        cmd = generate_command(device_id="ABCD1234", device_type=5)
        assert cmd[0] == 0xAA
        assert cmd[1] == 0x5A

    def test_device_type_in_command(self):
        cmd = generate_command(device_id="ABCD1234", device_type=5)
        assert cmd[14] == 5

    def test_action_placed_at_entity_offset(self):
        cmd = generate_command(
            device_id="ABCD1234", device_type=5,
            read_only=False, entity=2, entity_type=1, action=255,
        )
        assert cmd[18 + 2] == 255

    def test_shutter_action_sets_extra_byte(self):
        cmd = generate_command(
            device_id="ABCD1234", device_type=5,
            read_only=False, entity=1, entity_type=3, action=255,
        )
        assert cmd[18 + 1] == 255
        assert cmd[18 + 1 + 16] == 255

    def test_invalid_device_id_returns_empty(self):
        cmd = generate_command(device_id="", device_type=5)
        assert cmd == b""

    def test_invalid_device_type_returns_empty(self):
        cmd = generate_command(device_id="ABCD1234", device_type=0)
        assert cmd == b""

    def test_checksum_is_deterministic(self):
        cmd1 = generate_command(device_id="ABCD1234", device_type=5)
        cmd2 = generate_command(device_id="ABCD1234", device_type=5)
        assert cmd1 == cmd2


class TestChecksumHandler:
    def test_checksum_produces_two_bytes(self):
        data = bytearray(48)
        result = ChecksumHandler.get_checksum(data, 2, 20)
        assert len(result) == 2

    def test_checksum_is_deterministic(self):
        data = bytearray([i for i in range(48)])
        r1 = ChecksumHandler.get_checksum(data, 2, 20)
        r2 = ChecksumHandler.get_checksum(data, 2, 20)
        assert r1 == r2

    def test_different_data_produces_different_checksum(self):
        data1 = bytearray(48)
        data2 = bytearray(48)
        data2[10] = 42
        assert ChecksumHandler.get_checksum(data1, 2, 20) != ChecksumHandler.get_checksum(data2, 2, 20)

    def test_invalid_range_returns_zero(self):
        data = bytearray(48)
        assert ChecksumHandler.compute_checksum(data, 10, 5, 28) == 0
        assert ChecksumHandler.compute_checksum(data, -1, 5, 28) == 0


class TestEncodeToken:
    def test_token_length(self):
        token = "0123456789abcdef0123456789abcdef"
        result = encode_token(token)
        assert len(result) == 16

    def test_known_encoding(self):
        token = "ff" + "00" * 15
        result = encode_token(token)
        assert result[0] == 0xFF
        assert result[1] == 0x00


class TestAuthCommand:
    def test_auth_command_length(self):
        token = "0123456789abcdef0123456789abcdef"
        cmd = generate_auth_command(token)
        assert len(cmd) == 48

    def test_auth_command_start_bytes(self):
        token = "0123456789abcdef0123456789abcdef"
        cmd = generate_auth_command(token)
        assert cmd[0] == 0xAA
        assert cmd[1] == 0x5A


class TestVerifyResponse:
    def test_offline_response_is_valid(self):
        cmd = generate_command(device_id="ABCD1234", device_type=5)
        response = bytearray(48)
        response[4:9] = bytes([1, 1, 1, 1, 13])
        assert verify_response(cmd, bytes(response)) is True

    def test_matching_device_and_type(self):
        cmd = generate_command(device_id="ABCD1234", device_type=5)
        response = bytearray(cmd)
        assert verify_response(cmd, bytes(response)) is True

    def test_mismatched_device_id(self):
        cmd = generate_command(device_id="ABCD1234", device_type=5)
        response = bytearray(cmd)
        response[9] = 0
        assert verify_response(cmd, bytes(response)) is False
