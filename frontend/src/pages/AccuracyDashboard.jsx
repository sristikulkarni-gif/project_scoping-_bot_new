import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './AccuracyDashboard.css';

const AccuracyDashboard = () => {
    const [metrics, setMetrics] = useState(null);
    const [projects, setProjects] = useState([]);
    const [trends, setTrends] = useState([]);
    const [loading, setLoading] = useState(true);
    const [filters, setFilters] = useState({
        startDate: '',
        endDate: '',
        complexity: '',
        domain: ''
    });

    useEffect(() => {
        fetchAccuracyData();
    }, [filters]);

    const fetchAccuracyData = async () => {
        try {
            setLoading(true);
            const token = localStorage.getItem('token');

            // Check if token exists
            if (!token) {
                console.error('No authentication token found');
                window.location.href = '/login';
                return;
            }

            const headers = { Authorization: `Bearer ${token}` };

            // Build query params
            const params = new URLSearchParams();
            if (filters.startDate) params.append('start_date', filters.startDate);
            if (filters.endDate) params.append('end_date', filters.endDate);
            if (filters.complexity) params.append('complexity', filters.complexity);
            if (filters.domain) params.append('domain', filters.domain);

            // Fetch all data
            const [metricsRes, projectsRes, trendsRes] = await Promise.all([
                axios.get(`/api/accuracy/metrics?${params}`, { headers }),
                axios.get(`/api/accuracy/projects?${params}`, { headers }),
                axios.get('/api/accuracy/trends?months=6', { headers })
            ]);

            setMetrics(metricsRes.data.metrics);
            setProjects(projectsRes.data.projects);
            setTrends(trendsRes.data.trends);
        } catch (error) {
            console.error('Failed to fetch accuracy data:', error);

            // If 401 Unauthorized, redirect to login
            if (error.response && error.response.status === 401) {
                console.error('Authentication failed - redirecting to login');
                localStorage.removeItem('token');
                window.location.href = '/login';
            }
        } finally {
            setLoading(false);
        }
    };

    const handleFilterChange = (field, value) => {
        setFilters(prev => ({ ...prev, [field]: value }));
    };

    if (loading) {
        return (
            <div className="accuracy-dashboard">
                <div className="loading">Loading accuracy metrics...</div>
            </div>
        );
    }

    return (
        <div className="accuracy-dashboard">
            <div className="dashboard-header">
                <h1>📊 Accuracy Dashboard</h1>
                <p>Monitor application performance and estimation accuracy</p>
            </div>

            {/* Filters */}
            <div className="filters-section">
                <div className="filter-group">
                    <label>Start Date:</label>
                    <input
                        type="date"
                        value={filters.startDate}
                        onChange={(e) => handleFilterChange('startDate', e.target.value)}
                    />
                </div>
                <div className="filter-group">
                    <label>End Date:</label>
                    <input
                        type="date"
                        value={filters.endDate}
                        onChange={(e) => handleFilterChange('endDate', e.target.value)}
                    />
                </div>
                <div className="filter-group">
                    <label>Complexity:</label>
                    <select
                        value={filters.complexity}
                        onChange={(e) => handleFilterChange('complexity', e.target.value)}
                    >
                        <option value="">All</option>
                        <option value="Simple">Simple</option>
                        <option value="Medium">Medium</option>
                        <option value="High">High</option>
                    </select>
                </div>
                <div className="filter-group">
                    <label>Domain:</label>
                    <input
                        type="text"
                        placeholder="e.g., Healthcare"
                        value={filters.domain}
                        onChange={(e) => handleFilterChange('domain', e.target.value)}
                    />
                </div>
            </div>

            {/* Summary Cards */}
            <div className="metrics-grid">
                <div className="metric-card overall">
                    <div className="metric-icon">🎯</div>
                    <div className="metric-content">
                        <h3>Overall Accuracy</h3>
                        <div className="metric-value">{metrics?.overall_accuracy?.toFixed(1)}%</div>
                        <div className="metric-subtitle">Across all projects</div>
                    </div>
                </div>

                <div className="metric-card duration">
                    <div className="metric-icon">⏱️</div>
                    <div className="metric-content">
                        <h3>Duration Accuracy</h3>
                        <div className="metric-value">{metrics?.duration_accuracy?.toFixed(1)}%</div>
                        <div className="metric-subtitle">Avg. variance: {metrics?.average_duration_variance?.toFixed(1)}%</div>
                    </div>
                </div>

                <div className="metric-card cost">
                    <div className="metric-icon">💰</div>
                    <div className="metric-content">
                        <h3>Cost Accuracy</h3>
                        <div className="metric-value">{metrics?.cost_accuracy?.toFixed(1)}%</div>
                        <div className="metric-subtitle">Avg. variance: {metrics?.average_cost_variance?.toFixed(1)}%</div>
                    </div>
                </div>

                <div className="metric-card completion">
                    <div className="metric-icon">✅</div>
                    <div className="metric-content">
                        <h3>Completion Rate</h3>
                        <div className="metric-value">{metrics?.completion_rate?.toFixed(1)}%</div>
                        <div className="metric-subtitle">{metrics?.total_projects_analyzed} projects analyzed</div>
                    </div>
                </div>
            </div>

            {/* Trends Chart */}
            <div className="chart-section">
                <h2>Accuracy Trends (Last 6 Months)</h2>
                <div className="trends-chart">
                    {trends.map((trend, index) => (
                        <div key={index} className="trend-bar">
                            <div className="trend-label">{trend.month}</div>
                            <div className="trend-bars-container">
                                <div
                                    className="trend-bar-fill overall"
                                    style={{ height: `${trend.overall_accuracy}%` }}
                                    title={`Overall: ${trend.overall_accuracy.toFixed(1)}%`}
                                />
                                <div
                                    className="trend-bar-fill duration"
                                    style={{ height: `${trend.duration_accuracy}%` }}
                                    title={`Duration: ${trend.duration_accuracy.toFixed(1)}%`}
                                />
                                <div
                                    className="trend-bar-fill cost"
                                    style={{ height: `${trend.cost_accuracy}%` }}
                                    title={`Cost: ${trend.cost_accuracy.toFixed(1)}%`}
                                />
                            </div>
                            <div className="trend-count">{trend.projects_count} projects</div>
                        </div>
                    ))}
                </div>
                <div className="chart-legend">
                    <span className="legend-item overall">Overall</span>
                    <span className="legend-item duration">Duration</span>
                    <span className="legend-item cost">Cost</span>
                </div>
            </div>

            {/* Projects Table */}
            <div className="projects-section">
                <h2>Project Accuracy Breakdown</h2>
                <div className="projects-table-container">
                    <table className="projects-table">
                        <thead>
                            <tr>
                                <th>Project Name</th>
                                <th>Domain</th>
                                <th>Complexity</th>
                                <th>Est. Duration</th>
                                <th title="Calendar duration from project start to end dates">Actual Duration</th>
                                <th title="Total person-months (sum of all activity durations)">Total Effort</th>
                                <th>Est. Cost</th>
                                <th>Actual Cost</th>
                                <th>Duration Accuracy</th>
                                <th>Cost Accuracy</th>
                                <th>Completion Rate</th>
                            </tr>
                        </thead>
                        <tbody>
                            {projects.map((project) => (
                                <tr key={project.id}>
                                    <td className="project-name">{project.name}</td>
                                    <td>{project.domain || 'N/A'}</td>
                                    <td>
                                        <span className={`complexity-badge ${project.complexity?.toLowerCase()}`}>
                                            {project.complexity || 'N/A'}
                                        </span>
                                    </td>
                                    <td>{project.estimated_duration || 'N/A'}</td>
                                    <td>{project.actual_duration}</td>
                                    <td><span style={{ color: '#6366f1', fontWeight: '500' }}>{project.total_effort || 'N/A'}</span></td>
                                    <td>{project.estimated_cost || 'N/A'}</td>
                                    <td>{project.actual_cost || 'N/A'}</td>
                                    <td>
                                        <div className="accuracy-cell">
                                            <div className="accuracy-bar">
                                                <div
                                                    className="accuracy-fill duration"
                                                    style={{ width: `${project.duration_accuracy}%` }}
                                                />
                                            </div>
                                            <span>{project.duration_accuracy.toFixed(1)}%</span>
                                        </div>
                                    </td>
                                    <td>
                                        <div className="accuracy-cell">
                                            <div className="accuracy-bar">
                                                <div
                                                    className="accuracy-fill cost"
                                                    style={{ width: `${project.cost_accuracy}%` }}
                                                />
                                            </div>
                                            <span>{project.cost_accuracy.toFixed(1)}%</span>
                                        </div>
                                    </td>
                                    <td>
                                        <div className="accuracy-cell">
                                            <div className="accuracy-bar">
                                                <div
                                                    className="accuracy-fill completion"
                                                    style={{ width: `${project.completion_rate}%` }}
                                                />
                                            </div>
                                            <span>{project.completion_rate.toFixed(1)}%</span>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default AccuracyDashboard;
