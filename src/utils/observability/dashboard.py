"""
Dashboard generation for observability metrics.
Creates HTML dashboards with execution traces, agent statistics, and performance metrics.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict

from .trace_logger import TraceLogger, ExecutionTrace


def generate_dashboard(
    output_file: Path,
    trace_logger: TraceLogger,
    lookback_hours: int = 24
) -> Path:
    """
    Generate HTML dashboard with observability metrics.
    
    Args:
        output_file: Path to output HTML file
        trace_logger: TraceLogger instance
        lookback_hours: Hours of history to include
        
    Returns:
        Path to generated dashboard
    """
    # Load recent traces
    traces = _load_recent_traces(trace_logger, lookback_hours)
    
    # Calculate metrics
    metrics = _calculate_metrics(traces)
    
    # Generate HTML
    html = _generate_html(metrics, traces)
    
    # Save dashboard
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_file


def export_metrics_summary(
    output_file: Path,
    trace_logger: TraceLogger,
    lookback_hours: int = 24
) -> Path:
    """
    Export metrics summary to JSON file.
    
    Args:
        output_file: Path to output JSON file
        trace_logger: TraceLogger instance
        lookback_hours: Hours of history to include
        
    Returns:
        Path to exported file
    """
    traces = _load_recent_traces(trace_logger, lookback_hours)
    metrics = _calculate_metrics(traces)
    
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    return output_file


def _load_recent_traces(
    trace_logger: TraceLogger,
    lookback_hours: int
) -> List[ExecutionTrace]:
    """Load traces from recent time period"""
    cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
    traces = []
    
    # Search trace files
    for trace_file in trace_logger.output_dir.rglob("*.json"):
        try:
            with open(trace_file, 'r') as f:
                data = json.load(f)
            
            # Check if within time window
            start_time = datetime.fromisoformat(data["start_time_iso"])
            if start_time >= cutoff_time:
                # Reconstruct minimal trace
                trace = ExecutionTrace(
                    trace_id=data["trace_id"],
                    workflow_name=data["workflow_name"],
                    start_time=data["start_time"],
                    end_time=data.get("end_time"),
                    status=data.get("status", "unknown")
                )
                # Load events for statistics
                from .trace_logger import TraceEvent, TraceEventType, TraceLevel
                for event_data in data.get("events", []):
                    event = TraceEvent(
                        event_id=event_data["event_id"],
                        event_type=TraceEventType(event_data["event_type"]),
                        timestamp=event_data["timestamp"],
                        level=TraceLevel(event_data["level"]),
                        agent_name=event_data.get("agent_name"),
                        tool_name=event_data.get("tool_name"),
                        metadata=event_data.get("metadata", {}),
                        duration=event_data.get("duration")
                    )
                    trace.events.append(event)
                
                traces.append(trace)
        except Exception:
            continue
    
    return sorted(traces, key=lambda t: t.start_time, reverse=True)


def _calculate_metrics(traces: List[ExecutionTrace]) -> Dict[str, Any]:
    """Calculate aggregate metrics from traces"""
    if not traces:
        return {
            "summary": {
                "total_workflows": 0,
                "completed": 0,
                "failed": 0,
                "running": 0,
                "avg_duration": 0,
                "total_events": 0
            },
            "agents": {},
            "tools": {},
            "timeline": []
        }
    
    metrics = {
        "summary": {
            "total_workflows": len(traces),
            "completed": sum(1 for t in traces if t.status == "completed"),
            "failed": sum(1 for t in traces if t.status == "failed"),
            "running": sum(1 for t in traces if t.status == "running"),
            "avg_duration": 0,
            "total_events": sum(len(t.events) for t in traces)
        },
        "agents": defaultdict(lambda: {"invocations": 0, "responses": 0, "tool_calls": 0}),
        "tools": defaultdict(lambda: {"calls": 0, "successes": 0, "failures": 0, "avg_duration": 0, "durations": []}),
        "timeline": []
    }
    
    # Calculate durations
    completed_traces = [t for t in traces if t.duration is not None]
    if completed_traces:
        metrics["summary"]["avg_duration"] = sum(t.duration for t in completed_traces) / len(completed_traces)
    
    # Aggregate agent and tool statistics
    for trace in traces:
        # Timeline entry
        metrics["timeline"].append({
            "trace_id": trace.trace_id,
            "start_time": datetime.fromtimestamp(trace.start_time).isoformat(),
            "duration": trace.duration,
            "status": trace.status,
            "event_count": len(trace.events)
        })
        
        # Get trace statistics
        trace_logger = TraceLogger()
        stats = trace_logger.get_agent_statistics(trace)
        
        # Aggregate agent stats
        for agent_name, agent_stats in stats.get("agents", {}).items():
            for key, value in agent_stats.items():
                metrics["agents"][agent_name][key] += value
        
        # Aggregate tool stats
        for tool_name, tool_stats in stats.get("tools", {}).items():
            for key, value in tool_stats.items():
                metrics["tools"][tool_name][key] += value
    
    # Calculate tool average durations
    for tool_name, tool_stats in metrics["tools"].items():
        if tool_stats["durations"]:
            tool_stats["avg_duration"] = sum(tool_stats["durations"]) / len(tool_stats["durations"])
        del tool_stats["durations"]  # Remove raw durations from output
    
    # Convert defaultdicts to regular dicts
    metrics["agents"] = dict(metrics["agents"])
    metrics["tools"] = dict(metrics["tools"])
    
    return metrics


def _generate_html(metrics: Dict[str, Any], traces: List[ExecutionTrace]) -> str:
    """Generate HTML dashboard"""
    
    # Summary section
    summary = metrics["summary"]
    success_rate = (summary["completed"] / summary["total_workflows"] * 100) if summary["total_workflows"] > 0 else 0
    
    # Agent section
    agent_rows = ""
    for agent_name, stats in sorted(metrics["agents"].items()):
        agent_rows += f"""
        <tr>
            <td>{agent_name}</td>
            <td>{stats['invocations']}</td>
            <td>{stats['responses']}</td>
            <td>{stats['tool_calls']}</td>
        </tr>
        """
    
    # Tool section
    tool_rows = ""
    for tool_name, stats in sorted(metrics["tools"].items()):
        success_rate_tool = (stats['successes'] / stats['calls'] * 100) if stats['calls'] > 0 else 0
        tool_rows += f"""
        <tr>
            <td>{tool_name}</td>
            <td>{stats['calls']}</td>
            <td>{stats['successes']}</td>
            <td>{stats['failures']}</td>
            <td>{success_rate_tool:.1f}%</td>
        </tr>
        """
    
    # Timeline section
    timeline_rows = ""
    for entry in metrics["timeline"][:20]:  # Show last 20
        duration_str = f"{entry['duration']:.2f}s" if entry['duration'] else "N/A"
        status_color = {"completed": "#28a745", "failed": "#dc3545", "running": "#ffc107"}.get(entry['status'], "#6c757d")
        timeline_rows += f"""
        <tr>
            <td><code>{entry['trace_id'][:16]}...</code></td>
            <td>{entry['start_time']}</td>
            <td>{duration_str}</td>
            <td><span style="color: {status_color};">●</span> {entry['status']}</td>
            <td>{entry['event_count']}</td>
        </tr>
        """
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Red Teaming - Observability Dashboard</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: #f5f5f5;
            color: #333;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            font-size: 28px;
            margin-bottom: 10px;
        }}
        .header p {{
            opacity: 0.9;
            font-size: 14px;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            font-size: 18px;
            margin-bottom: 20px;
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        .metric {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        .metric-label {{
            font-size: 14px;
            color: #666;
        }}
        .metric-value {{
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }}
        .metric-value.success {{
            color: #28a745;
        }}
        .metric-value.danger {{
            color: #dc3545;
        }}
        .metric-value.warning {{
            color: #ffc107;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #667eea;
            font-size: 14px;
        }}
        td {{
            font-size: 14px;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }}
        .badge-success {{
            background: #d4edda;
            color: #155724;
        }}
        .badge-danger {{
            background: #f8d7da;
            color: #721c24;
        }}
        .timestamp {{
            color: #999;
            font-size: 12px;
        }}
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: monospace;
            font-size: 13px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🛡️ AI Red Teaming - Observability Dashboard</h1>
        <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | Multi-Agent System Performance Monitoring</p>
    </div>
    
    <div class="grid">
        <div class="card">
            <h2>📊 Workflow Summary</h2>
            <div class="metric">
                <span class="metric-label">Total Workflows</span>
                <span class="metric-value">{summary['total_workflows']}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Completed</span>
                <span class="metric-value success">{summary['completed']}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Failed</span>
                <span class="metric-value danger">{summary['failed']}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Success Rate</span>
                <span class="metric-value {'success' if success_rate >= 80 else 'warning'}">{success_rate:.1f}%</span>
            </div>
        </div>
        
        <div class="card">
            <h2>⏱️ Performance</h2>
            <div class="metric">
                <span class="metric-label">Avg Duration</span>
                <span class="metric-value">{summary['avg_duration']:.2f}s</span>
            </div>
            <div class="metric">
                <span class="metric-label">Total Events</span>
                <span class="metric-value">{summary['total_events']}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Agents Active</span>
                <span class="metric-value">{len(metrics['agents'])}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Tools Used</span>
                <span class="metric-value">{len(metrics['tools'])}</span>
            </div>
        </div>
    </div>
    
    <div class="card" style="margin-bottom: 20px;">
        <h2>🤖 Agent Activity</h2>
        <table>
            <thead>
                <tr>
                    <th>Agent Name</th>
                    <th>Invocations</th>
                    <th>Responses</th>
                    <th>Tool Calls</th>
                </tr>
            </thead>
            <tbody>
                {agent_rows if agent_rows else '<tr><td colspan="4">No agent activity</td></tr>'}
            </tbody>
        </table>
    </div>
    
    <div class="card" style="margin-bottom: 20px;">
        <h2>🔧 Tool Usage</h2>
        <table>
            <thead>
                <tr>
                    <th>Tool Name</th>
                    <th>Calls</th>
                    <th>Successes</th>
                    <th>Failures</th>
                    <th>Success Rate</th>
                </tr>
            </thead>
            <tbody>
                {tool_rows if tool_rows else '<tr><td colspan="5">No tool usage</td></tr>'}
            </tbody>
        </table>
    </div>
    
    <div class="card">
        <h2>📈 Recent Executions</h2>
        <table>
            <thead>
                <tr>
                    <th>Trace ID</th>
                    <th>Start Time</th>
                    <th>Duration</th>
                    <th>Status</th>
                    <th>Events</th>
                </tr>
            </thead>
            <tbody>
                {timeline_rows if timeline_rows else '<tr><td colspan="5">No recent executions</td></tr>'}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
    
    return html
