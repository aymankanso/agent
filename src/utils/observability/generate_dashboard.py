"""
Generate observability dashboard from execution traces.

Usage:
    python -m src.utils.observability.generate_dashboard
"""

from pathlib import Path
from src.utils.observability import get_trace_logger, generate_dashboard, export_metrics_summary


def main():
    """Generate dashboard and export metrics"""
    print("🔍 Generating Observability Dashboard...")
    
    # Get trace logger
    trace_logger = get_trace_logger()
    
    # Generate HTML dashboard
    dashboard_path = Path("logs/dashboard.html")
    generate_dashboard(dashboard_path, trace_logger, lookback_hours=24)
    print(f"✅ Dashboard generated: {dashboard_path.absolute()}")
    
    # Export metrics summary
    metrics_path = Path("logs/metrics_summary.json")
    export_metrics_summary(metrics_path, trace_logger, lookback_hours=24)
    print(f"✅ Metrics exported: {metrics_path.absolute()}")
    
    print("\n📊 Open the dashboard in your browser:")
    print(f"   file:///{dashboard_path.absolute()}")


if __name__ == "__main__":
    main()
