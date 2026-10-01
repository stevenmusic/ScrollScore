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
