from typing import Iterable, List, TypeVar

T = TypeVar("T")

def batched(it: Iterable[T], size: int) -> Iterable[List[T]]:
    batch = []
    for x in it:
        batch.append(x)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch
