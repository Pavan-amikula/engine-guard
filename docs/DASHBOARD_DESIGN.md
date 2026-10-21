# Air-path observatory: interface design

The interface uses the layout and controls of an engineering analysis workspace: a persistent recording library, large aligned signal readouts, synchronized pressure/residual plots, event navigation, and a transport with a whole-recording overview. The visual treatment uses warm paper, graphite, vermilion measured-pressure traces and cobalt virtual-pressure traces. Serif display typography contrasts with monospaced measurements and compact control labels. Panels use shared rules rather than a grid of rounded cards.

## Reference review

- [MoTeC i2](https://motec.com.au/products/i2): the official product description discusses channel overlays, linked graph cursors, workbook organization, and synchronized playback. Adapted ideas: linked pressure/residual views, individual channel visibility, inspectable traces and timeline navigation. EngineGuard does not use MoTeC code or assets.
- [CSS Electronics automotive telematics dashboards](https://www.csselectronics.com/pages/telematics-dashboard-open-source): the official examples discuss vehicle-signal visualization, interactive device selection, and event summaries. Adapted ideas: an experiment selector and clickable fault/alarm observations tied to recorded time. EngineGuard does not use their cloud infrastructure or dashboard templates.

Reviewed 21 October 2026. These references inform analysis interactions; the graphic composition and implementation are specific to this project.

## Interaction contract

- The initial view opens paused near 145 s to show a useful recorded window. Restart returns to 0 s.
- Selecting a recording resets the playback state and loads that recording's compiled C outputs. A request counter prevents a slow previous request from replacing a newer selection.
- The pressure/residual panels share a 60 s, 120 s or full-recording time range. Pressure-channel legend controls toggle the two traces independently. Clicking a pressure trace seeks to that time. Hovering reveals synchronized time/pressure values on wider screens.
- Event controls jump to recording start, documented fault onset, or the first C-generated alarm. The overview exposes the entire recording, while pressure/residual detail traces and alarm shading stop at the playback cursor.
- The filtered residual is reconstructed for visualization from the rounded displayed pressure channels using the same EWMA coefficient. The C-produced alarm/status channels remain authoritative; no new alarm classification is performed in the browser.
- The evidence view uses the saved evaluation metrics, with baseline comparisons and deployment limits. It pauses replay while open.
- At narrow sizes the recording rail becomes a horizontal selector; readouts, event observations and transport controls reflow. Keyboard navigation, visible focus, descriptive control labels and non-color alarm text are provided.
- Google Fonts supplies DM Sans, IBM Plex Mono and Instrument Serif. Local Arial/Consolas/Georgia fallbacks remain usable when the font service is unavailable. Recorded-data playback requires the local Python server.

No estimator weights, C inference logic, benchmark results or diagnostic thresholds were changed for the redesign.
