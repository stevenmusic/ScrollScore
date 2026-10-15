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

`build/hall_ir.py` builds the earlier simulated hall (pyroomacoustics), which is no longer used.
