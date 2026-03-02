
import React, { useMemo } from "react";
import { Gantt, ViewMode } from "gantt-task-react";
import "gantt-task-react/dist/index.css";

const PHASE_COLORS = [
    { bg: "#3b82f6", selected: "#2563eb" },
    { bg: "#8b5cf6", selected: "#7c3aed" },
    { bg: "#10b981", selected: "#059669" },
    { bg: "#f59e0b", selected: "#d97706" },
    { bg: "#ef4444", selected: "#dc2626" },
    { bg: "#06b6d4", selected: "#0891b2" },
    { bg: "#ec4899", selected: "#db2777" },
    { bg: "#84cc16", selected: "#65a30d" },
];

const GanttChart = ({ activities }) => {
    const tasks = useMemo(() => {
        if (!activities || !Array.isArray(activities) || activities.length === 0) {
            return [];
        }

        // Assign colors by phase
        const phaseColorMap = {};
        let colorIdx = 0;
        activities.forEach((act) => {
            const phase = act["Phase"] || "Execution";
            if (!phaseColorMap[phase]) {
                phaseColorMap[phase] = PHASE_COLORS[colorIdx % PHASE_COLORS.length];
                colorIdx++;
            }
        });

        return activities.map((act, index) => {
            const startDate = new Date(act["Start Date"]);
            const endDate = new Date(act["End Date"]);

            if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
                return null;
            }

            const phase = act["Phase"] || "Execution";
            const colors = phaseColorMap[phase];

            return {
                start: startDate,
                end: endDate,
                name: act["Activities"] || `Activity ${index + 1}`,
                id: `Task-${index}`,
                type: "task",
                progress: 0,
                isDisabled: true,
                styles: {
                    progressColor: colors.bg,
                    progressSelectedColor: colors.selected,
                    backgroundColor: colors.bg,
                    backgroundSelectedColor: colors.selected,
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
        <div className="w-full bg-white dark:bg-gray-800 rounded-lg shadow-sm p-4">
            <div className="mb-4 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-200">Project Timeline</h3>
            </div>
            <div style={{ overflowX: "auto", paddingBottom: "40px", paddingRight: "300px" }}>
                <Gantt
                    tasks={tasks}
                    viewMode={ViewMode.Month}
                    listCellWidth=""
                    columnWidth={60}
                    headerHeight={50}
                    rowHeight={60}
                    barFill={60}
                    barCornerRadius={4}
                />
            </div>
        </div>
    );
};

export default GanttChart;
