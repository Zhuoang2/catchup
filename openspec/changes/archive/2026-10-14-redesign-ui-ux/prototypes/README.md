# UI prototypes for `redesign-ui-ux`

Static HTML prototypes used to choose the visual direction for #24. They are design references, not application code.

- `index.html` lists every direction. **C7 · Front page grid** was chosen on 2026-10-06.
- `shared/` contains the sample data (`data.js`, taken from the 2026-10-05 manual test), the renderer for all screens and states (`render.js`), shared structure (`base.css`), and the prototype control bar (`proto.css`).
- `directions/` contains one stylesheet and page per direction. C7 loads `c.css` → `c3.css` → `c3b.css` → `c7.css`, and sets `DIRECTION.rail`.

To view them, run this from this folder and open http://127.0.0.1:5180/:

```bash
python3 -m http.server 5180 --bind 127.0.0.1
```

Use the bar at the top of a prototype to switch direction, screen, state, light/dark, and a 420 px window.
