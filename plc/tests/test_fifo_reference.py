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
