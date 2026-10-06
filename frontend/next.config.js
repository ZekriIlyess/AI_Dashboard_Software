/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Ensure that standalone build is generated for Docker deployments
  output: 'standalone',
}

module.exports = nextConfig
