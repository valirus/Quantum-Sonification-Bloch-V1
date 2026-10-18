# Branding update — quantumhub-branding-1

Presentation-only update. The 17 V3 interface sources, five original test files, 54 scientific public assets, and frozen renderer remain unchanged.

The new branding layer supplies a vector product mark, a vectorized QuantumHub wordmark, seven contributor credits, a link to https://www.qhubperu.com/, and a favicon. The product symbol is a simplified geometric redraw of the supplied raster reference; the corporate wordmark retains its original outlined lettering and a vectorized mask of the supplied symbol. No embedded rasters or external fonts are used.

The immutable V3 provenance manifest has not been rewritten. Footer content lives in `src/branding/BrandFooter.tsx`; styling in `src/branding/branding.css`. A public `branding/version.json` identifies this presentation update after deployment.

Validation: 49 original tests, TypeScript, production build, seven names in server-rendered footer, source integrity and SVG inspection. Actual deployed browser rendering remains a post-deployment check.
