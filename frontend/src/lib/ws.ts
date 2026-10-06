export function createWSConnection(path: string): WebSocket {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  // Replace http/https with ws/wss
  const wsBaseUrl = apiBaseUrl.replace(/^http/, "ws");
  const url = `${wsBaseUrl}/api/${path.replace(/^\//, "")}`;
  return new WebSocket(url);
}

export function parseWSMessage(event: MessageEvent): any {
  try {
    return JSON.parse(event.data);
  } catch (e) {
    return event.data;
  }
}
