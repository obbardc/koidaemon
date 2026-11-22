# Testing a backend on hardware

The unit tests run every backend against fakes, which only show that
koid sends what it was written to send. Whether a real KVM does the
right thing with it, and what the target makes of it, can only be found
out on hardware. This is how the backends so far were tried, as a list
to work through for a new backend or a new KVM.

Record what was tried in the backend's page under [docs](.), what has
not in [TESTING.md](../TESTING.md), and keep the README's summary in
step with both.

## What you need

- A KVM, and a target in front of it that can run both firmware (UEFI
  setup menus, a UEFI shell) and an operating system with a desktop.
  Each finds different problems: firmware is slow to read its keyboard
  and usually has no pointer, while a desktop has acceleration, hot
  corners and several screen resolutions.
- A way to get the target to a known state without the KVM, such as a
  serial console or a lab job that boots it and then waits. Keep it
  booting what it already has: there is no need to flash it again for
  each round of testing.
- A koid of its own for testing, with its own configuration and socket,
  so that a mistake does not disturb a koid others use. The NanoKVM-USB
  only opens its devices while it runs a command, so several targets can
  name the same device with different settings (`mouse = "relative"`,
  `key_interval = 0`, another capture size) and be switched between
  without restarting koid. Check that the backend allows this before
  relying on it.

Note the versions: the KVM's firmware or chip version (`status` often
has it), the target, and what it was running.

## Seeing what the target got

A snapshot only shows what the target chose to draw. To see what
actually arrived:

- **A terminal on the target.** Open one through the KVM: on GNOME,
  `super`, type `terminal`, `enter`. Typed text then shows up exactly
  as received, and commands such as `gdctl show --modes` or
  `cat /sys/power/mem_sleep` can be run and read from a snapshot.
- **The input devices.** The KVM's keyboard, mouse and media keys show
  up as devices under `/dev/input/`. `evtest` or `libinput debug-events`
  show what each sends; if the target has neither, this does the same,
  and is short enough to type through the KVM:

  ```python
  import struct, sys
  f = open(sys.argv[1], "rb")
  while True:
      _, _, kind, code, value = struct.unpack("llHHi", f.read(24))
      if kind:
          print(kind, code, value, flush=True)
  ```

  Run it with `sudo python3 ev.py /dev/input/eventN`. Not every device
  has a link under `/dev/input/by-id/`, so look in
  `/proc/bus/input/devices` for its `eventN`. The codes are in Linux's
  `input-event-codes.h`.
- **The pointer in the snapshot.** Most KVMs capture the pointer with the
  picture. After `mouse move X Y`, crop the snapshot around (X, Y) and
  mark that pixel: the pointer's tip should be on it.
- **The target's own logs.** `journalctl -f` in the terminal, or the
  serial console, for what a power or sleep key did.

## Checklist

Go through each capability the backend has. When something fails,
find out whether the KVM, the target or koid is at fault before
writing it down.

### status

- [ ] With the target running: every field is there and sensible.
- [ ] With the target off: what `status` says, and whether it can tell.
- [ ] With the KVM unplugged or unreachable: koid fails cleanly and
      recovers when it comes back.

### Snapshots

- [ ] At each capture size the backend can ask for, and the size it
      reports.
- [ ] With the target at another resolution from the capture, including
      another shape (a 4:3 or 5:4 mode with a 16:9 capture): whether the
      KVM scales, stretches, adds borders or fails. On GNOME,
      `gdctl show --modes` lists the modes the target offers, and
      `gdctl set --logical-monitor --primary --monitor HDMI-1 --mode
      1024x768@60.004` switches to one.
- [ ] With no signal, such as the target off or asleep: whether
      `snapshot` fails or returns a blank picture, and what that looks
      like.
- [ ] How long a snapshot takes, and whether the first frame is whole.

### Keyboard

- [ ] Type mixed-case text with every shifted symbol into a terminal,
      and compare what appears.
- [ ] Combinations: `ctrl+alt+t`, `super`, a lone modifier, a key held
      with `keyboard down` across other commands.
- [ ] In firmware: a run of arrow keys in a setup menu. Firmware misses
      keys pressed and released too quickly, so this is where a pause
      between reports, like the NanoKVM-USB's `key_interval`, is found.
- [ ] Lock lights (caps, num, scroll) in `status`, if the KVM reports
      them.

### Media and system keys

- [ ] Each key arrives with the right code, checked on the input device.
- [ ] `power` only after making it harmless (on GNOME,
      `gsettings set org.gnome.settings-daemon.plugins.power
      power-button-action nothing`).
- [ ] `sleep` last of all, since the target may not wake again; then
      `wake`, a key and the mouse, to see whether anything brings it
      back.

### Mouse

- [ ] Aim at pixels in a snapshot, near the middle and near each edge,
      and check where the pointer lands, at each capture size and with
      the target at each resolution tried for snapshots.
- [ ] Click, double click (`--count 2`), and drag (`mouse down`, `mouse
      move`, `mouse up`): select text in a terminal or move a window.
- [ ] Every button the backend lists, checked on the input device:
      right and middle may do nothing visible.
- [ ] The wheel both ways, and a modifier held across a click.
- [ ] A relative mouse, if the backend has one: with the desktop's
      pointer acceleration on and off, and with the target at another
      resolution from the capture.

### USB storage

- [ ] `storage insert` as a stick and as a CD: the target sees the disk
      (`lsblk`, `dmesg`) and can read it, and the image's checksum
      matches.
- [ ] `--push-file`, and inserting the same image twice.
- [ ] `storage eject`: the disk goes away on the target.
- [ ] Booting from it, if the target's firmware can.

### kvm.reset

- [ ] With the target running: how long it takes, what the target sees
      (the devices unplugged and plugged in again?), and how long until
      it takes input again.
- [ ] With the target off.

## Pitfalls

- **Lock screens eat keys.** A desktop that has just started or woken
  may show a lock screen that drops the first keys: on the RB3gen2,
  GNOME's ignored `escape` but woke on a click. Take a snapshot before
  typing.
- **Desktop settings get in the way.** On GNOME: pointer acceleration
  throws off a relative mouse, the top-left hot corner opens the
  overview, and middle-click paste may be off, so a middle click shows
  nothing. Turn them off with `gsettings` for the test, and note that
  you did.
- **Killing processes over ssh.** `pkill -f PATTERN` also matches the
  ssh session's own command line if it contains the pattern, and kills
  it. Kill by process ID instead.
- **The KVM decides the modes.** A KVM tells the target what monitor it
  is (its EDID), so the target offers the modes the KVM lists, not
  those of any screen behind it.
