# Home Assistant Brands proposal

`custom_integrations/smart_shutter/icon.png` is a copy of the integration's
existing `custom_components/smart_shutter/brand/icon.png`. It is a PNG with
transparency, 256x256 pixels, square, and named for the `smart_shutter` domain
in `manifest.json`. No logo or 2x icon is needed for this square mark.

Home Assistant 2026.3+ supports the in-integration `brand/` directory. The
central `custom_integrations/` directory is documented as a legacy location,
and a current HACS report says a new custom integration icon PR was closed
under the newer local-branding policy. This candidate is prepared for review,
but should only be submitted after the Brands maintainers confirm that they
will accept it. A Brands merge alone also does not prove HACS has refreshed or
changed its icon lookup behavior.

If acceptance is confirmed:

1. Fork `home-assistant/brands` and copy only
   `custom_integrations/smart_shutter/icon.png` into the matching folder.
2. Open a PR titled **Add Smart Shutter Manager brand icon** using
   [PR_DESCRIPTION.md](PR_DESCRIPTION.md).
3. Confirm the official checks pass and wait for merge and CDN propagation.
4. Check the legacy icon URL and the HACS UI separately. Do not change this
   integration's working local brand assets to work around HACS behavior.
