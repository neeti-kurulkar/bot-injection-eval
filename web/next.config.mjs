/** Static export: the dashboard is plain HTML/JS/CSS with no server.
 *  BASE_PATH is set when hosting under a sub-path (GitHub Pages: /bot-injection-eval). */
const basePath = process.env.BASE_PATH || "";

const nextConfig = {
  output: "export",
  basePath,
  images: { unoptimized: true },
  trailingSlash: true,
  env: { NEXT_PUBLIC_BASE_PATH: basePath },
};

export default nextConfig;
