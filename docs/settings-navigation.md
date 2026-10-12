# Settings navigation: overlapping functions

The task menu changes where existing controls are found. It does not change how
settings are stored or resolved. These overlaps are candidates for a later
integration pass:

| Function | Current locations | Later integration question |
| --- | --- | --- |
| Movement times and automation | Global times, recurring profiles, area presets, individual shutters, external triggers | How should a user compare the effective time and trigger for one shutter in one place? |
| Seasonal profiles | Global timing settings and global time entities; area and shutter time editors also select a season | Should seasonal activation and seasonal values share one editor? |
| Frost protection and sensors | Global sensors and threshold, area sensor/threshold, shutter fallback, sun-position conditions | How should the effective sensor and threshold be explained without changing precedence? |
| Notifications | Global recipient, lead time and templates; area and shutter recipient and warning overrides | How should the effective recipient and warning lead time be previewed per shutter? |
| Date-based exceptions and recurring profiles | One-time exceptions; global and area recurring time profiles | A shared overview may compare their priority, while keeping creation and editing separate. |
| Dashboard shortcuts | Home page and Startseite anpassen | Should editing be available directly from the home page? |

Area presets still use their existing explicit “apply to members” action. This
navigation work does not introduce area inheritance or change precedence.
