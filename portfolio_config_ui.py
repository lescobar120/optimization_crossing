import ipywidgets as widgets
from IPython.display import display, clear_output
import pandas as pd
from datetime import datetime, date
import json
from typing import Dict, List, Optional, Any
from dataclasses import asdict
import copy

# Import your existing config classes
from portfolio_configs import PortfolioConfig, PortfolioConfigManager, PORTFOLIO_CONFIGS

class PortfolioConfigUI:
    """
    Interactive UI for managing portfolio optimization configurations.
    
    Provides a three-panel layout for editing portfolio-specific and global settings
    with real-time validation and preview capabilities.
    """
    
    def __init__(self, config_manager: PortfolioConfigManager = None):
        """
        Initialize the configuration UI.
        
        Args:
            config_manager: Existing PortfolioConfigManager or None to create new one
        """
        # Initialize with existing config or create new one
        if config_manager is None:
            self.config_manager = PortfolioConfigManager(copy.deepcopy(PORTFOLIO_CONFIGS))
        else:
            self.config_manager = config_manager
        
        # Store original configs for reset functionality
        self.original_configs = copy.deepcopy(self.config_manager.configs)
        
        # Global settings (applied to all portfolios)
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
        """Create all UI widgets."""
        
        # === LEFT PANEL - Portfolio Selection & Parameters ===
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
        
        # Portfolio-specific trading parameters
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
        
        # === CENTER PANEL - Global Settings ===
        self.sector_tolerance = widgets.FloatText(
            value=self.global_settings['sector_weight_tolerance'] * 100,
            description='Sector Tolerance:',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='180px'),
            step=0.01,
            tooltip='Global sector weight tolerance (±%)'
        )
        
        self.country_tolerance = widgets.FloatText(
            value=self.global_settings['country_weight_tolerance'] * 100,
            description='Country Tolerance:',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='180px'),
            step=0.01,
            tooltip='Global country weight tolerance (±%)'
        )
        
        self.security_tolerance = widgets.FloatText(
            value=self.global_settings['security_weight_tolerance'] * 100,
            description='Security Tolerance:',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='180px'),
            step=0.01,
            tooltip='Global security weight tolerance (±%)'
        )
        
        self.optimization_date = widgets.DatePicker(
            description='Optimization Date:',
            value=self.global_settings['optimization_date'],
            style={'description_width': '120px'},
            layout=widgets.Layout(width='250px')
        )
        
        self.reporting_currency = widgets.Dropdown(
            options=['USD', 'EUR', 'GBP', 'JPY', 'CAD'],
            value=self.global_settings['reporting_currency'],
            description='Currency:',
            style={'description_width': '120px'},
            layout=widgets.Layout(width='250px')
        )
        
        self.reset_global_btn = widgets.Button(
            description='Reset Global Settings',
            button_style='warning',
            layout=widgets.Layout(width='180px', margin='10px 0px')
        )
        
        # === RIGHT PANEL - Actions & Status ===
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
        
        self.status_display = widgets.HTML(
            value="<b>Status:</b> <span style='color: green;'>Configuration Valid</span>",
            layout=widgets.Layout(margin='10px 0px')
        )
        
        self.last_modified = widgets.HTML(
            value=f"<b>Last Modified:</b> {datetime.now().strftime('%H:%M:%S')}",
            layout=widgets.Layout(margin='5px 0px')
        )
        
        # Output area for preview/export
        self.output_area = widgets.Output(
            layout=widgets.Layout(
                border='1px solid #ccc',
                padding='10px',
                height='300px',
                overflow='auto'
            )
        )
    
    def _setup_layout(self):
        """Create the three-panel layout."""
        
        # Left Panel - Portfolio Settings
        left_panel = widgets.VBox([
            widgets.HTML("<h3>Portfolio Configuration</h3>"),
            self.portfolio_dropdown,
            self.benchmark_display,
            widgets.HTML("<h4>Trading Parameters</h4>"),
            self.min_trade_size,
            self.round_lot_size,
            self.min_trade_value,
            self.reset_portfolio_btn
        ], layout=widgets.Layout(
            border='1px solid #ddd',
            padding='15px',
            margin='5px',
            width='320px'
        ))
        
        # Center Panel - Global Settings
        center_panel = widgets.VBox([
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
            border='1px solid #ddd',
            padding='15px',
            margin='5px',
            width='320px'
        ))
        
        # Right Panel - Actions & Status
        right_panel = widgets.VBox([
            widgets.HTML("<h3>Actions & Status</h3>"),
            self.preview_btn,
            self.export_btn,
            self.import_btn,
            widgets.HTML("<hr>"),
            self.status_display,
            self.last_modified,
            widgets.HTML("<h4>Preview/Export Output</h4>"),
            self.output_area
        ], layout=widgets.Layout(
            border='1px solid #ddd',
            padding='15px',
            margin='5px',
            width='380px'
        ))
        
        # Main layout
        self.main_layout = widgets.HBox([
            left_panel,
            center_panel,
            right_panel
        ], layout=widgets.Layout(
            justify_content='space-around',
            align_items='flex-start',
            width='1100px'
        ))
    
    def _setup_event_handlers(self):
        """Setup event handlers for all interactive widgets."""
        
        # Portfolio selection
        self.portfolio_dropdown.observe(self._on_portfolio_change, names='value')
        
        # Portfolio-specific parameters
        self.min_trade_size.observe(self._on_portfolio_param_change, names='value')
        self.round_lot_size.observe(self._on_portfolio_param_change, names='value')
        self.min_trade_value.observe(self._on_portfolio_param_change, names='value')
        
        # Global parameters
        self.sector_tolerance.observe(self._on_global_param_change, names='value')
        self.country_tolerance.observe(self._on_global_param_change, names='value')
        self.security_tolerance.observe(self._on_global_param_change, names='value')
        self.optimization_date.observe(self._on_global_param_change, names='value')
        self.reporting_currency.observe(self._on_global_param_change, names='value')
        
        # Buttons
        self.reset_portfolio_btn.on_click(self._on_reset_portfolio)
        self.reset_global_btn.on_click(self._on_reset_global)
        self.preview_btn.on_click(self._on_preview_config)
        self.export_btn.on_click(self._on_export_config)
        self.import_btn.on_click(self._on_import_config)
    
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
        
        # Update the config based on which widget changed
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
        
        # Apply global tolerances to all portfolios
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
        
        # Update benchmark display
        self.benchmark_display.value = f"Benchmark:<font color='gray'><b> {config.benchmark}</b> "
        
        # Update parameter widgets
        self.min_trade_size.value = config.min_trade_size
        self.round_lot_size.value = config.round_lot_size
        self.min_trade_value.value = config.min_trade_value
    
    def _validate_current_config(self):
        """Validate current portfolio configuration."""
        if self.current_portfolio is None:
            return
        
        config = self.config_manager.get_config(self.current_portfolio)
        errors = []
        
        # Validation rules
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
        all_valid = all(
            status.get('valid', True) 
            for status in self.validation_status.values()
        )
        
        if all_valid:
            self.status_display.value = (
                "<b>Status:</b> <span style='color: green;'>Configuration Valid</span>"
            )
        else:
            error_count = sum(
                len(status.get('errors', [])) 
                for status in self.validation_status.values()
            )
            self.status_display.value = (
                f"<b>Status:</b> <span style='color: red;'>✗ {error_count} Validation Error(s)</span>"
            )
    
    def _update_last_modified(self):
        """Update the last modified timestamp."""
        self.last_modified.value = f"<b>Last Modified:</b> {datetime.now().strftime('%H:%M:%S')}"
    
    def _on_reset_portfolio(self, button):
        """Reset current portfolio to default settings."""
        if self.current_portfolio is None:
            return
        
        # Get original config
        original_config = self.original_configs[self.current_portfolio]
        
        # Reset current config
        current_config = self.config_manager.get_config(self.current_portfolio)
        current_config.min_trade_size = original_config.min_trade_size
        current_config.round_lot_size = original_config.round_lot_size
        current_config.min_trade_value = original_config.min_trade_value
        
        # Update display
        self._update_portfolio_display()
        self._update_status()
        self._update_last_modified()
    
    def _on_reset_global(self, button):
        """Reset global settings to defaults."""
        # Reset global settings
        self.global_settings = {
            'sector_weight_tolerance': 0.01,
            'country_weight_tolerance': 0.01,
            'security_weight_tolerance': 0.01,
            'optimization_date': date.today(),
            'reporting_currency': 'USD'
        }
        
        # Update widgets
        self.sector_tolerance.value = 1.0
        self.country_tolerance.value = 1.0
        self.security_tolerance.value = 1.0
        self.optimization_date.value = date.today()
        self.reporting_currency.value = 'USD'
        
        # Apply to all portfolios
        self._apply_global_tolerances()
        self._update_status()
        self._update_last_modified()
    
    def _on_preview_config(self, button):
        """Show preview of current configuration."""
        with self.output_area:
            clear_output()
            print("=== PORTFOLIO OPTIMIZATION CONFIGURATION PREVIEW ===\n")
            
            # Global settings
            print("GLOBAL SETTINGS:")
            print(f"  Sector Weight Tolerance: ±{self.global_settings['sector_weight_tolerance']*100:.2f}%")
            print(f"  Country Weight Tolerance: ±{self.global_settings['country_weight_tolerance']*100:.2f}%")
            print(f"  Security Weight Tolerance: ±{self.global_settings['security_weight_tolerance']*100:.2f}%")
            print(f"  Optimization Date: {self.global_settings['optimization_date']}")
            print(f"  Reporting Currency: {self.global_settings['reporting_currency']}")
            print()
            
            # Portfolio-specific settings
            print("PORTFOLIO-SPECIFIC SETTINGS:")
            for portfolio_id, config in self.config_manager.configs.items():
                print(f"\n{portfolio_id} (Benchmark: {config.benchmark}):")
                print(f"  Min Trade Size: {config.min_trade_size:,} shares")
                print(f"  Round Lot Size: {config.round_lot_size:,} shares")
                print(f"  Min Trade Value: ${config.min_trade_value:,}")
                
                # Show validation status
                status = self.validation_status.get(portfolio_id, {'valid': True, 'errors': []})
                if not status['valid']:
                    print(f"  VALIDATION ERRORS: {', '.join(status['errors'])}")
    
    def _on_export_config(self, button):
        """Export current configuration to JSON."""
        with self.output_area:
            clear_output()
            
            export_data = {
                'global_settings': self.global_settings.copy(),
                'portfolio_configs': {}
            }
            
            # Convert date to string for JSON serialization
            export_data['global_settings']['optimization_date'] = str(self.global_settings['optimization_date'])
            
            # Export portfolio configs
            for portfolio_id, config in self.config_manager.configs.items():
                export_data['portfolio_configs'][portfolio_id] = asdict(config)
            
            # Display JSON
            print("=== EXPORTED CONFIGURATION (Copy this JSON) ===\n")
            print(json.dumps(export_data, indent=2))
    
    def _on_import_config(self, button):
        """Import configuration from JSON (placeholder for file upload)."""
        with self.output_area:
            clear_output()
            print("=== IMPORT CONFIGURATION ===\n")
            print("To import a configuration:")
            print("1. Copy your JSON configuration")
            print("2. Create a new cell and run:")
            print("   config_ui.import_from_json(your_json_string)")
            print("\nExample:")
            print('config_ui.import_from_json(\'{"global_settings": {...}, "portfolio_configs": {...}}\')')
    
    def import_from_json(self, json_string: str):
        """Import configuration from JSON string."""
        try:
            data = json.loads(json_string)
            
            # Import global settings
            if 'global_settings' in data:
                self.global_settings.update(data['global_settings'])
                
                # Convert date string back to date object
                if 'optimization_date' in self.global_settings:
                    date_str = self.global_settings['optimization_date']
                    self.global_settings['optimization_date'] = datetime.strptime(date_str, '%Y-%m-%d').date()
                
                # Update global widgets
                self.sector_tolerance.value = self.global_settings['sector_weight_tolerance'] * 100
                self.country_tolerance.value = self.global_settings['country_weight_tolerance'] * 100
                self.security_tolerance.value = self.global_settings['security_weight_tolerance'] * 100
                self.optimization_date.value = self.global_settings['optimization_date']
                self.reporting_currency.value = self.global_settings['reporting_currency']
            
            # Import portfolio configs
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
            
            # Refresh display
            self._apply_global_tolerances()
            self._update_portfolio_display()
            self._update_status()
            self._update_last_modified()
            
            print("Configuration imported successfully!")
            
        except Exception as e:
            print(f"Import failed: {str(e)}")
    
    def get_config_manager(self) -> PortfolioConfigManager:
        """Get the updated configuration manager."""
        return self.config_manager
    
    def get_global_settings(self) -> Dict[str, Any]:
        """Get the current global settings."""
        return self.global_settings.copy()
    
    def display(self):
        """Display the UI."""
        display(self.main_layout)


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


if __name__ == "__main__":
    config_ui = create_portfolio_config_ui()