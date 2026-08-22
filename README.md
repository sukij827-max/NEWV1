# GenZ Expression — V4 Experience Builder

This build is based on the latest working V3 SQL/PostgreSQL ZIP. The database schema is intentionally kept compatible with V3; the new Experience metadata is stored inside the existing `experiences.body` JSON payload, so no new database variable is required.

## Experience structure

- 📖 STORY — interactive chapters with live scene transitions and Next Chapter.
- 💌 LETTER — reveal-style digital letters.
- 🎉 EVENT — event details, countdown, location, RSVP and gallery.
- 📸 MEMORIES — dynamic archive, film roll and memory wall layouts.
- 🎮 PLAY — quiz/game flow with one-submit leaderboard.

Each category has its own visual styles and its own interaction pattern. Styles are not just color swaps.

## Creation modes

- ✨ Quick Create — fills only the important content; layout and animation are automatic.
- 🛠️ Custom Create — adds recipient/event details/custom visual notes and keeps optional fields skippable.
- ❓ Bantuan — feature-by-feature explanations and simple usage instructions.

## Preserved V3 behavior

- SQL/PostgreSQL via `DATABASE_URL`; SQLite is not used.
- Universal Telegram audio input: Audio, Voice Note, and audio documents.
- Audio is stored as Telegram `file_id`, so Railway redeploys do not break playback.
- Direct Mini App URL: `/miniapp/{code}` to avoid redirecting back to the bot.
- Share URL, Telegram link and web link.
- Message Owner from shared links, including anonymous visitors.
- Expiration with category-specific defaults.
- Quiz batches + `/selesai` + one submission per Experience + leaderboard.
- Existing legacy Experience kinds remain renderable through the legacy renderer.

## Railway

Keep the existing required environment variables from V3, especially `DATABASE_URL` using PostgreSQL and `RAILWAY_PUBLIC_DOMAIN` for generated Mini App links.
