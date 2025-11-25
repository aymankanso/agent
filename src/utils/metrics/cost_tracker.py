"""
Cost tracking utility for monitoring LLM API usage and costs.

This module provides real-time tracking of:
- Token usage (input/output tokens per call)
- API costs based on actual model pricing
- Latency measurements
- Per-task metrics aggregation

Usage:
    from src.utils.metrics import get_cost_tracker
    
    tracker = get_cost_tracker()
    tracker.start_task("recon_scan")
    tracker.log_llm_call("gpt-4o-mini", input_tokens=150, output_tokens=300)
    metrics = tracker.end_task("recon_scan")
"""

import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json
import csv
from pathlib import Path


@dataclass
class LLMCall:
    """Records a single LLM API call."""
    timestamp: float
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    latency: Optional[float] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TaskMetrics:
    """Aggregated metrics for a single task."""
    task_id: str
    start_time: float
    end_time: Optional[float] = None
    llm_calls: List[LLMCall] = field(default_factory=list)
    
    @property
    def duration(self) -> Optional[float]:
        """Task duration in seconds."""
        if self.end_time is None:
            return None
        return self.end_time - self.start_time
    
    @property
    def total_input_tokens(self) -> int:
        """Total input tokens across all LLM calls."""
        return sum(call.input_tokens for call in self.llm_calls)
    
    @property
    def total_output_tokens(self) -> int:
        """Total output tokens across all LLM calls."""
        return sum(call.output_tokens for call in self.llm_calls)
    
    @property
    def total_tokens(self) -> int:
        """Total tokens (input + output) across all LLM calls."""
        return self.total_input_tokens + self.total_output_tokens
    
    @property
    def total_cost(self) -> float:
        """Total cost in USD across all LLM calls."""
        return sum(call.cost for call in self.llm_calls)
    
    @property
    def avg_latency(self) -> Optional[float]:
        """Average latency across all LLM calls with latency data."""
        calls_with_latency = [call for call in self.llm_calls if call.latency is not None]
        if not calls_with_latency:
            return None
        return sum(call.latency for call in calls_with_latency) / len(calls_with_latency)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "task_id": self.task_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "avg_latency": self.avg_latency,
            "num_llm_calls": len(self.llm_calls),
            "llm_calls": [call.to_dict() for call in self.llm_calls]
        }


class CostTracker:
    """
    Tracks LLM API usage and costs across multiple tasks.
    
    Model Pricing (as of November 2025):
    - GPT-4o: $2.50 / 1M input tokens, $10.00 / 1M output tokens
    - GPT-4o-mini: $0.150 / 1M input tokens, $0.600 / 1M output tokens
    - GPT-3.5-turbo: $0.50 / 1M input tokens, $1.50 / 1M output tokens
    """
    
    # Model pricing in USD per 1M tokens
    MODEL_PRICING = {
        "gpt-4o": {"input": 2.50, "output": 10.00},
        "gpt-4o-mini": {"input": 0.150, "output": 0.600},
        "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        "gpt-4": {"input": 30.00, "output": 60.00},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    }
    
    def __init__(self, output_dir: Optional[Path] = None):
        """
        Initialize cost tracker.
        
        Args:
            output_dir: Directory to save cost reports (default: logs/metrics)
        """
        self.tasks: Dict[str, TaskMetrics] = {}
        self.current_task_id: Optional[str] = None
        
        if output_dir is None:
            output_dir = Path("logs/metrics")
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def start_task(self, task_id: str) -> None:
        """
        Start tracking a new task.
        
        Args:
            task_id: Unique identifier for the task
        """
        self.current_task_id = task_id
        self.tasks[task_id] = TaskMetrics(
            task_id=task_id,
            start_time=time.time()
        )
    
    def end_task(self, task_id: str) -> TaskMetrics:
        """
        End tracking for a task and return its metrics.
        
        Args:
            task_id: Unique identifier for the task
            
        Returns:
            TaskMetrics object with aggregated metrics
            
        Raises:
            KeyError: If task_id not found
        """
        if task_id not in self.tasks:
            raise KeyError(f"Task '{task_id}' not found. Did you call start_task()?")
        
        self.tasks[task_id].end_time = time.time()
        
        if self.current_task_id == task_id:
            self.current_task_id = None
        
        return self.tasks[task_id]
    
    def log_llm_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency: Optional[float] = None,
        task_id: Optional[str] = None
    ) -> float:
        """
        Log an LLM API call and calculate its cost.
        
        Args:
            model: Model name (e.g., "gpt-4o-mini")
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            latency: Call latency in seconds (optional)
            task_id: Task to associate with (uses current_task_id if None)
            
        Returns:
            Cost of this call in USD
            
        Raises:
            ValueError: If no active task and task_id not provided
        """
        # Determine which task to log to
        target_task_id = task_id or self.current_task_id
        if target_task_id is None:
            raise ValueError(
                "No active task. Call start_task() first or provide task_id parameter."
            )
        
        if target_task_id not in self.tasks:
            raise KeyError(f"Task '{target_task_id}' not found.")
        
        # Calculate cost
        cost = self._calculate_cost(model, input_tokens, output_tokens)
        
        # Create call record
        call = LLMCall(
            timestamp=time.time(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            latency=latency
        )
        
        # Add to task
        self.tasks[target_task_id].llm_calls.append(call)
        
        return cost
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        Calculate cost for an LLM call.
        
        Args:
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            
        Returns:
            Cost in USD
        """
        # Normalize model name (handle variants)
        model_key = model.lower()
        for key in self.MODEL_PRICING.keys():
            if key in model_key:
                model_key = key
                break
        
        if model_key not in self.MODEL_PRICING:
            # Unknown model - use conservative estimate (GPT-4o pricing)
            pricing = self.MODEL_PRICING["gpt-4o"]
        else:
            pricing = self.MODEL_PRICING[model_key]
        
        # Calculate cost (pricing is per 1M tokens)
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        
        return input_cost + output_cost
    
    def get_total_cost(self) -> float:
        """Get total cost across all tracked tasks."""
        return sum(task.total_cost for task in self.tasks.values())
    
    def get_total_tokens(self) -> int:
        """Get total tokens across all tracked tasks."""
        return sum(task.total_tokens for task in self.tasks.values())
    
    def get_task_metrics(self, task_id: str) -> Optional[TaskMetrics]:
        """Get metrics for a specific task."""
        return self.tasks.get(task_id)
    
    def export_to_csv(self, filename: Optional[str] = None) -> Path:
        """
        Export task metrics to CSV file.
        
        Args:
            filename: Output filename (default: cost_report_TIMESTAMP.csv)
            
        Returns:
            Path to the created CSV file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cost_report_{timestamp}.csv"
        
        output_path = self.output_dir / filename
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                "Task ID",
                "Duration (s)",
                "Total Tokens",
                "Input Tokens",
                "Output Tokens",
                "Total Cost (USD)",
                "Avg Latency (s)",
                "Num LLM Calls"
            ])
            
            # Data rows
            for task in self.tasks.values():
                writer.writerow([
                    task.task_id,
                    f"{task.duration:.2f}" if task.duration else "N/A",
                    task.total_tokens,
                    task.total_input_tokens,
                    task.total_output_tokens,
                    f"{task.total_cost:.4f}",
                    f"{task.avg_latency:.2f}" if task.avg_latency else "N/A",
                    len(task.llm_calls)
                ])
            
            # Summary row
            writer.writerow([])
            writer.writerow([
                "TOTAL",
                "",
                self.get_total_tokens(),
                sum(t.total_input_tokens for t in self.tasks.values()),
                sum(t.total_output_tokens for t in self.tasks.values()),
                f"{self.get_total_cost():.4f}",
                "",
                sum(len(t.llm_calls) for t in self.tasks.values())
            ])
        
        return output_path
    
    def export_to_json(self, filename: Optional[str] = None) -> Path:
        """
        Export detailed metrics to JSON file.
        
        Args:
            filename: Output filename (default: cost_report_TIMESTAMP.json)
            
        Returns:
            Path to the created JSON file
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cost_report_{timestamp}.json"
        
        output_path = self.output_dir / filename
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_cost_usd": self.get_total_cost(),
                "total_tokens": self.get_total_tokens(),
                "total_tasks": len(self.tasks),
                "total_llm_calls": sum(len(t.llm_calls) for t in self.tasks.values())
            },
            "tasks": [task.to_dict() for task in self.tasks.values()]
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        return output_path
    
    def print_summary(self) -> None:
        """Print a summary of tracked metrics to console."""
        print("\n" + "="*60)
        print("COST TRACKING SUMMARY")
        print("="*60)
        print(f"Total Tasks: {len(self.tasks)}")
        print(f"Total LLM Calls: {sum(len(t.llm_calls) for t in self.tasks.values())}")
        print(f"Total Tokens: {self.get_total_tokens():,}")
        print(f"Total Cost: ${self.get_total_cost():.4f} USD")
        print("="*60)
        
        if self.tasks:
            print("\nPer-Task Breakdown:")
            print("-"*60)
            for task in self.tasks.values():
                print(f"\nTask: {task.task_id}")
                print(f"  Duration: {task.duration:.2f}s" if task.duration else "  Duration: N/A")
                print(f"  Tokens: {task.total_tokens:,} ({task.total_input_tokens:,} in / {task.total_output_tokens:,} out)")
                print(f"  Cost: ${task.total_cost:.4f}")
                print(f"  LLM Calls: {len(task.llm_calls)}")
                if task.avg_latency:
                    print(f"  Avg Latency: {task.avg_latency:.2f}s")
        
        print("\n" + "="*60 + "\n")


# Global instance for convenience
_global_tracker: Optional[CostTracker] = None


def get_cost_tracker(output_dir: Optional[Path] = None) -> CostTracker:
    """
    Get the global cost tracker instance (singleton pattern).
    
    Args:
        output_dir: Directory to save cost reports (only used on first call)
        
    Returns:
        Global CostTracker instance
    """
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = CostTracker(output_dir=output_dir)
    return _global_tracker
