# Legal Office Management – Frontend

Arabic (RTL) single-page frontend for a law-office management system.
Plain HTML + CSS + vanilla JavaScript. **No framework, no build step, no dependencies.**

## Run
Open `index.html` in a browser. (Or serve the folder: `python3 -m http.server`.)
All data is demo data held in memory (`js/01-data.js`); nothing is saved on reload.

## Structure
```
index.html
css/style.css                         Layout + grayscale design tokens
js/01-data.js                         Demo data (`db`) and constants (lawyers, statuses, stages)
js/02-core.js                         Helpers, router, shared UI pieces (tables, forms, drawer, toast), event delegation
js/03-shell.js                        Sidebar, top bar, global search, "New" menu
js/04-dashboard-cases.js              Form schemas, generic sub-collection handlers, Dashboard, Cases list + detail
js/05-sessions-clients-finance.js     Sessions, Clients (+detail), Invoices, Expenses
js/06-enforcement-office-files.js     Enforcement cases (+detail), Office files: general / companies / lands (+detail)
js/07-main.js                         Boot
```

## Pages (hash routes)
`#dashboard` `#cases` `#case-ID` `#sessions` `#clients` `#client-ID` `#invoices`
`#exec` `#exec-ID` `#office` `#office-ID` `#expenses`

## How it works
- **Routing:** `location.hash` -> `PAGES[name](id)` returns an HTML string -> rendered into `#page`.
- **Events:** one delegated listener per event type. Elements declare behaviour with data attributes:
  `data-go="case-1"` navigate, `data-act="name"` -> `ACT[name]`, `data-form="name"` -> `FORM[name]`,
  `data-change`/`data-input` -> `CHG`/`INP`. No inline JavaScript in templates.
- **Forms:** schemas in `SCH` (04-dashboard-cases.js) drive the drawer forms; inline "quick add" forms use `inl()`.
- **Sub-collections** (procedures, plan, expenses, papers, tasks...) share generic handlers: `FORM.subAdd`, `ACT.subDel`, `ACT.subToggle`.
- **Styling:** layout only, in grayscale (no colors, no shadows). All colors are variables in `:root` at the top of `css/style.css`, so a color scheme can be added later by editing those values.

## Add a page
1. `PAGES.myPage = id => head({title:'...'}) + ...` and (for lists) `LIST.myPage`.
2. Add `ACT`/`FORM` handlers.
3. Add an entry to `NAV` in `03-shell.js`.

## Connecting a real backend later
Replace reads of `db.*` with API calls and the mutations inside `ACT`/`FORM` handlers with requests.
Keep ids as the links between entities (case.clientId, session.caseId, ...).
File uploads currently use `URL.createObjectURL` (memory only) and need real storage.

## Known limits of this build
- No authentication, roles, or multi-office (tenant) separation yet.
