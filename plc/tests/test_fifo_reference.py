from dataclasses import dataclass


@dataclass(frozen=True)
class Item:
    shape: int
    semantic_id: int


class Fifo:
    def __init__(self, capacity=3):
        self.capacity = capacity
        self.items = []

    def enqueue(self, item):
        if len(self.items) >= self.capacity:
            return False
        self.items.append(item)
        return True

    def dequeue(self):
        return self.items.pop(0) if self.items else None

    def reset(self):
        self.items.clear()


class ButtonPulse:
    """Small reference model of FB_ButtonPulse's scan-count semantics."""

    def __init__(self, debounce_scans=2):
        self.debounce_scans = debounce_scans
        self.previous_raw = False
        self.stable_raw = False
        self.stable_count = 0

    def scan(self, raw, reset=False):
        pulse = False
        if reset:
            self.previous_raw = False
            self.stable_raw = False
            self.stable_count = 0
        else:
            if raw == self.previous_raw:
                if self.stable_count < self.debounce_scans:
                    self.stable_count += 1
            else:
                self.stable_count = 0
            if self.stable_count >= self.debounce_scans and self.stable_raw != raw:
                self.stable_raw = raw
                if self.stable_raw:
                    pulse = True
            self.previous_raw = raw
        return pulse, self.stable_raw


def test_fifo_order_and_full_boundary():
    fifo = Fifo()
    values = [Item(1, 1), Item(2, 2), Item(3, 3)]
    assert all(fifo.enqueue(v) for v in values)
    assert not fifo.enqueue(Item(1, 4))
    assert [fifo.dequeue(), fifo.dequeue(), fifo.dequeue()] == values
    assert fifo.dequeue() is None


def test_reset_clears_length_and_empty():
    fifo = Fifo()
    fifo.enqueue(Item(1, 1))
    fifo.reset()
    assert fifo.items == []


def test_full_fifo_can_replace_head_in_one_scan():
    fifo = Fifo()
    assert all(fifo.enqueue(Item(shape, shape)) for shape in (1, 2, 3))
    consumed = fifo.dequeue()
    assert consumed == Item(1, 1)
    assert fifo.enqueue(Item(1, 4))
    assert fifo.items == [Item(2, 2), Item(3, 3), Item(1, 4)]


def test_internal_led_semantics():
    displayed = None

    def leds(item):
        nonlocal displayed
        if item is not None and item.shape in (1, 2, 3):
            displayed = item.shape
        return tuple(displayed is not None and displayed >= n for n in (1, 2, 3))

    assert leds(None) == (False, False, False)
    assert leds(Item(1, 1)) == (True, False, False)
    assert leds(None) == (True, False, False)  # latched until next dequeue/reset
    assert leds(Item(2, 2)) == (True, True, False)
    assert leds(Item(3, 3)) == (True, True, True)
    assert leds(Item(99, 4)) == (True, True, True)  # unknown does not alter display


def test_button_pulse_is_single_shot_after_stable_scans():
    button = ButtonPulse(debounce_scans=2)
    assert button.scan(False) == (False, False)
    assert button.scan(True) == (False, False)
    assert button.scan(True) == (False, False)
    assert button.scan(True) == (True, True)
    assert button.scan(True) == (False, True)
    assert button.scan(False) == (False, True)
    assert button.scan(False) == (False, True)
    assert button.scan(False) == (False, False)


def test_reset_clears_button_state_and_led_state():
    button = ButtonPulse(debounce_scans=1)
    button.scan(True)
    assert button.scan(True) == (True, True)
    assert button.scan(False, reset=True) == (False, False)
