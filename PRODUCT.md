# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Phase 1: a single self-contained HTML page published as a Claude artifact, using the artifact `db` capability for storage (accessible from any device signed in to Claude). Data access lives behind one small storage adapter so the same code can later move to the user's own server as an installable PWA with Supabase (Postgres + auth) and offline support. Framework choice inside the page: delegated.

## Users

One person: a Greek guitarist who plays live in venues, in rehearsals with other musicians, and at gatherings and feasts (παρέες, γλέντια). The app is for them alone; bandmates do not view or edit. They use phone, tablet and laptop equally, for both playing and managing the library.

## Product Purpose

My Songbook replaces physical songbooks and folders of handwritten/printed lyrics with chords. It is a personal, searchable, editable library of 100–500 songs, organized into ordered setlists and unordered collections, with a clean display for playing. Success: on stage, the right song is on screen in seconds, readable at a glance; at home, adding or correcting a song takes a minute.

## Positioning

Unlike public chord sites (kithara.to), it is a private library shaped by the player's own versions, notes and set order; chords are stored as structured data bound to syllables, so they stay aligned when lines wrap on a phone and transpose reliably.

## Operating Context

- Live stage / venue: low or uneven light, hands on the guitar, glances between strumming, setlist played in order, next song needs to be ready.
- Rehearsals and γλέντια: requests shouted out ("παίξε εκείνο το…"), fast search by title or artist is critical.
- Management on any device: pasting songs from kithara.to (chord line above lyric line, monospace, repeat marks like `| 2x`), from text/PDF, or photos of handwritten pages.
- Some lists are played from full lyrics+chords; other lists are used only as a cue sheet showing title and key.

## Capabilities and Constraints

- A song exists once; collections reference songs and keep their own order; a song can be in many collections and have many tags.
- Song fields: title, artist, key, genre(s), rhythm, time signature, notes (e.g. «αργά», «κάπο στο 2»), lyrics with chords. Incomplete songs (title only) allowed.
- Chords are Latin notation (Am, D7, F#m). Repertoire: λαϊκά/ρεμπέτικα, έντεχνα/ελληνικό rock, παραδοσιακά/νησιώτικα.
- Song versions kept; transposition; chord validation.
- Performance: adjustable font size, autoscroll, prev/next within a collection, instant transpose, keep screen awake (may be limited inside the artifact), keyboard/Bluetooth pedal support.
- Collections have a display mode: full song (lyrics+chords) or cue list (title + key).
- Import: paste text (kithara format), text files, PDF, photo (OCR via Claude). Export single songs, collections, and full backup.
- UI language: Greek.

## Brand Commitments

The user chose the category standard over distinctive visual worlds: a clean, conventional songbook-app look, executed at the craft level of SongbookPro, Ultimate Guitar and OnSong. No themed or decorative world; familiarity is the goal.

## Evidence on Hand

No songs supplied yet. Demo content must be labeled sample data; do not reproduce copyrighted lyrics in full from real songs for demos.

## Product Principles

1. On stage, nothing stands between the player and the next chord.
2. One song, many places: never duplicate content.
3. The player's version wins: notes, keys and order are personal.
4. Entering a song should be as fast as pasting it.
5. Every device is a first-class citizen.

## Accessibility & Inclusion

Must remain legible at arm's length on a music stand in dim light; large touch targets usable between strums.
