# Music library and YouTube playlists

This folder contains optional, operator-provided music for the local Sing Yin roster workspace.

- Playback is manual. The website never starts music on page load.
- Built-in page playlists can run in sequential loop or shuffle loop mode.
- Custom local audio is imported from **Settings** into `music/custom/`; accepted formats are M4A, MP3, OGG, and WAV, up to 25 MB per file.
- Settings can store public YouTube playlist IDs in `music/youtube-playlists.json`. The normal visible player is free, needs no sign-in, and never autoplays.
- `SING_YIN_YOUTUBE_API_KEY` is optional and enables public in-app search only. Keep it in `.env`; never commit it or paste it into the interface.
- YouTube remains a visible control window with its own play, pause, volume, and track controls. It must not be hidden, reduced to audio-only playback, or placed behind roster data.
- Roster publication, published-duty adjustment, backup restore, errors, tables, names, and fairness records do not contain music controls.
- These files were supplied for controlled local use. Confirm copyright and distribution permission before enabling remote access or sharing the application beyond the approved school environment.

Future Head Study Prefects should use the in-app Settings guide rather than renaming or deleting built-in files manually. Music preferences are operator conveniences and are never part of roster, fairness, audit, PDF, backup, or advisor-review records.
