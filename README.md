# GM Assistant

GM Assistant is a Rails app for running image-driven tabletop sessions. It lets a GM organise campaign media into folders and albums, then present images to a player-facing screen in real time.

## Features

- Campaign library with nested folders, albums, and uploaded images
- Player display view for showing the current image to the table
- Real-time presentation updates over Action Cable
- User accounts and per-user display preferences

## Stack

- Ruby 3.4.9
- Rails 8.1
- Vite with React
- SQLite for app, queue, cable, and cache databases
- Active Storage for uploaded files

## Development

Local development runs from source on your machine. The prebuilt GHCR image in `compose.yml` is for deployment, not day-to-day development.

Prerequisites:

- Ruby 3.4.9
- Node.js 24 and npm
- SQLite 3

Initial setup:

```bash
bundle install
npm ci
bin/setup
```

Run the app:

```bash
bin/dev
```

The app will be available at `http://localhost:3000`.

Vite is configured to autobuild in development. If you want to run the Vite dev server for live asset rebuilds in a second terminal, use:

```bash
bin/vite dev
```

Useful commands:

- `bin/rails console`
- `bin/rails test`
- `bin/rails test:system`
- `bin/rubocop`
- `bin/brakeman`

Development and test SQLite databases live under `storage/`. Uploaded files also use local storage in development.

## Deployment

Production uses the prebuilt image defined in `compose.yml`, currently `ghcr.io/moonlitmoo/gm-assistant:latest`. The following example setup uses the `compose.yml` in the repository.

1. Create a `.env` file for Compose and add the required production values.

   ```bash
   touch .env
   ```

   At minimum, set `SECRET_KEY_BASE` so Rails can boot in production.

   ```env
   SECRET_KEY_BASE=replace-with-a-long-random-string
   ```

   If you use encrypted Rails credentials, also set:

   ```env
   RAILS_MASTER_KEY=replace-with-your-master-key
   ```

2. Add this site block to the existing Caddyfile, then reload Caddy. Caddy will handle HTTPS automatically, and `reverse_proxy` supports Action Cable WebSocket upgrades for `/cable`.

   ```caddyfile
   codex.moonlitmoo.com {
   	reverse_proxy localhost:3000
   }
   ```

   ```bash
   sudo systemctl reload caddy
   ```

3. Pull the latest image and start the app.

   ```bash
   docker compose pull
   docker compose up -d
   ```

4. To update the app later:

   ```bash
   docker compose pull && docker compose up -d
   ```

5. To open a Rails console in the running container:

   ```bash
   docker compose exec web bin/rails console
   ```

SQLite database files and Active Storage uploads persist in the `sqlite_data` Docker volume mounted at `/rails/storage`.
