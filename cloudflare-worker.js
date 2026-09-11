const TARGET_ORIGIN = "https://topstokee.com";
const TEST_PRODUCT_PATH = "/product/teniska-minecraft-5";

function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "content-type": "application/json; charset=UTF-8",
      "cache-control": "no-store",
    },
  });
}

function validTargetPath(path) {
  return (
    typeof path === "string" &&
    path.startsWith("/") &&
    !path.startsWith("//") &&
    !path.includes("\\") &&
    !/[\r\n]/.test(path)
  );
}

async function fetchTopStokee(path, incomingRequest) {
  const target = new URL(path, TARGET_ORIGIN);
  target.hash = "";
  if (target.origin !== TARGET_ORIGIN) {
    throw new Error("Invalid target origin");
  }

  const headers = new Headers({
    "User-Agent":
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) " +
      "AppleWebKit/537.36 (KHTML, like Gecko) " +
      "Chrome/152.0.0.0 Safari/537.36",
    Accept:
      incomingRequest.headers.get("Accept") ||
      "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language":
      incomingRequest.headers.get("Accept-Language") || "bg-BG,bg;q=0.9,en;q=0.8",
    Referer: TARGET_ORIGIN + "/",
    "Cache-Control": "no-cache",
  });

  const requestedWith = incomingRequest.headers.get("X-Requested-With");
  if (requestedWith) {
    headers.set("X-Requested-With", requestedWith);
  }

  return fetch(target.toString(), {
    method: "GET",
    headers,
    redirect: "follow",
    cf: {
      cacheTtl: 0,
      cacheEverything: false,
    },
  });
}

export default {
  async fetch(request, env) {
    const requestUrl = new URL(request.url);

    if (request.method !== "GET") {
      return new Response("Method not allowed", { status: 405 });
    }

    if (requestUrl.pathname === "/" || requestUrl.pathname === "/health") {
      return jsonResponse({ workerActive: true });
    }

    if (requestUrl.pathname === "/test") {
      try {
        const response = await fetchTopStokee(TEST_PRODUCT_PATH, request);
        const html = await response.text();
        const containsProduct = html.toLowerCase().includes("minecraft");
        return jsonResponse({
          workerActive: true,
          testSuccessful: response.status === 200 && containsProduct,
          upstreamStatus: response.status,
          contentLength: html.length,
          containsProductName: containsProduct,
          contentType: response.headers.get("content-type"),
        });
      } catch (error) {
        return jsonResponse(
          { workerActive: true, testSuccessful: false, error: String(error) },
          502
        );
      }
    }

    if (requestUrl.pathname !== "/proxy") {
      return new Response("Not found", { status: 404 });
    }

    if (!env.PROXY_TOKEN) {
      return new Response("Worker secret is not configured", { status: 503 });
    }
    if (request.headers.get("X-Proxy-Token") !== env.PROXY_TOKEN) {
      return new Response("Unauthorized", { status: 401 });
    }

    const path = requestUrl.searchParams.get("path");
    if (!validTargetPath(path)) {
      return new Response("Invalid TopStokee path", { status: 400 });
    }

    try {
      const upstream = await fetchTopStokee(path, request);
      const responseHeaders = new Headers({
        "cache-control": "no-store",
        "x-upstream-status": String(upstream.status),
      });
      for (const name of ["content-type", "content-language", "last-modified"]) {
        const value = upstream.headers.get(name);
        if (value) {
          responseHeaders.set(name, value);
        }
      }
      return new Response(upstream.body, {
        status: upstream.status,
        statusText: upstream.statusText,
        headers: responseHeaders,
      });
    } catch (error) {
      return jsonResponse({ error: "TopStokee request failed", detail: String(error) }, 502);
    }
  },
};
