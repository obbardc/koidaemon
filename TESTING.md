# Still to test on hardware

What has been tried on real devices is in the README and each backend's
page under [docs](docs/). This is what has not been tried yet.

## nanokvm-usb

Tested so far: status, snapshots, and the keyboard (keys, typing,
combinations) on a NanoKVM-USB in front of a Radxa Dragon Q8B, in its
UEFI menus and shell; and snapshots, typing and single left clicks in
front of a Qualcomm RB3gen2 at the GNOME login screen. In a GNOME
session on the RB3gen2, a modifier pressed on its own also works:
`keyboard press super` opens and closes the overview.

- [x] `mouse.move`: a pixel position lands where it should on the
      snapshot, at 1920x1080 on the RB3gen2. (The device is told 0..4095
      scaled by the snapshot size.)
- [ ] `mouse.click`: a single left click works; not yet `--count 2` or
      the other buttons
- [ ] `mouse.down` / `mouse.up`: a drag
- [ ] `mouse.scroll`: does a positive number scroll up?
- [ ] `keyboard.down` held across other commands, e.g. shift held while
      clicking
- [ ] Capture sizes other than 1920x1080 (`width`/`height`), and a target
      running at a different resolution from the capture size
- [ ] Whether the 50 ms `key_interval` is needed once Linux is running,
      or only in UEFI
- [ ] `keyboard.media`: the bit for each key is from the CH9329
      protocol and has not been tried, e.g. that `volumeup` shows the
      GNOME volume OSD and `calculator` opens a calculator
- [ ] `mouse = "relative"`: whether a move lands where it should with
      GNOME's flat acceleration profile, and in a UEFI with a pointer
