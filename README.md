# আলো

A birthday page, made for one person, opened on a phone.

One HTML file, no build step, no framework, no dependencies. It is a single
continuous scroll in four acts:

| | | |
|---|---|---|
| **০** | The envelope | she breaks the wax seal, the flap unfolds, the card rises |
| **১** | The cake | five candles; she blows at the mic, or taps a button |
| **২** | The scratch card | gold foil she rubs away with a finger to find a note |
| **৩** | The reasons | a swipeable deck, one reason per card, a photo on each |

Her name is a deliberate pun on the whole design: **আলো** means *light*, so the
candles, the glow, the foil and the closing line all point back at it. When the
last candle goes out the whole page warms from cream to dusk.

---

## Preview it

Any static server works. From this folder:

```sh
py -3 -m http.server 8765
```

then open <http://127.0.0.1:8765/>.

Or just double-click `index.html` — it works that way too, photos and all. The
photo list is emitted as a `<script>` (`photos/web/photos.js`) rather than fetched
as JSON, because a browser blocks `fetch` of a local file on `file://` but allows
a plain script. That matters: if you ever hand her the folder instead of a link,
nothing is missing.

To preview as a phone, open DevTools → toggle device toolbar → pick a phone.

## Add or change photos

Drop the originals into `photos/` (jpg, png, webp, heic, bmp, tiff — HEIC needs
`py -3 -m pip install pillow-heif`, which the script will tell you about), then:

```sh
py -3 tools/prepare_photos.py
```

It writes `photos/web/` — the originals stay untouched, and the originals are
**not** published (see `.gitignore`). Each photo becomes two crops:

- `-panel.webp` `4:3` — the photo at the top of the scratch card
- `-band.webp` `3:2` — the strip across a reason card
- plus a 12px blur, inlined in the manifest so the page has something warm to
  paint before the real image arrives

Order is the alphabetical order of filenames, so rename to `01-…`, `02-…` to
control it. If a crop cuts someone's head off, add or adjust that file's entry in
`FOCUS` at the top of the script — it is the point the crop is centred on, as a
fraction of width and height.

```sh
py -3 tools/prepare_photos.py --check   # report sizes and crops, write nothing
```

## Change the words

Everything she reads is near the top of the `<script>` in `index.html`, marked
`✎ EDIT THESE`:

- `REASONS` — the deck. Each card shows the Bangla line large, the English line
  small beneath it. Add or remove freely; the counter follows.
- The hero and closing lines are in the markup — search for `ALO` and `সবসময়`.

The scratch card's note is in `.scratch-note` in the markup.

## Publish

The page is static and has no server needs. On GitHub:

```sh
git remote add origin https://github.com/<you>/birthday.git
git push -u origin main
```

Then Settings → Pages → Source: *Deploy from a branch* → `main` / `/ (root)`.
It serves at `https://<you>.github.io/birthday/`. Pages needs a **public** repo
on the free plan.

`.nojekyll` is already here so Pages serves the files byte-for-byte.
`<meta name="robots" content="noindex, nofollow">` and `robots.txt` keep it out
of search results — a link you send is the only way in.

---

## What it does on a bad connection

Worth knowing, because she will open this on mobile data, probably somewhere
noisy, possibly on an old phone.

- **Whole page** is ~16 KB gzipped. The only external request is Google Fonts.
- **First paint** does not wait for photographs: the seal and the envelope are
  pure CSS and SVG. The hero photo is a 12px blur that is *inside* the manifest,
  so it needs no request of its own, and the real image swaps in when decoded.
- **Deck photos** are held until the deck is within 300 px of the viewport, so
  they never compete with the hero.
- **All sixteen crops** total ~1.2 MB, sized for a 390 pt phone at DPR 3 —
  sharper than it can display.
- **The mic is never requested on load.** It asks only if she taps "মাইক দিয়ে ফুঁ
  দিতে চাই", and if she denies it the button path still works and the page says
  so plainly.
- **No JS** — the page is still a complete, readable card (the `<noscript>` at
  the bottom). Nothing is trapped behind a button that cannot fire.
- **`prefers-reduced-motion`** — no dust, no confetti, no flicker, no delays.
  Every act still completes; it simply does not move.
- **Fonts blocked** — falls back to a Bangla system face and a Latin serif; the
  layout holds and nothing overflows.
- **Reloading** after she has opened it does not trap her at the envelope again.

## Files

```
index.html              the whole experience
photos/                 originals (not published) + web/ derivatives (published)
photos/web/photos.js    the photo list the page loads (generated)
tools/prepare_photos.py the crop-and-compress pipeline
.nojekyll               tells GitHub Pages to serve files untouched
robots.txt              keep it out of search engines
```
