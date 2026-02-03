import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import projectApi from "../api/projectApi";
import { RefreshCw, Download, File, Archive, X, Save } from "lucide-react";

export default function ProjectDetails() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(false);
  const [finalizedScope, setFinalizedScope] = useState(null);
  const [scopeLoading, setScopeLoading] = useState(false);

  // Closeout State
  const [showCloseModal, setShowCloseModal] = useState(false);
  const [actuals, setActuals] = useState({});
  const [closing, setClosing] = useState(false);
  const [isImageModalOpen, setIsImageModalOpen] = useState(false);

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

  const handleOpenCloseout = () => {
    if (!finalizedScope?.activities) {
      alert("Cannot close project without finalized activities.");
      return;
    }
    // Initialize actuals from estimates
    const initialActuals = {};
    finalizedScope.activities.forEach(act => {
      initialActuals[act.ID] = {
        name: act['Activities'],
        estimated_duration: act['Effort Months'] + ' months',
        actual_duration: act['Effort Months'], // Default to estimate
        notes: ''
      };
    });
    setActuals(initialActuals);
    setShowCloseModal(true);
  };

  const submitCloseout = async () => {
    try {
      setClosing(true);
      const payload = {
        activities: Object.values(actuals).map(a => ({
          name: a.name,
          estimated_duration: a.estimated_duration,
          actual_duration: a.actual_duration + ' months',
          notes: a.notes
        }))
      };

      await projectApi.closeProject(id, payload);
      setShowCloseModal(false);
      alert("Project Closed Successfully! Actuals have been learned.");
      // Optionally refresh project status
    } catch (err) {
      console.error("Failed to close project", err);
      alert("Failed to close project. See console.");
    } finally {
      setClosing(false);
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
          <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">
            {project.name}
          </h1>
          <button
            onClick={regenerateScope}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg shadow hover:bg-secondary transition disabled:opacity-50"
          >
            <RefreshCw className={`w-5 h-5 ${loading ? "animate-spin" : ""}`} />
            {loading ? "Regenerating..." : "Regenerate Scope"}
          </button>

          <button
            onClick={handleOpenCloseout}
            className="flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg shadow hover:bg-emerald-700 transition ml-2"
          >
            <Archive className="w-5 h-5" />
            Close Project
          </button>
        </div>

        <div className="grid md:grid-cols-2 gap-4 text-gray-700 dark:text-gray-300">
          <p><strong>Domain:</strong> {project.domain || "-"}</p>
          <p><strong>Complexity:</strong> {project.complexity || "-"}</p>
          <p><strong>Tech Stack:</strong> {project.tech_stack || "-"}</p>
          <p><strong>Use Cases:</strong> {project.use_cases || "-"}</p>
          <p><strong>Compliance:</strong> {project.compliance || "-"}</p>
          <p><strong>Duration:</strong> {project.duration || "-"}</p>
        </div>
      </div>

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
      {scopeLoading ? (
        <div className="bg-white dark:bg-dark-surface p-6 rounded-xl shadow-md border border-gray-200 dark:border-dark-muted">
          <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-gray-100">
            Architecture Diagram
          </h2>
          <p className="text-gray-500 dark:text-gray-400">Loading...</p>
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
      ) : null}

      {/* Project Summary */}
      {scopeLoading ? (
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
      ) : null}

      {/* Lightbox Modal for Architecture Diagram */}
      {isImageModalOpen && finalizedScope?.architecture_diagram && (
        <div
          className="fixed inset-0 bg-black/90 z-[60] flex items-center justify-center p-4 backdrop-blur-sm animate-in fade-in duration-200"
          onClick={() => setIsImageModalOpen(false)}
        >
          <div className="relative max-w-[95vw] max-h-[95vh] w-full h-full flex items-center justify-center">
            <button
              onClick={() => setIsImageModalOpen(false)}
              className="absolute top-4 right-4 bg-black/50 hover:bg-black/70 text-white rounded-full p-2 transition z-50 border border-white/20"
            >
              <X className="w-6 h-6" />
            </button>
            <img
              src={`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/blobs/download/${finalizedScope.architecture_diagram?.replace('.png', '.svg')}?base=projects`}
              alt="Architecture Diagram Full Size"
              className="max-w-full max-h-full object-contain rounded-md shadow-2xl"
              onClick={(e) => e.stopPropagation()} // Prevent click from closing modal
              onError={(e) => {
                const currentSrc = e.target.src;
                if (currentSrc.includes('.svg')) {
                  e.target.src = currentSrc.replace('.svg', '.png');
                }
              }}
            />
          </div>
        </div>
      )}

      {/* Closeout Modal */}
      {showCloseModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white dark:bg-dark-card w-full max-w-3xl rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center bg-gray-50 dark:bg-gray-800">
              <h3 className="text-xl font-bold text-gray-800 dark:text-gray-100 flex items-center gap-2">
                <Archive className="w-5 h-5 text-emerald-600" />
                Project Closeout & Learning
              </h3>
              <button onClick={() => setShowCloseModal(false)} className="text-gray-500 hover:text-red-500">
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto flex-1">
              <p className="mb-4 text-sm text-gray-600 dark:text-gray-300 bg-blue-50 dark:bg-blue-900/20 p-3 rounded-lg border border-blue-100 dark:border-blue-800">
                ℹ️ <strong>Continuous Learning:</strong> Please enter the <em>Actual</em> duration for each activity.
                The AI will learn from this to improve future estimates for similar projects.
              </p>

              <table className="w-full text-sm text-left">
                <thead className="text-xs text-gray-700 uppercase bg-gray-100 dark:bg-gray-700 dark:text-gray-300">
                  <tr>
                    <th className="px-4 py-3">Activity</th>
                    <th className="px-4 py-3">Est. Months</th>
                    <th className="px-4 py-3 w-32">Actual Months</th>
                    <th className="px-4 py-3">Notes (Why different?)</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.keys(actuals).map(key => (
                    <tr key={key} className="bg-white border-b dark:bg-gray-800 dark:border-gray-700">
                      <td className="px-4 py-2 font-medium">{actuals[key].name}</td>
                      <td className="px-4 py-2 text-gray-500">{actuals[key].estimated_duration}</td>
                      <td className="px-4 py-2">
                        <input
                          type="number"
                          step="0.1"
                          className="w-full p-1 border rounded"
                          value={actuals[key].actual_duration}
                          onChange={(e) => setActuals({
                            ...actuals,
                            [key]: { ...actuals[key], actual_duration: e.target.value }
                          })}
                        />
                      </td>
                      <td className="px-4 py-2">
                        <input
                          type="text"
                          className="w-full p-1 border rounded"
                          placeholder="Slow API, bugs..."
                          value={actuals[key].notes}
                          onChange={(e) => setActuals({
                            ...actuals,
                            [key]: { ...actuals[key], notes: e.target.value }
                          })}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 flex justify-end gap-3">
              <button
                onClick={() => setShowCloseModal(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 font-medium"
              >
                Cancel
              </button>
              <button
                onClick={submitCloseout}
                disabled={closing}
                className="px-6 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 font-medium flex items-center gap-2 disabled:opacity-50"
              >
                {closing ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                Save & Learn
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}