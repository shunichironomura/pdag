from collections import defaultdict, deque
from collections.abc import Collection, Hashable, Mapping


def topological_sort[T: Hashable](dependencies: Mapping[T, Collection[T]]) -> list[T]:
    """Sort a graph of dependencies topologically.

    Given a dependency graph (a dict mapping a node to a collection of nodes that depend on it),
    perform a topological sort and return an ordered list of nodes.
    Raises an error if a cycle is detected.
    """
    indegree: defaultdict[T, int] = defaultdict(int)
    for node, deps in dependencies.items():
        indegree[node] = indegree.get(node, 0)
        for dep in deps:
            indegree[dep] += 1
    q = deque([node for node, deg in indegree.items() if deg == 0])
    order = []
    while q:
        node = q.popleft()
        order.append(node)
        for dep in dependencies.get(node, []):
            indegree[dep] -= 1
            if indegree[dep] == 0:
                q.append(dep)
    if len(order) != len(indegree):
        msg = "Cycle detected in relationship dependencies!"
        raise ValueError(msg)
    return order
