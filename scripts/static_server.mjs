import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(process.cwd());
const port = Number(process.argv[2] ?? "8123");

const contentTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

createServer(async (request, response) => {
  try {
    const url = new URL(request.url ?? "/", "http://127.0.0.1");
    const relative = decodeURIComponent(url.pathname).replace(/^\/+/, "");
    if (!relative) {
      response.writeHead(200, { "Content-Type": "text/plain; charset=utf-8" }).end("ok");
      return;
    }
    let target = resolve(root, relative);
    if (target !== root && !target.startsWith(`${root}${sep}`)) {
      response.writeHead(403).end("Forbidden");
      return;
    }

    const info = await stat(target);
    if (info.isDirectory()) target = resolve(target, "index.html");
    const type = contentTypes[extname(target)] ?? "application/octet-stream";
    response.writeHead(200, { "Content-Type": type });
    createReadStream(target).pipe(response);
  } catch {
    response.writeHead(404).end("Not found");
  }
}).listen(port, "127.0.0.1", () => {
  process.stdout.write(`static server listening on http://127.0.0.1:${port}\n`);
});