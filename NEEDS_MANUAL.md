# Locale gaps needing a native speaker

This locale-parity batch adds machine-translated files across 12 locales.
Every added line is a candidate for native review, not a verified
translation.

`fa-IR` shipped only `skill.json` before this change; it now has the full
intent and dialog/voc set except two files the MT route
(`m2m100-418M-int8`) could not produce anything usable for:

- `volume.max.boost.intent`: every phrasing tried for "crank [the] volume
  [up]" / "turn [the] volume all the way up" produced unrelated hallucinated
  text (including, on one attempt, an unrelated religious quotation).
  Dropped entirely rather than shipped. Needs a native speaker to write it
  directly.
- `volume.mute.toggle.intent`: "toggle [the] (mute|muting|audio|sound|volume)"
  produced either unrelated text or a degenerate repetition loop on every
  phrasing tried. Dropped entirely. Needs a native speaker to write it
  directly.

Several other `fa-IR` lines needed a manual pass after the direct MT output
was reviewed and found wrong before this PR was opened (not by a native
speaker, by inspection against back-translation): "mute"/"unmute" on their
own translate to non-words or unrelated concepts through this route, and a
few "turn up/down the volume" phrasings degenerated into repetition or
unrelated text. Those lines were rebuilt from alternate English phrasings
that this route renders correctly (verified by back-translating fa->en).
They still need a native speaker's review before they are trusted, same as
every other line here — the manual pass only removed clear defects, it did
not verify correctness.

The other 11 locales (`ca-ES`, `da-DK`, `de-DE`, `es-ES`, `eu-ES`, `fr-FR`,
`gl-ES`, `it-IT`, `nl-NL`, `pt-BR`, `pt-PT`) each gained exactly two files,
`volume.level.unknown.dialog` and `level.medium.voc`, machine-translated
cleanly on the first pass.
