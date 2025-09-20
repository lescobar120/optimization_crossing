# Enhanced portfolio_config_ui.py - Complete implementation with improved layout

import ipywidgets as widgets
from IPython.display import display, clear_output
import pandas as pd
from datetime import datetime, date
import json
from typing import Dict, List, Optional, Any
from dataclasses import asdict
import copy
from contextlib import redirect_stdout, redirect_stderr
import io


# Import your existing config classes
from portfolio_configs import PortfolioConfig, PortfolioConfigManager, PORTFOLIO_CONFIGS

class PortfolioConfigUI:
    """
    Enhanced UI with optimization and crossing execution capabilities.
    Features toggle navigation between main config, configuration management, and execution details.
    """
    
    def __init__(self, config_manager: PortfolioConfigManager = None, 
                 report_handler=None, orchestrator=None, crossing_engine=None,
                 workflow_state=None, ui_callbacks=None):
        """
        Initialize with optional execution components.
        
        Args:
            config_manager: Existing PortfolioConfigManager
            report_handler: ReportHandler instance for data retrieval
            orchestrator: OptimizationOrchestrator instance  
            crossing_engine: PortfolioCrossingEngine instance
            workflow_state: WorkflowState instance for sharing data
            ui_callbacks: Dictionary of callback functions for UI building
        """
        # Initialize config manager
        if config_manager is None:
            self.config_manager = PortfolioConfigManager(copy.deepcopy(PORTFOLIO_CONFIGS))
        else:
            self.config_manager = config_manager
        
        self.original_configs = copy.deepcopy(self.config_manager.configs)
        
        # Execution components (can be None initially)
        self.report_handler = report_handler
        self.orchestrator = orchestrator
        self.crossing_engine = crossing_engine
        
        # Workflow integration components
        self.workflow_state = workflow_state
        self.ui_callbacks = ui_callbacks or {}
        
        # Import analytics engine for analysis generation
        try:
            from portfolio_analytics_engine import PortfolioAnalyticsEngine
            self.analytics_engine = PortfolioAnalyticsEngine(tolerance_threshold=0.0005)
        except ImportError:
            self.analytics_engine = None
        
        # Execution state
        self.optimization_results = {}
        self.crossing_result = None
        self.execution_status = "ready"  # "ready", "optimizing", "crossing", "complete", "error"
        
        # View state
        self.current_view = "main"  # "main", "config_mgmt", "execution_detail"
        
        # Global settings
        self.global_settings = {
            'sector_weight_tolerance': 0.01,
            'country_weight_tolerance': 0.01,
            'security_weight_tolerance': 0.01,
            'optimization_date': date.today(),
            'reporting_currency': 'USD'
        }
        
        # UI state
        self.current_portfolio = None
        self.validation_status = {}
        
        # Create UI components
        self._create_widgets()
        self._setup_layout()
        self._setup_event_handlers()
        
        # Initialize with first portfolio
        portfolio_ids = list(self.config_manager.configs.keys())
        if portfolio_ids:
            self.current_portfolio = portfolio_ids[0]
            self._update_portfolio_display()
    
    def _create_widgets(self):
        """Create all UI widgets including toggle navigation."""
        
        # === PORTFOLIO CONFIGURATION WIDGETS ===
        self.portfolio_dropdown = widgets.Dropdown(
            options=list(self.config_manager.configs.keys()),
            description='Portfolio:',
            style={'description_width': 'initial'},
            layout=widgets.Layout(width='200px')
        )
        
        self.benchmark_display = widgets.HTML(
            value="<b>Benchmark:</b> Select a portfolio",
            layout=widgets.Layout(margin='5px 0px')
        )
        
        # Portfolio-specific parameters
        self.min_trade_size = widgets.IntText(
            description='Min Trade Size:',
            style={'description_width': '100px'},
            layout=widgets.Layout(width='200px'),
            tooltip='Minimum number of shares per trade'
        )
        
        self.round_lot_size = widgets.IntText(
            description='Round Lot Size:',
            style={'description_width': '100px'},
            layout=widgets.Layout(width='200px'),
            tooltip='Trade size must be multiple of this value'
        )
        
        self.min_trade_value = widgets.IntText(
            description='Min Trade Value:',
            style={'description_width': '100px'},
            layout=widgets.Layout(width='200px'),
            tooltip='Minimum dollar value per trade'
        )
        
        self.reset_portfolio_btn = widgets.Button(
            description='Reset to Default',
            button_style='warning',
            layout=widgets.Layout(width='150px', margin='10px 0px')
        )
        
        # === GLOBAL SETTINGS WIDGETS ===
        self.sector_tolerance = widgets.FloatText(
            value=1.0,
            description='Sector Tolerance:',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='180px'),
            step=0.01,
            tooltip='Global sector weight tolerance (±%)'
        )
        
        self.country_tolerance = widgets.FloatText(
            value=1.0,
            description='Country Tolerance:',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='180px'),
            step=0.01,
            tooltip='Global country weight tolerance (±%)'
        )
        
        self.security_tolerance = widgets.FloatText(
            value=1.0,
            description='Security Tolerance:',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='180px'),
            step=0.01,
            tooltip='Global security weight tolerance (±%)'
        )
        
        self.optimization_date = widgets.DatePicker(
            description='Optimization Date:',
            value=date.today(),
            style={'description_width': '120px'},
            layout=widgets.Layout(width='250px')
        )
        
        self.reporting_currency = widgets.Dropdown(
            options=['USD', 'EUR', 'GBP', 'JPY', 'CAD'],
            value='USD',
            description='Currency:',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='250px')
        )
        
        self.reset_global_btn = widgets.Button(
            description='Reset Global Settings',
            button_style='warning',
            layout=widgets.Layout(width='180px', margin='10px 0px')
        )
        
        # === EXECUTION WIDGETS ===
        self.execution_portfolios = widgets.SelectMultiple(
            options=list(self.config_manager.configs.keys()),
            value=list(self.config_manager.configs.keys()),  # Default: all portfolios
            description='Run On:',
            style={'description_width': '80px'},
            layout=widgets.Layout(width='250px', height='120px'),
            tooltip='Select portfolios to optimize'
        )
        
        self.run_optimization_btn = widgets.Button(
            description='Run Optimization',
            button_style='primary',
            layout=widgets.Layout(width='200px', margin='5px'),
            disabled=False
        )
        
        self.run_crossing_btn = widgets.Button(
            description='Run Crossing',
            button_style='success', 
            layout=widgets.Layout(width='200px', margin='5px'),
            disabled=True  # Disabled until optimization completes
        )
        
        self.progress_bar = widgets.IntProgress(
            value=0, min=0, max=100,
            description='Progress:',
            style={'description_width': '80px'},
            layout=widgets.Layout(width='250px', margin='5px')
        )
        
        self.status_label = widgets.HTML(
            value="<b>Status:</b> Ready to run optimization",
            layout=widgets.Layout(margin='5px')
        )
        
        # Results summary for optimization only
        self.results_summary = widgets.HTML(
            value="<i>No optimization results yet</i>",
            layout=widgets.Layout(margin='5px', padding='10px', 
                                border='1px solid #ddd', min_height='100px')
        )
        
        # Separate crossing summary display
        self.crossing_summary_display = widgets.HTML(
            value="<i>No crossing results yet</i>",
            layout=widgets.Layout(margin='5px', padding='10px', 
                                border='1px solid #ddd', min_height='100px')
        )
        
        self.execution_output = widgets.Output(
            layout=widgets.Layout(
                border='1px solid #ccc',
                padding='10px',
                height='600px',
                overflow='auto'
            )
        )
        
        # === TOGGLE NAVIGATION BUTTONS ===
        self.config_mgmt_btn = widgets.Button(
            description='Configuration Management',
            button_style='info',
            layout=widgets.Layout(width='180px', margin='5px'),
            tooltip='Preview, export, and import configurations'
        )
        
        self.execution_detail_btn = widgets.Button(
            description='Workflow Details', 
            button_style='success',
            layout=widgets.Layout(width='150px', margin='5px'),
            tooltip='View detailed workflow progress and logs'
        )
        
        self.back_to_main_btn = widgets.Button(
            description='← Back to Main',
            button_style='warning',
            layout=widgets.Layout(width='150px', margin='5px')
        )
        
        # === CONFIGURATION MANAGEMENT WIDGETS ===
        self.preview_btn = widgets.Button(
            description='Preview Configuration',
            button_style='info',
            layout=widgets.Layout(width='180px', margin='5px')
        )
        
        self.export_btn = widgets.Button(
            description='Export Settings',
            button_style='success',
            layout=widgets.Layout(width='180px', margin='5px')
        )
        
        self.import_btn = widgets.Button(
            description='Import Settings',
            button_style='primary',
            layout=widgets.Layout(width='180px', margin='5px')
        )
        
        self.config_output_area = widgets.Output(
            layout=widgets.Layout(
                border='1px solid #ccc',
                padding='10px',
                height='400px',
                overflow='auto'
            )
        )
        
        # === COLLAPSIBLE EXECUTION LOG ===
        self.log_accordion = widgets.Accordion([
            widgets.VBox([
                widgets.HTML("<p style='color: #666; font-style: italic;'>Workflow log will appear here when workflows are running...</p>"),
                self.execution_output
            ])
        ])
        self.log_accordion.set_title(0, "Workflow Log")
        self.log_accordion.selected_index = None  # Start collapsed
        
        # === STATUS AND NAVIGATION ===
        self.view_indicator = widgets.HTML(
            value="<b>Current View:</b> Main Configuration",
            layout=widgets.Layout(margin='5px')
        )
    
    def _setup_layout(self):
        """Create layout with view switching capability."""
        
        # === MAIN VIEW LAYOUT ===
        # Left Panel - Portfolio Settings
        self.left_panel = widgets.VBox([
            widgets.HTML("<h3>Portfolio Configuration</h3>"),
            self.portfolio_dropdown,
            self.benchmark_display,
            widgets.HTML("<h4>Trading Parameters</h4>"),
            self.min_trade_size,
            self.round_lot_size,
            self.min_trade_value,
            self.reset_portfolio_btn
        ], layout=widgets.Layout(
            border='1px solid #ddd', padding='15px', margin='5px', width='320px'
        ))
        
        # Center Panel - Global Settings
        self.center_panel = widgets.VBox([
            widgets.HTML("<h3>Global Settings</h3>"),
            widgets.HTML("<h4>Weight Tolerances (Applied to All Portfolios)</h4>"),
            self.sector_tolerance,
            self.country_tolerance,
            self.security_tolerance,
            widgets.HTML("<h4>Optimization Settings</h4>"),
            self.optimization_date,
            self.reporting_currency,
            self.reset_global_btn
        ], layout=widgets.Layout(
            border='1px solid #ddd', padding='15px', margin='5px', width='320px'
        ))
        
        # Right Panel - IMPROVED LAYOUT
        # Advanced actions row at top (horizontal)
        advanced_actions_row = widgets.HBox([
            self.config_mgmt_btn,
            self.execution_detail_btn
        ], layout=widgets.Layout(justify_content='flex-start', margin='5px 0px'))
        
        # Status row with progress and status side by side (horizontal)
        status_row = widgets.HBox([
            self.progress_bar,
            widgets.VBox([self.status_label], layout=widgets.Layout(margin='0px 10px'))
        ], layout=widgets.Layout(align_items='center', margin='5px 0px'))
        
        self.right_panel_main = widgets.VBox([
            widgets.HTML("<h3>Execute Workflow</h3>"),
            widgets.HTML("<h4>Advanced Actions</h4>"),
            advanced_actions_row,
            widgets.HTML("<hr>"),
            widgets.HTML("<h4>Portfolio Selection</h4>"),
            self.execution_portfolios,
            widgets.HTML("<h4>Run Analysis</h4>"),
            widgets.VBox([self.run_optimization_btn, self.run_crossing_btn]),
            widgets.HTML("<hr>"),
            widgets.HTML("<h4>Status</h4>"),
            status_row
        ], layout=widgets.Layout(
            border='1px solid #ddd', padding='15px', margin='5px', width='380px'
        ))
        
        # === CONFIGURATION MANAGEMENT VIEW ===
        self.config_mgmt_view = widgets.VBox([
            widgets.HTML("<h2>Configuration Management</h2>"),
            widgets.HBox([self.back_to_main_btn, self.view_indicator]),
            widgets.HTML("<hr>"),
            widgets.VBox([
                widgets.HTML("<h3>Configuration Actions</h3>"),
                widgets.HBox([self.preview_btn, self.export_btn]),
                self.import_btn,
                widgets.HTML("<h3>Configuration Output</h3>"),
                self.config_output_area
            ], layout=widgets.Layout(
                border='1px solid #ddd', padding='20px', margin='10px'
            ))
        ])
        
        # === EXECUTION DETAIL VIEW - IMPROVED RESULTS SECTION ===
        # Enhanced results summary with separate optimization and crossing sections
        self.enhanced_results_section = widgets.VBox([
            widgets.HTML("<h4>Optimization Results</h4>"),
            self.results_summary,
            widgets.HTML("<h4>Crossing Analysis</h4>"),
            self.crossing_summary_display
        ])
        
        self.execution_detail_view = widgets.VBox([
            widgets.HTML("<h2>Workflow Details</h2>"),
            widgets.HBox([self.back_to_main_btn, self.view_indicator]),
            widgets.HTML("<hr>"),
            widgets.VBox([
                widgets.HTML("<h3>Workflow Status</h3>"),
                widgets.HBox([
                    self.progress_bar,
                    widgets.VBox([self.status_label], layout=widgets.Layout(margin='0px 10px'))
                ], layout=widgets.Layout(align_items='center')),
                widgets.HTML("<h3>Results Summary</h3>"),
                self.enhanced_results_section,
                widgets.HTML("<h3>Workflow Log</h3>"),
                self.log_accordion
            ], layout=widgets.Layout(
                border='1px solid #ddd', padding='20px', margin='10px'
            ))
        ])
        
        # === MAIN LAYOUT CONTAINER ===
        self.main_config_layout = widgets.HBox([
            self.left_panel,
            self.center_panel,
            self.right_panel_main
        ])
        
        # === DYNAMIC LAYOUT CONTAINER ===
        self.main_layout = widgets.VBox([
            self.main_config_layout  # Start with main view
        ])
    
    def _setup_event_handlers(self):
        """Setup all event handlers including view navigation."""
        
        # Portfolio configuration handlers
        self.portfolio_dropdown.observe(self._on_portfolio_change, names='value')
        self.min_trade_size.observe(self._on_portfolio_param_change, names='value')
        self.round_lot_size.observe(self._on_portfolio_param_change, names='value')
        self.min_trade_value.observe(self._on_portfolio_param_change, names='value')
        
        # Global settings handlers
        self.sector_tolerance.observe(self._on_global_param_change, names='value')
        self.country_tolerance.observe(self._on_global_param_change, names='value')
        self.security_tolerance.observe(self._on_global_param_change, names='value')
        self.optimization_date.observe(self._on_global_param_change, names='value')
        self.reporting_currency.observe(self._on_global_param_change, names='value')
        
        # Reset button handlers
        self.reset_portfolio_btn.on_click(self._on_reset_portfolio)
        self.reset_global_btn.on_click(self._on_reset_global)
        
        # Execution button handlers
        self.run_optimization_btn.on_click(self._on_run_optimization)
        self.run_crossing_btn.on_click(self._on_run_crossing)
        
        # View navigation handlers
        self.config_mgmt_btn.on_click(self._show_config_mgmt_view)
        self.execution_detail_btn.on_click(self._show_execution_detail_view)
        self.back_to_main_btn.on_click(self._show_main_view)
        
        # Configuration management handlers
        self.preview_btn.on_click(self._on_preview_config)
        self.export_btn.on_click(self._on_export_config)
        self.import_btn.on_click(self._on_import_config)
    
    # === PORTFOLIO CONFIGURATION METHODS ===
    
    def _on_portfolio_change(self, change):
        """Handle portfolio selection change."""
        self.current_portfolio = change['new']
        self._update_portfolio_display()
        self._update_status()
    
    def _on_portfolio_param_change(self, change):
        """Handle portfolio-specific parameter changes."""
        if self.current_portfolio is None:
            return
        
        config = self.config_manager.get_config(self.current_portfolio)
        
        if change['owner'] == self.min_trade_size:
            config.min_trade_size = change['new']
        elif change['owner'] == self.round_lot_size:
            config.round_lot_size = change['new']
        elif change['owner'] == self.min_trade_value:
            config.min_trade_value = change['new']
        
        self._validate_current_config()
        self._update_status()
        self._update_last_modified()
    
    def _on_global_param_change(self, change):
        """Handle global parameter changes."""
        if change['owner'] == self.sector_tolerance:
            self.global_settings['sector_weight_tolerance'] = change['new'] / 100
        elif change['owner'] == self.country_tolerance:
            self.global_settings['country_weight_tolerance'] = change['new'] / 100
        elif change['owner'] == self.security_tolerance:
            self.global_settings['security_weight_tolerance'] = change['new'] / 100
        elif change['owner'] == self.optimization_date:
            self.global_settings['optimization_date'] = change['new']
        elif change['owner'] == self.reporting_currency:
            self.global_settings['reporting_currency'] = change['new']
        
        self._apply_global_tolerances()
        self._update_status()
        self._update_last_modified()
    
    def _apply_global_tolerances(self):
        """Apply global tolerance settings to all portfolios."""
        for config in self.config_manager.configs.values():
            config.sector_weight_tolerance = self.global_settings['sector_weight_tolerance']
            config.country_weight_tolerance = self.global_settings['country_weight_tolerance']
            config.security_weight_tolerance = self.global_settings['security_weight_tolerance']
    
    def _update_portfolio_display(self):
        """Update the portfolio-specific display widgets."""
        if self.current_portfolio is None:
            return
        
        config = self.config_manager.get_config(self.current_portfolio)
        self.benchmark_display.value = f"<b>Benchmark:</b> {config.benchmark}"
        self.min_trade_size.value = config.min_trade_size
        self.round_lot_size.value = config.round_lot_size
        self.min_trade_value.value = config.min_trade_value
    
    def _validate_current_config(self):
        """Validate current portfolio configuration."""
        if self.current_portfolio is None:
            return
        
        config = self.config_manager.get_config(self.current_portfolio)
        errors = []
        
        if config.min_trade_size <= 0:
            errors.append("Min trade size must be positive")
        if config.round_lot_size <= 0:
            errors.append("Round lot size must be positive")
        if config.min_trade_value <= 0:
            errors.append("Min trade value must be positive")
        if config.round_lot_size > config.min_trade_size:
            errors.append("Round lot size cannot exceed min trade size")
        
        self.validation_status[self.current_portfolio] = {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def _update_status(self):
        """Update the status display."""
        pass
    
    def _update_last_modified(self):
        """Update the last modified timestamp."""
        pass
    
    def _on_reset_portfolio(self, button):
        """Reset current portfolio to default settings."""
        if self.current_portfolio is None:
            return
        
        original_config = self.original_configs[self.current_portfolio]
        current_config = self.config_manager.get_config(self.current_portfolio)
        current_config.min_trade_size = original_config.min_trade_size
        current_config.round_lot_size = original_config.round_lot_size
        current_config.min_trade_value = original_config.min_trade_value
        
        self._update_portfolio_display()
        self._update_status()
        self._update_last_modified()
    
    def _on_reset_global(self, button):
        """Reset global settings to defaults."""
        self.global_settings = {
            'sector_weight_tolerance': 0.01,
            'country_weight_tolerance': 0.01,
            'security_weight_tolerance': 0.01,
            'optimization_date': date.today(),
            'reporting_currency': 'USD'
        }
        
        self.sector_tolerance.value = 1.0
        self.country_tolerance.value = 1.0
        self.security_tolerance.value = 1.0
        self.optimization_date.value = date.today()
        self.reporting_currency.value = 'USD'
        
        self._apply_global_tolerances()
        self._update_status()
        self._update_last_modified()
    
    # === VIEW NAVIGATION METHODS ===
    
    def _show_main_view(self, button=None):
        """Switch to main configuration view."""
        self.current_view = "main"
        self.main_layout.children = [self.main_config_layout]
        self.view_indicator.value = "<b>Current View:</b> Main Configuration"
    
    def _show_config_mgmt_view(self, button):
        """Switch to configuration management view."""
        self.current_view = "config_mgmt"
        self.main_layout.children = [self.config_mgmt_view]
        self.view_indicator.value = "<b>Current View:</b> Configuration Management"
    
    def _show_execution_detail_view(self, button):
        """Switch to execution detail view."""
        self.current_view = "execution_detail"
        self.main_layout.children = [self.execution_detail_view]
        self.view_indicator.value = "<b>Current View:</b> Workflow Details"
    
    # === CONFIGURATION MANAGEMENT METHODS ===
    
    def _on_preview_config(self, button):
        """Show preview of current configuration."""
        with self.config_output_area:
            clear_output()
            print("=== PORTFOLIO OPTIMIZATION CONFIGURATION PREVIEW ===\n")
            
            print("GLOBAL SETTINGS:")
            print(f"  Sector Weight Tolerance: ±{self.global_settings['sector_weight_tolerance']*100:.2f}%")
            print(f"  Country Weight Tolerance: ±{self.global_settings['country_weight_tolerance']*100:.2f}%")
            print(f"  Security Weight Tolerance: ±{self.global_settings['security_weight_tolerance']*100:.2f}%")
            print(f"  Optimization Date: {self.global_settings['optimization_date']}")
            print(f"  Reporting Currency: {self.global_settings['reporting_currency']}")
            print()
            
            print("PORTFOLIO-SPECIFIC SETTINGS:")
            for portfolio_id, config in self.config_manager.configs.items():
                print(f"\n{portfolio_id} (Benchmark: {config.benchmark}):")
                print(f"  Min Trade Size: {config.min_trade_size:,} shares")
                print(f"  Round Lot Size: {config.round_lot_size:,} shares")
                print(f"  Min Trade Value: ${config.min_trade_value:,}")
                
                status = self.validation_status.get(portfolio_id, {'valid': True, 'errors': []})
                if not status['valid']:
                    print(f"  VALIDATION ERRORS: {', '.join(status['errors'])}")
    
    def _on_export_config(self, button):
        """Export current configuration to JSON."""
        with self.config_output_area:
            clear_output()
            
            export_data = {
                'global_settings': self.global_settings.copy(),
                'portfolio_configs': {}
            }
            
            export_data['global_settings']['optimization_date'] = str(self.global_settings['optimization_date'])
            
            for portfolio_id, config in self.config_manager.configs.items():
                export_data['portfolio_configs'][portfolio_id] = asdict(config)
            
            print("=== EXPORTED CONFIGURATION (Copy this JSON) ===\n")
            print(json.dumps(export_data, indent=2))
    
    def _on_import_config(self, button):
        """Import configuration from JSON."""
        with self.config_output_area:
            clear_output()
            print("=== IMPORT CONFIGURATION ===\n")
            print("To import a configuration:")
            print("1. Copy your JSON configuration")
            print("2. Create a new cell and run:")
            print("   config_ui.import_from_json(your_json_string)")
    
    def import_from_json(self, json_string: str):
        """Import configuration from JSON string."""
        try:
            data = json.loads(json_string)
            
            if 'global_settings' in data:
                self.global_settings.update(data['global_settings'])
                
                if 'optimization_date' in self.global_settings:
                    date_str = self.global_settings['optimization_date']
                    self.global_settings['optimization_date'] = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                self.sector_tolerance.value = self.global_settings['sector_weight_tolerance'] * 100
                self.country_tolerance.value = self.global_settings['country_weight_tolerance'] * 100
                self.security_tolerance.value = self.global_settings['security_weight_tolerance'] * 100
                self.optimization_date.value = self.global_settings['optimization_date']
                self.reporting_currency.value = self.global_settings['reporting_currency']
            
            if 'portfolio_configs' in data:
                for portfolio_id, config_data in data['portfolio_configs'].items():
                    if portfolio_id in self.config_manager.configs:
                        config = self.config_manager.configs[portfolio_id]
                        config.min_trade_size = config_data['min_trade_size']
                        config.round_lot_size = config_data['round_lot_size']
                        config.min_trade_value = config_data['min_trade_value']
                        config.sector_weight_tolerance = config_data.get('sector_weight_tolerance', 0.01)
                        config.country_weight_tolerance = config_data.get('country_weight_tolerance', 0.01)
                        config.security_weight_tolerance = config_data.get('security_weight_tolerance', 0.01)
            
            self._apply_global_tolerances()
            self._update_portfolio_display()
            self._update_status()
            self._update_last_modified()
            
            print("Configuration imported successfully!")
            
        except Exception as e:
            print(f"Import failed: {str(e)}")
    
    # === EXECUTION METHODS ===
    
    def _on_run_optimization(self, button):
        """Handle optimization button click."""
        if not self._validate_execution_readiness():
            return
        
        self._set_execution_state("optimizing")
        self._run_optimization_workflow()
    
    def _on_run_crossing(self, button):
        """Handle crossing button click.""" 
        if not self.optimization_results:
            self._log_execution("ERROR: No optimization results available for crossing")
            return
        
        self._set_execution_state("crossing")
        self._run_crossing_workflow()
    
    def _validate_execution_readiness(self) -> bool:
        """Validate that execution can proceed."""
        if not self.orchestrator or not self.report_handler:
            self._log_execution("ERROR: Missing workflow components. Need orchestrator and report_handler.")
            return False
        
        selected_portfolios = list(self.execution_portfolios.value)
        if not selected_portfolios:
            self._log_execution("ERROR: No portfolios selected for workflow")
            return False
        
        return True
    
    def _set_execution_state(self, state: str):
        """Update UI based on execution state."""
        self.execution_status = state
        
        if state == "optimizing":
            self.run_optimization_btn.disabled = True
            self.run_crossing_btn.disabled = True
            self.status_label.value = "<b>Status:</b> <span style='color: orange;'>Running optimization...</span>"
            self.progress_bar.value = 0
            
            if self.current_view == "main":
                self._show_execution_detail_view(None)
                self.log_accordion.selected_index = 0
            
        elif state == "crossing":
            self.run_optimization_btn.disabled = True  
            self.run_crossing_btn.disabled = True
            self.status_label.value = "<b>Status:</b> <span style='color: blue;'>Running crossing analysis...</span>"
            
            if self.current_view == "main":
                self._show_execution_detail_view(None)
                self.log_accordion.selected_index = 0
            
        elif state == "complete":
            self.run_optimization_btn.disabled = False
            self.run_crossing_btn.disabled = False
            self.status_label.value = "<b>Status:</b> <span style='color: green;'>Workflow complete</span>"
            self.progress_bar.value = 100
            
        elif state == "error":
            self.run_optimization_btn.disabled = False
            self.run_crossing_btn.disabled = True
            self.status_label.value = "<b>Status:</b> <span style='color: red;'>Error occurred</span>"
            
        elif state == "ready":
            self.run_optimization_btn.disabled = False
            self.run_crossing_btn.disabled = not bool(self.optimization_results)
            self.status_label.value = "<b>Status:</b> Ready to run"
    
    def _log_execution(self, message: str):
        """Add message to execution log and auto-expand if needed."""
        with self.execution_output:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] {message}")
        
        if self.current_view == "execution_detail" and "Starting" in message:
            self.log_accordion.selected_index = 0
    
    # inside PortfolioConfigUI
    def _print_analysis_report_to_output(self, portfolio_id: str, analysis_result):
        buf_out, buf_err = io.StringIO(), io.StringIO()
        # Capture anything the analytics engine prints/logs to stdout/stderr
        with redirect_stdout(buf_out), redirect_stderr(buf_err):
            self.analytics_engine.print_detailed_analysis_report(analysis_result)

        text = (buf_out.getvalue() + buf_err.getvalue()).strip()
        if not text:
            text = "(no analysis text emitted)"

        with self.execution_output:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] Analysis Report — {portfolio_id}")
            print()
            print(text)
            print()

    def _print_crossing_summary_to_output(self, crossing_result) -> None:
        """print crossing analysis summary to workflow log"""
        with self.execution_output:
            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}] Crossing Analysis Report")
            print()
            print("=== CROSSING ANALYSIS SUMMARY ===")
            summary = crossing_result.crossing_summary

            print(f"Portfolio Analysis:")
            print(f"  Total portfolios processed: {summary['total_portfolios']}")

            print(f"\nOriginal Trade Data:")
            print(f"  Original trade count: {summary['original_trade_count']:,}")
            print(f"  Original volume: {summary['original_volume']:,.0f}")

            print(f"\nCrossing Results:")
            print(f"  Crossed trade count: {summary['crossed_trade_count']:,}")
            print(f"  Crossed volume: {summary['crossed_volume']:,.0f}")
            print(f"  Crossing rate: {summary['crossing_rate']:.1%}")
            print(f"  Volume reduction: {summary['volume_reduction']:,.0f}")

            print(f"\nRemaining Trades:")
            print(f"  Remaining trade count: {summary['remaining_trade_count']:,}")
            print(f"  Remaining volume: {summary['remaining_volume']:,.0f}")

            print(f"\nSecurity Analysis:")
            print(f"  Securities with crosses: {summary['securities_with_crosses']}")
            print(f"  Securities needing external liquidity: {summary['securities_needing_external_liquidity']}")
            print()

    def _run_optimization_workflow(self):
        """Execute optimization workflow synchronously."""
        try:
            self._log_execution("Starting optimization workflow...")
            
            selected_portfolios = list(self.execution_portfolios.value)
            optimization_date = self.global_settings['optimization_date'].strftime('%Y-%m-%d')
            
            self._log_execution(f"Running optimization for {len(selected_portfolios)} portfolios")
            self._log_execution(f"Optimization date: {optimization_date}")
            
            self.progress_bar.value = 10
            
            # Run batch optimization
            batch_results = self.orchestrator.run_batch_optimizations(
                portfolio_ids=selected_portfolios,
                optimization_date=optimization_date
            )
            
            # Check if any portfolio failed - stop completely if so
            failed_portfolios = [pid for pid, result in batch_results.items() if result.status == "FAILED"]
            if failed_portfolios:
                self._log_execution(f"ERROR: {len(failed_portfolios)} portfolios failed: {failed_portfolios}")
                self._log_execution("Stopping workflow due to portfolio failures")
                
                # Clear UI tabs on error
                if self.ui_callbacks and 'clear_all_tabs' in self.ui_callbacks:
                    self._log_execution("Clearing result tabs due to error...")
                    self.ui_callbacks['clear_all_tabs']()
                
                self._set_execution_state("error")
                return
            
            self.optimization_results = batch_results
            self.progress_bar.value = 40

            # Store optimization results in workflow state
            if self.workflow_state:
                self.workflow_state.set_optimization_results(batch_results)
            
            # Generate analysis results if analytics engine available
            analysis_results = {}
            if self.analytics_engine:
                self._log_execution("Generating portfolio analysis results...")
                
                for portfolio_id, result in batch_results.items():
                    if (result.status == "SUCCESS" and 
                        result.clean_holdings_data is not None and 
                        result.proposed_trades_df is not None):
                        
                        try:
                            self._log_execution(f"Analyzing portfolio {portfolio_id}...")
                            analysis_result = self.analytics_engine.analyze_portfolio_optimization(
                                portfolio_id=portfolio_id,
                                original_holdings_df=result.clean_holdings_data,
                                proposed_trades_df=result.proposed_trades_df
                            )
                            analysis_results[portfolio_id] = analysis_result

                            self._print_analysis_report_to_output(portfolio_id, analysis_result)

                            
                        except Exception as e:
                            self._log_execution(f"Warning: Analysis failed for {portfolio_id}: {str(e)}")
                
                self._log_execution(f"Generated analysis results for {len(analysis_results)} portfolios")
            
            else:
                self._log_execution("Warning: No analytics engine available - skipping analysis generation")
            
            self.progress_bar.value = 70
            
            # Store analysis results in workflow state
            if self.workflow_state:
                self.workflow_state.set_analysis_results(analysis_results)
            
            # Update results summary
            summary = self.orchestrator.get_batch_summary(batch_results)
            self._update_results_summary(summary, None)
            
            self._log_execution(f"Optimization complete: {summary['success_count']} success, {summary['failure_count']} failures")
            
            # Trigger UI building callback
            if self.ui_callbacks and 'build_optimization_ui' in self.ui_callbacks:
                self._log_execution("Building optimization results UI...")
                try:
                    self.ui_callbacks['build_optimization_ui']()
                    self._log_execution("Optimization results UI built successfully")
                except Exception as e:
                    self._log_execution(f"Error building optimization UI: {str(e)}")
            else:
                self._log_execution("Warning: No UI callback available for building optimization results")
            
            self.progress_bar.value = 100
            self.run_crossing_btn.disabled = False
            self._set_execution_state("ready")
            
        except Exception as e:
            self._log_execution(f"Optimization workflow failed: {str(e)}")
            
            # Clear UI tabs on error
            if self.ui_callbacks and 'clear_all_tabs' in self.ui_callbacks:
                self._log_execution("Clearing result tabs due to error...")
                self.ui_callbacks['clear_all_tabs']()
            
            self._set_execution_state("error")
    
    def _run_crossing_workflow(self):
        """Execute crossing workflow synchronously."""
        try:
            self._log_execution("Starting crossing analysis...")
            
            if not self.crossing_engine:
                self._log_execution("ERROR: No crossing engine available")
                self._set_execution_state("error") 
                return
            
            # Prepare portfolio trades data
            portfolio_trades = {}
            for portfolio_id, result in self.optimization_results.items():
                if result.status == "SUCCESS" and result.proposed_trades_df is not None:
                    portfolio_trades[portfolio_id] = result.proposed_trades_df
            
            if not portfolio_trades:
                self._log_execution("ERROR: No successful optimization results available for crossing")
                self._set_execution_state("error")
                return
            
            self._log_execution(f"Analyzing trades from {len(portfolio_trades)} portfolios")
            
            # Execute crossing analysis
            crossing_result = self.crossing_engine.execute_crossing(portfolio_trades)
            self.crossing_result = crossing_result
            
            # Store crossing results in workflow state
            if self.workflow_state:
                self.workflow_state.set_crossing_result(crossing_result)
            
            # Update results summary
            opt_summary = self.orchestrator.get_batch_summary(self.optimization_results)
            self._update_results_summary(opt_summary, crossing_result)
            
            self._print_crossing_summary_to_output(crossing_result)
            # self._log_execution(f"Crossing complete: {len(crossing_result.crossed_trades)} trades crossed")
            # self._log_execution(f"Volume reduction: {crossing_result.crossing_summary['volume_reduction']:,.0f} shares")
            # self._log_execution(f"Crossing rate: {crossing_result.crossing_summary['crossing_rate']:.1%}")
            
            # Trigger UI building callback
            if self.ui_callbacks and 'build_crossing_ui' in self.ui_callbacks:
                self._log_execution("Building crossing results UI...")
                try:
                    self.ui_callbacks['build_crossing_ui']()
                    self._log_execution("Crossing results UI built successfully")
                except Exception as e:
                    self._log_execution(f"Error building crossing UI: {str(e)}")
            else:
                self._log_execution("Warning: No UI callback available for building crossing results")
            
            self._set_execution_state("complete")
            
        except Exception as e:
            self._log_execution(f"Crossing workflow failed: {str(e)}")
            
            # Clear UI tabs on error
            if self.ui_callbacks and 'clear_all_tabs' in self.ui_callbacks:
                self._log_execution("Clearing result tabs due to error...")
                self.ui_callbacks['clear_all_tabs']()
            
            self._set_execution_state("error")
    
    def _update_results_summary(self, opt_summary: Dict, crossing_result=None):
        """Update the results summary display with separate sections."""
        # Update optimization results summary
        opt_html = "<div style='font-size: 12px;'>"
        opt_html += f"<b>Portfolio Analysis:</b><br/>"
        opt_html += f"• Total portfolios: {opt_summary['total_portfolios']}<br/>"
        opt_html += f"• Successful: {opt_summary['success_count']}<br/>"
        opt_html += f"• Failed: {opt_summary['failure_count']}<br/>"
        opt_html += f"• Success rate: {opt_summary['success_rate']:.1%}<br/>"
        opt_html += f"• Avg run time: {opt_summary['average_execution_time']:.1f}s<br/>"
        opt_html += f"• Total replacements: {opt_summary['total_replacements_made']}<br/>"
        opt_html += "</div>"
        self.results_summary.value = opt_html
        
        # Update crossing results summary
        if crossing_result:
            summary = crossing_result.crossing_summary
            crossing_html = "<div style='font-size: 12px;'>"
            crossing_html += f"<b>Trade Crossing Analysis:</b><br/>"
            crossing_html += f"• Original trades: {summary['original_trade_count']:,}<br/>"
            crossing_html += f"• Original volume: {summary['original_volume']:,}<br/>"
            crossing_html += f"• Crossed trades: {summary['crossed_trade_count']:,}<br/>"
            crossing_html += f"• Crossed volume: {summary['crossed_volume']:,}<br/>"
            crossing_html += f"• Crossing rate: {summary['crossing_rate']:.1%}<br/>"
            crossing_html += f"• Volume reduction: {summary['volume_reduction']:,.0f}<br/>"
            crossing_html += f"• Securities crossed: {summary['securities_with_crosses']}<br/>"
            crossing_html += f"• External liquidity needed: {summary['securities_needing_external_liquidity']}<br/>"
            crossing_html += "</div>"
            self.crossing_summary_display.value = crossing_html
        else:
            self.crossing_summary_display.value = "<i>No crossing results yet</i>"
    
    # === UTILITY METHODS ===
    
    def set_execution_components(self, report_handler=None, orchestrator=None, crossing_engine=None):
        """Set execution components after UI initialization."""
        if report_handler:
            self.report_handler = report_handler
        if orchestrator:
            self.orchestrator = orchestrator  
        if crossing_engine:
            self.crossing_engine = crossing_engine
    
    def get_config_manager(self) -> PortfolioConfigManager:
        """Get the updated configuration manager."""
        return self.config_manager
    
    def get_global_settings(self) -> Dict[str, Any]:
        """Get the current global settings."""
        return self.global_settings.copy()
    
    def get_optimization_results(self):
        """Get optimization results."""
        return self.optimization_results
    
    def get_crossing_result(self):
        """Get crossing result.""" 
        return self.crossing_result
    
    def display(self):
        """Display the UI."""
        display(self.main_layout)


# Convenience functions
def create_portfolio_config_ui_with_execution(config_manager=None, report_handler=None, 
                                            orchestrator=None, crossing_engine=None,
                                            workflow_state=None, ui_callbacks=None):
    """Create config UI with execution capabilities."""
    ui = PortfolioConfigUI(config_manager, report_handler, orchestrator, crossing_engine,
                          workflow_state, ui_callbacks)
    ui.display()
    return ui

def create_portfolio_config_ui(config_manager: PortfolioConfigManager = None) -> PortfolioConfigUI:
    """
    Convenience function to create and display the portfolio configuration UI.
    
    Args:
        config_manager: Existing PortfolioConfigManager or None for default
    
    Returns:
        PortfolioConfigUI instance
    """
    ui = PortfolioConfigUI(config_manager)
    ui.display()
    return ui


