
import React, { useMemo } from "react";
import { Gantt, ViewMode } from "gantt-task-react";
import "gantt-task-react/dist/index.css";

const GanttChart = ({ activities }) => {
    const tasks = useMemo(() => {
        if (!activities || !Array.isArray(activities) || activities.length === 0) {
            return [];
        }

        return activities.map((act, index) => {
            const startDate = new Date(act["Start Date"]);
            const endDate = new Date(act["End Date"]);

            // Ensure valid dates
            if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
                return null;
            }

            return {
                start: startDate,
                end: endDate,
                name: act["Activities"] || `Activity ${index + 1}`,
                id: `Task-${index}`,
                type: "task",
                progress: 0,
                isDisabled: true,
                styles: {
                    progressColor: "#10b981", // Emerald 500
                    progressSelectedColor: "#059669",
                    backgroundColor: "#34d399", // Emerald 400
                    backgroundSelectedColor: "#10b981",
                }
            };
        }).filter(t => t !== null);
    }, [activities]);

    if (tasks.length === 0) {
        return (
            <div className="flex items-center justify-center p-12 text-gray-400 border-2 border-dashed border-gray-200 rounded-lg">
                <p>No valid activity dates found for Gantt Chart.</p>
            </div>
        );
    }

    return (
        <div className="w-full bg-white dark:bg-gray-800 rounded-lg shadow-sm overflow-hidden p-4">
            <div className="mb-4 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200">Project Timeline</h3>
            </div>
            <div className="overflow-x-auto">
                <Gantt
                    tasks={tasks}
                    viewMode={ViewMode.Month} // Default to month view for better high-level overview
                    listCellWidth="" // Hide the list column to save space if needed, or keep default
                    columnWidth={60}
                    headerHeight={50}
                    barFill={60}
                    barCornerRadius={4}
                    barBackgroundColor="#34d399"
                />
            </div>
        </div>
    );
};

export default GanttChart;
