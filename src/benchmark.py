#!/usr/bin/env python3
import json
import os
import datetime
import sys

# Define difficulty buckets based on the puzzle size string.
SMALL_SIZES = {"2x2", "2x3", "2x4", "2x5", "2x6", "3x2", "3x3", "4x2"}
MEDIUM_SIZES = {"3x4", "3x5", "3x6", "4x3", "4x4", "5x2", "6x2"}
LARGE_SIZES = {"4x5", "5x3", "4x6", "5x4", "6x3"}
XLARGE_SIZES = {"5x5", "6x4", "5x6", "6x5", "6x6"}

def get_difficulty(size_str):
    """Return difficulty bucket as a string given a size string."""
    s = size_str.lower().strip()
    if s in SMALL_SIZES:
        return "Small"
    elif s in MEDIUM_SIZES:
        return "Medium"
    elif s in LARGE_SIZES:
        return "Large"
    elif s in XLARGE_SIZES:
        return "X-Large"
    else:
        return "Unknown"

def parse_timestamp(ts_str):
    """Parse a timestamp string in the format 'YYYY-MM-DD HH:MM:SS'."""
    try:
        return datetime.datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None

def aggregate_stats(log_entries):
    overall = {
        "solve": {"count": 0, "accuracy_sum": 0.0, "weighted_sum": 0.0, "total_fields": 0},
        "convert": {"count": 0, "accuracy_sum": 0.0, "weighted_sum": 0.0, "total_fields": 0},
        "constraints": {"count": 0, "accuracy_sum": 0.0, "weighted_sum": 0.0, "total_fields": 0},
        "by_difficulty": {}
    }
    
    timestamps = []
    
    for entry in log_entries:
        ts = parse_timestamp(entry.get("timestamp", ""))
        if ts:
            timestamps.append(ts)
        
        # Use the "puzzle_size" field already stored in the log
        puzzle_size = entry.get("puzzle_size", "Unknown")
        diff = get_difficulty(puzzle_size)
        if diff not in overall["by_difficulty"]:
            overall["by_difficulty"][diff] = {
                "solve": {"count": 0, "accuracy_sum": 0.0, "weighted_sum": 0.0, "total_fields": 0},
                "convert": {"count": 0, "accuracy_sum": 0.0, "weighted_sum": 0.0, "total_fields": 0},
                "constraints": {"count": 0, "accuracy_sum": 0.0, "weighted_sum": 0.0, "total_fields": 0}
            }
        
        # Process SOLVE data: using solve_accuracy, solve_correct_fields, solve_total_fields
        try:
            solve_total = float(entry.get("solve_total_fields", 0))
            solve_correct = float(entry.get("solve_correct_fields", 0))
            solve_acc = float(entry.get("solve_accuracy", 0))
            if solve_total > 0:
                overall["solve"]["count"] += 1
                overall["solve"]["accuracy_sum"] += 1 if solve_acc == 1 else 0
                overall["solve"]["weighted_sum"] += (solve_correct / solve_total)
                overall["solve"]["total_fields"] += solve_total

                overall["by_difficulty"][diff]["solve"]["count"] += 1
                overall["by_difficulty"][diff]["solve"]["accuracy_sum"] += 1 if solve_acc == 1 else 0
                overall["by_difficulty"][diff]["solve"]["weighted_sum"] += (solve_correct / solve_total)
                overall["by_difficulty"][diff]["solve"]["total_fields"] += solve_total
        except Exception:
            pass

        # Process CONVERT data: using convert_solver_accuracy, convert_correct_fields, convert_total_fields
        try:
            conv_total = float(entry.get("convert_total_fields", 0))
            conv_correct = float(entry.get("convert_correct_fields", 0))
            conv_acc = float(entry.get("convert_solver_accuracy", 0))
            if conv_total > 0:
                overall["convert"]["count"] += 1
                overall["convert"]["accuracy_sum"] += 1 if conv_acc == 1 else 0
                overall["convert"]["weighted_sum"] += (conv_correct / conv_total)
                overall["convert"]["total_fields"] += conv_total

                overall["by_difficulty"][diff]["convert"]["count"] += 1
                overall["by_difficulty"][diff]["convert"]["accuracy_sum"] += 1 if conv_acc == 1 else 0
                overall["by_difficulty"][diff]["convert"]["weighted_sum"] += (conv_correct / conv_total)
                overall["by_difficulty"][diff]["convert"]["total_fields"] += conv_total
        except Exception:
            pass

        # Process CONSTRAINTS data: using constraints_accuracy, constraints_correct_fields, constraints_total_fields
        try:
            constr_total = float(entry.get("constraints_total_fields", 0))
            constr_correct = float(entry.get("constraints_correct_fields", 0))
            constr_acc = float(entry.get("constraints_accuracy", 0))
            if constr_total > 0:
                overall["constraints"]["count"] += 1
                overall["constraints"]["accuracy_sum"] += 1 if constr_acc == 1 else 0
                overall["constraints"]["weighted_sum"] += (constr_correct / constr_total)
                overall["constraints"]["total_fields"] += constr_total

                overall["by_difficulty"][diff]["constraints"]["count"] += 1
                overall["by_difficulty"][diff]["constraints"]["accuracy_sum"] += 1 if constr_acc == 1 else 0
                overall["by_difficulty"][diff]["constraints"]["weighted_sum"] += (constr_correct / constr_total)
                overall["by_difficulty"][diff]["constraints"]["total_fields"] += constr_total
        except Exception:
            pass

    def compute_avg(stats):
        if stats["count"] > 0:
            return {
                "average_accuracy": stats["accuracy_sum"] / stats["count"],
                "weighted_accuracy": stats["weighted_sum"] / stats["count"],
                "total_fields": stats["total_fields"],
                "entries": stats["count"]
            }
        else:
            return {
                "average_accuracy": 0,
                "weighted_accuracy": 0,
                "total_fields": 0,
                "entries": 0
            }

    overall["solve"]["averages"] = compute_avg(overall["solve"])
    overall["convert"]["averages"] = compute_avg(overall["convert"])
    overall["constraints"]["averages"] = compute_avg(overall["constraints"])

    for diff in overall["by_difficulty"]:
        overall["by_difficulty"][diff]["solve"]["averages"] = compute_avg(overall["by_difficulty"][diff]["solve"])
        overall["by_difficulty"][diff]["convert"]["averages"] = compute_avg(overall["by_difficulty"][diff]["convert"])
        overall["by_difficulty"][diff]["constraints"]["averages"] = compute_avg(overall["by_difficulty"][diff]["constraints"])

    if timestamps:
        overall["time_range"] = {
            "earliest": min(timestamps).strftime("%Y-%m-%d %H:%M:%S"),
            "latest": max(timestamps).strftime("%Y-%m-%d %H:%M:%S")
        }
    else:
        overall["time_range"] = {"earliest": "N/A", "latest": "N/A"}

    return overall

if __name__ == "__main__":
    log_file = "results/log.json"
    if not os.path.exists(log_file):
        print("Log file not found.")
        sys.exit(1)
    with open(log_file, "r") as f:
        logs = json.load(f)
    
    stats = aggregate_stats(logs)
    # Write the aggregated statistics to a JSON file
    with open("benchmarks_stats.json", "w") as out_file:
        json.dump(stats, out_file, indent=4)
    print("Benchmark statistics have been written to benchmarks_stats.json")
