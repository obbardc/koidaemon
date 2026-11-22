# Still to test on hardware

What has been tried on real devices is in the README and each backend's
page under [docs](docs/). This is what has not been tried yet.
[docs/hardware-testing.md](docs/hardware-testing.md) is the list to
work through for a new backend or KVM.

## nanokvm-usb

Tested so far: status, snapshots, and the keyboard (keys, typing,
combinations) on a NanoKVM-USB in front of a Radxa Dragon Q8B, in its
UEFI menus and shell; and everything listed in
[docs/nanokvm-usb.md](docs/nanokvm-usb.md) in front of a Qualcomm
RB3gen2 running GNOME and a Lenovo ThinkPad T14s Gen 7 in ThinkPad
Setup.

- [ ] Why ThinkPad Setup on the T14s ignores the absolute mouse, and
      whether other firmware with a pointer does the same

## linkr

Tried with a Linkr on Ethernet, with its own power supply, in front of a
ThinkPad T14s Gen 7 in ThinkPad Setup (drawn on HDMI at 1280x800), and
in the GNOME live system of a qcom-deb-images installer image booted
from the Linkr's own virtual disk (HDMI at 1920x1080, as a second
monitor beside the laptop's panel), reading the Linkr's input devices
with a small evdev reader. Over USB-C the host saw a "Realtek Linkr USB
LAN" adapter but received no packets and got no DHCP lease.

- [x] Reaching the Linkr over Ethernet and HTTPS, with its self-signed
      certificate (CN localhost) as `ca_file`
- [x] The access token: accepted, and a wrong one refused with 403
- [x] `status`: the Linkr refuses an empty list of events ("control
      failed"), so koid sends a delay of 0
- [x] `snapshot`: JPEG, and the size koid reads from it (1280x800 in
      Setup). With no HDMI signal the Linkr answers "snapshot failed",
      which koid passes on
- [x] `keyboard.type`: text, Enter and tab; a 450-character script with
      quotes and newlines, typed into a terminal, ran as typed
- [x] `keyboard.press`, `.down`, `.up` with browser key codes, including
      ctrl+alt+delete (ctrl, alt and delete, in that order; GNOME opened
      its log-out dialog). Keys sent back to back in one request are
      lost: of 40 presses of down sent five to a request in Setup, 14
      arrived; with 20 ms between events, as koid now sends them, all 40
- [x] `keyboard.media`: AudioVolumeUp, AudioVolumeDown, AudioVolumeMute
      and Power arrive as KEY_VOLUMEUP, KEY_VOLUMEDOWN, KEY_MUTE and
      KEY_POWER on the keyboard. MediaPlayPause, MediaTrackNext, Eject,
      BrowserBack, LaunchApp2, WakeUp, F13 and Help send nothing, though
      the Linkr answers success; Sleep was not tried
- [ ] `mouse.move` and clicks land where they should with the absolute
      mouse. ThinkPad Setup ignores `mouse_abs`, as it does the
      NanoKVM-USB's absolute mouse. In GNOME with the laptop's panel and
      HDMI both on, the absolute mouse spans the whole desktop, not the
      screen the Linkr captures: asked for the middle of HDMI, the
      pointer landed 190 pixels from its left edge. Still to try with
      HDMI the only screen
- [x] Back and forward: button bits 0x08 and 0x10 arrive as BTN_SIDE and
      BTN_EXTRA, from both mice; 0x20 sends nothing. Each mouse declares
      eight buttons
- [x] `mouse = "relative"` in ThinkPad Setup: moves are 1:1, clicks land
      on the pixel asked, a move of more than 127 is cut to 127, and
      events closer together than about 10 ms are lost (docs/linkr.md)
- [x] `mouse.scroll`: a positive `wheelV` scrolls down, as Radxa's own
      client says, and each step is five notches (REL_WHEEL -5 for 1,
      -15 for 3, horizontally too), whatever the Linkr's `wheel_rate` and
      `wheel_mode` settings. ThinkPad Setup ignores the wheel
- [x] `status` with the password: model Radxa Linkr, firmware 1.0.0
- [x] USB storage over the private API (docs/linkr.md): login, list,
      space, upload over `/ws`, mount, unmount and delete, with a 4 MiB
      image and nothing on the Linkr's USB side
- [x] How a target sees a mounted image: a writable removable disk,
      never a CD (see docs/linkr.md)
- [x] `storage.insert`, `.eject` and `.status` through koid, with a 4 MiB
      image: uploaded, seen by the target with the right MD5, ejected,
      and inserted again without uploading
- [ ] Why one mount sent straight after an unmount took about 90 seconds
      to reach the target (not seen through koid)
- [x] What a wrong password gets from a real Linkr: HTTP 200 with code 1,
      "password incorrect"
- [x] Uploading a full-size image: 3.6 GB took 16 minutes, including
      koid hashing it on a worker with an SD card, about 3.3 MB/s; the
      Linkr keeps a partial upload as `NAME.incomplete`
- [x] Resuming an interrupted upload from `NextChunkIndex`: with koid
      stopped at 1.08 GB of 3.9 GB, inserting again carried on from
      there
- [x] Booting the target from a Linkr image: the qcom-deb-images
      installer image (MBR and FAT32, 3.9 GB) showed up in the T14s's F12
      menu as "USB HDD Linkr Virtual Media" and booted to GRUB and a live
      system, where Linux saw it as a removable USB disk, "Virtual Media"
- [ ] Why Debian's testing arm64 live GNOME ISO (a hybrid ISO, 3.6 GB),
      mounted the same way, was not in the F12 menu, even after a restart
