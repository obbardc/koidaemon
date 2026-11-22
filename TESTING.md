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
