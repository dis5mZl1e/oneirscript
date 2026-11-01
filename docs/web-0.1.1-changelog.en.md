# Web 0.1.1 Changelog

## Web Frontend Redesign: Dream Archive

- Replaced glass-heavy rounded surfaces with dark paper, fine dividers and restrained category colors across the home screen, workspaces and dialogs.
- Added compact resource readouts, revised navigation and map/content proportions, and desktop/narrow-screen layouts.
- Desktop inventory details and slots scroll independently. Item actions remain visible while the description scrolls.
- Separated construct cards from their previews and firing-source headings, statistics, magazines, availability reasons and actions.
- Added journal timelines, task progress cards and grouped personal statistics; revised board, tamper, codex and settings reading layouts.
- Split new-game controls and save slots into columns on wide home screens.

> Release note: the desktop 0.1.1 build was released on 2026-11-01 (eight Chinese/English packages for Windows, Linux and macOS, plus a source archive and checksums). The web frontend source is maintained in the development repository and is not included in this desktop-source repository; no separate web release package was produced. See the [v0.1.1 Release](https://github.com/dis5mZl1e/oneirscript/releases/tag/v0.1.1).

## Latest Desktop Features

- Added a default five-column inventory grid, scrolling and a list toggle. Clicking uses items while keeping the inventory open. Large icons use font outlines, with separate quantity and equipped-star overlays.
- Added category backgrounds, rarity borders, creased frame corners and a wooden selection frame. Item details appear above the grid, with collapsible serif descriptions.
- Construct cards show category colors and type effects. Card bodies select; the Cast button or Enter activates.
- Firing cards show weapon values, magazine counts and reload controls. Aim remembers the previous source, advances reload steps for empty magazines, and switches to the next consumable source when exhausted.
- Gas density uses three distinct dot patterns; liquid glyphs remain bottom-aligned. Removed stray material edge lines and included updated plant and item fonts. PUA glyphs are enabled by default.
- Added inventory frame/icon and character-style preferences, a six-page introduction for ordinary new saves, replay from Data settings, and tampering help.
- Added actual damage numbers for hits, kills and blocks. Feedback respects visibility, avoids duplicates on repaint, expires automatically and uses static numbers with reduced motion.

This update brings more of the desktop version's map presentation and interactions to the browser, alongside a redesigned web interface.

## Map and Visuals

- Added image map rendering and enabled it by default. The mode remains configurable, and existing manual preferences are preserved.
- Ported desktop terrain layers and elevation rendering, correcting overlap and alignment between floors, creatures, items, and corner markers.
- Added lighting around the player and desktop character-based spell animations for clearer combat feedback.
- Unified map glyphs, floor dots, player appearance, and icon fonts, fixing several special-character rendering issues.
- Removed unnecessary footstep, liquid, and gas particle effects. Materials now retain only subtle motion.

## Interface and Controls

- Reorganized the left and right panels and floating windows, improving clipped text, overflowing submenus, and responsive scaling.
- Added distinct colors for tabs and functional areas, with frosted-glass backgrounds, subtle textures, and interactive button feedback.
- Applied consistent field colors and aligned the labels, bars, and values of all three resource meters.
- Reorganized tampering into separate areas for targets, slots, candidates, previews, costs, and risks. The right panel now supports editing directly, with the option to continue in a floating window.
- Tampering now uses a large floating window; only the association board remains fullscreen. Floating windows can be dragged.
- Made map hints more transparent, increased the event log height, and removed the bottom-left left-click instruction.
- Improved held arrow-key pacing to reduce bursts of movement caused by queued input.
- Clicking the player's tile no longer opens terrain inspection. The dedicated inspection control and existing pickup and interaction actions remain available.

## Codex, Association Board, and Text

- Completed the web codex entry point, with categories, search, and detail views.
- Replaced equipment initials on the association board with desktop-style patterns and enlarged the bottom action buttons.
- Added the desktop symbolic sentence representation while keeping the full text available for inspection.
- English layer names now use their full names instead of symbolic abbreviations.
- Fixed incorrect icons beside inventory items.

## Performance and Compatibility

- Cached material textures and reduced redundant rendering and unchanged interface rebuilds.
- Character animations stop after a brief playback, avoiding a continuous animation loop.
- Updated both the web release package and local HTML, with improved Chinese, English, and special-glyph font loading.
