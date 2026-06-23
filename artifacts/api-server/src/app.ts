import { request as httpRequest, type IncomingMessage } from "node:http";
import express, { type Express, type Request, type Response } from "express";
import cors from "cors";
import pinoHttp from "pino-http";
import router from "./routes";
import { logger } from "./lib/logger";

const app: Express = express();

app.use(
  pinoHttp({
    logger,
    serializers: {
      req(req) {
        return {
          id: req.id,
          method: req.method,
          url: req.url?.split("?")[0],
        };
      },
      res(res) {
        return {
          statusCode: res.statusCode,
        };
      },
    },
  }),
);

app.use(cors());

// Reverse proxy for AutoSub AI Backend (Python/FastAPI on port 8000).
// Must be registered BEFORE express.json() / express.urlencoded() so the
// raw request body stream is still available for piping (not yet consumed).
app.use("/autosub-ai", (req: Request, res: Response) => {
  const targetPath = req.url || "/"; // Express already strips the /autosub-ai prefix

  const proxyReq = httpRequest(
    {
      hostname: "localhost",
      port: 8000,
      path: targetPath,
      method: req.method,
      headers: { ...req.headers, host: "localhost:8000" },
    },
    (proxyRes: IncomingMessage) => {
      res.writeHead(proxyRes.statusCode ?? 200, proxyRes.headers);
      proxyRes.pipe(res);
    },
  );

  proxyReq.on("error", () => {
    if (!res.headersSent) {
      res.status(502).json({ error: "AutoSub AI Backend unavailable" });
    }
  });

  req.pipe(proxyReq);
});

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.use("/api", router);

export default app;
