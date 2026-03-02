import { useEffect, useState } from "react";
import { useETL } from "../contexts/ETLContext";

import * as presentonApi from "../api/presentonApi";
import projectApi from "../api/projectApi";
import {
  RefreshCcw,
  CheckCircle,
  XCircle,
  Clock,
  FileText,
  Database,
  AlertCircle,
  TrendingUp,
  Play,
  BookOpen,
  ExternalLink,
  Presentation,
} from "lucide-react";

export default function ETLDashboard() {
  const {
    pendingUpdates,
    processingJobs,
    kbDocuments,
    pendingCaseStudies,
    stats,
    loading,
    error,
    triggerScan,
    getScanStatus,
    loadPendingUpdates,
    approvePendingUpdate,
    rejectPendingUpdate,
    loadProcessingJobs,
    loadKBDocuments,
    loadPendingCaseStudies,
    approveCaseStudy,
    rejectCaseStudy,
    loadStats,
    resetFailedDocuments,
  } = useETL();

  const [activeTab, setActiveTab] = useState("stats");
  const [scanLoading, setScanLoading] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);
  const [processingId, setProcessingId] = useState(null);
  const [adminComment, setAdminComment] = useState("");
  const [selectedPending, setSelectedPending] = useState(null);

  // Presenton state
  const [presentonStatus, setPresentonStatus] = useState("checking");
  const [showProjectSelector, setShowProjectSelector] = useState(false);
  const [projects, setProjects] = useState([]);
  const [loadingProjects, setLoadingProjects] = useState(false);
  const [generatingPresenton, setGeneratingPresenton] = useState(false);
  const [lastGeneratedPresentation, setLastGeneratedPresentation] = useState(null);



  useEffect(() => {
    // Initial load
    loadStats();
    loadPendingUpdates();
    loadProcessingJobs();
    loadProcessingJobs();
    loadKBDocuments();
    loadPendingCaseStudies();

    // Check Presenton health
    checkPresentonHealth();

    // Check if scan was running when page loaded
    initializeScanState();

    // Cleanup on unmount
    return () => {
      if (window.etlPollingInterval) {
        clearInterval(window.etlPollingInterval);
      }
    };
  }, [loadStats, loadPendingUpdates, loadProcessingJobs, loadKBDocuments, loadPendingCaseStudies]);

  // Initialize scan state on mount (check if scan is running)
  const initializeScanState = async () => {
    const scanStartTime = localStorage.getItem('etl_scan_started');

    if (scanStartTime) {
      // Scan was triggered before, check if still running
      setScanLoading(true);

      const stillProcessing = await checkIfStillProcessing();

      if (stillProcessing) {
        console.log('✅ ETL scan is still running, resuming polling...');
        startStatusPolling();
      } else {
        console.log('✅ ETL scan completed while away');
        cleanupScanState();
        // Refresh all data
        loadStats();
        loadProcessingJobs();
        loadKBDocuments();
      }
    }
  };

  // Check if ETL scan is still running using the backend endpoint
  const checkIfStillProcessing = async () => {
    try {
      const statusData = await getScanStatus();
      return statusData.is_scanning === true;
    } catch (error) {
      console.error('Failed to check processing status:', error);
      return false;
    }
  };

  // Start polling to check scan status every 5 seconds
  const startStatusPolling = () => {
    // Clear any existing interval
    if (window.etlPollingInterval) {
      clearInterval(window.etlPollingInterval);
    }

    // Poll every 5 seconds
    window.etlPollingInterval = setInterval(async () => {
      const stillProcessing = await checkIfStillProcessing();

      if (!stillProcessing) {
        console.log('✅ ETL scan completed!');
        cleanupScanState();

        // Refresh all data
        loadStats();
        loadPendingUpdates();
        loadProcessingJobs();
        loadProcessingJobs();
        loadKBDocuments();
        loadPendingCaseStudies();

        // Stop polling
        clearInterval(window.etlPollingInterval);
      }
    }, 5000); // 5 seconds
  };

  // Clean up scan state
  const cleanupScanState = () => {
    setScanLoading(false);
    localStorage.removeItem('etl_scan_started');

    if (window.etlPollingInterval) {
      clearInterval(window.etlPollingInterval);
    }
  };

  const handleTriggerScan = async () => {
    setScanLoading(true);

    // Save scan start time to localStorage
    localStorage.setItem('etl_scan_started', Date.now().toString());

    try {
      await triggerScan();
      // Don't set scanLoading to false here!
      // Let polling detect when it's done
      console.log('✅ ETL scan triggered, starting polling...');
      startStatusPolling();
    } catch (err) {
      alert(`ETL scan failed: ${err.message}`);
      cleanupScanState();
    }
  };

  const handleApprove = async (pendingUpdateId) => {
    if (!confirm("Are you sure you want to approve this update?")) return;

    setProcessingId(pendingUpdateId);
    try {
      await approvePendingUpdate(pendingUpdateId, adminComment || null);
      alert("Update approved successfully!");
      setAdminComment("");
      setSelectedPending(null);
    } catch (err) {
      alert(`Failed to approve: ${err.message}`);
    } finally {
      setProcessingId(null);
    }
  };

  const handleReject = async (pendingUpdateId) => {
    if (!confirm("Are you sure you want to reject this update?")) return;

    setProcessingId(pendingUpdateId);
    try {
      await rejectPendingUpdate(pendingUpdateId, adminComment || null);
      alert("Update rejected successfully!");
      setAdminComment("");
      setSelectedPending(null);
    } catch (err) {
      alert(`Failed to reject: ${err.message}`);
    } finally {
      setProcessingId(null);
    }
  };

  const handleApproveCaseStudy = async (pendingId) => {
    if (!confirm("Are you sure you want to approve this case study? It will be added to the Knowledge Base.")) return;

    setProcessingId(pendingId);
    try {
      await approveCaseStudy(pendingId, adminComment || null);
      alert("Case Study approved successfully!");
      setAdminComment("");
      setSelectedPending(null);
    } catch (err) {
      alert(`Failed to approve: ${err.message}`);
    } finally {
      setProcessingId(null);
    }
  };

  const handleRejectCaseStudy = async (pendingId) => {
    if (!confirm("Are you sure you want to reject and delete this case study?")) return;

    setProcessingId(pendingId);
    try {
      await rejectCaseStudy(pendingId, adminComment || null);
      alert("Case Study rejected successfully!");
      setAdminComment("");
      setSelectedPending(null);
    } catch (err) {
      alert(`Failed to reject: ${err.message}`);
    } finally {
      setProcessingId(null);
    }
  };

  const handleRefresh = () => {
    loadStats();
    if (activeTab === "pending") {
      loadPendingUpdates();
      loadPendingCaseStudies();
    }
    if (activeTab === "jobs") loadProcessingJobs();
    if (activeTab === "documents") loadKBDocuments();
  };

  const handleResetFailed = async () => {
    if (!confirm("This will reset all failed documents for reprocessing. Make sure Ollama is running! Continue?")) return;

    setResetLoading(true);
    try {
      const result = await resetFailedDocuments();
      alert(`Success! ${result.message}\n\nNow click "Trigger ETL Scan" to reprocess the documents.`);
    } catch (err) {
      alert(`Failed to reset documents: ${err.message}`);
    } finally {
      setResetLoading(false);
    }
  };

  // Check Presenton service health
  const checkPresentonHealth = async () => {
    try {
      const response = await fetch('/api/presenton/health');
      const data = await response.json();
      setPresentonStatus(data.status);
    } catch (error) {
      console.error('Failed to check Presenton health:', error);
      setPresentonStatus('unavailable');
    }
  };

  // Load projects for Presenton modal
  const loadProjectsForPresenton = async () => {
    setLoadingProjects(true);
    try {
      const response = await projectApi.getProjects();
      // Filter projects that have finalized scope by checking for finalized_scope.json file
      const projectsWithScope = response.data.filter(p => {
        // Check if project has a finalized_scope.json file
        return p.files && p.files.some(f => f.file_name === 'finalized_scope.json');
      });
      setProjects(projectsWithScope);
    } catch (error) {
      console.error('Failed to load projects:', error);
      alert('Failed to load projects');
    } finally {
      setLoadingProjects(false);
    }
  };

  // Handle Presenton generation
  const handleGenerateWithPresenton = async (projectId) => {
    setGeneratingPresenton(true);
    setLastGeneratedPresentation(null);
    try {
      const result = await presentonApi.generateWithPresenton(projectId);
      setLastGeneratedPresentation(result);
      // alert(`✅ Presentation generated successfully!\n\nClick OK to open in Presenton editor.`);
      // Open Presenton in new tab (might be blocked, so we show the link in UI too)
      window.open(result.edit_url, '_blank');
      setShowProjectSelector(false);
    } catch (error) {
      console.error('Presenton generation failed:', error);
      alert(`❌ Failed to generate presentation:\n${error.response?.data?.detail || error.message}`);
    } finally {
      setGeneratingPresenton(false);
    }
  };

  // Open project selector modal
  const openProjectSelector = () => {
    setShowProjectSelector(true);
    loadProjectsForPresenton();
  };

  // Helper function to check if a job failed recently (within last 24 hours)
  const getRecentFailedJobs = () => {
    const twentyFourHoursAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
    return processingJobs.filter(job => {
      if (job.status !== "failed") return false;
      const failedAt = job.completed_at || job.started_at;
      if (!failedAt) return true; // Include if no timestamp (safety)
      return new Date(failedAt) > twentyFourHoursAgo;
    });
  };



  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-extrabold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
            ETL Pipeline Admin
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Monitor and manage knowledge base document processing
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-primary to-accent text-white rounded-xl hover:shadow-lg transition-all duration-200"
          >
            <RefreshCcw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            onClick={handleTriggerScan}
            disabled={scanLoading}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-secondary to-orange-600 text-white rounded-xl hover:shadow-lg transition-all duration-200 disabled:opacity-70 disabled:cursor-not-allowed"
          >
            <Play className={`w-4 h-4 ${scanLoading ? "animate-pulse" : ""}`} />
            {scanLoading ? "Scanning..." : "Trigger ETL Scan"}
          </button>
        </div>
      </div>

      {/* Scanning Status Alert */}
      {scanLoading && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-4 flex items-start gap-3">
          <Clock className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5 animate-pulse" />
          <div>
            <p className="font-semibold text-blue-900 dark:text-blue-100">ETL Scan in Progress</p>
            <p className="text-sm text-blue-700 dark:text-blue-300">
              Processing knowledge base documents... You can navigate away and come back. The scan will continue running.
            </p>
          </div>
        </div>
      )}

      {/* Error Alert */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold text-red-900 dark:text-red-100">Error</p>
            <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
          </div>
        </div>
      )}



      {/* Presenton AI Presentation Studio Section */}
      <div className="bg-gradient-to-br from-purple-50 to-indigo-50 dark:from-purple-900/20 dark:to-indigo-900/20 rounded-2xl p-6 border border-purple-200 dark:border-purple-800 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-gradient-to-br from-purple-600 to-indigo-600">
              <Presentation className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                Presenton - AI Presentation Studio
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-300">
                Advanced AI presentation generator with templates and editing
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-3 h-3 rounded-full ${presentonStatus === 'available' ? 'bg-green-500 animate-pulse' : 'bg-red-500'
              }`} />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {presentonStatus === 'available' ? 'Running' : presentonStatus === 'checking' ? 'Checking...' : 'Offline'}
            </span>
          </div>
        </div>

        <p className="text-gray-700 dark:text-gray-300 mb-6">
          Create professional presentations with AI-powered content generation, custom templates,
          and a live editor. Generate presentations from your project scope data or start from scratch.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          {/* Open Presenton Studio */}
          <a
            href="http://localhost:5000"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-4 p-4 bg-white dark:bg-gray-800 rounded-xl border-2 border-purple-300 dark:border-purple-700 hover:border-purple-500 dark:hover:border-purple-500 hover:shadow-lg transition-all duration-200 group"
          >
            <div className="p-3 rounded-lg bg-purple-100 dark:bg-purple-900/30 group-hover:bg-purple-200 dark:group-hover:bg-purple-900/50 transition-colors">
              <ExternalLink className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                Open Presenton Studio
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Create presentations with templates & editor
              </p>
            </div>
          </a>

          {/* Generate from Project Scope */}
          <button
            onClick={openProjectSelector}
            disabled={presentonStatus !== 'available'}
            className="flex items-center gap-4 p-4 bg-white dark:bg-gray-800 rounded-xl border-2 border-indigo-300 dark:border-indigo-700 hover:border-indigo-500 dark:hover:border-indigo-500 hover:shadow-lg transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:border-indigo-300 dark:disabled:hover:border-indigo-700 group"
          >
            <div className="p-3 rounded-lg bg-indigo-100 dark:bg-indigo-900/30 group-hover:bg-indigo-200 dark:group-hover:bg-indigo-900/50 transition-colors">
              <FileText className="w-6 h-6 text-indigo-600 dark:text-indigo-400" />
            </div>
            <div className="flex-1 text-left">
              <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                Generate from Project Scope
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Use your finalized scope data
              </p>
            </div>
          </button>
        </div>

        {/* Features Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 bg-white/50 dark:bg-gray-800/50 rounded-lg px-3 py-2">
            <span className="text-lg">🎨</span>
            <span className="font-medium">Custom Templates</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 bg-white/50 dark:bg-gray-800/50 rounded-lg px-3 py-2">
            <span className="text-lg">✏️</span>
            <span className="font-medium">Live Editor</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 bg-white/50 dark:bg-gray-800/50 rounded-lg px-3 py-2">
            <span className="text-lg">📊</span>
            <span className="font-medium">Charts & Icons</span>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 bg-white/50 dark:bg-gray-800/50 rounded-lg px-3 py-2">
            <span className="text-lg">💾</span>
            <span className="font-medium">PPTX & PDF Export</span>
          </div>
        </div>

        {/* Success Alert for Generation */}
        {lastGeneratedPresentation && (
          <div className="mb-6 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl p-4 flex items-center justify-between animate-fade-in">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-6 h-6 text-green-600 dark:text-green-400" />
              <div>
                <h3 className="font-bold text-green-900 dark:text-green-100">Presentation Generated Successfully!</h3>
                <p className="text-sm text-green-700 dark:text-green-300">
                  Your presentation is ready. If it didn't open automatically, click the button to view it.
                </p>
              </div>
            </div>
            <a
              href={lastGeneratedPresentation.edit_url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors shadow-md"
            >
              <Presentation className="w-4 h-4" />
              Open Presentation
            </a>
          </div>
        )}

        {/* Offline Warning */}
        {presentonStatus === 'unavailable' && (
          <div className="mt-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3 flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
            <div className="text-sm">
              <p className="font-semibold text-yellow-900 dark:text-yellow-100">Presenton is offline</p>
              <p className="text-yellow-700 dark:text-yellow-300">
                Start Presenton with: <code className="bg-yellow-100 dark:bg-yellow-900/50 px-1 rounded">docker-compose up presenton</code>
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex gap-6">
          {[
            { id: "stats", label: "Overview", icon: TrendingUp },
            { id: "pending", label: "Pending Approvals", icon: Clock },
            { id: "jobs", label: "Processing Jobs", icon: FileText },
            { id: "documents", label: "KB Documents", icon: Database },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-3 font-medium transition-all duration-200 border-b-2 ${activeTab === tab.id
                ? "border-primary text-primary dark:border-dark-primary dark:text-dark-primary"
                : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="min-h-[400px]">
        {/* Stats Tab */}
        {activeTab === "stats" && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <StatCard
              title="Total Documents"
              value={stats?.total_documents || 0}
              icon={Database}
              color="blue"
            />
            <StatCard
              title="Vectorized"
              value={stats?.vectorized_documents || 0}
              icon={CheckCircle}
              color="green"
            />
            <StatCard
              title="Unvectorized"
              value={stats?.unvectorized_documents || 0}
              icon={AlertCircle}
              color="orange"
            />
            <StatCard
              title="Pending Approvals"
              value={stats?.pending_approvals || 0}
              icon={Clock}
              color="yellow"
            />
            <StatCard
              title="Completed Jobs"
              value={stats?.processing_jobs?.completed || 0}
              icon={CheckCircle}
              color="green"
            />
            <StatCard
              title="Failed Jobs"
              value={stats?.processing_jobs?.failed || 0}
              icon={XCircle}
              color="red"
            />
          </div>
        )}

        {/* Pending Approvals Tab - Consolidated */}
        {activeTab === "pending" && (
          <div className="space-y-4">
            {pendingUpdates.length === 0 && pendingCaseStudies.length === 0 ? (
              <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                <Clock className="w-16 h-16 mx-auto mb-4 opacity-30" />
                <p className="text-lg font-medium">No pending approvals</p>
                <p className="text-sm">All updates and case studies have been reviewed</p>
              </div>
            ) : (
              // Combined list of Pending Updates and Case Studies
              [
                // KB Updates
                ...pendingUpdates.map(u => ({ ...u, type: 'kb_update' })),
                // Case Studies (with safe fallback if not array)
                ...(Array.isArray(pendingCaseStudies) ? pendingCaseStudies : []).map(c => ({ ...c, type: 'case_study' }))
              ]
                .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
                .map((item) => (
                  <div
                    key={item.id}
                    className="bg-white dark:bg-dark-surface rounded-2xl p-6 border border-gray-200 dark:border-gray-700 shadow-sm"
                  >
                    {/* --- Header Difference based on Type --- */}
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex-1">
                        {item.type === 'kb_update' ? (
                          <>
                            <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-1">
                              {item.document.file_name}
                            </h3>
                            <p className="text-sm text-gray-600 dark:text-gray-400">
                              {item.document.blob_path}
                            </p>
                          </>
                        ) : (
                          <>
                            <div className="flex items-center gap-2 mb-1">
                              <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">
                                {item.client_name}
                              </h3>
                              {item.generated_by_llm && (
                                <span className="px-2 py-0.5 rounded text-xs bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300 font-medium">
                                  AI Generated
                                </span>
                              )}
                            </div>
                            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                              Project: {item.project_title}
                            </p>
                            <p className="text-sm text-gray-500 dark:text-gray-400">
                              {item.file_name}
                            </p>
                          </>
                        )}
                      </div>

                      {/* --- Badge Difference --- */}
                      {item.type === 'kb_update' ? (
                        <span
                          className={`px-3 py-1 rounded-full text-xs font-semibold ${item.update_type === "duplicate"
                            ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                            : item.update_type === "update"
                              ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400"
                              : "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                            }`}
                        >
                          {item.update_type.toUpperCase()}
                        </span>
                      ) : (
                        <span className="px-3 py-1 rounded-full text-xs font-semibold bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
                          CASE STUDY
                        </span>
                      )}
                    </div>

                    {/* --- Content Difference --- */}
                    {item.type === 'kb_update' ? (
                      <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">Similarity:</span>
                          <span className="ml-2 font-semibold text-gray-900 dark:text-gray-100">
                            {(item.similarity_score * 100).toFixed(1)}%
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-500 dark:text-gray-400">Created:</span>
                          <span className="ml-2 font-semibold text-gray-900 dark:text-gray-100">
                            {new Date(item.created_at).toLocaleDateString()}
                          </span>
                        </div>
                      </div>
                    ) : (
                      <div className="mb-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg p-4">
                        <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">Overview</h4>
                        <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-3">
                          {item.overview}
                        </p>
                        <div className="mt-3 grid grid-cols-2 gap-4">
                          <div>
                            <h4 className="text-xs font-semibold text-gray-500 uppercase">Solution</h4>
                            <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-2">{item.solution}</p>
                          </div>
                          <div>
                            <h4 className="text-xs font-semibold text-gray-500 uppercase">Impact</h4>
                            <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-2">{item.impact}</p>
                          </div>
                        </div>
                      </div>
                    )}

                    {item.type === 'kb_update' && (
                      <div className="mb-4">
                        <p className="text-sm text-gray-700 dark:text-gray-300 mb-2">
                          <strong>Reason:</strong> {item.reason}
                        </p>
                        {item.related_documents && item.related_documents.length > 0 && (
                          <details className="text-sm">
                            <summary className="cursor-pointer text-primary dark:text-dark-primary font-medium">
                              View {item.related_documents.length} similar document(s)
                            </summary>
                            <ul className="mt-2 ml-4 space-y-1">
                              {item.related_documents.map((doc, idx) => (
                                <li key={idx} className="text-gray-600 dark:text-gray-400">
                                  • {doc.file_name} ({(doc.similarity_score * 100).toFixed(1)}%)
                                </li>
                              ))}
                            </ul>
                          </details>
                        )}
                      </div>
                    )}

                    {/* --- Action Buttons (Shared Logic) --- */}
                    {selectedPending === item.id && (
                      <div className="mb-4">
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                          Admin Comment (optional)
                        </label>
                        <textarea
                          value={adminComment}
                          onChange={(e) => setAdminComment(e.target.value)}
                          placeholder="Add a comment about this decision..."
                          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100"
                          rows={2}
                        />
                      </div>
                    )}

                    <div className="flex items-center gap-3">
                      {selectedPending === item.id ? (
                        <>
                          <button
                            onClick={() => item.type === 'kb_update' ? handleApprove(item.id) : handleApproveCaseStudy(item.id)}
                            disabled={processingId === item.id}
                            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
                          >
                            <CheckCircle className="w-4 h-4" />
                            {processingId === item.id ? "Approving..." : "Confirm Approve"}
                          </button>
                          <button
                            onClick={() => item.type === 'kb_update' ? handleReject(item.id) : handleRejectCaseStudy(item.id)}
                            disabled={processingId === item.id}
                            className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                          >
                            <XCircle className="w-4 h-4" />
                            {processingId === item.id ? "Rejecting..." : "Confirm Reject"}
                          </button>
                          <button
                            onClick={() => {
                              setSelectedPending(null);
                              setAdminComment("");
                            }}
                            className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                          >
                            Cancel
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            onClick={() => setSelectedPending(item.id)}
                            className="flex items-center gap-2 px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-colors"
                          >
                            Review {item.type === 'case_study' ? 'Case Study' : ''}
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))
            )}
          </div>
        )}

        {/* Processing Jobs Tab */}
        {activeTab === "jobs" && (
          <div className="space-y-4">
            {/* Failed Documents Alert and Reset Button - Only show for recent failures (last 24 hours) */}
            {getRecentFailedJobs().length > 0 && (
              <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-xl p-4 flex items-start justify-between">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-orange-600 dark:text-orange-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="font-semibold text-orange-900 dark:text-orange-100">Failed Documents Detected</p>
                    <p className="text-sm text-orange-700 dark:text-orange-300 mt-1">
                      {getRecentFailedJobs().length} document(s) failed processing in the last 24 hours.
                      Make sure Ollama is running, then click "Reset & Retry" to reprocess them.
                    </p>
                  </div>
                </div>
                <button
                  onClick={handleResetFailed}
                  disabled={resetLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 transition-colors disabled:opacity-50 whitespace-nowrap"
                >
                  <RefreshCcw className={`w-4 h-4 ${resetLoading ? "animate-spin" : ""}`} />
                  {resetLoading ? "Resetting..." : "Reset & Retry"}
                </button>
              </div>
            )}

            <div className="overflow-x-auto">
              <table className="professional-table w-full">
                <thead>
                  <tr>
                    <th>Document</th>
                    <th>Status</th>
                    <th>Chunks</th>
                    <th>Vectors</th>
                    <th>Started</th>
                    <th>Completed</th>
                    <th>Error</th>
                  </tr>
                </thead>
                <tbody>
                  {processingJobs.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="text-center py-8 text-gray-500 dark:text-gray-400">
                        No processing jobs found
                      </td>
                    </tr>
                  ) : (
                    processingJobs.map((job) => (
                      <tr key={job.id}>
                        <td className="font-medium">{job.document?.file_name || "Unknown"}</td>
                        <td>
                          <span
                            className={`badge ${job.status === "completed"
                              ? "badge-success"
                              : job.status === "failed"
                                ? "badge-danger"
                                : job.status === "processing"
                                  ? "badge-warning"
                                  : "badge-info"
                              }`}
                          >
                            {job.status}
                          </span>
                        </td>
                        <td>{job.chunks_processed || 0}</td>
                        <td>{job.vectors_created || 0}</td>
                        <td className="text-sm text-gray-600 dark:text-gray-400">
                          {job.started_at ? new Date(job.started_at).toLocaleString() : "-"}
                        </td>
                        <td className="text-sm text-gray-600 dark:text-gray-400">
                          {job.completed_at ? new Date(job.completed_at).toLocaleString() : "-"}
                        </td>
                        <td className="text-sm text-red-600 dark:text-red-400">
                          {job.error_message || "-"}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* KB Documents Tab */}
        {activeTab === "documents" && (
          <div className="overflow-x-auto">
            <table className="professional-table w-full">
              <thead>
                <tr>
                  <th>File Name</th>
                  <th>Blob Path</th>
                  <th>Size</th>
                  <th>Vectorized</th>
                  <th>Vectors</th>
                  <th>Uploaded</th>
                  <th>Last Checked</th>
                </tr>
              </thead>
              <tbody>
                {kbDocuments.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-8 text-gray-500 dark:text-gray-400">
                      No KB documents found
                    </td>
                  </tr>
                ) : (
                  kbDocuments.map((doc) => (
                    <tr key={doc.id}>
                      <td className="font-medium">{doc.file_name}</td>
                      <td className="text-sm text-gray-600 dark:text-gray-400">{doc.blob_path}</td>
                      <td className="text-sm">{(doc.file_size / 1024).toFixed(1)} KB</td>
                      <td>
                        {doc.is_vectorized ? (
                          <CheckCircle className="w-5 h-5 text-green-600 dark:text-green-400" />
                        ) : (
                          <XCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
                        )}
                      </td>
                      <td>{doc.vector_count || 0}</td>
                      <td className="text-sm text-gray-600 dark:text-gray-400">
                        {doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : "-"}
                      </td>
                      <td className="text-sm text-gray-600 dark:text-gray-400">
                        {doc.last_checked ? new Date(doc.last_checked).toLocaleDateString() : "-"}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Project Selector Modal for Presenton */}
      {showProjectSelector && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowProjectSelector(false)}>
          <div className="bg-white dark:bg-dark-surface rounded-2xl p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                Select Project for Presenton
              </h2>
              <button
                onClick={() => setShowProjectSelector(false)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                <XCircle className="w-6 h-6" />
              </button>
            </div>

            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Choose a project with finalized scope to generate a presentation
            </p>

            {loadingProjects ? (
              <div className="text-center py-12">
                <RefreshCcw className="w-12 h-12 mx-auto mb-4 animate-spin text-primary" />
                <p className="text-gray-600 dark:text-gray-400">Loading projects...</p>
              </div>
            ) : projects.length === 0 ? (
              <div className="text-center py-12">
                <AlertCircle className="w-16 h-16 mx-auto mb-4 text-gray-400" />
                <p className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  No Projects Available
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  You need to finalize at least one project scope first
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {projects.map((project) => (
                  <button
                    key={project.id}
                    onClick={() => handleGenerateWithPresenton(project.id)}
                    disabled={generatingPresenton}
                    className="w-full text-left p-4 border-2 border-gray-200 dark:border-gray-700 rounded-xl hover:border-primary dark:hover:border-dark-primary hover:shadow-md transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900 dark:text-white mb-1">
                          {project.name}
                        </h3>
                        <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                          {project.domain || 'No domain specified'}
                        </p>
                      </div>
                      <Presentation className="w-6 h-6 text-primary dark:text-dark-primary flex-shrink-0 ml-4" />
                    </div>
                  </button>
                ))}
              </div>
            )}

            {generatingPresenton && (
              <div className="mt-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4 flex items-center gap-3">
                <RefreshCcw className="w-5 h-5 text-blue-600 dark:text-blue-400 animate-spin flex-shrink-0" />
                <div>
                  <p className="font-semibold text-blue-900 dark:text-blue-100">Generating presentation...</p>
                  <p className="text-sm text-blue-700 dark:text-blue-300">
                    This may take a moment. Please wait.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// Stat Card Component
function StatCard({ title, value, icon: Icon, color }) {
  const colorClasses = {
    blue: "from-blue-500 to-blue-600 dark:from-blue-400 dark:to-blue-500",
    green: "from-green-500 to-green-600 dark:from-green-400 dark:to-green-500",
    orange: "from-orange-500 to-orange-600 dark:from-orange-400 dark:to-orange-500",
    yellow: "from-yellow-500 to-yellow-600 dark:from-yellow-400 dark:to-yellow-500",
    red: "from-red-500 to-red-600 dark:from-red-400 dark:to-red-500",
  };

  return (
    <div className="bg-white dark:bg-dark-surface rounded-2xl p-6 border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide">
          {title}
        </h3>
        <div className={`p-2 rounded-xl bg-gradient-to-br ${colorClasses[color]}`}>
          <Icon className="w-5 h-5 text-white" />
        </div>
      </div>
      <p className="text-4xl font-extrabold text-gray-900 dark:text-gray-100">{value}</p>
    </div>
  );
}