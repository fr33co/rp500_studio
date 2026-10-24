# RP500 Studio

**RP500 Studio** is a desktop editor for the **DigiTech RP500** multi-effects pedal on Linux. It follows the approach of
[gdigi](https://github.com/desowin/gdigi) — every effect type and parameter, preset banks, storing presets — with a modern
interface inspired by the pedal itself: an amber LCD for the preset, a chassis-style panel with metal footswitch-like
buttons (one colour per effect) and hardware knobs with LED rings.

> Unofficial project, not affiliated with DigiTech or Harman. It speaks the pedal's USB-MIDI SysEx protocol, documented by
> the gdigi project. **Use it at your own risk**: it writes to the pedal's memory.

## What it does

- **Connection screen**: looks for the RP500 over USB and connects when you click the device. If it is unplugged, the app
  returns to that screen on its own.
- Amber LCD showing the preset number/name, the selected block and the last parameter you touched; it follows preset
  changes made on the pedal itself.
- Lists the 100 user presets and the system presets (with search) and loads the one you pick on the pedal.
- Signal chain Wah → Amp → Cab → EQ → Compressor → Distortion → Gate → Mod/FX → Delay → Reverb, with a power switch and a
  category icon per block.
- Every effect type with its real parameters, ranges and units, as knobs. Changing the type resets the parameters to the
  pedal's defaults for that type, exactly as the pedal does.
- **Expression pedal** block: assigned parameter plus Min/Max.
- Live editing: changes go to the pedal's edit buffer (RAM) as you turn the knobs; the pedal's own panel follows.
- **Save to…** writes the edit buffer to a user preset, after confirmation and after saving a backup of the preset it replaces.
- File menu: export/import `.rp500p` (the XML format used by gdigi) and back up all 100 user presets.
- 8 colour themes. Drop-downs open inside the window (native Qt popups close on mouse release under Wayland).

## Status

| Feature | Status |
|---|---|
| Reading presets, names and the edit buffer | Tested with the pedal (firmware 2) |
| Live editing, switches, effect types, expression pedal assignment | Tested with the pedal |
| Saving to a user preset (flash) with read-back check | Tested on a scratch preset |
| `.rp500p` export/import round trip | Tested with the pedal |
| Pedal → app sync of knobs moved on the pedal | Implemented, not verified |
| Amp/Cab bypass polarity | Deduced from gdigi, not verified by ear |
| Files written by gdigi itself | Not tested |
| System bank editing, bank-change detection, LFOs (RP355 only) | Not implemented |

## Requirements

- Linux with ALSA (`amidi`) and Python 3.10+
- `PyQt5` (`pip install PyQt5` or your distribution's `python3-pyqt5`)
- The RP500 connected over USB. Your user must be able to open `/dev/snd/midiC*D*` (the `audio` group). The ALSA port is
  exclusive: close gdigi or any other program that uses the pedal.

## Installation (.deb package)

```
sh packaging/build_deb.sh            # builds dist/rp500-studio_0.2.0_all.deb
sudo apt install ./dist/rp500-studio_0.2.0_all.deb
rp500-studio
```

It installs the app in `/usr/lib/rp500-studio` and depends on `python3-pyqt5` and `alsa-utils`. Backups are stored in
`~/.local/share/rp500-studio/backups/`.

## Usage

```
cd rp500_linux
python3 run.py
```

## Credits and license

The SysEx protocol and the effect/parameter tables (`rp500_linux/rp500/data/*.json`) were derived from
[gdigi](https://github.com/desowin/gdigi) by Tomasz Moń, so this project is released under the **GNU GPL v3 or later**
(see `LICENSE`).
