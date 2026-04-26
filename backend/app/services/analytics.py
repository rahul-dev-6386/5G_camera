"""Analytics service for occupancy trends and time-series aggregation."""

from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from ..config import get_settings
from ..db import get_database
from ..logger import get_logger


class AnalyticsService:
    """Service for occupancy analytics and time-series aggregation."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    async def get_occupancy_trend(
        self,
        classroom: str,
        course_code: str,
        hours: int = 24
    ) -> List[dict]:
        """Get occupancy trend over time for a classroom."""
        database = get_database()
        
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        # Query occupancy logs for the time period
        if hasattr(database, 'occupancy_logs'):
            # MongoDB
            cursor = database.occupancy_logs.find(
                {
                    "classroom": classroom,
                    "course_code": course_code.upper(),
                    "timestamp": {"$gte": start_time.isoformat()}
                },
                {"timestamp": 1, "count": 1, "_id": 0}
            ).sort("timestamp", 1)
            
            records = await cursor.to_list(length=None)
        else:
            # Local JSON
            cursor = database.occupancy_logs.find(
                {
                    "classroom": classroom,
                    "course_code": course_code.upper(),
                }
            )
            all_records = await cursor.to_list(length=None)
            records = [
                {"timestamp": r["timestamp"], "count": r["count"]}
                for r in all_records
                if datetime.fromisoformat(r["timestamp"]) >= start_time
            ]
            records.sort(key=lambda x: x["timestamp"])
        
        # Aggregate by hour
        hourly_data = defaultdict(list)
        for record in records:
            dt = datetime.fromisoformat(record["timestamp"])
            hour_key = dt.replace(minute=0, second=0, microsecond=0).isoformat()
            hourly_data[hour_key].append(record["count"])
        
        # Calculate hourly averages
        trend = []
        for hour in sorted(hourly_data.keys()):
            counts = hourly_data[hour]
            avg_count = sum(counts) / len(counts)
            max_count = max(counts)
            min_count = min(counts)
            
            trend.append({
                "timestamp": hour,
                "average_count": round(avg_count, 2),
                "max_count": max_count,
                "min_count": min_count,
                "sample_count": len(counts)
            })
        
        self.logger.info(f"Generated occupancy trend for {classroom} over {hours} hours")
        return trend
    
    async def get_peak_occupancy(
        self,
        classroom: str,
        course_code: str,
        days: int = 7
    ) -> dict:
        """Get peak occupancy statistics."""
        database = get_database()
        
        start_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        if hasattr(database, 'occupancy_logs'):
            cursor = database.occupancy_logs.find(
                {
                    "classroom": classroom,
                    "course_code": course_code.upper(),
                    "timestamp": {"$gte": start_time.isoformat()}
                },
                {"count": 1, "timestamp": 1, "_id": 0}
            )
            records = await cursor.to_list(length=None)
        else:
            cursor = database.occupancy_logs.find({
                "classroom": classroom,
                "course_code": course_code.upper(),
            })
            all_records = await cursor.to_list(length=None)
            records = [
                {"count": r["count"], "timestamp": r["timestamp"]}
                for r in all_records
                if datetime.fromisoformat(r["timestamp"]) >= start_time
            ]
        
        if not records:
            return {
                "peak_count": 0,
                "peak_time": None,
                "average_count": 0,
                "total_records": 0
            }
        
        counts = [r["count"] for r in records]
        peak_record = max(records, key=lambda x: x["count"])
        
        return {
            "peak_count": peak_record["count"],
            "peak_time": peak_record["timestamp"],
            "average_count": round(sum(counts) / len(counts), 2),
            "total_records": len(records)
        }
    
    async def get_classroom_comparison(
        self,
        classrooms: Optional[List[str]] = None,
        hours: int = 24
    ) -> List[dict]:
        """Compare occupancy across multiple classrooms."""
        database = get_database()
        
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        if not classrooms:
            # Get all unique classrooms
            if hasattr(database, 'occupancy_logs'):
                pipeline = [
                    {"$match": {"timestamp": {"$gte": start_time.isoformat()}}},
                    {"$group": {"_id": "$classroom", "avg_count": {"$avg": "$count"}}}
                ]
                results = await database.occupancy_logs.aggregate(pipeline).to_list(length=None)
                classrooms = [r["_id"] for r in results]
            else:
                # For local JSON, need to scan
                cursor = database.occupancy_logs.find({})
                all_records = await cursor.to_list(length=None)
                classrooms = list(set(r.get("classroom", "General") for r in all_records))
        
        comparison = []
        for classroom in classrooms:
            stats = await self.get_peak_occupancy(classroom, "GEN-101", days=1)
            comparison.append({
                "classroom": classroom,
                "peak_count": stats["peak_count"],
                "average_count": stats["average_count"],
                "total_records": stats["total_records"]
            })
        
        comparison.sort(key=lambda x: x["peak_count"], reverse=True)
        return comparison
    
    async def get_hourly_heatmap(
        self,
        classroom: str,
        course_code: str,
        days: int = 7
    ) -> dict:
        """Generate hourly occupancy heatmap data."""
        database = get_database()
        
        start_time = datetime.now(timezone.utc) - timedelta(days=days)
        
        if hasattr(database, 'occupancy_logs'):
            cursor = database.occupancy_logs.find(
                {
                    "classroom": classroom,
                    "course_code": course_code.upper(),
                    "timestamp": {"$gte": start_time.isoformat()}
                },
                {"count": 1, "timestamp": 1, "_id": 0}
            )
            records = await cursor.to_list(length=None)
        else:
            cursor = database.occupancy_logs.find({
                "classroom": classroom,
                "course_code": course_code.upper(),
            })
            all_records = await cursor.to_list(length=None)
            records = [
                {"count": r["count"], "timestamp": r["timestamp"]}
                for r in all_records
                if datetime.fromisoformat(r["timestamp"]) >= start_time
            ]
        
        # Aggregate by day of week and hour
        heatmap_data = defaultdict(lambda: defaultdict(list))
        
        for record in records:
            dt = datetime.fromisoformat(record["timestamp"])
            day_of_week = dt.strftime("%A")  # Monday, Tuesday, etc.
            hour = dt.hour
            heatmap_data[day_of_week][hour].append(record["count"])
        
        # Calculate averages for each day/hour cell
        heatmap = {}
        day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        for day in day_order:
            if day in heatmap_data:
                heatmap[day] = {}
                for hour in range(24):
                    if hour in heatmap_data[day] and heatmap_data[day][hour]:
                        avg = sum(heatmap_data[day][hour]) / len(heatmap_data[day][hour])
                        heatmap[day][hour] = round(avg, 2)
                    else:
                        heatmap[day][hour] = 0
        
        return heatmap


# Global analytics service instance
analytics_service = AnalyticsService()
