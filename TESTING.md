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
ThinkPad T14s Gen 7 in ThinkPad Setup (drawn on HDMI at 1280x800). Over
USB-C the host saw a "Realtek Linkr USB LAN" adapter but received no
packets and got no DHCP lease.

- [x] Reaching the Linkr over Ethernet and HTTPS, with its self-signed
      certificate (CN localhost) as `ca_file`
- [x] The access token: accepted, and a wrong one refused with 403
- [x] `status`: the Linkr refuses an empty list of events ("control
      failed"), so koid sends a delay of 0
- [x] `snapshot`: JPEG, and the size koid reads from it (1280x800 in
      Setup). With no HDMI signal the Linkr answers "snapshot failed",
      which koid passes on
- [ ] `keyboard.type`: text, Enter and tab; long text over several
      requests arrives in order (a request returns at once, in about half
      a second even with a delay of 2000 in it)
- [ ] `keyboard.press`, `.down`, `.up` with browser key codes, including
      ctrl+alt+delete
- [ ] `mouse.move` and clicks land where they should. ThinkPad Setup
      ignores `mouse_abs`, as it does the NanoKVM-USB's absolute mouse
- [ ] `mouse.scroll`: does a positive `wheelV` scroll down, as Radxa's
      own client says?
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
- [ ] Uploading a full-size ISO: speed, and resuming an interrupted
      upload from `NextChunkIndex`
