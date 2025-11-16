import { Page } from "@playwright/test";

export async function captureWebsocketHealth(page: Page) {
  return page.evaluate(async () => {
    const result: Record<string, unknown> = {};

    try {
      const socketIoType = typeof (window as unknown as { io?: unknown }).io;
      const wsType = typeof WebSocket;
      result.socketIOLoaded = socketIoType !== "undefined";
      result.webSocketAvailable = wsType !== "undefined";

      if (socketIoType === "function") {
        const socket = (window as unknown as { io: typeof import("socket.io-client") }).io(
          window.location.origin.replace(":5173", ":8080").replace(":5174", ":8080"),
          {
            path: "/ws/socket.io",
            transports: ["websocket", "polling"],
            timeout: 10_000,
          },
        );

        result.connection = await new Promise((resolve) => {
          const outcome: Record<string, unknown> = {};
          socket.on("connect", () => {
            outcome.success = true;
            outcome.socketId = socket.id;
            socket.emit("message", { type: "playwright-probe", timestamp: Date.now() });
            socket.disconnect();
            resolve(outcome);
          });
          socket.on("connect_error", (error: Error) => {
            outcome.success = false;
            outcome.error = error.message;
            resolve(outcome);
          });
          setTimeout(() => {
            outcome.success = false;
            outcome.error = "timeout";
            resolve(outcome);
          }, 10_000);
        });
      }
    } catch (error) {
      result.error = (error as Error).message;
    }

    return result;
  });
}
