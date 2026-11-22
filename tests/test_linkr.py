# Copyright (c) 2026 Matt H
#
# SPDX-License-Identifier: MIT

import ssl

import pytest

from koidaemon import keys
from koidaemon.backends import linkr
from koidaemon.backends.base import Settings
from koidaemon.errors import BackendError, ConfigError, InvalidRequest

from fake_kvmd import make_jpeg
from fake_linkr import FakeLinkr


def make_backend(tmp_path, url, token="radxa_linkr_secret", **settings) -> linkr.LinkrBackend:
    (tmp_path / "token").write_text(token + "\n")
    values = {"url": url, "token_file": "token", **settings}
    return linkr.LinkrBackend("board", Settings("board", values, tmp_path))


@pytest.fixture
def device():
    with FakeLinkr() as fake:
        yield fake


@pytest.fixture(autouse=True)
def slept(monkeypatch):
    """What the backend slept, in seconds, without sleeping."""
    slept = []
    monkeypatch.setattr(linkr.time, "sleep", slept.append)
    return slept


@pytest.fixture
def backend(tmp_path, device):
    return make_backend(tmp_path, device.url)


def unpaced(events):
    """Several events without the delays between them, checking each is
    followed by one; a single event goes alone."""
    if len(events) == 1:
        return events
    assert events[1::2] == [["delay", linkr.EVENT_DELAY_MS]] * (len(events) // 2)
    return events[0::2]


# ----------------------------------------------------------------------
# Settings and connection
# ----------------------------------------------------------------------

def test_settings(tmp_path):
    backend = make_backend(tmp_path, "https://linkr.lab/", timeout=5)
    assert backend.url == "https://linkr.lab"
    assert backend.token == "radxa_linkr_secret"
    assert backend.resource == "linkr:https://linkr.lab"
    assert backend.describe()["url"] == "https://linkr.lab"
    assert "storage.cdrom" not in backend.describe()["capabilities"]
    assert backend._tls.verify_mode == ssl.CERT_REQUIRED


def test_bad_url(tmp_path):
    with pytest.raises(ConfigError, match="must start with https://"):
        make_backend(tmp_path, "linkr.lab")


def test_tls_check_can_be_turned_off(tmp_path):
    backend = make_backend(tmp_path, "https://linkr.lab", verify_tls=False)
    assert backend._tls.verify_mode == ssl.CERT_NONE


def test_unknown_setting(tmp_path):
    with pytest.raises(ConfigError, match="unknown settings colour"):
        make_backend(tmp_path, "https://linkr.lab", colour="red")


def test_wrong_token(tmp_path, device):
    backend = make_backend(tmp_path, device.url, token="radxa_linkr_wrong")
    with pytest.raises(BackendError, match="refused the access token"):
        backend.status()


def test_unreachable(tmp_path):
    backend = make_backend(tmp_path, "http://127.0.0.1:1")
    with pytest.raises(BackendError, match="cannot reach"):
        backend.status()


def test_command_fails(device, backend):
    device.control_answer = {"code": 1, "data": None, "message": "HID not ready"}
    with pytest.raises(BackendError, match="HID not ready"):
        backend.key_down(keys.usage_for_name("a"))


# ----------------------------------------------------------------------
# Status and snapshot
# ----------------------------------------------------------------------

def test_status(device, backend):
    assert backend.status() == {"online": True, "video": None}
    assert device.controls == [[["delay", 0]]]
    assert device.snapshots == 0
    backend.snapshot()
    assert backend.status()["video"] == {"width": 1920, "height": 1080}


def test_snapshot(device, backend):
    device.screen = (1280, 720)
    snapshot = backend.snapshot()
    assert snapshot.format == "jpeg"
    assert snapshot.data == make_jpeg(1280, 720)
    assert (snapshot.width, snapshot.height) == (1280, 720)
    assert device.headers[0]["Authorization"] == "token radxa_linkr_secret"


def test_snapshot_that_is_not_a_jpeg(device, backend):
    device.snapshot_data = b"\x89PNG"
    with pytest.raises(BackendError, match="not a JPEG"):
        backend.snapshot()


def test_snapshot_with_no_video(device, backend):
    device.snapshot_data = b'{"code":1,"message":"snapshot failed"}'
    with pytest.raises(BackendError, match="snapshot failed"):
        backend.snapshot()


# ----------------------------------------------------------------------
# Keyboard
# ----------------------------------------------------------------------

def test_type_text(device, backend):
    backend.type_text("root\n")
    assert device.controls == [[["text", "root\n"]]]


def test_type_long_text(device, backend):
    text = "x" * 65
    backend.type_text(text)
    assert device.controls == [[
        ["text", "x" * 30], ["delay", 1000], ["text", "x" * 30], ["delay", 1000],
        ["text", "x" * 5],
    ]]


def test_type_very_long_text_in_several_requests(device, backend):
    backend.type_text("y" * 300)
    assert len(device.controls) == 3
    assert device.controls[1] == [["delay", 1000]]
    typed = "".join(event[1] for events in device.controls for event in events
                    if event[0] == "text")
    assert typed == "y" * 300


def test_type_text_it_cannot(device, backend):
    with pytest.raises(InvalidRequest, match="cannot type"):
        backend.type_text("café")
    assert device.controls == []


def test_press(device, backend, slept):
    backend.press([keys.parse_combination("ctrl+alt+delete"), [keys.usage_for_name("enter")]])
    # Spaced out, as a Linkr loses keys sent back to back.
    assert [unpaced(events) for events in device.controls] == [[
        ["keyboard", "ControlLeft", True], ["keyboard", "AltLeft", True],
        ["keyboard", "Delete", True], ["keyboard", "Delete", False],
        ["keyboard", "AltLeft", False], ["keyboard", "ControlLeft", False],
        ["keyboard", "Enter", True], ["keyboard", "Enter", False],
    ]]
    # koid waits for the Linkr to play them before it answers.
    assert slept == [8 * linkr.EVENT_DELAY_MS / 1000]


def test_down_and_up(device, backend):
    backend.key_down(keys.usage_for_name("rshift"))
    backend.key_up(keys.usage_for_name("rshift"))
    assert device.controls == [[["keyboard", "ShiftRight", True]],
                               [["keyboard", "ShiftRight", False]]]


# ----------------------------------------------------------------------
# Mouse
# ----------------------------------------------------------------------

def test_move_takes_a_snapshot_for_the_screen_size(device, backend):
    device.screen = (1001, 501)
    backend.mouse_move(500, 500)
    backend.mouse_move(2000, -3)
    assert device.snapshots == 1
    assert device.controls == [[["mouse_abs", 0, 0.5, 1.0, 0, 0]],
                               [["mouse_abs", 0, 1.0, 0.0, 0, 0]]]


def test_click(device, backend):
    backend.snapshot()
    backend.mouse_click("left", 2, 0, 1079)
    assert [unpaced(events) for events in device.controls] == [
        [["mouse_abs", 0, 0.0, 1.0, 0, 0]],
        [["mouse_abs", 1, 0.0, 1.0, 0, 0], ["mouse_abs", 0, 0.0, 1.0, 0, 0]],
        [["mouse_abs", 1, 0.0, 1.0, 0, 0], ["mouse_abs", 0, 0.0, 1.0, 0, 0]],
    ]


def test_click_where_the_pointer_is_needs_no_snapshot(device, backend):
    backend.mouse_click("right", 1, None, None)
    assert device.snapshots == 0
    assert [unpaced(events) for events in device.controls] == [[["mouse_abs", 2, 0.0, 0.0, 0, 0],
                                ["mouse_abs", 0, 0.0, 0.0, 0, 0]]]


def test_down_and_up_buttons(device, backend):
    backend.mouse_down("left")
    backend.mouse_down("middle")
    backend.mouse_up("left")
    backend.mouse_up("middle")
    assert [events[0][1] for events in device.controls] == [1, 5, 4, 0]


def test_scroll(device, backend):
    # koid scrolls up for positive notches; the Linkr scrolls down for
    # positive wheelV.
    backend.mouse_scroll(-45)
    backend.mouse_scroll(3)
    assert [unpaced(events) for events in device.controls] == [[
        ["mouse_abs", 0, 0.0, 0.0, 20, 0], ["mouse_abs", 0, 0.0, 0.0, 20, 0],
        ["mouse_abs", 0, 0.0, 0.0, 5, 0],
    ], [["mouse_abs", 0, 0.0, 0.0, -3, 0]]]



def test_scroll_by_nothing_sends_nothing(device, backend):
    backend.mouse_scroll(0)
    assert device.controls == []


# Relative mouse

@pytest.fixture
def relative(tmp_path, device):
    backend = make_backend(tmp_path, device.url, mouse="relative", mouse_step=100)
    device.screen = (300, 200)
    return backend


def test_relative_settings(tmp_path):
    with pytest.raises(ConfigError, match="mouse must be absolute or relative"):
        make_backend(tmp_path, "https://linkr.lab", mouse="sideways")
    for step in (0, 128):
        with pytest.raises(ConfigError, match="mouse_step must be from 1 to 127"):
            make_backend(tmp_path, "https://linkr.lab", mouse="relative", mouse_step=step)


def test_relative_move_goes_by_the_corner(device, relative, slept):
    relative.mouse_move(250, 150)
    assert device.snapshots == 1
    [events] = device.controls
    assert unpaced(events) == [
        ["mouse_rel", 0, -127, -127, 0, 0], ["mouse_rel", 0, -127, -73, 0, 0],
        ["mouse_rel", 0, -46, 0, 0, 0],
        ["mouse_rel", 0, 100, 100, 0, 0], ["mouse_rel", 0, 100, 50, 0, 0],
        ["mouse_rel", 0, 50, 0, 0, 0],
    ]
    # koid waits for the Linkr to play the events before it answers.
    assert slept == [6 * linkr.EVENT_DELAY_MS / 1000]


def test_relative_move_off_the_screen_stops_at_its_edge(device, relative):
    relative.mouse_move(1000, -5)
    moves = unpaced(device.controls[0])
    assert sum(event[2] for event in moves) == -300 + 299
    assert sum(event[3] for event in moves) == -200


def test_relative_drag_moves_on_from_the_last_position(device, relative):
    relative.mouse_move(10, 10)
    relative.mouse_down("left")
    relative.mouse_move(20, 5)
    relative.mouse_up("left")
    assert [unpaced(events) for events in device.controls[1:]] == [
        [["mouse_rel", 1, 0, 0, 0, 0]],
        [["mouse_rel", 1, 10, -5, 0, 0]],
        [["mouse_rel", 0, 0, 0, 0, 0]],
    ]


def test_relative_drag_by_nothing_sends_nothing(device, relative):
    relative.mouse_move(10, 10)
    relative.mouse_down("left")
    relative.mouse_move(10, 10)
    assert len(device.controls) == 2


def test_relative_click_and_scroll(device, relative):
    relative.mouse_click("left", 1, None, None)
    relative.mouse_scroll(2)
    assert [unpaced(events) for events in device.controls] == [
        [["mouse_rel", 1, 0, 0, 0, 0], ["mouse_rel", 0, 0, 0, 0, 0]],
        [["mouse_rel", 0, 0, 0, -2, 0]],
    ]

# ----------------------------------------------------------------------
# USB storage
# ----------------------------------------------------------------------

import hashlib
import io

from koidaemon import commands
from koidaemon.backends import linkr_storage
from koidaemon.errors import Unsupported
from koidaemon.uploads import LocalImage, PushedImage


def test_protobuf_round_trip():
    message = linkr_storage.encode([(1, 8), (2, "jwt"), (3, 0), (20, linkr_storage.encode(
        [(4, 300), (5, b"\x00\xff")]))])
    fields = linkr_storage.decode(message)
    assert fields[1] == 8 and fields[2] == b"jwt" and 3 not in fields
    assert linkr_storage.decode(fields[20]) == {4: 300, 5: b"\x00\xff"}


def test_protobuf_cut_short():
    with pytest.raises(ValueError):
        linkr_storage.decode(linkr_storage.encode([(2, "hello")])[:-1])


def test_password_hash():
    # As Radxa's harness-linkr hashes it.
    assert linkr_storage.hash_password("pw") == hashlib.sha256(
        b"RADXA_FIXED_SALT_v1pw").hexdigest()


@pytest.fixture
def storage_backend(tmp_path, device):
    (tmp_path / "password").write_text(device.password + "\n")
    return make_backend(tmp_path, device.url, password_file="password")


def local_image(tmp_path, size, name="disk.img") -> LocalImage:
    path = tmp_path / name
    path.write_bytes(bytes(index % 251 for index in range(size)))
    return LocalImage(path)


def stored_name(image) -> str:
    return linkr_storage.image_name(image.name, image.digest())


@pytest.fixture
def small_chunks(monkeypatch):
    monkeypatch.setattr(linkr_storage, "CHUNK_SIZE", 1000)


def test_no_storage_without_a_password(backend):
    assert commands.STORAGE_STICK not in backend.capabilities
    with pytest.raises(Unsupported, match="password_file"):
        backend.storage_status()


def test_storage_capability(storage_backend):
    assert storage_backend.capabilities >= {commands.STORAGE_STICK}
    assert commands.STORAGE_CDROM not in storage_backend.capabilities


def test_unreadable_password_file(tmp_path, device):
    with pytest.raises(ConfigError, match="cannot read"):
        make_backend(tmp_path, device.url, password_file="missing")


def test_wrong_password(tmp_path, device):
    (tmp_path / "password").write_text("wrong\n")
    backend = make_backend(tmp_path, device.url, password_file="password")
    with pytest.raises(BackendError, match="password incorrect"):
        backend.storage_status()


def test_insert_uploads_and_mounts(tmp_path, device, storage_backend, small_chunks):
    image = local_image(tmp_path, 2500)
    status = storage_backend.storage_insert(image, "stick", True)
    name = stored_name(image)
    assert status == {"inserted": True, "image": name, "mode": "stick", "writable": True}
    assert device.images[name] == image.path.read_bytes()
    assert device.mounted == name
    chunks = [m["request"][4] if 4 in m["request"] else 0
              for m in device.ws_messages if m["type"] == linkr_storage.UPLOAD_CHUNK]
    assert chunks == [0, 1, 2]
    start = device.ws_messages[0]["request"]
    assert start[3].decode() == hashlib.md5(image.path.read_bytes()).hexdigest()
    assert start[4] == 2500 and start[5] == 3
    assert name.startswith("koid-" + image.digest()[:12])


def test_insert_an_image_already_there(tmp_path, device, storage_backend):
    image = local_image(tmp_path, 100)
    storage_backend.storage_insert(image, "stick", True)
    storage_backend.storage_eject()
    device.ws_messages.clear()
    storage_backend.storage_insert(image, "stick", True)
    assert device.ws_messages == []
    assert device.mounted == stored_name(image)


def test_insert_unmounts_another_image_first(tmp_path, device, storage_backend):
    device.images["other.iso"] = b"x"
    device.mounted = "other.iso"
    image = local_image(tmp_path, 100)
    storage_backend.storage_insert(image, "stick", True)
    calls = [(method, path) for method, path, _ in device.storage_calls]
    assert ("POST", "/api/storage/unmount") in calls
    assert calls.index(("POST", "/api/storage/unmount")) < calls.index(
        ("POST", "/api/storage/mount"))
    assert device.mounted == stored_name(image)


def test_insert_the_mounted_image_again(tmp_path, device, storage_backend):
    image = local_image(tmp_path, 100)
    storage_backend.storage_insert(image, "stick", True)
    device.storage_calls.clear()
    storage_backend.storage_insert(image, "stick", True)
    # Re-plugging the Linkr's USB gadget for nothing would drop the keyboard.
    assert not [call for call in device.storage_calls if call[0] == "POST"]


def test_insert_read_only_is_refused(tmp_path, device, storage_backend):
    with pytest.raises(InvalidRequest, match="--writable"):
        storage_backend.storage_insert(local_image(tmp_path, 100), "stick", False)
    assert device.images == {}


def test_insert_as_a_cd_is_refused(tmp_path, storage_backend):
    with pytest.raises(Unsupported, match="USB stick"):
        storage_backend.storage_insert(local_image(tmp_path, 100), "cdrom", False)


def test_insert_a_pushed_image(tmp_path, device, storage_backend, small_chunks):
    data = bytes(range(256)) * 9
    digest = hashlib.sha256(data).hexdigest()
    image = PushedImage("pushed.img", len(data), digest, lambda size: io.BytesIO(data))
    storage_backend.storage_insert(image, "stick", True)
    assert device.images[linkr_storage.image_name("pushed.img", digest)] == data


def test_insert_a_pushed_image_that_is_not_what_it_said(tmp_path, device, storage_backend):
    data = b"a" * 100
    image = PushedImage("pushed.img", len(data), "0" * 64, lambda size: io.BytesIO(data))
    with pytest.raises(Exception, match="SHA-256"):
        storage_backend.storage_insert(image, "stick", True)
    assert device.images == {} and device.ws_messages == []


def test_upload_carries_on_after_the_token_expires(tmp_path, device, storage_backend,
                                                   small_chunks):
    device.expire_after_chunks = 2
    image = local_image(tmp_path, 4500)
    storage_backend.storage_insert(image, "stick", True)
    assert device.images[stored_name(image)] == image.path.read_bytes()
    chunks = [m["request"].get(4, 0) for m in device.ws_messages
              if m["type"] == linkr_storage.UPLOAD_CHUNK]
    # Two chunks, a refused third, then the rest after logging in again.
    assert chunks == [0, 1, 2, 2, 3, 4]
    assert device.logins == 2


def test_upload_with_no_space(tmp_path, device, storage_backend):
    device.no_space = True
    with pytest.raises(BackendError, match="no space"):
        storage_backend.storage_insert(local_image(tmp_path, 100), "stick", True)


def test_image_bigger_than_the_free_space(tmp_path, device, storage_backend):
    device.space = 50
    with pytest.raises(BackendError, match="50 bytes free"):
        storage_backend.storage_insert(local_image(tmp_path, 100), "stick", True)
    assert device.ws_messages == []


def test_login_again_when_the_token_expires(device, storage_backend):
    storage_backend.storage_status()
    device.expire_tokens()
    assert storage_backend.storage_status()["inserted"] is False
    assert device.logins == 2


def test_eject(tmp_path, device, storage_backend):
    storage_backend.storage_insert(local_image(tmp_path, 100), "stick", True)
    storage_backend.storage_eject()
    assert device.mounted == ""
    assert storage_backend.storage_status() == {"inserted": False, "image": None,
                                                "mode": "stick", "writable": True}


def test_eject_with_nothing_mounted(device, storage_backend):
    storage_backend.storage_eject()
    assert ("POST", "/api/storage/unmount", None) not in device.storage_calls
