import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createAppServer } from "./server.js";

const statePath = fileURLToPath(new URL("../data/workshop-state.json", import.meta.url));
const port = Number(process.env.PORT ?? 4187);
const server = createAppServer({ statePath });
server.on("error", (error) => {
  console.error(`Workshop server failed: ${error.message}`);
  process.exitCode = 1;
});
server.listen(port, "127.0.0.1", () => {
  console.log(`SIMULATED / OFFLINE workshop: http://127.0.0.1:${server.address().port}`);
  console.log(`Dedicated state: ${resolve(statePath)}`);
});
