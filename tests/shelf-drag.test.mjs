import test from 'node:test';
import assert from 'node:assert/strict';
import { startShelfDrag, moveShelfDrag, shelfWheelDelta } from '../assets/shelf-drag.js';

const pointer = (x, y, extra = {}) => ({
  button: 0, pointerId: 1, pointerType: 'mouse', isPrimary: true,
  clientX: x, clientY: y, ...extra,
});
const options = {
  angle: 0, scroll: 150, mode: 'ring', bounds: { top: 100, height: 580 },
};

test('wheel pixels, lines and pages use comparable distances', () => {
  assert.equal(shelfWheelDelta({ deltaX: 0, deltaY: 48, deltaMode: 0 }, 580), 48);
  assert.equal(shelfWheelDelta({ deltaX: 0, deltaY: 3, deltaMode: 1 }, 580), 48);
  assert.equal(shelfWheelDelta({ deltaX: 0, deltaY: -1, deltaMode: 2 }, 580), -580);
  assert.equal(shelfWheelDelta({ deltaX: -3, deltaY: 1, deltaMode: 1 }, 580), -48);
});

test('rightward drags move books right at both the top and bottom of the ring', () => {
  for (const [y, theta] of [[180, 0], [600, Math.PI]]) {
    for (const dx of [-80, 80]) {
      const drag = startShelfDrag(pointer(300, y), options);
      const result = moveShelfDrag(drag, pointer(300 + dx, y));
      const bookDx = Math.sin(theta + result.angle * Math.PI / 180) - Math.sin(theta);
      assert.equal(Math.sign(bookDx), Math.sign(dx));
    }
  }
});

test('crossing the centre during a drag keeps the original direction', () => {
  const drag = startShelfDrag(pointer(300, 600), options);
  const first = moveShelfDrag(drag, pointer(320, 600));
  const crossed = moveShelfDrag(drag, pointer(340, 180));
  assert.ok(crossed.angle < first.angle);
});

test('vertical drift after activation keeps updating smoothly', () => {
  const drag = startShelfDrag(pointer(300, 180), options);
  moveShelfDrag(drag, pointer(320, 180));
  assert.equal(moveShelfDrag(drag, pointer(340, 400)).angle, 12.8);
});

test('small movements remain clicks and unrelated pointers cannot move the shelf', () => {
  const drag = startShelfDrag(pointer(300, 180), options);
  assert.equal(moveShelfDrag(drag, pointer(306, 182)), null);
  assert.equal(moveShelfDrag(drag, pointer(340, 180, { pointerId: 2 })), null);
  assert.equal(drag.active, false);
});

test('vertical touch intent stays with page scrolling', () => {
  const drag = startShelfDrag(pointer(300, 180, { pointerType: 'touch' }), options);
  assert.equal(moveShelfDrag(drag, pointer(303, 220, { pointerType: 'touch' })), null);
  assert.equal(moveShelfDrag(drag, pointer(400, 225, { pointerType: 'touch' })), null);
});

test('horizontal touch drags work on either half of the ring', () => {
  for (const y of [180, 600]) {
    const drag = startShelfDrag(pointer(300, y, { pointerType: 'touch' }), options);
    const result = moveShelfDrag(drag, pointer(350, y, { pointerType: 'touch' }));
    assert.equal(result.angle, y === 180 ? 16 : -16);
  }
});

test('rail mouse dragging keeps its scroll direction and touch uses native scrolling', () => {
  const opts = { ...options, mode: 'rail' };
  const drag = startShelfDrag(pointer(300, 600), opts);
  assert.equal(moveShelfDrag(drag, pointer(340, 600)).scroll, 110);
  assert.equal(startShelfDrag(pointer(300, 600, { pointerType: 'touch' }), opts), null);
});

test('secondary buttons and additional touch pointers cannot start a drag', () => {
  assert.equal(startShelfDrag(pointer(300, 180, { button: 2 }), options), null);
  assert.equal(startShelfDrag(pointer(300, 180, { isPrimary: false }), options), null);
});
