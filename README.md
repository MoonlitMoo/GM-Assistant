# GM Assistant

## Deployment

1. Clone the repo on the server and change into the app directory.

   ```bash
   git clone <your-repo-url>
   cd GM-Assistant
   ```

2. Copy `.env.example` to `.env`, then fill in the deployment values.

   ```bash
   cp .env.example .env
   ```

3. Add this site block to the existing Caddyfile, then reload Caddy. Caddy will handle HTTPS automatically once DNS is pointed at the server.

   ```caddyfile
   mydomain.com {
   	reverse_proxy localhost:3000
   }
   ```

   ```bash
   sudo systemctl reload caddy
   ```

4. Build and start the app.

   ```bash
   docker compose up -d --build
   ```

5. To update a deployed app, pull and restart if you are using a registry image:

   ```bash
   docker compose pull && docker compose up -d
   ```

   If you are building locally instead, rebuild and restart:

   ```bash
   docker compose up -d --build
   ```

6. To open a Rails console in the running container:

   ```bash
   docker compose exec web bin/rails console
   ```

SQLite database files and Active Storage uploads persist in the `sqlite_data` Docker volume mounted at `/rails/storage`.
