import { copyFileSync, mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const scriptPath = fileURLToPath(import.meta.url);
const projectDirectory = resolve(dirname(scriptPath), "..");
const packageDirectory = resolve(projectDirectory, "node_modules", "jsqr");
const vendorDirectory = resolve(projectDirectory, "web", "vendor");

mkdirSync(vendorDirectory, { recursive: true });
copyFileSync(
  resolve(packageDirectory, "dist", "jsQR.js"),
  resolve(vendorDirectory, "jsQR.js"),
);
copyFileSync(
  resolve(packageDirectory, "LICENSE"),
  resolve(vendorDirectory, "JSQR-LICENSE.txt"),
);
