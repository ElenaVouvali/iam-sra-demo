// Every tool working page is src/tools/<id>.vue, loaded lazily: each is its own chunk, so Plotly and Leaflet
// are only downloaded on pages that use them.
const pages = import.meta.glob('./tools/*.vue')

/** The lazy loader for a tool's working page, or undefined when the file doesn't exist yet. */
export const pageFor = (id) => pages[`./tools/${id}.vue`]
