// Shared by the reading and writing shelves in the deployed application.
const DRAG_THRESHOLD = 7;
const DEGREES_PER_PIXEL = 0.32;

export function shelfWheelDelta(event, pageHeight) {
  // Wheel deltas may be pixels, text lines or entire pages (Firefox/devices).
  const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? pageHeight : 1;
  const delta = Math.abs(event.deltaY) > Math.abs(event.deltaX) ? event.deltaY : event.deltaX;
  return delta * unit;
}

export function startShelfDrag(event, { angle, scroll, mode, bounds }) {
  if (event.button !== 0 || event.isPrimary === false) return null;
  // The rail already supports native touch scrolling and momentum.
  if (mode === 'rail' && event.pointerType === 'touch') return null;
  return {
    id: event.pointerId,
    x: event.clientX,
    y: event.clientY,
    angle,
    scroll,
    mode,
    active: false,
    scrolling: false,
    // Match the orbit's 49% vertical origin. Lock this sign for the whole
    // gesture so crossing the centre cannot suddenly reverse the rotation.
    direction: event.clientY > bounds.top + bounds.height * 0.49 ? -1 : 1,
  };
}

export function moveShelfDrag(drag, event) {
  if (!drag || drag.id !== event.pointerId || drag.scrolling) return null;
  const dx = event.clientX - drag.x;
  const dy = event.clientY - drag.y;
  if (!drag.active) {
    if (Math.max(Math.abs(dx), Math.abs(dy)) < DRAG_THRESHOLD) return null;
    if (Math.abs(dy) > Math.abs(dx) * 1.5) {
      // A vertical touch gesture belongs to page scrolling until release.
      drag.scrolling = event.pointerType === 'touch';
      return null;
    }
    if (Math.abs(dx) < DRAG_THRESHOLD) return null;
    drag.active = true;
  }
  // Once dragging starts, vertical drift must not pause horizontal updates.
  return {
    angle: drag.angle + dx * DEGREES_PER_PIXEL * drag.direction,
    scroll: drag.scroll - dx,
  };
}
