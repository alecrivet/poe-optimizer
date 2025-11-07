"""
Main window for PoE Build Optimizer Desktop GUI
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QTextEdit, QPushButton, QLabel, QComboBox, QSpinBox,
    QGroupBox, QProgressBar, QTableWidget, QTableWidgetItem, QSplitter,
    QMessageBox, QLineEdit, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QClipboard
import logging

logger = logging.getLogger(__name__)


class OptimizerThread(QThread):
    """
    Worker thread for running optimization without blocking UI
    """
    progress = pyqtSignal(int, float, float)  # generation, best_fitness, avg_fitness
    finished = pyqtSignal(object)  # optimization result
    error = pyqtSignal(str)  # error message

    def __init__(self, build_xml, optimizer, objective):
        super().__init__()
        self.build_xml = build_xml
        self.optimizer = optimizer
        self.objective = objective

    def run(self):
        """Run optimization in background"""
        try:
            from src.optimizer.tree_optimizer import GreedyTreeOptimizer
            from src.optimizer.genetic_optimizer import GeneticTreeOptimizer

            result = self.optimizer.optimize(self.build_xml, self.objective)

            # Emit progress updates (if genetic algorithm)
            if isinstance(self.optimizer, GeneticTreeOptimizer):
                for gen, (best, avg) in enumerate(zip(
                    result.best_fitness_history,
                    result.avg_fitness_history
                )):
                    self.progress.emit(gen + 1, best, avg)

            self.finished.emit(result)

        except Exception as e:
            logger.exception("Optimization error")
            self.error.emit(str(e))


class MainWindow(QMainWindow):
    """
    Main application window for PoE Build Optimizer
    """

    def __init__(self):
        super().__init__()
        self.current_build_xml = None
        self.current_result = None
        self.optimizer_thread = None

        self.init_ui()
        self.setWindowTitle("Path of Exile Build Optimizer v0.4.0")
        self.resize(1400, 900)

    def init_ui(self):
        """Initialize the user interface"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        main_layout = QHBoxLayout(central_widget)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Input/Config/Output
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # Right panel: Visualization and Results
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        # Set initial sizes (40% left, 60% right)
        splitter.setSizes([560, 840])

        main_layout.addWidget(splitter)

    def create_left_panel(self):
        """Create left panel with input, config, and output"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # PoB Code Input Section
        input_group = QGroupBox("Build Input")
        input_layout = QVBoxLayout()

        self.pob_input = QTextEdit()
        self.pob_input.setPlaceholderText("Paste your Path of Building code here...")
        self.pob_input.setMaximumHeight(100)
        input_layout.addWidget(self.pob_input)

        load_btn_layout = QHBoxLayout()
        self.load_build_btn = QPushButton("Load Build")
        self.load_build_btn.clicked.connect(self.load_build)
        load_btn_layout.addWidget(self.load_build_btn)

        self.paste_btn = QPushButton("Paste from Clipboard")
        self.paste_btn.clicked.connect(self.paste_from_clipboard)
        load_btn_layout.addWidget(self.paste_btn)

        input_layout.addLayout(load_btn_layout)
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # Build Info Section
        info_group = QGroupBox("Build Information")
        info_layout = QVBoxLayout()

        self.build_info_text = QTextEdit()
        self.build_info_text.setReadOnly(True)
        self.build_info_text.setMaximumHeight(200)
        self.build_info_text.setPlaceholderText("Build information will appear here after loading...")
        info_layout.addWidget(self.build_info_text)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Optimizer Configuration Section
        config_group = QGroupBox("Optimizer Configuration")
        config_layout = QVBoxLayout()

        # Algorithm selection
        algo_layout = QHBoxLayout()
        algo_layout.addWidget(QLabel("Algorithm:"))
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems(["Greedy (Fast)", "Genetic (Thorough)"])
        self.algorithm_combo.currentTextChanged.connect(self.on_algorithm_changed)
        algo_layout.addWidget(self.algorithm_combo)
        config_layout.addLayout(algo_layout)

        # Objective selection
        obj_layout = QHBoxLayout()
        obj_layout.addWidget(QLabel("Objective:"))
        self.objective_combo = QComboBox()
        self.objective_combo.addItems(["DPS", "Life", "EHP", "Balanced"])
        obj_layout.addWidget(self.objective_combo)
        config_layout.addLayout(obj_layout)

        # Greedy-specific settings
        self.greedy_settings = QWidget()
        greedy_layout = QVBoxLayout(self.greedy_settings)
        greedy_layout.setContentsMargins(0, 0, 0, 0)

        iter_layout = QHBoxLayout()
        iter_layout.addWidget(QLabel("Max Iterations:"))
        self.iterations_spin = QSpinBox()
        self.iterations_spin.setRange(10, 500)
        self.iterations_spin.setValue(50)
        iter_layout.addWidget(self.iterations_spin)
        greedy_layout.addLayout(iter_layout)

        config_layout.addWidget(self.greedy_settings)

        # Genetic-specific settings
        self.genetic_settings = QWidget()
        genetic_layout = QVBoxLayout(self.genetic_settings)
        genetic_layout.setContentsMargins(0, 0, 0, 0)

        pop_layout = QHBoxLayout()
        pop_layout.addWidget(QLabel("Population:"))
        self.population_spin = QSpinBox()
        self.population_spin.setRange(10, 100)
        self.population_spin.setValue(30)
        pop_layout.addWidget(self.population_spin)
        genetic_layout.addLayout(pop_layout)

        gen_layout = QHBoxLayout()
        gen_layout.addWidget(QLabel("Generations:"))
        self.generations_spin = QSpinBox()
        self.generations_spin.setRange(10, 200)
        self.generations_spin.setValue(50)
        gen_layout.addWidget(self.generations_spin)
        genetic_layout.addLayout(gen_layout)

        self.genetic_settings.hide()
        config_layout.addWidget(self.genetic_settings)

        # Common settings
        self.optimize_masteries_check = QCheckBox("Optimize Masteries")
        self.optimize_masteries_check.setChecked(True)
        config_layout.addWidget(self.optimize_masteries_check)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        # Optimize Button
        self.optimize_btn = QPushButton("Start Optimization")
        self.optimize_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }")
        self.optimize_btn.clicked.connect(self.start_optimization)
        self.optimize_btn.setEnabled(False)
        layout.addWidget(self.optimize_btn)

        # Progress Section
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()

        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("Ready to optimize")
        progress_layout.addWidget(self.progress_label)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # Output Section
        output_group = QGroupBox("Optimized Build Output")
        output_layout = QVBoxLayout()

        self.pob_output = QTextEdit()
        self.pob_output.setReadOnly(True)
        self.pob_output.setPlaceholderText("Optimized build code will appear here...")
        self.pob_output.setMaximumHeight(100)
        output_layout.addWidget(self.pob_output)

        copy_btn_layout = QHBoxLayout()
        self.copy_btn = QPushButton("Copy to Clipboard")
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        self.copy_btn.setEnabled(False)
        copy_btn_layout.addWidget(self.copy_btn)

        self.import_pob_btn = QPushButton("Open in PoB")
        self.import_pob_btn.setEnabled(False)
        copy_btn_layout.addWidget(self.import_pob_btn)

        output_layout.addLayout(copy_btn_layout)
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        layout.addStretch()

        return panel

    def create_right_panel(self):
        """Create right panel with visualization and results"""
        panel = QWidget()
        layout = QVBoxLayout(panel)

        # Tabs for different views
        tabs = QTabWidget()

        # Results Tab
        results_tab = self.create_results_tab()
        tabs.addTab(results_tab, "Results")

        # Build Details Tab
        details_tab = self.create_details_tab()
        tabs.addTab(details_tab, "Build Details")

        # Tree Visualization Tab
        tree_tab = self.create_tree_tab()
        tabs.addTab(tree_tab, "Passive Tree")

        # Evolution Tab (for genetic algorithm)
        evolution_tab = self.create_evolution_tab()
        tabs.addTab(evolution_tab, "Evolution")

        layout.addWidget(tabs)

        return panel

    def create_results_tab(self):
        """Create results comparison tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Stats comparison table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Stat", "Original", "Optimized"])
        self.results_table.setRowCount(10)

        # Populate with placeholder rows
        stats = ["DPS", "Life", "EHP", "Energy Shield", "Mana", "Armour", "Evasion", "Block %", "Points Used", "Level"]
        for i, stat in enumerate(stats):
            self.results_table.setItem(i, 0, QTableWidgetItem(stat))
            self.results_table.setItem(i, 1, QTableWidgetItem("-"))
            self.results_table.setItem(i, 2, QTableWidgetItem("-"))

        layout.addWidget(self.results_table)

        # Improvement summary
        summary_group = QGroupBox("Improvement Summary")
        summary_layout = QVBoxLayout()

        self.improvement_label = QLabel("No optimization run yet")
        self.improvement_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        summary_layout.addWidget(self.improvement_label)

        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        return tab

    def create_details_tab(self):
        """Create build details tab (gear, gems, etc.)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Character info
        char_group = QGroupBox("Character")
        char_layout = QVBoxLayout()
        self.char_info_text = QTextEdit()
        self.char_info_text.setReadOnly(True)
        self.char_info_text.setPlaceholderText("Character information will appear here...")
        char_layout.addWidget(self.char_info_text)
        char_group.setLayout(char_layout)
        layout.addWidget(char_group)

        # Gear
        gear_group = QGroupBox("Equipment")
        gear_layout = QVBoxLayout()
        self.gear_text = QTextEdit()
        self.gear_text.setReadOnly(True)
        self.gear_text.setPlaceholderText("Equipment will appear here...")
        gear_layout.addWidget(self.gear_text)
        gear_group.setLayout(gear_layout)
        layout.addWidget(gear_group)

        # Gems
        gems_group = QGroupBox("Gems")
        gems_layout = QVBoxLayout()
        self.gems_text = QTextEdit()
        self.gems_text.setReadOnly(True)
        self.gems_text.setPlaceholderText("Gems will appear here...")
        gems_layout.addWidget(self.gems_text)
        gems_group.setLayout(gems_layout)
        layout.addWidget(gems_group)

        return tab

    def create_tree_tab(self):
        """Create passive tree visualization tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Add tree canvas
        from src.gui.widgets import TreeCanvas
        self.tree_canvas = TreeCanvas()
        self.tree_canvas.node_clicked.connect(self.on_node_clicked)
        layout.addWidget(self.tree_canvas)

        # Add controls
        controls_layout = QHBoxLayout()

        reset_view_btn = QPushButton("Reset View")
        reset_view_btn.clicked.connect(self.tree_canvas.reset_view)
        controls_layout.addWidget(reset_view_btn)

        controls_layout.addStretch()

        zoom_label = QLabel("Zoom: Mouse Wheel | Pan: Click & Drag")
        controls_layout.addWidget(zoom_label)

        layout.addLayout(controls_layout)

        return tab

    def on_node_clicked(self, node_id):
        """Handle node click in tree canvas"""
        logger.info(f"Node clicked: {node_id}")
        # TODO: Show node details in a tooltip or panel

    def create_evolution_tab(self):
        """Create evolution progress tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.evolution_text = QTextEdit()
        self.evolution_text.setReadOnly(True)
        self.evolution_text.setPlaceholderText("Evolution progress will appear here during genetic optimization...")
        layout.addWidget(self.evolution_text)

        return tab

    # Event Handlers

    def on_algorithm_changed(self, text):
        """Handle algorithm selection change"""
        if "Greedy" in text:
            self.greedy_settings.show()
            self.genetic_settings.hide()
        else:
            self.greedy_settings.hide()
            self.genetic_settings.show()

    def paste_from_clipboard(self):
        """Paste PoB code from clipboard"""
        clipboard = QApplication.clipboard()
        self.pob_input.setPlainText(clipboard.text())

    def load_build(self):
        """Load and decode PoB build"""
        try:
            from src.pob.codec import decode_pob_code
            from src.pob.xml_parser import parse_pob_stats
            from src.pob.modifier import get_passive_tree_summary

            pob_code = self.pob_input.toPlainText().strip()
            if not pob_code:
                QMessageBox.warning(self, "Error", "Please paste a PoB code first")
                return

            # Decode build
            self.progress_label.setText("Loading build...")
            self.current_build_xml = decode_pob_code(pob_code)

            # Parse build info
            stats = parse_pob_stats(self.current_build_xml)
            tree_summary = get_passive_tree_summary(self.current_build_xml)

            # Display build info
            info_text = f"""Character Level: {stats.get('Level', 'Unknown')}
Class: {stats.get('ClassName', 'Unknown')}
Ascendancy: {stats.get('AscendClassName', 'None')}

Passive Points: {len(tree_summary['allocated_nodes'])}
Mastery Effects: {len(tree_summary.get('mastery_effects', {}))}

Total DPS: {stats.get('TotalDPS', 0):,.0f}
Life: {stats.get('Life', 0):,.0f}
Energy Shield: {stats.get('EnergyShield', 0):,.0f}
Mana: {stats.get('Mana', 0):,.0f}
"""
            self.build_info_text.setPlainText(info_text)

            # Enable optimize button
            self.optimize_btn.setEnabled(True)
            self.progress_label.setText("Build loaded successfully")

            # Update results table with original stats
            self.update_results_table_original(stats, tree_summary)

            # Update tree canvas with allocated nodes
            self.tree_canvas.set_allocated_nodes(set(tree_summary['allocated_nodes']))

            # TODO: Display gear and gems
            self.display_build_details(stats)

            QMessageBox.information(self, "Success", "Build loaded successfully!")

        except Exception as e:
            logger.exception("Failed to load build")
            QMessageBox.critical(self, "Error", f"Failed to load build: {str(e)}")
            self.progress_label.setText("Error loading build")

    def update_results_table_original(self, stats, tree_summary):
        """Update results table with original build stats"""
        self.results_table.setItem(0, 1, QTableWidgetItem(f"{stats.get('TotalDPS', 0):,.0f}"))
        self.results_table.setItem(1, 1, QTableWidgetItem(f"{stats.get('Life', 0):,.0f}"))
        self.results_table.setItem(2, 1, QTableWidgetItem(f"{stats.get('TotalEHP', 0):,.0f}"))
        self.results_table.setItem(3, 1, QTableWidgetItem(f"{stats.get('EnergyShield', 0):,.0f}"))
        self.results_table.setItem(4, 1, QTableWidgetItem(f"{stats.get('Mana', 0):,.0f}"))
        self.results_table.setItem(5, 1, QTableWidgetItem(f"{stats.get('Armour', 0):,.0f}"))
        self.results_table.setItem(6, 1, QTableWidgetItem(f"{stats.get('Evasion', 0):,.0f}"))
        self.results_table.setItem(7, 1, QTableWidgetItem(f"{stats.get('BlockChance', 0):.1f}%"))
        self.results_table.setItem(8, 1, QTableWidgetItem(f"{len(tree_summary['allocated_nodes'])}"))
        self.results_table.setItem(9, 1, QTableWidgetItem(f"{stats.get('Level', 0)}"))

    def display_build_details(self, stats):
        """Display character info, gear, and gems"""
        # Character info
        char_text = f"""Level {stats.get('Level', '?')} {stats.get('ClassName', 'Unknown')}
Ascendancy: {stats.get('AscendClassName', 'None')}
"""
        self.char_info_text.setPlainText(char_text)

        # TODO: Parse and display gear from XML
        self.gear_text.setPlainText("Equipment parsing coming soon...")

        # TODO: Parse and display gems from XML
        self.gems_text.setPlainText("Gem parsing coming soon...")

    def start_optimization(self):
        """Start optimization in background thread"""
        try:
            from src.optimizer.tree_optimizer import GreedyTreeOptimizer
            from src.optimizer.genetic_optimizer import GeneticTreeOptimizer

            if not self.current_build_xml:
                QMessageBox.warning(self, "Error", "Please load a build first")
                return

            # Get settings
            is_greedy = "Greedy" in self.algorithm_combo.currentText()
            objective = self.objective_combo.currentText().lower()
            optimize_masteries = self.optimize_masteries_check.isChecked()

            # Create optimizer
            if is_greedy:
                optimizer = GreedyTreeOptimizer(
                    max_iterations=self.iterations_spin.value(),
                    optimize_masteries=optimize_masteries
                )
            else:
                optimizer = GeneticTreeOptimizer(
                    population_size=self.population_spin.value(),
                    generations=self.generations_spin.value(),
                    optimize_masteries=optimize_masteries
                )

            # Disable UI during optimization
            self.optimize_btn.setEnabled(False)
            self.load_build_btn.setEnabled(False)
            self.progress_label.setText("Optimization in progress...")
            self.progress_bar.setValue(0)

            # Create and start worker thread
            self.optimizer_thread = OptimizerThread(
                self.current_build_xml,
                optimizer,
                objective
            )
            self.optimizer_thread.progress.connect(self.on_optimization_progress)
            self.optimizer_thread.finished.connect(self.on_optimization_finished)
            self.optimizer_thread.error.connect(self.on_optimization_error)
            self.optimizer_thread.start()

        except Exception as e:
            logger.exception("Failed to start optimization")
            QMessageBox.critical(self, "Error", f"Failed to start optimization: {str(e)}")
            self.optimize_btn.setEnabled(True)
            self.load_build_btn.setEnabled(True)

    def on_optimization_progress(self, generation, best_fitness, avg_fitness):
        """Handle optimization progress updates"""
        self.progress_bar.setValue(int(generation / self.generations_spin.value() * 100))
        self.progress_label.setText(f"Generation {generation}: Best {best_fitness:+.2f}%, Avg {avg_fitness:+.2f}%")

        # Update evolution tab
        self.evolution_text.append(f"Gen {generation}: Best = {best_fitness:+.2f}%, Avg = {avg_fitness:+.2f}%")

    def on_optimization_finished(self, result):
        """Handle optimization completion"""
        try:
            from src.pob.codec import encode_pob_code
            from src.pob.xml_parser import parse_pob_stats
            from src.pob.modifier import get_passive_tree_summary

            self.current_result = result

            # Get optimized build code
            optimized_xml = result.optimized_xml if hasattr(result, 'optimized_xml') else result.best_xml
            optimized_code = encode_pob_code(optimized_xml)
            self.pob_output.setPlainText(optimized_code)

            # Parse optimized stats
            optimized_stats = parse_pob_stats(optimized_xml)
            optimized_tree = get_passive_tree_summary(optimized_xml)

            # Update results table
            self.results_table.setItem(0, 2, QTableWidgetItem(f"{optimized_stats.get('TotalDPS', 0):,.0f}"))
            self.results_table.setItem(1, 2, QTableWidgetItem(f"{optimized_stats.get('Life', 0):,.0f}"))
            self.results_table.setItem(2, 2, QTableWidgetItem(f"{optimized_stats.get('TotalEHP', 0):,.0f}"))
            self.results_table.setItem(3, 2, QTableWidgetItem(f"{optimized_stats.get('EnergyShield', 0):,.0f}"))
            self.results_table.setItem(4, 2, QTableWidgetItem(f"{optimized_stats.get('Mana', 0):,.0f}"))
            self.results_table.setItem(5, 2, QTableWidgetItem(f"{optimized_stats.get('Armour', 0):,.0f}"))
            self.results_table.setItem(6, 2, QTableWidgetItem(f"{optimized_stats.get('Evasion', 0):,.0f}"))
            self.results_table.setItem(7, 2, QTableWidgetItem(f"{optimized_stats.get('BlockChance', 0):.1f}%"))
            self.results_table.setItem(8, 2, QTableWidgetItem(f"{len(optimized_tree['allocated_nodes'])}"))
            self.results_table.setItem(9, 2, QTableWidgetItem(f"{optimized_stats.get('Level', 0)}"))

            # Update tree canvas with optimization results
            original_tree = get_passive_tree_summary(self.current_build_xml)
            original_nodes = set(original_tree['allocated_nodes'])
            optimized_nodes = set(optimized_tree['allocated_nodes'])

            added_nodes = optimized_nodes - original_nodes
            removed_nodes = original_nodes - optimized_nodes

            self.tree_canvas.set_allocated_nodes(optimized_nodes)
            self.tree_canvas.set_tree_diff(added_nodes, removed_nodes)

            # Update improvement summary
            if hasattr(result, 'optimized_stats'):
                improvement_text = f"""✅ Optimization Complete!

DPS: {result.optimized_stats.dps_change_percent:+.2f}%
Life: {result.optimized_stats.life_change_percent:+.2f}%
EHP: {result.optimized_stats.ehp_change_percent:+.2f}%
"""
            else:
                improvement_text = f"✅ Optimization Complete!\n\nBest fitness: {result.best_fitness:+.2f}%"

            self.improvement_label.setText(improvement_text)

            # Re-enable UI
            self.optimize_btn.setEnabled(True)
            self.load_build_btn.setEnabled(True)
            self.copy_btn.setEnabled(True)
            self.import_pob_btn.setEnabled(True)
            self.progress_bar.setValue(100)
            self.progress_label.setText("Optimization complete!")

            QMessageBox.information(self, "Success", "Optimization completed successfully!")

        except Exception as e:
            logger.exception("Error processing optimization result")
            QMessageBox.critical(self, "Error", f"Error processing result: {str(e)}")

    def on_optimization_error(self, error_msg):
        """Handle optimization error"""
        self.optimize_btn.setEnabled(True)
        self.load_build_btn.setEnabled(True)
        self.progress_label.setText("Optimization failed")
        QMessageBox.critical(self, "Error", f"Optimization failed: {error_msg}")

    def copy_to_clipboard(self):
        """Copy optimized build code to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.pob_output.toPlainText())
        QMessageBox.information(self, "Success", "Optimized build code copied to clipboard!")


def main():
    """Main entry point for GUI application"""
    app = QApplication(sys.argv)

    # Set application style
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
