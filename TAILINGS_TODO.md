# Solid waste (tailings, coal ash) — paused (since v0.8)

Solid waste support is switched off while the water-dam workflow is
finalised. The code is intact: set `SOLID_WASTE_ENABLED = True` near the top
of `app.py` to bring back the dam type choice, the Tailings release page, the
tailings case histories, bulked hydrographs and the tailings report section.
Test cases S1 and S2 are in `test_cases/solid_waste_paused/`.

Fix these before switching it back on.

## From Nahyan's v0.7 testing (4 October 2026)

1. **Plots on Tailings release do not update when inputs change.** The
   charts draw before some of the inputs that feed them, so a change shows
   only on the next interaction. Reorder the page so every input is read
   before anything is drawn (or draw into placeholders filled at the end).
2. **Spikes near t = 1 h in the tailings, bulked and water hydrographs**
   (S1 and S2).
   - Likely cause (inference, not yet confirmed by a re-run): the S1/S2
     stage-storage tables hold 42 rows of zero volume from 0 to 21 m. When
     the pond drains to 21 m, the level cannot be found from the volume.
     Model setup now warns about flat ranges. Re-run S1 and S2 with a single
     zero row at 21 m to confirm.
   - The cone of depression method makes the tailings rate from
     `np.gradient` of the cone volume, which turns any jump in breach width
     or invert into a spike. Smooth or rate-limit it, or present the cone as a
     volume only.
3. **"Sensitivity: tailings in the stage-storage" card does nothing** unless
   the cone method is chosen and shown on the cross-section, and even then
   it only describes the idea. Either build it (route the cone volume as
   water on top of the pond, run, compare) or remove it.
4. **Two hydrographs, unclear relationship.** Tailings release shows water,
   tailings and bulked; Single run shows water and bulked. Decide on one home
   for the bulked hydrograph (suggest Single run, with Tailings release
   showing volumes only), and label which DLBreach run it comes from.
5. **Unclear whether a page is running the water or the tailings case.**
   Show the dam type in the status strip and in each run's title, and say on
   Single run that DLBreach itself always routes clear water.
6. **Colours:** solid waste orange, pond water blue. Done in the drawings
   and chart colours in v0.8; check the Tailings release page charts once it
   is back on.

## Carried over from the v0.7 handover

- Rana et al. (2023, TMW) full citation for the Fig. 5 reference.
- Per-run tailings release for browser-mode Monte Carlo uploads is untested
  on real outputs.
- Solid waste help text: `dlbreach_help.py` has no entries yet for the
  Tailings release page fields.
- Interpretation flags to keep: cone of depression, uniform bulking, cone
  growth taken as release rate.
