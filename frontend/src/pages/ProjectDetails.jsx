import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import projectApi from "../api/projectApi";
import { RefreshCw, Download, File, Archive, X, Save, Plus, Minus } from "lucide-react";
import ReactFlowDiagram from "../components/ReactFlowDiagram";
import ScopePreviewTabs from "../components/ScopePreviewTabs";
import ConfidenceGauge from "../components/ConfidenceGauge";

/**
 * Modal to view Architecture Diagram with Zoom/Pan controls
 */
const DiagramModal = ({ src, onClose }) => {
  const [zoom, setZoom] = useState(1);

  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.25, 3));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.25, 0.5));
  const handleResetZoom = () => setZoom(1);

  return (
    <div
      className="fixed inset-0 bg-black/90 z-[60] flex items-center justify-center p-4 backdrop-blur-sm animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div className="relative max-w-[95vw] max-h-[95vh] w-full h-full flex items-center justify-center flex-col">
        {/* Controls Toolbar */}
        <div className="absolute top-4 right-4 z-50 flex gap-2" onClick={(e) => e.stopPropagation()}>
          <div className="flex bg-white/10 backdrop-blur-md rounded-lg shadow-lg border border-white/20 overflow-hidden">
            <button onClick={handleZoomOut} className="px-3 py-2 hover:bg-white/10 text-white transition" title="Zoom Out">
              <Minus className="w-4 h-4" />
            </button>
            <span className="px-2 py-2 text-sm font-medium border-x border-white/20 text-white flex items-center min-w-[3rem] justify-center">
              {Math.round(zoom * 100)}%
            </span>
            <button onClick={handleZoomIn} className="px-3 py-2 hover:bg-white/10 text-white transition" title="Zoom In">
              <Plus className="w-4 h-4" />
            </button>
          </div>

          <button
            onClick={handleResetZoom}
            className="bg-white/10 hover:bg-white/20 text-white backdrop-blur-md rounded-lg shadow-lg px-3 py-2 text-sm font-medium border border-white/20 transition"
          >
            Reset
          </button>

          <a
            href={src}
            download
            target="_blank"
            rel="noopener noreferrer"
            className="bg-primary/90 hover:bg-primary text-white backdrop-blur-md rounded-lg shadow-lg px-3 py-2 border border-white/20 flex items-center justify-center transition"
            title="Download Diagram"
          >
            <Download className="w-5 h-5" />
          </a>

          <button
            onClick={onClose}
            className="bg-black/50 hover:bg-red-500/80 text-white backdrop-blur-md rounded-lg shadow-lg px-3 py-2 border border-white/20 flex items-center justify-center transition ml-2"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Image Container with Scroll/Pan */}
        <div
          className="flex-1 w-full overflow-auto flex items-center justify-center cursor-grab active:cursor-grabbing p-4 rounded-lg"
          onClick={(e) => e.stopPropagation()}
        >
          <img
            src={src}
            alt="Architecture Diagram Full Size"
            style={{
              transform: `scale(${zoom})`,
              transformOrigin: 'center center',
              transition: 'transform 0.2s ease-out'
            }}
            className="max-w-none object-contain shadow-2xl rounded-md bg-white dark:bg-gray-800"
            draggable={false}
            onError={(e) => {
              const currentSrc = e.target.src;
              if (currentSrc.includes('.svg')) {
                e.target.src = currentSrc.replace('.svg', '.png');
              }
            }}
          />
        </div>
      </div>
    </div>
  );
};

/**
 * Modal to close project and input actuals
 */
const CloseoutModal = ({ isOpen, onClose, project, initialResources, onReset }) => {
  const [actuals, setActuals] = useState([]);
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    if (isOpen && initialResources) {
      console.log("Initial Resources for Closeout:", initialResources);
      // Initialize actuals from the finalized resourcing plan
      // Group by Role to avoid duplicates if same role appears multiple times?
      // Usually resourcing plan has unique roles.
      const initialData = initialResources.map(r => ({
        resource_name: r.Resources || r.Role || r.role_name || r.role || "Unknown",
        rate_per_month: parseFloat(r["Rate/month"] || r.Rate || r.monthly_rate || r.rate || 0),
        estimated_effort_months: parseFloat(r.Efforts || r["Effort Months"] || r.estimated_effort || r.effort_months || 0),
        actual_effort_months: parseFloat(r.Efforts || r["Effort Months"] || r.estimated_effort || r.effort_months || 0),
        estimated_cost: parseFloat(r.Cost || r.estimated_cost || r.cost || 0),
        actual_cost: parseFloat(r.Cost || r.estimated_cost || r.cost || 0),
        notes: ""
      }));
      setActuals(initialData);
    }
  }, [isOpen, initialResources]);

  const handleChange = (index, field, value) => {
    const newActuals = [...actuals];
    newActuals[index][field] = value;

    // Auto-calculate cost if effort changes
    if (field === "actual_effort_months") {
      const effort = parseFloat(value) || 0;
      const rate = newActuals[index].rate_per_month;
      newActuals[index].actual_cost = effort * rate;
    }

    setActuals(newActuals);
  };

  const handleSubmit = async () => {
    try {
      setSubmitting(true);
      const payload = { actuals };
      const res = await projectApi.closeProject(project.id, payload);

      // Close modal
      onClose();

      // Navigate to exports with new scope
      if (res.data?.scope) {
        navigate(`/exports/${project.id}`, { state: { draftScope: res.data.scope } });
      } else {
        // Just refresh
        onReset();
      }

    } catch (err) {
      console.error("Failed to close project:", err);
      alert("Failed to close project. See console for details.");
    } finally {
      setSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4 backdrop-blur-sm">
      <div className="bg-white dark:bg-dark-surface w-full max-w-4xl rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center bg-gray-50 dark:bg-gray-800">
          <div>
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100">Close Project & Log Actuals</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400">Enter actual effort values to regenerate the scope with real data.</p>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full transition">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="flex-1 overflow-auto p-6">
          <table className="min-w-full text-sm text-left">
            <thead className="text-xs text-gray-700 uppercase bg-gray-100 dark:bg-gray-700 dark:text-gray-200">
              <tr>
                <th className="px-4 py-3 rounded-tl-lg">Resource / Role</th>
                <th className="px-4 py-3">Rate / Mo</th>
                <th className="px-4 py-3">Est. Effort</th>
                <th className="px-4 py-3 bg-blue-50 dark:bg-blue-900/20 border-b-2 border-blue-500">ACTUAL Effort (Months)</th>
                <th className="px-4 py-3">Est. Cost</th>
                <th className="px-4 py-3 font-semibold">ACTUAL Cost</th>
                <th className="px-4 py-3 rounded-tr-lg">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {actuals.map((item, idx) => (
                <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-800 transition">
                  <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">
                    {item.resource_name}
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    ${item.rate_per_month.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {item.estimated_effort_months} m
                  </td>
                  <td className="px-4 py-3 bg-blue-50 dark:bg-blue-900/10">
                    <input
                      type="number"
                      step="0.1"
                      min="0"
                      value={item.actual_effort_months}
                      onChange={(e) => handleChange(idx, "actual_effort_months", e.target.value)}
                      className="w-full px-2 py-1 rounded border border-blue-300 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white font-bold text-blue-700 dark:text-blue-300"
                    />
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    ${item.estimated_cost.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 font-bold text-gray-800 dark:text-gray-200">
                    ${item.actual_cost.toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <input
                      type="text"
                      placeholder="Optional notes..."
                      value={item.notes}
                      onChange={(e) => handleChange(idx, "notes", e.target.value)}
                      className="w-full px-2 py-1 text-xs rounded border border-gray-300 focus:ring-1 focus:ring-blue-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {actuals.length === 0 && (
            <div className="text-center py-10 text-gray-500">
              <p>No resources found in the finalized scope.</p>
              <p className="text-xs mt-2">Generate a scope first to track actuals.</p>
            </div>
          )}
        </div>

        <div className="p-6 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 flex justify-end gap-3 rounded-b-xl">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:ring-4 focus:ring-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:border-gray-600 dark:hover:bg-gray-700"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting || actuals.length === 0}
            className="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700 focus:ring-4 focus:ring-blue-300 disabled:opacity-50 flex items-center gap-2 shadow-lg shadow-blue-500/30"
          >
            {submitting ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Closing...
              </>
            ) : (
              <>
                <Archive className="w-4 h-4" />
                Confirm Closeout
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default function ProjectDetails() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(false);
  const [finalizedScope, setFinalizedScope] = useState(null);
  const [scopeLoading, setScopeLoading] = useState(false);
  const [isImageModalOpen, setIsImageModalOpen] = useState(false);
  const [isCloseoutModalOpen, setIsCloseoutModalOpen] = useState(false);

  useEffect(() => {
    const loadProject = async () => {
      try {
        const res = await projectApi.getProject(id);
        setProject(res.data);
      } catch (err) {
        console.error("Failed to fetch project:", err);
      }
    };

    loadProject();
  }, [id]);

  // Load finalized scope to display architecture and summary
  useEffect(() => {
    const loadFinalizedScope = async () => {
      try {
        setScopeLoading(true);
        const res = await projectApi.getFinalizedScope(id);
        if (res.data && Object.keys(res.data).length > 0) {
          setFinalizedScope(res.data);
        }
      } catch (err) {
        console.error("Failed to fetch finalized scope:", err);
        // It's okay if there's no finalized scope yet
      } finally {
        setScopeLoading(false);
      }
    };

    if (id) {
      loadFinalizedScope();
    }
  }, [id]);

  const regenerateScope = async () => {
    try {
      setLoading(true);
      const res = await projectApi.generateScope(id);
      navigate(`/exports/${id}`, { state: { draftScope: res.data } });
    } catch (err) {
      console.error("Failed to regenerate scope:", err);
    } finally {
      setLoading(false);
    }
  };


  if (!project)
    return (
      <p className="text-gray-500 dark:text-gray-400 text-center mt-10">
        Loading project...
      </p>
    );

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Project Header */}
      <div className="bg-white dark:bg-dark-surface p-6 rounded-xl shadow-md border border-gray-200 dark:border-dark-muted">
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100 flex items-center gap-2">
            {project.name}
            {project.status === "closed" && (
              <span className="text-sm px-3 py-1 bg-gray-500 text-white rounded-full">
                Closed
              </span>
            )}
          </h1>

          <div className="flex gap-3">
            {project.status !== "closed" && finalizedScope && (
              <button
                onClick={() => setIsCloseoutModalOpen(true)}
                className="flex items-center gap-2 px-4 py-2 bg-white text-gray-700 border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 transition"
                title="Close Project & Log Actuals"
              >
                <Archive className="w-4 h-4" />
                Close Project
              </button>
            )}

            <button
              onClick={regenerateScope}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg shadow hover:bg-secondary transition disabled:opacity-50"
            >
              <RefreshCw className={`w-5 h-5 ${loading ? "animate-spin" : ""}`} />
              {loading ? "Regenerating..." : "Regenerate Scope"}
            </button>
          </div>

        </div>

        <div className="grid md:grid-cols-2 gap-4 text-gray-700 dark:text-gray-300">
          <p><strong>Domain:</strong> {project.domain || "-"}</p>
          <p><strong>Complexity:</strong> {project.complexity || "-"}</p>
          <p><strong>Tech Stack:</strong> {project.tech_stack || "-"}</p>
          <p><strong>Use Cases:</strong> {project.use_cases || "-"}</p>
          <p><strong>Compliance:</strong> {project.compliance || "-"}</p>
          <p><strong>Duration:</strong> {finalizedScope?.overview?.Duration || project.duration || "-"}</p>
          {project.status === "closed" && project.actual_total_cost > 0 && (
            <p className="font-bold text-green-600">
              <strong>Actual Cost:</strong> ${project.actual_total_cost.toLocaleString()}
            </p>
          )}
        </div>
      </div>

      {finalizedScope?._warnings && finalizedScope._warnings.length > 0 && (
        <div className="flex flex-col gap-2 p-4 bg-orange-50 border border-orange-200 text-orange-800 rounded-xl shadow-md mt-4">
          <div className="flex items-center gap-2 font-semibold text-orange-900">
            <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            Industry Benchmark Warnings
          </div>
          <ul className="list-disc list-inside space-y-1 ml-1 text-sm">
            {finalizedScope._warnings.map((warning, idx) => (
              <li key={idx}>{warning}</li>
            ))}
          </ul>
        </div>
      )}

      <ConfidenceGauge
        score={finalizedScope?.confidence_score}
        reasons={finalizedScope?.confidence_reasons || []}
      />

      {/* Uploaded Files */}
      <div className="bg-white dark:bg-dark-surface p-6 rounded-xl shadow-md border border-gray-200 dark:border-dark-muted">
        <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-100">
          Uploaded Documents
        </h2>
        {project.files && project.files.length > 0 ? (
          <ul className="divide-y divide-gray-200 dark:divide-gray-700">
            {project.files.map((file) => (
              <li
                key={file.id}
                className="flex justify-between items-center py-3 hover:bg-gray-50 dark:hover:bg-dark-background rounded-lg px-2 transition"
              >
                <div className="flex items-center gap-2">
                  <File className="w-5 h-5 text-gray-500 dark:text-gray-400" />
                  <span className="font-medium text-gray-800 dark:text-gray-200">
                    {file.file_name}
                  </span>
                  {file.file_type && (
                    <span className="text-sm text-gray-500 dark:text-gray-400">
                      ({file.file_type})
                    </span>
                  )}
                </div>
                <a
                  href={projectApi.getDownloadUrl(file.file_path, "projects")}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1 text-primary hover:underline text-sm"
                >
                  <Download className="w-4 h-4" />
                  Download
                </a>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-gray-500 dark:text-gray-400">No documents uploaded.</p>
        )}
      </div>

      {/* Architecture Diagram */}
      {
        scopeLoading ? (
          <div className="bg-white dark:bg-dark-surface p-6 rounded-xl shadow-md border border-gray-200 dark:border-dark-muted">
            <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-100">
              Architecture Diagram
            </h2>
            <p className="text-gray-500 dark:text-gray-400">Loading...</p>
          </div>
        ) : typeof finalizedScope?.architecture_diagram === 'object' && finalizedScope.architecture_diagram.nodes ? (
          <div className="bg-white dark:bg-dark-surface p-6 rounded-xl shadow-md border border-gray-200 dark:border-dark-muted">
            <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-100">
              Architecture Diagram
            </h2>
            <div className="h-[600px] w-full mt-4">
              <ReactFlowDiagram data={finalizedScope.architecture_diagram} />
            </div>
          </div>
        ) : finalizedScope?.architecture_diagram ? (
          <div className="bg-white dark:bg-dark-surface p-6 rounded-xl shadow-md border border-gray-200 dark:border-dark-muted">
            <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-100">
              Architecture Diagram
            </h2>
            <div className="flex flex-col items-center justify-center p-4">
              <div
                className="relative group cursor-zoom-in w-full flex justify-center bg-gray-50 dark:bg-gray-800 rounded-lg shadow-lg border border-gray-300 dark:border-gray-600 p-2 overflow-auto"
                onClick={() => setIsImageModalOpen(true)}
              >
                <img
                  src={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/blobs/download/${finalizedScope.architecture_diagram?.replace('.png', '.svg')}?base=projects`}
                  alt="Architecture Diagram"
                  className="max-w-full max-h-[600px] w-auto h-auto object-contain transition-transform duration-300 group-hover:scale-[1.01]"
                  onError={(e) => {
                    const currentSrc = e.target.src;
                    if (currentSrc.includes('.svg')) {
                      // If SVG fails, try PNG (fallback)
                      e.target.src = currentSrc.replace('.svg', '.png');
                    } else {
                      // If both fail, show placeholder
                      e.target.onerror = null;
                      e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300"><rect width="400" height="300" fill="%23f3f4f6"/><text x="50%" y="50%" text-anchor="middle" fill="%236b7280" font-family="Arial" font-size="16">Image not available</text></svg>';
                    }
                  }}
                />
                <div className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <span className="bg-black/75 text-white text-xs px-2 py-1 rounded shadow-sm">Click to expand</span>
                </div>
              </div>
            </div>
          </div>
        ) : null
      }

      {/* Project Summary */}
      {
        scopeLoading ? (
          <div className="bg-white dark:bg-dark-surface p-6 rounded-xl shadow-md border border-gray-200 dark:border-dark-muted">
            <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-100">
              Project Summary
            </h2>
            <p className="text-gray-500 dark:text-gray-400">Loading...</p>
          </div>
        ) : finalizedScope?.project_summary ? (
          <div className="bg-white dark:bg-dark-surface p-6 rounded-xl shadow-md border border-gray-200 dark:border-dark-muted">
            <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-100">
              Project Summary
            </h2>
            <div className="space-y-4">
              {/* Executive Summary */}
              {finalizedScope.project_summary.executive_summary && (
                <div>
                  <h3 className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">
                    Executive Summary
                  </h3>
                  <p className="text-gray-600 dark:text-gray-400">
                    {finalizedScope.project_summary.executive_summary}
                  </p>
                </div>
              )}

              {/* Key Deliverables */}
              {finalizedScope.project_summary.key_deliverables &&
                Array.isArray(finalizedScope.project_summary.key_deliverables) &&
                finalizedScope.project_summary.key_deliverables.length > 0 && (
                  <div>
                    <h3 className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Key Deliverables
                    </h3>
                    <ul className="list-disc list-inside space-y-1 ml-4">
                      {finalizedScope.project_summary.key_deliverables.map((item, idx) => (
                        <li key={idx} className="text-gray-600 dark:text-gray-400">
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

              {/* Success Criteria */}
              {finalizedScope.project_summary.success_criteria &&
                Array.isArray(finalizedScope.project_summary.success_criteria) &&
                finalizedScope.project_summary.success_criteria.length > 0 && (
                  <div>
                    <h3 className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Success Criteria
                    </h3>
                    <ul className="list-disc list-inside space-y-1 ml-4">
                      {finalizedScope.project_summary.success_criteria.map((item, idx) => (
                        <li key={idx} className="text-gray-600 dark:text-gray-400">
                          {item}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

              {/* Risks and Mitigation */}
              {finalizedScope.project_summary.risks_and_mitigation &&
                Array.isArray(finalizedScope.project_summary.risks_and_mitigation) &&
                finalizedScope.project_summary.risks_and_mitigation.length > 0 && (
                  <div>
                    <h3 className="text-lg font-medium text-gray-700 dark:text-gray-300 mb-2">
                      Risks and Mitigation Strategies
                    </h3>
                    <div className="overflow-x-auto">
                      <table className="min-w-full border border-gray-300 dark:border-gray-600">
                        <thead className="bg-gray-100 dark:bg-gray-700">
                          <tr>
                            <th className="px-4 py-2 text-left text-sm font-semibold text-gray-700 dark:text-gray-200 border-b border-gray-300 dark:border-gray-600">
                              Risk
                            </th>
                            <th className="px-4 py-2 text-left text-sm font-semibold text-gray-700 dark:text-gray-200 border-b border-gray-300 dark:border-gray-600">
                              Mitigation Strategy
                            </th>
                          </tr>
                        </thead>
                        <tbody>
                          {finalizedScope.project_summary.risks_and_mitigation.map((risk, idx) => (
                            <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                              <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
                                {risk.risk || '-'}
                              </td>
                              <td className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
                                {risk.mitigation || '-'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}
            </div>
          </div>
        ) : null
      }

      {/* Lightbox Modal for Architecture Diagram */}
      {
        isImageModalOpen && finalizedScope?.architecture_diagram && (
          <DiagramModal
            src={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/blobs/download/${finalizedScope.architecture_diagram?.replace('.png', '.svg')}?base=projects`}
            onClose={() => setIsImageModalOpen(false)}
          />
        )
      }

      {/* Closeout Modal */}
      <CloseoutModal
        isOpen={isCloseoutModalOpen}
        onClose={() => setIsCloseoutModalOpen(false)}
        project={project}
        initialResources={finalizedScope?.resourcing_plan}
        onReset={() => {
          // Reload project to update status
          setLoading(true); // temporary reuse
          window.location.reload();
        }}
      />

    </div >
  );
}