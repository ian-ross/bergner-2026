import { existsSync, readdirSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

const outputDirectory = resolve("dist");
const indexPath = resolve(outputDirectory, "index.html");
if (!existsSync(indexPath)) throw new Error("Missing dist/index.html; run the Vite production build first.");

const html = readFileSync(indexPath, "utf8");
const assetReferences = [...html.matchAll(/<(?:script|link)\b[^>]+(?:src|href)="([^"]+)"/g)].map((match) => match[1]);
if (assetReferences.length === 0) throw new Error("Production index contains no runtime asset references.");

for (const reference of assetReferences) {
  if (/^(?:https?:)?\/\//i.test(reference)) throw new Error(`Remote runtime dependency is not allowed: ${reference}`);
  if (!reference.startsWith("/")) throw new Error(`Production asset must be root-relative: ${reference}`);
  if (!existsSync(resolve(outputDirectory, `.${reference}`))) throw new Error(`Missing local production asset: ${reference}`);
}

const assets = readdirSync(resolve(outputDirectory, "assets"));
if (!assets.some((asset) => asset.startsWith("integration.worker-") && asset.endsWith(".js"))) {
  throw new Error("Production bundle is missing the locally emitted integration worker.");
}

console.log(`Verified ${assetReferences.length} local runtime asset(s) and the local integration worker in dist/.`);
