# Jewel Socket Optimization Enhancement Plan

## Overview

Current implementation only swaps jewels between **currently occupied** sockets. This leaves significant optimization potential on the table:

- ~40-45 empty jewel sockets never considered
- No pathing cost awareness (could save 5-20+ points)
- No jewel removal evaluation
- Can't explore alternative tree configurations

## Gap Analysis

| Gap | Current Behavior | Desired Behavior |
|-----|-----------------|------------------|
| Socket Discovery | Only returns occupied sockets | Return ALL compatible sockets on tree |
| Move Operations | Only swap between occupied | Move to any compatible socket (occupied or empty) |
| Pathing Cost | Not calculated | Calculate min path cost from start to each socket |
| Jewel Removal | Not possible | Evaluate if removing jewel + freeing path is net positive |
| Protected Nodes | All socket nodes protected | Only protect if jewel is socketed |

---

## Phase 1: Socket Discovery Enhancement

### 1.1 Fix `find_compatible_sockets()`

**File**: `src/pob/jewel/socket_optimizer.py`

**Current** (lines 204-231):
```python
def find_compatible_sockets(self, jewel: BaseJewel, allocated_sockets: Set[int]) -> Set[int]:
    all_sockets = self.discover_all_sockets()
    compatible = set()

    for node_id, socket in all_sockets.items():
        # BUG: Skips unoccupied sockets!
        if node_id in allocated_sockets and node_id != jewel.socket_node_id:
            continue
        if socket.can_hold_jewel(jewel):
            compatible.add(node_id)
    return compatible
```

**Fixed**:
```python
def find_compatible_sockets(
    self,
    jewel: BaseJewel,
    occupied_sockets: Set[int],
    include_empty: bool = True  # NEW PARAMETER
) -> Set[int]:
    """Find all sockets compatible with the given jewel.

    Args:
        jewel: Jewel to find sockets for
        occupied_sockets: Sockets currently holding jewels
        include_empty: If True, include unoccupied sockets
    """
    all_sockets = self.discover_all_sockets()
    compatible = set()

    for node_id, socket in all_sockets.items():
        # Skip if occupied by ANOTHER jewel (not this one)
        if node_id in occupied_sockets and node_id != jewel.socket_node_id:
            continue

        # Skip empty sockets if not requested
        if not include_empty and node_id not in occupied_sockets:
            continue

        if socket.can_hold_jewel(jewel):
            compatible.add(node_id)

    return compatible
```

### 1.2 Add Pathing Cost Calculation

**File**: `src/pob/jewel/socket_optimizer.py`

Add method to `SocketDiscovery` class:

```python
def calculate_socket_distances(
    self,
    allocated_nodes: Set[int],
    class_start_node: int
) -> Dict[int, int]:
    """Calculate minimum pathing cost to each socket.

    Args:
        allocated_nodes: Currently allocated passive nodes
        class_start_node: Starting node for the character class

    Returns:
        Dict mapping socket_node_id -> minimum_points_to_reach
    """
    sockets = self.discover_all_sockets()
    distances = {}

    for socket_id in sockets:
        if socket_id in allocated_nodes:
            # Already allocated - 0 additional cost
            distances[socket_id] = 0
        else:
            # Calculate shortest path from any allocated node to this socket
            min_distance = self.tree_graph.shortest_path_length(
                from_nodes=allocated_nodes,
                to_node=socket_id
            )
            distances[socket_id] = min_distance if min_distance else float('inf')

    return distances
```

**Requires**: Add `shortest_path_length()` to `PassiveTreeGraph` in `src/pob/tree_parser.py`:

```python
def shortest_path_length(self, from_nodes: Set[int], to_node: int) -> Optional[int]:
    """Find shortest path from any source node to target.

    Uses BFS for unweighted shortest path.
    """
    if to_node in from_nodes:
        return 0

    visited = set()
    queue = [(node, 0) for node in from_nodes]

    while queue:
        current, distance = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        if current == to_node:
            return distance

        for neighbor in self.get_neighbors(current):
            if neighbor not in visited:
                queue.append((neighbor, distance + 1))

    return None  # No path found
```

---

## Phase 2: Move Operations (Not Just Swaps)

### 2.1 Add Empty Socket Moves to Greedy

**File**: `src/optimizer/tree_optimizer.py`

Enhance `_generate_jewel_swap_candidates()`:

```python
def _generate_jewel_move_candidates(
    self,
    current_xml: str,
    allocated_nodes: set,
    objective: str,
) -> Dict[str, str]:
    """Generate jewel move candidates (swaps + moves to empty sockets)."""
    candidates = {}

    registry = JewelRegistry.from_build_xml(current_xml)

    # Get socket distances for point-aware evaluation
    socket_distances = self.socket_discovery.calculate_socket_distances(
        allocated_nodes,
        self._get_class_start_node(current_xml)
    )

    movable_jewels = [
        j for j in registry.all_jewels
        if j.category != JewelCategory.TIMELESS and j.socket_node_id
    ]

    occupied_sockets = {j.socket_node_id for j in registry.all_jewels if j.socket_node_id}

    for jewel in movable_jewels:
        # Find ALL compatible sockets (including empty ones)
        compatible = self.socket_discovery.find_compatible_sockets(
            jewel,
            occupied_sockets,
            include_empty=True  # NEW: Include empty sockets
        )

        current_socket = jewel.socket_node_id
        current_cost = socket_distances.get(current_socket, 0)

        for target_socket in compatible:
            if target_socket == current_socket:
                continue

            target_cost = socket_distances.get(target_socket, float('inf'))

            # Skip if target is unreachable
            if target_cost == float('inf'):
                continue

            # Calculate point savings
            point_savings = current_cost - target_cost

            # Generate candidate
            if target_socket in occupied_sockets:
                # This is a SWAP with another jewel
                other_jewel = next(
                    j for j in movable_jewels
                    if j.socket_node_id == target_socket
                )
                candidate_name = f"Swap: {jewel.item_id} <-> {other_jewel.item_id}"
            else:
                # This is a MOVE to empty socket
                candidate_name = f"Move jewel {jewel.item_id} to socket {target_socket} (saves {point_savings} pts)"

            modified_xml = self._apply_jewel_move(current_xml, jewel, target_socket)
            candidates[candidate_name] = modified_xml

            if len(candidates) >= 15:  # Limit for performance
                return candidates

    return candidates
```

### 2.2 Add Empty Socket Mutation to Genetic

**File**: `src/optimizer/genetic_optimizer.py`

Add new mutation type:

```python
def _mutate_jewel_move(self, xml: str) -> str:
    """Move a random jewel to a random compatible socket (including empty)."""
    try:
        registry = JewelRegistry.from_build_xml(xml)

        movable_jewels = [
            j for j in registry.all_jewels
            if j.category != JewelCategory.TIMELESS and j.socket_node_id
        ]

        if not movable_jewels:
            return xml

        # Pick random jewel
        jewel = random.choice(movable_jewels)

        occupied_sockets = {j.socket_node_id for j in registry.all_jewels if j.socket_node_id}

        # Find ALL compatible sockets
        compatible = self.socket_discovery.find_compatible_sockets(
            jewel,
            occupied_sockets,
            include_empty=True
        )

        # Remove current socket
        compatible.discard(jewel.socket_node_id)

        if not compatible:
            return xml

        # Pick random target
        target_socket = random.choice(list(compatible))

        # Apply move
        return self._apply_jewel_move_to_xml(xml, jewel.item_id, target_socket)

    except Exception as e:
        logger.debug(f"Jewel move mutation failed: {e}")
        return xml
```

Update mutation selection:

```python
# In _mutate():
mutation_types = ['add', 'remove', 'mastery']
if self.optimize_jewel_sockets:
    mutation_types.extend(['jewel_swap', 'jewel_move'])  # ADD NEW TYPE
```

---

## Phase 3: Jewel Removal

### 3.1 Add Jewel Removal Mutation

**File**: `src/optimizer/genetic_optimizer.py`

```python
def _mutate_jewel_removal(self, xml: str) -> str:
    """Try removing a jewel entirely to free up pathing points."""
    try:
        registry = JewelRegistry.from_build_xml(xml)

        # Only consider removing non-essential jewels
        removable = [
            j for j in registry.all_jewels
            if j.category not in [JewelCategory.TIMELESS, JewelCategory.CLUSTER]
            and j.socket_node_id
        ]

        if not removable:
            return xml

        # Pick random jewel to remove
        jewel = random.choice(removable)

        # Remove jewel from XML
        root = ET.fromstring(xml)

        # Remove from Items section
        for items_elem in root.findall(".//Items"):
            for item in items_elem.findall("Item"):
                if item.get("id") == str(jewel.item_id):
                    items_elem.remove(item)
                    break

        # Remove socket assignment
        for sockets_elem in root.findall(".//Sockets"):
            for socket in sockets_elem.findall("Socket"):
                if socket.get("itemId") == str(jewel.item_id):
                    socket.set("itemId", "0")  # Clear socket
                    break

        logger.debug(f"Mutation: Removed jewel {jewel.item_id}")
        return ET.tostring(root, encoding='unicode')

    except Exception as e:
        logger.debug(f"Jewel removal mutation failed: {e}")
        return xml
```

### 3.2 Add Jewel Removal to Greedy Candidates

```python
def _generate_jewel_removal_candidates(
    self,
    current_xml: str,
    allocated_nodes: set,
    objective: str,
) -> Dict[str, str]:
    """Generate candidates for removing jewels entirely."""
    candidates = {}

    registry = JewelRegistry.from_build_xml(current_xml)
    socket_distances = self.socket_discovery.calculate_socket_distances(...)

    for jewel in registry.all_jewels:
        # Don't remove timeless (build-defining) or clusters (complex)
        if jewel.category in [JewelCategory.TIMELESS, JewelCategory.CLUSTER]:
            continue

        socket_cost = socket_distances.get(jewel.socket_node_id, 0)

        # Only consider removal if socket costs significant points
        if socket_cost >= 5:
            modified_xml = self._remove_jewel_from_xml(current_xml, jewel)
            candidate_name = f"Remove jewel {jewel.item_id} (frees {socket_cost} pts)"
            candidates[candidate_name] = modified_xml

    return candidates
```

---

## Phase 4: Protected Nodes Fix

### 4.1 Make Socket Protection Conditional

**File**: `src/pob/jewel/registry.py`

```python
def get_protected_nodes(
    self,
    allocated_nodes: Optional[Set[int]] = None,
    protect_empty_sockets: bool = False  # NEW PARAMETER
) -> Set[int]:
    """Return nodes that should not be modified.

    Args:
        allocated_nodes: Currently allocated nodes
        protect_empty_sockets: If False, only protect sockets WITH jewels
    """
    protected = set()

    # Protect jewel socket nodes ONLY if jewel is socketed
    for jewel in self.all_jewels:
        if jewel.socket_node_id:
            protected.add(jewel.socket_node_id)

    # Always protect cluster-generated nodes (they're special)
    for cluster in self.cluster_jewels:
        protected.update(cluster.generated_nodes)

    # Protect cluster nodes from allocated set
    if allocated_nodes:
        for node_id in allocated_nodes:
            if is_cluster_node_id(node_id):
                protected.add(node_id)

    return protected
```

### 4.2 Update Optimizer to Use Conditional Protection

**File**: `src/optimizer/genetic_optimizer.py`

```python
# In optimize() method:
registry = JewelRegistry.from_build_xml(build_xml)
self.protected_nodes = registry.get_protected_nodes(
    allocated_nodes=allocated_nodes,
    protect_empty_sockets=False  # Allow deallocating empty sockets
)
```

---

## Phase 5: Point-Aware Fitness

### 5.1 Add Point Efficiency to Fitness Calculation

When evaluating a build, consider points used:

```python
def _evaluate_fitness_with_points(
    self,
    build_xml: str,
    objective: str,
    point_budget: int
) -> float:
    """Evaluate fitness with point efficiency bonus."""

    # Get base stats
    result = self.pob_caller.calculate_build(build_xml)

    # Get points used
    summary = get_passive_tree_summary(build_xml)
    points_used = summary['total_nodes']
    points_remaining = point_budget - points_used

    # Base fitness from objective
    if objective == "dps":
        base_fitness = result.total_dps
    elif objective == "life":
        base_fitness = result.life
    elif objective == "ehp":
        base_fitness = result.total_ehp
    elif objective == "balanced":
        base_fitness = (
            result.total_dps / 1_000_000 +
            result.life / 1000 +
            result.total_ehp / 10_000
        )

    # Bonus for unused points (can be spent elsewhere)
    # Each unused point is worth ~1% of current stats
    point_bonus = 1 + (points_remaining * 0.01)

    return base_fitness * point_bonus
```

---

## Implementation Order

1. **Phase 1.1**: Fix `find_compatible_sockets()` - Quick fix, immediate benefit
2. **Phase 1.2**: Add pathing cost calculation - Requires tree graph enhancement
3. **Phase 2.1**: Add empty socket moves to greedy - Uses Phase 1
4. **Phase 2.2**: Add empty socket mutation to genetic - Uses Phase 1
5. **Phase 4**: Fix protected nodes - Quick fix, enables removal
6. **Phase 3**: Add jewel removal - Uses Phase 4
7. **Phase 5**: Point-aware fitness - Polish and optimization

## Testing Strategy

1. **Unit Tests**: Each new method in socket_optimizer.py
2. **Integration Test**: Run on cyclone build, verify it considers empty sockets
3. **Regression Test**: Ensure timeless jewels still can't move
4. **Performance Test**: Ensure pathing calculations don't slow down too much
5. **Validation Test**: Build with expensive jewel path → verify optimizer finds cheaper path

## Expected Improvements

| Scenario | Current | Enhanced |
|----------|---------|----------|
| Jewel in expensive socket (15 pts) | No change | Moves to 3-pt socket, saves 12 pts |
| Mediocre jewel | Keeps forever | Evaluates removal trade-off |
| Empty socket near start | Never considered | Considered for all jewels |
| Alternative tree path | Locked to current | Can explore entirely different tree |

## Risk Mitigation

1. **Performance**: Limit candidates per iteration (15-20 max)
2. **Complexity**: Add feature flags to enable/disable each enhancement
3. **Regression**: Maintain constraint validation for timeless/cluster jewels
4. **Testing**: Run extensive tests before enabling in production

---

*Plan created: 2024-12-25*
*Status: Ready for implementation*
