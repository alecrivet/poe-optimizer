"""
Passive Skill Tree Canvas Widget

Displays the PoE passive skill tree with:
- Node rendering (allocated, available, added, removed)
- Zoom and pan controls
- Connection lines between nodes
- Animated transitions for genetic algorithm visualization
"""

import logging
import math
from typing import Dict, Set, Optional, Tuple
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPointF, QRectF, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QWheelEvent, QMouseEvent, QPainterPath

logger = logging.getLogger(__name__)


class TreeCanvas(QWidget):
    """
    Widget for displaying and interacting with the passive skill tree.

    Features:
    - Zoom (mouse wheel)
    - Pan (click and drag)
    - Node highlighting (allocated, added, removed)
    - Smooth animations
    """

    # Signals
    node_clicked = pyqtSignal(int)  # Emits node ID when clicked

    def __init__(self, parent=None):
        super().__init__(parent)

        # Tree data
        self.tree_graph = None
        self.node_positions: Dict[int, Tuple[float, float]] = {}

        # Display state
        self.allocated_nodes: Set[int] = set()
        self.added_nodes: Set[int] = set()
        self.removed_nodes: Set[int] = set()
        self.highlighted_nodes: Set[int] = set()  # For GA animation

        # View transformation
        self.zoom = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 5.0
        self.pan_x = 0.0
        self.pan_y = 0.0

        # Interaction state
        self.panning = False
        self.last_mouse_pos = None

        # Node appearance
        self.node_radius = 8
        self.connection_width = 2

        # Colors
        self.colors = {
            'background': QColor(20, 20, 30),
            'connection': QColor(60, 60, 80, 150),
            'node_unallocated': QColor(80, 80, 100),
            'node_allocated': QColor(220, 200, 100),
            'node_added': QColor(100, 220, 100),
            'node_removed': QColor(220, 100, 100),
            'node_highlighted': QColor(100, 150, 255),
            'node_notable': QColor(150, 150, 200),
            'node_keystone': QColor(200, 150, 200),
            'node_mastery': QColor(200, 100, 150),
        }

        # Animation
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update)
        self.animation_frame = 0

        # Widget settings
        self.setMinimumSize(400, 400)
        self.setMouseTracking(True)

        # Load tree data
        self._load_tree_data()

    def _load_tree_data(self):
        """Load passive tree graph and generate node positions"""
        try:
            from src.pob.tree_parser import load_passive_tree

            logger.info("Loading passive tree data...")
            self.tree_graph = load_passive_tree()

            # Generate node positions (simple radial layout for now)
            # TODO: Load actual positions from PoB tree data
            self._generate_node_layout()

            logger.info(f"Loaded {len(self.tree_graph.nodes)} nodes")

        except Exception as e:
            logger.error(f"Failed to load tree data: {e}")
            logger.info("Tree visualization will be unavailable")
            self.tree_graph = None
            self.node_positions = {}

    def _generate_node_layout(self):
        """
        Generate node positions using a simple radial/circular layout.

        TODO: Replace with actual PoB tree positions from TreeData.json
        """
        if not self.tree_graph or not self.tree_graph.nodes:
            logger.warning("Cannot generate layout: tree graph is empty")
            return

        # Center of the canvas
        center_x = 0.0
        center_y = 0.0

        # For now, use a simple circular layout based on node connectivity
        # This is a placeholder - real PoB tree has specific coordinates

        try:
            # Find node with most connections (likely tree center)
            center_node = max(
                self.tree_graph.nodes.keys(),
                key=lambda n: len(self.tree_graph.get_neighbors(n))
            )
        except (ValueError, AttributeError) as e:
            logger.error(f"Failed to find center node: {e}")
            return

        # BFS from center to assign layers
        visited = {center_node}
        current_layer = {center_node}
        layer_num = 0
        layers = {center_node: 0}

        while current_layer:
            next_layer = set()
            for node_id in current_layer:
                for neighbor in self.tree_graph.get_neighbors(node_id):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        next_layer.add(neighbor)
                        layers[neighbor] = layer_num + 1
            current_layer = next_layer
            layer_num += 1

        # Position nodes in concentric circles
        layer_counts = {}
        for node_id, layer in layers.items():
            layer_counts[layer] = layer_counts.get(layer, 0) + 1

        layer_positions = {}
        for node_id, layer in layers.items():
            if layer not in layer_positions:
                layer_positions[layer] = 0

            # Circular positioning
            radius = layer * 40  # 40 pixels per layer
            count = layer_counts[layer]
            angle = (2 * math.pi * layer_positions[layer]) / max(count, 1)

            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)

            self.node_positions[node_id] = (x, y)
            layer_positions[layer] += 1

        logger.info(f"Generated positions for {len(self.node_positions)} nodes in {layer_num} layers")

    def set_allocated_nodes(self, node_ids: Set[int]):
        """Set which nodes are currently allocated"""
        self.allocated_nodes = set(node_ids)
        if self.tree_graph:  # Only update if tree is loaded
            self.update()

    def set_tree_diff(self, added: Set[int], removed: Set[int]):
        """Set which nodes were added/removed by optimization"""
        self.added_nodes = set(added)
        self.removed_nodes = set(removed)
        if self.tree_graph:  # Only update if tree is loaded
            self.update()

    def highlight_nodes(self, node_ids: Set[int]):
        """Highlight specific nodes (for GA animation)"""
        self.highlighted_nodes = set(node_ids)
        if self.tree_graph:  # Only update if tree is loaded
            self.update()

    def start_animation(self):
        """Start animation timer (for GA visualization)"""
        self.animation_timer.start(50)  # 20 FPS

    def stop_animation(self):
        """Stop animation timer"""
        self.animation_timer.stop()

    def reset_view(self):
        """Reset zoom and pan to default"""
        self.zoom = 1.0
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.update()

    def paintEvent(self, event):
        """Render the tree canvas"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fill background
        painter.fillRect(self.rect(), self.colors['background'])

        if not self.tree_graph or not self.node_positions:
            # Show error/loading message
            painter.setPen(QColor(150, 150, 150))
            if self.tree_graph is None:
                painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                               "Tree visualization unavailable\n\n"
                               "Check that PathOfBuilding submodule is initialized:\n"
                               "git submodule update --init --recursive")
            else:
                painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Loading tree data...")
            return

        # Apply transformations (zoom and pan)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(self.zoom, self.zoom)
        painter.translate(self.pan_x, self.pan_y)

        # Draw connections first (behind nodes)
        self._draw_connections(painter)

        # Draw nodes
        self._draw_nodes(painter)

    def _draw_connections(self, painter: QPainter):
        """Draw lines connecting nodes"""
        painter.setPen(QPen(self.colors['connection'], self.connection_width / self.zoom))

        drawn_connections = set()

        for node_id, (x, y) in self.node_positions.items():
            # Only draw connections for allocated nodes (or their neighbors)
            if node_id not in self.allocated_nodes:
                continue

            for neighbor_id in self.tree_graph.get_neighbors(node_id):
                if neighbor_id not in self.node_positions:
                    continue

                # Avoid drawing same connection twice
                connection = tuple(sorted([node_id, neighbor_id]))
                if connection in drawn_connections:
                    continue
                drawn_connections.add(connection)

                # Draw line
                nx, ny = self.node_positions[neighbor_id]
                painter.drawLine(QPointF(x, y), QPointF(nx, ny))

    def _draw_nodes(self, painter: QPainter):
        """Draw individual nodes"""
        for node_id, (x, y) in self.node_positions.items():
            node_data = self.tree_graph.nodes.get(node_id, {})

            # Determine node color
            if node_id in self.highlighted_nodes:
                # Animated highlight for GA visualization
                alpha = int(128 + 127 * math.sin(self.animation_frame * 0.2))
                color = QColor(self.colors['node_highlighted'])
                color.setAlpha(alpha)
            elif node_id in self.added_nodes:
                color = self.colors['node_added']
            elif node_id in self.removed_nodes:
                color = self.colors['node_removed']
            elif node_id in self.allocated_nodes:
                # Check node type (PassiveNode uses attributes, not dict)
                if getattr(node_data, 'isKeystone', False):
                    color = self.colors['node_keystone']
                elif getattr(node_data, 'isNotable', False):
                    color = self.colors['node_notable']
                elif getattr(node_data, 'isMastery', False):
                    color = self.colors['node_mastery']
                else:
                    color = self.colors['node_allocated']
            else:
                color = self.colors['node_unallocated']

            # Determine node size
            radius = self.node_radius / self.zoom
            if getattr(node_data, 'isKeystone', False):
                radius *= 1.5
            elif getattr(node_data, 'isNotable', False):
                radius *= 1.2

            # Draw node
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor(0, 0, 0), 1 / self.zoom))
            painter.drawEllipse(QPointF(x, y), radius, radius)

        self.animation_frame += 1

    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zooming"""
        # Get zoom factor
        delta = event.angleDelta().y()
        zoom_factor = 1.1 if delta > 0 else 0.9

        # Apply zoom
        new_zoom = self.zoom * zoom_factor
        new_zoom = max(self.min_zoom, min(self.max_zoom, new_zoom))

        if new_zoom != self.zoom:
            self.zoom = new_zoom
            self.update()

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for panning or node selection"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if clicking on a node
            clicked_node = self._get_node_at_pos(event.pos())
            if clicked_node is not None:
                self.node_clicked.emit(clicked_node)
            else:
                # Start panning
                self.panning = True
                self.last_mouse_pos = event.pos()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for panning"""
        if self.panning and self.last_mouse_pos:
            # Calculate pan delta
            delta = event.pos() - self.last_mouse_pos
            self.pan_x += delta.x() / self.zoom
            self.pan_y += delta.y() / self.zoom
            self.last_mouse_pos = event.pos()
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def _get_node_at_pos(self, pos) -> Optional[int]:
        """Find node at screen position (if any)"""
        # Transform screen coordinates to tree coordinates
        tree_x = (pos.x() - self.width() / 2) / self.zoom - self.pan_x
        tree_y = (pos.y() - self.height() / 2) / self.zoom - self.pan_y

        # Find closest node within click radius
        click_radius = 15 / self.zoom
        closest_node = None
        closest_dist = float('inf')

        for node_id, (x, y) in self.node_positions.items():
            dist = math.sqrt((x - tree_x) ** 2 + (y - tree_y) ** 2)
            if dist < click_radius and dist < closest_dist:
                closest_dist = dist
                closest_node = node_id

        return closest_node
