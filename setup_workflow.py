"""
Complete setup script for Portfolio Optimization & Crossing Workflow.
This script initializes all components and provides authentication helpers.
"""

from portfolio_configs import PortfolioConfigManager, PORTFOLIO_CONFIGS
from ReportHandler import ReportHandler
from request_builder import PortfolioOptimizerRequestBuilder
from orchestrator import OptimizationOrchestrator
from crossing_engine import PortfolioCrossingEngine, CrossingEngineConfig
from combined_workflow_ui import create_comprehensive_workflow_ui
from auth_helper import auth_helper

# Authentication configuration
AUTH_CONFIG_PATH = 'config/port_v2_config.json'

def setup_workflow_components():
    """
    Initialize all workflow components.
    
    Returns:
        tuple: (report_handler, config_manager, builder, orchestrator, crossing_engine)
    """
    print("Initializing workflow components...")
    
    # Setup report handler
    report_handler = ReportHandler(AUTH_CONFIG_PATH)
    
    # Setup config manager
    config_manager = PortfolioConfigManager(PORTFOLIO_CONFIGS)
    
    # Setup request builder
    builder = PortfolioOptimizerRequestBuilder(
        template_path='config/portfolio_optimization_template.yml',
        config_manager=config_manager
    )
    
    # Inject portfolio restrictions
    PORTFOLIO_RESTRICTIONS = {
        "S-17147": None,
        "P-93050": ['EQ0010054600001000', 'EQ0000000026033823'],
        "P-61230": None,
        "P-47227": None,
        "P-36182": None
    }
    config_manager.inject_restrictions(PORTFOLIO_RESTRICTIONS)
    
    # Initialize orchestrator
    orchestrator = OptimizationOrchestrator(
        report_handler,
        config_manager,
        builder
    )
    
    # Initialize crossing engine
    priority_list = ["S17147", "P36182", "P47227", "P93050", "P-61230"]
    crossing_config = CrossingEngineConfig(portfolio_priority=priority_list)
    crossing_engine = PortfolioCrossingEngine(crossing_config)
    
    print("All workflow components initialized successfully!")
    
    return report_handler, config_manager, builder, orchestrator, crossing_engine

def check_authentication_status():
    """Check if Bloomberg API authentication is available."""
    from config.api_config import is_authenticated
    
    if is_authenticated():
        print("✅ Bloomberg API authentication is active")
        return True
    else:
        print("❌ Bloomberg API authentication required")
        return False

def start_authentication_flow():
    """Start the Bloomberg API authentication process."""
    print("Starting Bloomberg API authentication...")
    print("Follow the instructions below:")
    print("-" * 50)
    
    # Use the auth helper to start authentication
    return auth_helper.trigger_authentication_flow()

def complete_authentication():
    """Complete the Bloomberg API authentication process."""
    print("Completing Bloomberg API authentication...")
    return auth_helper.complete_authentication()

def test_api_connection():
    """Test the Bloomberg API connection."""
    print("Testing Bloomberg API connection...")
    return auth_helper.test_api_connection()

def create_workflow_ui(authenticated=False):
    """
    Create and display the comprehensive workflow UI.
    
    Args:
        authenticated: If True, assumes authentication is complete
    
    Returns:
        ComprehensiveWorkflowUI instance
    """
    if not authenticated and not check_authentication_status():
        print("⚠️  Warning: Authentication not verified. Some features may not work.")
        print("   Run authenticate_and_setup() to complete authentication first.")
    
    # Setup all components
    report_handler, config_manager, builder, orchestrator, crossing_engine = setup_workflow_components()
    
    # Create and display the UI
    print("Creating comprehensive workflow UI...")
    workflow_ui = create_comprehensive_workflow_ui(
        config_manager=config_manager,
        report_handler=report_handler,
        orchestrator=orchestrator,
        crossing_engine=crossing_engine
    )
    
    return workflow_ui

def authenticate_and_setup():
    """
    Complete authentication flow and setup workflow.
    
    Returns:
        ComprehensiveWorkflowUI instance if successful, None if authentication failed
    """
    print("=" * 60)
    print("BLOOMBERG API AUTHENTICATION & WORKFLOW SETUP")
    print("=" * 60)
    
    # Check if already authenticated
    if check_authentication_status():
        print("Already authenticated! Proceeding to workflow setup...")
        return create_workflow_ui(authenticated=True)
    
    # Start authentication
    print("\n1. Starting authentication flow...")
    if not start_authentication_flow():
        print("❌ Failed to start authentication")
        return None
    
    # Wait for user to complete authentication
    print("\n2. Waiting for authentication completion...")
    input("Press Enter after you've approved the application in your browser...")
    
    # Complete authentication
    print("\n3. Completing authentication...")
    if not complete_authentication():
        print("❌ Authentication failed")
        return None
    
    # Test connection
    print("\n4. Testing API connection...")
    if not test_api_connection():
        print("❌ Connection test failed")
        return None
    
    # Setup workflow
    print("\n5. Setting up workflow components...")
    workflow_ui = create_workflow_ui(authenticated=True)
    
    print("\n" + "=" * 60)
    print("🚀 SETUP COMPLETE! Your workflow is ready to use.")
    print("=" * 60)
    
    return workflow_ui

def quick_setup():
    """
    Quick setup assuming authentication is already complete.
    
    Returns:
        ComprehensiveWorkflowUI instance
    """
    print("Quick setup - assuming authentication is complete...")
    return create_workflow_ui(authenticated=True)

# Example usage functions
def example_setup():
    """Example of how to set up the complete workflow."""
    
    print("Example: Complete Workflow Setup")
    print("-" * 40)
    
    # Option 1: Full authentication and setup
    print("Option 1: Full authentication and setup")
    print("workflow_ui = authenticate_and_setup()")
    
    print("\nOption 2: Quick setup (if already authenticated)")
    print("workflow_ui = quick_setup()")
    
    print("\nOption 3: Manual step-by-step")
    print("# 1. Start authentication")
    print("start_authentication_flow()")
    print("# 2. Complete after approval")
    print("complete_authentication()")
    print("# 3. Create UI")
    print("workflow_ui = create_workflow_ui()")
    
    print("\nOption 4: Just check status")
    print("check_authentication_status()")

if __name__ == "__main__":
    # Run example when script is executed directly
    example_setup()