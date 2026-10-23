# Piano samples

ScrollScore's piano. Yamaha C5 grand, 30 sampled notes (every minor third from A0 to C8) × 16 velocity layers, plus:
- release string resonance (`harmL*` / `harmS*`)
- key-release noise (`rel*`)
- pedal noise (`pedal*`)

**Source:** *Accurate-Salamander Grand Piano V6.2* (Chisato Yamauchi, https://github.com/cyamauch/NoctSalamanderGrandPiano), built from its published scripts. That build is a remaster/retune of *Salamander Grand Piano V3* by Alexander Holm, licensed CC-BY 3.0 (https://creativecommons.org/licenses/by/3.0/).

**Changes made for ScrollScore** (scratch build script `pf_build.py`):
- resampled to 48 kHz and converted to 16-bit FLAC with TPDF dither;
- pre-attack silence trimmed;
- tails cut at the noise floor or at a register-dependent length (16 s in the bass to 2.5 s at the top), then faded;
- the spaced stereo pair made mono-compatible: energy-preserving mid, side ×0.45, placed bass-left/treble-right, with the original loudness calibration restored.

`manifest.json` lists the following, which the app reads:
- velocity ranges and amp_veltrack 98.5 (Accurate-Salamander V6.2);
- per-key tuning in cents (retuning by Hiroharu Narikawa);
- per-sample loudness and length;
- `d`: the level offset from the original V3 recording, used to scale the release sounds the way the V3 SFZ does.

## Concert hall reverb (`hall.flac`)

The piano's reverb impulse response is a real measured concert hall: the Detmold Konzerthaus (about 600 seats), taken from

> S. V. Amengual Garí, B. Şahin, D. Eddy, M. Kob, *Open Database of Spatial Room Impulse Responses at Detmold University of Music*, 149th AES Convention, 2020. https://zenodo.org/records/4116247, licensed CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).

The measurement used is Set C, source S2 (a Neumann KH 120 A on the front of the stage) to seat 57 (third row, centre), recorded with an omnidirectional and a figure-of-eight microphone.

**Changes made for ScrollScore** (build script `build/hall_detmold.py`):
- the omni and figure-of-eight responses combined into M/S stereo (L = M + 1.2·S, R = M − 1.2·S);
- the measurement loudspeaker's high-frequency roll-off on axis compensated (+1.5 dB at 4 kHz, +4 dB at 8 kHz, +5.4 dB at 16 kHz);
- the direct sound removed, with time zero at its arrival;
- the tail, which the original files cut off at about 1.45 s, extended with noise that follows each frequency's measured decay rate and stereo correlation;
- written as 48 kHz 16-bit stereo FLAC.

## Room microphone layer (`room.flac`)

Early reflections of a real measured chamber music hall, from the same database (CC BY 4.0): Set A, the Brahmssaal of the Detmold University of Music (17.4 × 8.1 m, two grand pianos on stage), source S1 (Neumann KH 120 A, centre stage), receivers R2 (first row) and R3 (third row), front omnidirectional capsule of the open array. R2 is used as the left channel and R3 as the right, like a spaced pair of room microphones.

**Changes made for ScrollScore** (build script `build/room_brahms.py`):
- each channel aligned to its own direct-sound arrival, and the direct sound removed;
- the same loudspeaker high-frequency compensation as `hall.flac`;
- below 250 Hz the two channels pulled halfway toward their average;
- only the first 0.35 s kept (full level to 0.12 s, then a cosine fade-out);
- written as 48 kHz 16-bit stereo FLAC.

## Sympathetic resonance (`sympa.flac`)

Synthesized by `build/sympa_ir.py` (all 88 strings as resonators). Since 2026-10 each partial reaches the left and right channel with its own random phase and level above about 500 Hz, the way a soundboard radiates to two microphones.

`build/hall_ir.py` builds the earlier simulated hall (pyroomacoustics), which is no longer used.
